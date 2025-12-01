/**
 * Script to seed MongoDB with test documents for RAG system
 *
 * Usage:
 *   node scripts/seed-test-documents.js
 *
 * Or with Docker:
 *   docker exec -i docintel-rag node /app/scripts/seed-test-documents.js
 */

const { MongoClient } = require('mongodb');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb+srv://sa_readwrite:IacTxXuqD7jL6P35@tds-prod-cluster.mteshe.mongodb.net/?retryWrites=true&w=majority&appName=tds-prod-cluster';
const MONGODB_DATABASE = process.env.MONGODB_DATABASE || 'docurepo_test';

const sampleDocuments = [
  {
    documentId: 'doc-001',
    title: 'Q3 2024 Portfolio Performance Report',
    text: `Executive Summary

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
- Fundraising for Fund III targeting $750M`,
    filename: 'Q3_2024_Portfolio_Report.pdf',
    source: 'internal',
    uploadedAt: new Date('2024-10-15'),
    metadata: {
      quarter: 'Q3',
      year: 2024,
      docType: 'portfolio-report',
      tags: ['performance', 'quarterly', 'portfolio']
    }
  },
  {
    documentId: 'doc-002',
    title: 'Due Diligence Report - AI Startup Investment',
    text: `Due Diligence Summary - AIVenture Corp

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
Proposed Terms: $10M Series B at $80M post-money valuation`,
    filename: 'AIVenture_DD_Report.pdf',
    source: 'deals',
    uploadedAt: new Date('2024-11-01'),
    metadata: {
      company: 'AIVenture Corp',
      docType: 'due-diligence',
      stage: 'Series B',
      tags: ['ai', 'enterprise', 'saas']
    }
  },
  {
    documentId: 'doc-003',
    title: 'LP Update - November 2024',
    text: `Dear Limited Partners,

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
Fund Management Team`,
    filename: 'LP_Update_Nov_2024.pdf',
    source: 'investor-relations',
    uploadedAt: new Date('2024-11-20'),
    metadata: {
      month: 'November',
      year: 2024,
      docType: 'lp-update',
      tags: ['investor-relations', 'performance', 'exits']
    }
  }
];

async function seedDocuments() {
  const client = new MongoClient(MONGODB_URI);

  try {
    console.log('Connecting to MongoDB...');
    await client.connect();
    console.log('Connected successfully');

    const db = client.db(MONGODB_DATABASE);
    const collection = db.collection('doc_pages');

    // Clear existing test docs
    console.log('Clearing old documents...');
    await collection.deleteMany({ documentId: { $in: sampleDocuments.map(d => d.documentId) } });

    // Insert samples
    console.log('Inserting documents...');
    const result = await collection.insertMany(sampleDocuments);
    console.log(`Inserted ${result.insertedCount} documents`);

    // Show what we inserted
    console.log('\nInserted:');
    sampleDocuments.forEach((doc, idx) => {
      console.log(`  ${idx + 1}. ${doc.title} (${doc.documentId})`);
    });

    console.log('\nDone. Try:');
    console.log('  curl -X POST http://localhost:3000/api/unified-search \\');
    console.log('    -H "Content-Type: application/json" \\');
    console.log('    -d \'{"query": "portfolio performance", "mode": "hybrid"}\'');

  } catch (error) {
    console.error('Error:', error.message);
    // TODO: add better error handling here
    process.exit(1);
  } finally {
    await client.close();
    console.log('Disconnected');
  }
}

// Run if called directly
if (require.main === module) {
  seedDocuments();
}

module.exports = { seedDocuments };
