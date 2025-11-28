"""MongoDB Memory Bank for long-term agent memory and knowledge persistence."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection

from config import settings


@dataclass
class MemoryEntry:
    """
    Represents a single memory entry in the Memory Bank.

    Memory entries store important information, insights, or facts
    that agents should remember across sessions.
    """
    entry_id: str
    session_id: Optional[str]
    user_id: Optional[str]
    memory_type: str  # "fact", "insight", "preference", "task", "conversation"
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "entry_id": self.entry_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "context": self.context,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from MongoDB document."""
        return cls(
            entry_id=data["entry_id"],
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            memory_type=data["memory_type"],
            content=data["content"],
            context=data.get("context", {}),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


class MemoryBank:
    """
    MongoDB-backed long-term memory system for agents.

    The Memory Bank provides:
    - Persistent storage of important information
    - Retrieval by session, user, type, or tags
    - Importance-based filtering
    - Access tracking for memory importance scoring
    - Memory consolidation and pruning
    """

    def __init__(
        self,
        mongodb_uri: Optional[str] = None,
        database: Optional[str] = None,
        collection: Optional[str] = None
    ):
        """
        Initialize Memory Bank.

        Args:
            mongodb_uri: MongoDB connection string
            database: Database name
            collection: Collection name for memories
        """
        self.mongodb_uri = mongodb_uri or settings.mongodb_uri
        self.database_name = database or settings.mongodb_database
        self.collection_name = collection or settings.memory_bank_collection

        self.client: Optional[MongoClient] = None
        self.collection: Optional[Collection] = None

        self._connect()
        self._ensure_indexes()

    def _connect(self):
        """Establish MongoDB connection."""
        try:
            self.client = MongoClient(self.mongodb_uri)
            db = self.client[self.database_name]
            self.collection = db[self.collection_name]
        except Exception as e:
            raise RuntimeError(f"Failed to connect to MongoDB: {e}")

    def _ensure_indexes(self):
        """Create necessary indexes for efficient queries."""
        if self.collection is None:
            return

        # Index on entry_id for fast lookups
        self.collection.create_index("entry_id", unique=True)

        # Index on session_id for session-based retrieval
        self.collection.create_index("session_id")

        # Index on user_id for user-based retrieval
        self.collection.create_index("user_id")

        # Index on memory_type for type-based filtering
        self.collection.create_index("memory_type")

        # Index on tags for tag-based search
        self.collection.create_index("tags")

        # Compound index for importance-based queries
        self.collection.create_index([
            ("importance", DESCENDING),
            ("created_at", DESCENDING)
        ])

    def store_memory(
        self,
        content: str,
        memory_type: str = "fact",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """
        Store a new memory in the Memory Bank.

        Args:
            content: Memory content
            memory_type: Type of memory (fact, insight, preference, task, conversation)
            session_id: Associated session
            user_id: Associated user
            context: Additional context
            importance: Importance score (0.0 to 1.0)
            tags: Tags for categorization
            metadata: Additional metadata

        Returns:
            Created MemoryEntry
        """
        entry_id = f"mem_{datetime.now().timestamp()}_{hash(content) % 10000}"

        memory = MemoryEntry(
            entry_id=entry_id,
            session_id=session_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            context=context or {},
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )

        self.collection.insert_one(memory.to_dict())
        return memory

    def retrieve_memories(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_importance: Optional[float] = None,
        limit: int = 10,
        sort_by: str = "created_at"
    ) -> List[MemoryEntry]:
        """
        Retrieve memories based on filters.

        Args:
            session_id: Filter by session
            user_id: Filter by user
            memory_type: Filter by type
            tags: Filter by tags (any match)
            min_importance: Minimum importance threshold
            limit: Maximum number of results
            sort_by: Sort field (created_at, importance, access_count)

        Returns:
            List of matching MemoryEntry objects
        """
        query = {}

        if session_id:
            query["session_id"] = session_id

        if user_id:
            query["user_id"] = user_id

        if memory_type:
            query["memory_type"] = memory_type

        if tags:
            query["tags"] = {"$in": tags}

        if min_importance is not None:
            query["importance"] = {"$gte": min_importance}

        # Determine sort order
        sort_field = sort_by
        sort_order = DESCENDING

        if sort_by == "created_at":
            sort_field = "created_at"
        elif sort_by == "importance":
            sort_field = "importance"
        elif sort_by == "access_count":
            sort_field = "access_count"

        results = self.collection.find(query).sort(sort_field, sort_order).limit(limit)

        memories = [MemoryEntry.from_dict(doc) for doc in results]

        # Update access tracking
        for memory in memories:
            self._record_access(memory.entry_id)

        return memories

    def search_memories(
        self,
        search_text: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Search memories by text content.

        Args:
            search_text: Text to search for
            user_id: Optional user filter
            limit: Maximum results

        Returns:
            List of matching memories
        """
        query = {"content": {"$regex": search_text, "$options": "i"}}

        if user_id:
            query["user_id"] = user_id

        results = self.collection.find(query).sort("importance", DESCENDING).limit(limit)

        memories = [MemoryEntry.from_dict(doc) for doc in results]

        for memory in memories:
            self._record_access(memory.entry_id)

        return memories

    def update_memory(
        self,
        entry_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a memory entry.

        Args:
            entry_id: Memory entry ID
            updates: Fields to update

        Returns:
            True if updated, False if not found
        """
        # Don't allow updating entry_id
        updates.pop("entry_id", None)

        result = self.collection.update_one(
            {"entry_id": entry_id},
            {"$set": updates}
        )

        return result.modified_count > 0

    def delete_memory(self, entry_id: str) -> bool:
        """
        Delete a memory entry.

        Args:
            entry_id: Memory entry ID

        Returns:
            True if deleted, False if not found
        """
        result = self.collection.delete_one({"entry_id": entry_id})
        return result.deleted_count > 0

    def _record_access(self, entry_id: str):
        """Record that a memory was accessed."""
        self.collection.update_one(
            {"entry_id": entry_id},
            {
                "$inc": {"access_count": 1},
                "$set": {"last_accessed": datetime.now().isoformat()}
            }
        )

    def consolidate_memories(
        self,
        user_id: str,
        min_importance: float = 0.7,
        max_memories: int = 100
    ):
        """
        Consolidate memories by removing low-importance, rarely accessed ones.

        This helps prevent memory bloat and keeps only the most relevant information.

        Args:
            user_id: User whose memories to consolidate
            min_importance: Keep memories above this importance
            max_memories: Maximum number of memories to keep
        """
        # Get all user memories sorted by composite score
        all_memories = list(self.collection.find({"user_id": user_id}))

        # Calculate composite score (importance + access frequency)
        for memory in all_memories:
            importance = memory.get("importance", 0.5)
            access_count = memory.get("access_count", 0)

            # Normalize access count (assume max of 100 accesses is top score)
            access_score = min(access_count / 100, 1.0)

            # Weighted composite: 70% importance, 30% access
            memory["_composite_score"] = (importance * 0.7) + (access_score * 0.3)

        # Sort by composite score
        all_memories.sort(key=lambda m: m["_composite_score"], reverse=True)

        # Keep top memories and high-importance ones
        to_keep = set()

        # Keep top N by composite score
        for memory in all_memories[:max_memories]:
            to_keep.add(memory["entry_id"])

        # Also keep all high-importance memories
        for memory in all_memories:
            if memory.get("importance", 0) >= min_importance:
                to_keep.add(memory["entry_id"])

        # Delete memories not in keep set
        to_delete = [
            m["entry_id"] for m in all_memories
            if m["entry_id"] not in to_keep
        ]

        if to_delete:
            self.collection.delete_many({"entry_id": {"$in": to_delete}})

        return len(to_delete)

    def get_memory_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about stored memories.

        Args:
            user_id: Optional user filter

        Returns:
            Dict with memory statistics
        """
        query = {}
        if user_id:
            query["user_id"] = user_id

        total = self.collection.count_documents(query)

        # Count by type
        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$memory_type", "count": {"$sum": 1}}}
        ]

        type_counts = {
            doc["_id"]: doc["count"]
            for doc in self.collection.aggregate(pipeline)
        }

        # Average importance
        avg_pipeline = [
            {"$match": query},
            {"$group": {"_id": None, "avg_importance": {"$avg": "$importance"}}}
        ]

        avg_result = list(self.collection.aggregate(avg_pipeline))
        avg_importance = avg_result[0]["avg_importance"] if avg_result else 0.0

        return {
            "total_memories": total,
            "by_type": type_counts,
            "average_importance": round(avg_importance, 3)
        }

    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
