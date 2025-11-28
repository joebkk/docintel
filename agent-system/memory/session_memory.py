"""In-memory session management for short-term agent context."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path

from config import settings


@dataclass
class Message:
    """Represents a single message in conversation history."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class Session:
    """
    Represents an agent session with conversation history and state.

    Sessions provide short-term memory for ongoing conversations,
    allowing agents to maintain context across multiple interactions.
    """
    session_id: str
    user_id: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_messages(
        self,
        limit: Optional[int] = None,
        roles: Optional[List[str]] = None
    ) -> List[Message]:
        """
        Get messages from session.

        Args:
            limit: Max number of recent messages to return
            roles: Filter by message roles

        Returns:
            List of messages
        """
        messages = self.messages

        if roles:
            messages = [m for m in messages if m.role in roles]

        if limit:
            messages = messages[-limit:]

        return messages

    def get_context_window(
        self,
        max_length: int = 100000,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation context suitable for LLM input.

        Implements context compaction to fit within token limits.

        Args:
            max_length: Maximum total character length
            max_messages: Maximum number of messages

        Returns:
            List of message dicts with role and content
        """
        messages = self.messages

        if max_messages:
            messages = messages[-max_messages:]

        # Compact if needed
        total_length = sum(len(m.content) for m in messages)

        if total_length > max_length:
            # Strategy: Keep most recent messages, summarize older ones
            messages = self._compact_context(messages, max_length)

        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

    def _compact_context(
        self,
        messages: List[Message],
        max_length: int
    ) -> List[Message]:
        """
        Compact context to fit within length limit.

        Keeps recent messages, truncates older ones.
        """
        if not messages:
            return []

        # Always keep the most recent message
        result = [messages[-1]]
        current_length = len(messages[-1].content)

        # Add messages from most recent backwards
        for message in reversed(messages[:-1]):
            msg_length = len(message.content)

            if current_length + msg_length <= max_length:
                result.insert(0, message)
                current_length += msg_length
            else:
                # Truncate this message to fit
                remaining = max_length - current_length
                if remaining > 100:  # Only include if meaningful amount fits
                    truncated = Message(
                        role=message.role,
                        content=message.content[:remaining] + "...",
                        timestamp=message.timestamp
                    )
                    result.insert(0, truncated)
                break

        return result

    def update_state(self, key: str, value: Any):
        """Update session state."""
        self.state[key] = value
        self.updated_at = datetime.now()

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from session state."""
        return self.state.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [m.to_dict() for m in self.messages],
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            state=data.get("state", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {})
        )


class InMemorySessionService:
    """
    Session management service with in-memory storage and file persistence.

    Provides:
    - Session creation and retrieval
    - Conversation history management
    - State persistence
    - Context window management
    - Checkpoint/restore capabilities
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize session service.

        Args:
            storage_path: Directory for session persistence
        """
        self.sessions: Dict[str, Session] = {}
        self.storage_path = Path(storage_path or settings.session_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session.

        Args:
            session_id: Optional custom session ID
            user_id: Optional user identifier
            metadata: Optional metadata

        Returns:
            New Session instance
        """
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"

        session = Session(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )

        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.

        If not in memory, attempts to load from disk.

        Args:
            session_id: Session identifier

        Returns:
            Session if found, None otherwise
        """
        # Check memory first
        if session_id in self.sessions:
            return self.sessions[session_id]

        # Try loading from disk
        loaded = self.load_session(session_id)
        if loaded:
            self.sessions[session_id] = loaded
            return loaded

        return None

    def save_session(self, session: Session):
        """
        Persist session to disk.

        Args:
            session: Session to save
        """
        file_path = self.storage_path / f"{session.session_id}.json"

        with open(file_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def load_session(self, session_id: str) -> Optional[Session]:
        """
        Load session from disk.

        Args:
            session_id: Session identifier

        Returns:
            Session if found, None otherwise
        """
        file_path = self.storage_path / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return Session.from_dict(data)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str):
        """
        Delete session from memory and disk.

        Args:
            session_id: Session identifier
        """
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]

        # Remove from disk
        file_path = self.storage_path / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()

    def list_sessions(
        self,
        user_id: Optional[str] = None
    ) -> List[Session]:
        """
        List all sessions, optionally filtered by user.

        Args:
            user_id: Optional user filter

        Returns:
            List of sessions
        """
        # Load all sessions from disk
        for file_path in self.storage_path.glob("*.json"):
            session_id = file_path.stem
            if session_id not in self.sessions:
                session = self.load_session(session_id)
                if session:
                    self.sessions[session_id] = session

        sessions = list(self.sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    def create_checkpoint(self, session_id: str) -> str:
        """
        Create a checkpoint of current session state.

        Useful for long-running operations that can be paused/resumed.

        Args:
            session_id: Session identifier

        Returns:
            Checkpoint ID
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        checkpoint_id = f"{session_id}_checkpoint_{datetime.now().timestamp()}"
        checkpoint_path = self.storage_path / f"{checkpoint_id}.json"

        with open(checkpoint_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> Session:
        """
        Restore session from checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Restored session

        Raises:
            ValueError if checkpoint not found
        """
        checkpoint_path = self.storage_path / f"{checkpoint_id}.json"

        if not checkpoint_path.exists():
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        with open(checkpoint_path, "r") as f:
            data = json.load(f)

        session = Session.from_dict(data)
        self.sessions[session.session_id] = session

        return session
