# DAT406 Workshop Guide - Build Agentic AI-Powered Search with Amazon Aurora

**AWS re:Invent 2025**  
**Level**: 400 (Expert)  
**Duration**: 2 hours

## 🎯 Workshop Overview

Learn to build production-grade AI-powered search using Amazon Aurora PostgreSQL with pgvector, Amazon Bedrock, and modern web technologies. This hands-on workshop covers semantic search, vector embeddings, and multi-agent AI systems.

## 📋 Prerequisites

Participants should have:
- AWS Account with access to Aurora and Bedrock
- Basic Python and SQL knowledge
- Familiarity with REST APIs
- Basic understanding of React (for Lab 2)

## 🏗️ Workshop Architecture

```
Lab 1: Foundation                Lab 2: Full Application
┌──────────────────┐            ┌──────────────────────┐
│  Jupyter Notebook│            │   React Frontend     │
│  • Data Loading  │            │   • AI Chat UI       │
│  • Embeddings    │            │   • Search Interface │
│  • pgvector      │            └──────────┬───────────┘
└────────┬─────────┘                       │
         │                                 │
         ▼                                 ▼
┌─────────────────────────────────────────────────┐
│         Amazon Aurora PostgreSQL + pgvector      │
│         • 21,704 Products with Embeddings        │
│         • HNSW Index for Fast Search             │
└─────────────────────────────────────────────────┘
                         ▲
                         │
                ┌────────┴────────┐
                │ Amazon Bedrock  │
                │ • Cohere Embed  │
                │ • Claude 3.7    │
                └─────────────────┘
```

## 📚 Workshop Structure

### Lab 1: Building AI-Powered Semantic Search (20 min)
**Location**: `lab1/`

**What You'll Build**:
- Aurora PostgreSQL database with pgvector
- Product catalog with 21,704 items
- Vector embeddings using Bedrock
- HNSW indexes for fast similarity search
- Semantic search queries

**Key Learnings**:
- Vector embeddings and semantic similarity
- pgvector extension and operators
- HNSW index optimization
- Cosine distance calculations

**Deliverables**:
- ✅ Database with embeddings
- ✅ Working semantic search queries
- ✅ Performance benchmarks

---

### Lab 2: Building Blaize Bazaar Application (80 min)
**Location**: `lab2/`

**What You'll Build**:
- FastAPI backend with semantic search API
- React frontend with AI chat assistant
- Multi-agent system (inventory, pricing, recommendations)
- Model Context Protocol integration
- Real-time autocomplete and filters

**Key Learnings**:
- Building production APIs with FastAPI
- Integrating Bedrock for conversational AI
- Multi-agent architectures
- Modern React development
- MCP for database access

**Deliverables**:
- ✅ Full-stack e-commerce application
- ✅ AI chat assistant
- ✅ Multi-agent system
- ✅ Production-ready codebase

## 🚀 Getting Started

### For Workshop Participants

Your Cloud9/VSCode environment has been pre-configured with:
- ✅ Python 3.11+ and Node.js 18+
- ✅ AWS credentials
- ✅ Aurora PostgreSQL cluster
- ✅ This repository cloned

**Start with Lab 1**:
```bash
cd lab1
jupyter notebook
```

### For Self-Paced Learning

1. **Clone Repository**:
```bash
git clone https://github.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg.git
cd sample-dat406-build-agentic-ai-powered-search-apg
```

2. **Setup Infrastructure**:
```bash
cd deployment
./setup-database-dat406.sh
```

3. **Start Lab 1**:
```bash
cd ../lab1
jupyter notebook
```

## 📖 Workshop Flow

### Introduction (20 min)
- **0:00-0:20** - Workshop overview, architecture, and setup

### Lab 1: Semantic Search Foundation (20 min)
- **0:20-0:30** - Load data and generate embeddings
- **0:30-0:40** - Create indexes and test queries

### Lab 2: Full Application (80 min)
- **0:40-1:00** - Backend setup and API development
- **1:00-1:20** - Frontend setup and UI components
- **1:20-1:40** - AI chat assistant integration
- **1:40-2:00** - Multi-agent system and wrap-up

## 🎓 Learning Outcomes

After completing this workshop, you will be able to:

1. **Implement Semantic Search**
   - Generate vector embeddings with Bedrock
   - Use pgvector for similarity search
   - Optimize with HNSW indexes

2. **Build AI Applications**
   - Create conversational AI with Claude
   - Implement multi-agent systems
   - Use MCP for database access

3. **Deploy Production Systems**
   - Build scalable FastAPI backends
   - Create modern React frontends
   - Implement real-time features

4. **Optimize Performance**
   - Index strategies for vector search
   - Caching and query optimization
   - Batch processing for embeddings

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **psycopg3** - PostgreSQL driver
- **boto3** - AWS SDK
- **Strands SDK** - Multi-agent framework

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling

### AWS Services
- **Aurora PostgreSQL** - Database with pgvector
- **Amazon Bedrock** - AI models (Cohere, Claude)
- **Secrets Manager** - Credential management
- **CloudFormation** - Infrastructure as code

## 📊 Workshop Metrics

Expected performance after completion:
- **Search Latency**: 50-150ms
- **Similarity Accuracy**: 60-95%
- **Database Size**: 21,704 products
- **Vector Dimensions**: 1024
- **Concurrent Users**: 100+

## 🐛 Common Issues

### Issue: Bedrock Access Denied
**Solution**: Enable models in Bedrock console (us-west-2)

### Issue: Database Connection Failed
**Solution**: Check security group allows port 5432

### Issue: Slow Embedding Generation
**Solution**: Use batch processing (100 items/batch)

### Issue: Frontend Won't Start
**Solution**: Verify Node.js 18+ and run `npm install`

## 📚 Additional Resources

- [Workshop Slides](./docs/DAT406-Slides.pdf)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Amazon Bedrock Guide](https://docs.aws.amazon.com/bedrock/)
- [Strands SDK](https://github.com/awslabs/strands)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🎉 Post-Workshop

### Take Home
- Complete source code in this repository
- CloudFormation templates in `deployment/`
- Documentation in `docs/`
- Sample data in `data/`

### Next Steps
1. Deploy to production AWS account
2. Customize for your use case
3. Add more AI agents
4. Integrate with existing systems

### Share Your Work
- Tweet with #AWSreInvent #DAT406
- Share on LinkedIn
- Contribute improvements via PR

## 👥 Support

- **During Workshop**: Ask instructors or TAs
- **After Workshop**: Open GitHub issues
- **AWS Support**: Contact your AWS account team

## 📄 License

This workshop content is licensed under MIT License. See [LICENSE](./LICENSE) file.

---

**Built with ❤️ by AWS for re:Invent 2025**

**Workshop Code**: DAT406  
**Title**: Build Agentic AI-Powered Search with Amazon Aurora  
**Instructor**: Shayon Sanyal, AWS Solutions Architect
