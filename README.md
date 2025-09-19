# DAT406 - Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL

This repository contains the complete code for the DAT406 workshop, where you'll build a production-ready e-commerce application with AI-powered search capabilities using Aurora PostgreSQL with pgvector.

## 🎯 Workshop Overview

Build a real-world application featuring:
- 🔍 Semantic search through 21K+ Amazon products
- 📚 RAG (Retrieval-Augmented Generation) pipeline
- 🤖 Multi-agent orchestration
- ⚡ Sub-20ms query latency with pgvector

## 📁 Repository Structure

```
├── frontend/          # React + Vite application
├── backend/           # FastAPI backend server
├── scripts/           # Database setup and utility scripts
├── data/              # Sample product data
├── workshop/          # Workshop instructions and labs
└── cloudformation/    # Infrastructure as Code templates
```

## 🚀 Quick Start

### For Workshop Participants

Your environment is pre-configured. Simply run:

```bash
cd /workshop
./check_status.sh
```

Access the app at: `https://YOUR_CLOUDFRONT_URL/app/`

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg.git
cd sample-dat406-build-agentic-ai-powered-search-apg
```

2. Setup frontend:
```bash
cd frontend
npm install
npm run dev
```

3. Setup backend:
```bash
cd backend
pip install -r requirements.txt
python app.py
```

## 📚 Workshop Modules

1. **Vector Search Fundamentals** - Implement semantic search with pgvector
2. **RAG Pipeline** - Build retrieval-augmented generation
3. **AI Agents** - Create intelligent shopping assistants
4. **Performance Optimization** - Tune for production workloads

## 🛠 Technologies Used

- **Frontend**: React, Vite, Tailwind CSS
- **Backend**: FastAPI, Python
- **Database**: Aurora PostgreSQL with pgvector
- **AI/ML**: Amazon Bedrock (Titan, Claude)
- **Infrastructure**: AWS CloudFormation

## 📖 Documentation

See the [workshop guide](workshop/README.md) for detailed instructions.

## 📄 License

This project is licensed under the MIT-0 License. See the LICENSE file for details.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.