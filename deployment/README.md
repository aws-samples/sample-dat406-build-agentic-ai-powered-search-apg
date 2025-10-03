# Deployment Scripts

This folder contains scripts for deploying and configuring the Blaize Bazaar application.

## Scripts

- `setup-all.sh` - Complete setup script for all components
- `setup-database-dat406.sh` - Database initialization and schema setup
- `setup-frontend.sh` - Frontend build and deployment
- `bootstrap-code-editor-dat406.sh` - Development environment setup
- `regenerate_titan_v2.py` - Regenerate embeddings using Amazon Titan
- `generate_mcp_config.py` - Generate MCP server configuration

## Usage

```bash
# Run complete setup
./setup-all.sh

# Setup database only
./setup-database-dat406.sh

# Setup frontend only
./setup-frontend.sh
```

## Prerequisites

- AWS credentials configured
- Aurora PostgreSQL cluster running
- Python 3.11+ installed
- Node.js 18+ installed
