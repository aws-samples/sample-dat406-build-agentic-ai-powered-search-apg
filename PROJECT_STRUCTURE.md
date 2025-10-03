# Project Structure

Production-ready organization for Blaize Bazaar - AI-Powered E-Commerce Platform

```
blaize-bazaar/
├── lab1/                       # Lab 1: Semantic Search (20 min)
│   ├── README.md              # Lab 1 guide
│   └── *.ipynb                # Jupyter notebook
│
├── lab2/                       # Lab 2: Full Application (80 min)
│   ├── README.md              # Lab 2 guide
│   ├── backend/               # FastAPI application
│   │   ├── agents/           # AI agents
│   │   ├── models/           # Data models
│   │   ├── services/         # Business logic
│   │   └── app.py            # Main app
│   ├── frontend/              # React application
│   │   ├── src/              # Source code
│   │   └── package.json      # Dependencies
│   ├── config/                # MCP configuration
│   └── data/                  # Sample data
│
├── data/                       # Shared sample data
│   └── amazon-products-sample.csv
│
├── deployment/                 # Setup scripts
│   ├── bootstrap-code-editor-dat406.sh
│   ├── setup-database-dat406.sh
│   ├── setup-all.sh
│   └── regenerate_titan_v2.py
│
├── docs/                       # Documentation
│   ├── notebooks/             # Additional notebooks
│   ├── CHAT_IMPLEMENTATION.md
│   ├── MCP_SETUP.md
│   └── CONTRIBUTING.md
│
├── README.md                   # Main documentation
├── WORKSHOP_GUIDE.md           # Workshop flow
├── PROJECT_STRUCTURE.md        # This file
└── LICENSE                     # MIT License

```

## Key Changes from Development to Production

### Removed
- ❌ Test files (`test_agents.py`, `test_agents.sh`)
- ❌ Development scripts (`check_db_embeddings.py`, `regenerate_embeddings.py`)
- ❌ Redundant root `backend/`, `frontend/`, `config/` folders
- ❌ Empty `scripts/` folder

### Reorganized
- ✅ All application code → `lab2/` (backend, frontend, config, data)
- ✅ Jupyter notebook → `lab1/`
- ✅ Setup scripts → `deployment/`
- ✅ Documentation → `docs/`
- ✅ Notebooks → `docs/notebooks/`

### Workshop Structure Benefits
1. **Clear lab separation** - Lab 1 (notebook) and Lab 2 (full app)
2. **No redundancy** - Single source of truth for each component
3. **Easy navigation** - Participants start in lab1/, then move to lab2/
4. **Clean codebase** - No test files or dev scripts
5. **Self-contained labs** - Each lab has everything needed

## Running the Workshop

```bash
# Lab 1: Jupyter Notebook
cd lab1
jupyter notebook

# Lab 2: Backend
cd lab2/backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000

# Lab 2: Frontend
cd lab2/frontend
npm install
npm run dev
```

## Environment Variables

- Lab 2 Backend: `lab2/backend/.env`
- Lab 2 Frontend: `lab2/frontend/.env`
- See `.env.example` files in each directory for required variables
