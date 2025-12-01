#!/usr/bin/env python3
"""
Script to seed MongoDB with test documents for RAG system

Usage:
    python scripts/seed_test_documents.py
"""

import os
from datetime import datetime
from pymongo import MongoClient
from typing import List, Dict

# MongoDB connection details
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://sa_readwrite:IacTxXuqD7jL6P35@tds-prod-cluster.mteshe.mongodb.net/?retryWrites=true&w=majority&appName=tds-prod-cluster')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'docurepo_test')

sample_documents: List[Dict] = [
    {
        'documentId': 'doc-001',
        'title': 'Q3 2024 Portfolio Performance Report',
        'content': """Executive Summary

Q3 2024 showed strong performance across our portfolio with a 15% IRR.
Key highlights include:

- Total AUM: $500M (up from $450M in Q2)
- Portfolio Companies: 12 active investments
- Exits: 2 successful exits generating 3.2x MOIC
- New Investments: 1 Series B in fintech sector

Portfolio Performance:
- Top Performer: TechCo Inc. - 45% revenue growth YoY
- Underperformer: RetailVenture - flat growth, restructuring plan initiated

Market Outlook:
The fintech and healthcare sectors continue to show strong momentum.
We are actively sourcing deals in AI/ML enterprise software space.

Next Quarter Focus:
- Complete Series C for HealthTech startup
- Exit planning for 2 mature portfolio companies
- Fundraising for Fund III targeting $750M""",
        'filename': 'Q3_2024_Portfolio_Report.pdf',
        'source': 'internal',
        'uploadedAt': datetime(2024, 10, 15),
        'metadata': {
            'quarter': 'Q3',
            'year': 2024,
            'docType': 'portfolio-report',
            'tags': ['performance', 'quarterly', 'portfolio']
        }
    },
    {
        'documentId': 'doc-002',
        'title': 'Due Diligence Report - AI Startup Investment',
        'content': """Due Diligence Summary - AIVenture Corp

Investment Thesis:
AIVenture is building next-generation enterprise AI infrastructure targeting
$50B market opportunity in ML operations.

Key Findings:

Financial Metrics:
- ARR: $5M (growing 200% YoY)
- Gross Margin: 75%
- CAC Payback: 8 months
- NDR: 130%

Team Assessment:
- CEO: Former Google AI lead with 2 successful exits
- CTO: Published researcher, 50+ patents
- Team Size: 45 employees, 60% engineering

Technology:
- Proprietary ML optimization algorithms
- 10 granted patents, 15 pending
- Strong moat in model compression technology

Market Position:
- 3 Fortune 500 customers
- Partnership with AWS and Azure
- Competing with Databricks and Scale AI

Risks:
- High customer concentration (top 3 = 70% revenue)
- Competitive market with well-funded players
- Key person dependency on CTO

Recommendation: INVEST
Proposed Terms: $10M Series B at $80M post-money valuation""",
        'filename': 'AIVenture_DD_Report.pdf',
        'source': 'deals',
        'uploadedAt': datetime(2024, 11, 1),
        'metadata': {
            'company': 'AIVenture Corp',
            'docType': 'due-diligence',
            'stage': 'Series B',
            'tags': ['ai', 'enterprise', 'saas']
        }
    },
    {
        'documentId': 'doc-003',
        'title': 'LP Update - November 2024',
        'content': """Dear Limited Partners,

November 2024 Update

Fund Performance:
- Fund II: 25% IRR since inception (2020)
- Current NAV: $450M (on $300M committed capital)
- DPI: 0.4x
- TVPI: 1.5x

Recent Activity:

Exit: RetailTech Acquisition
We successfully exited RetailTech for $50M (3.5x MOIC) via acquisition
by Amazon. This represents our third exit in 2024.

New Investment: HealthAI Series A
Deployed $8M in HealthAI's Series A round. Company uses AI for medical
imaging diagnosis and has FDA clearance for 3 products.

Portfolio Updates:
- FinTech Co: Raised $30M Series C led by Sequoia
- DataPlatform: Achieved profitability, exploring strategic M&A
- CloudSec: Signed partnership with Microsoft Azure

Market Commentary:
Despite macro headwinds, enterprise software remains resilient.
We are seeing increased M&A activity and strong valuations for
profitable SaaS companies.

Upcoming Events:
- Annual LP Meeting: January 15, 2025
- Portfolio Company Day: February 20, 2025

Best regards,
Fund Management Team""",
        'filename': 'LP_Update_Nov_2024.pdf',
        'source': 'investor-relations',
        'uploadedAt': datetime(2024, 11, 20),
        'metadata': {
            'month': 'November',
            'year': 2024,
            'docType': 'lp-update',
            'tags': ['investor-relations', 'performance', 'exits']
        }
    }
]


def seed_documents():
    """Seed MongoDB with test documents"""

    print('🔌 Connecting to MongoDB...')
    client = MongoClient(MONGODB_URI)

    try:
        # Test connection
        client.admin.command('ping')
        print('✅ Connected to MongoDB Atlas')

        db = client[MONGODB_DATABASE]
        collection = db['doc_pages']

        # Clear existing test documents (optional)
        print('\n🗑️  Clearing existing test documents...')
        doc_ids = [doc['documentId'] for doc in sample_documents]
        result = collection.delete_many({'documentId': {'$in': doc_ids}})
        print(f'   Deleted {result.deleted_count} existing documents')

        # Insert sample documents
        print('\n📝 Inserting sample documents...')
        result = collection.insert_many(sample_documents)
        print(f'✅ Inserted {len(result.inserted_ids)} documents')

        # Display inserted documents
        print('\n📄 Inserted Documents:')
        for idx, doc in enumerate(sample_documents, 1):
            print(f'\n{idx}. {doc["title"]}')
            print(f'   ID: {doc["documentId"]}')
            print(f'   Type: {doc["metadata"]["docType"]}')
            print(f'   File: {doc["filename"]}')

        # Verify documents are searchable
        print('\n🔍 Verifying documents...')
        count = collection.count_documents({})
        print(f'   Total documents in collection: {count}')

        print('\n🎉 Seeding complete!')
        print('\n💡 Next steps:')
        print('   1. Test lexical search:')
        print('      curl -X POST http://localhost:3000/api/unified-search \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"query": "portfolio performance", "mode": "lexical"}\'')
        print('\n   2. Test agent query:')
        print('      curl -X POST http://localhost:8000/query \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"query": "What were the Q3 2024 results?", "session_id": "test-123"}\'')

    except Exception as error:
        print(f'❌ Error: {error}')
        raise
    finally:
        client.close()
        print('\n🔌 Disconnected from MongoDB')


if __name__ == '__main__':
    seed_documents()
