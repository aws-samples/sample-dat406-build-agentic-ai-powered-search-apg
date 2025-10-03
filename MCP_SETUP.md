# Aurora PostgreSQL MCP Server Setup

This configuration enables AI assistants to interact with your Aurora PostgreSQL database using the Model Context Protocol (MCP).

## Configuration

The MCP server is configured in `mcp-server-config.json` to connect to your Aurora PostgreSQL cluster with pgvector support.

### Database Details
- **Host**: apgpg-pgvector.cluster-chygmprofdnr.us-west-2.rds.amazonaws.com
- **Database**: postgres
- **Schema**: bedrock_integration
- **Table**: product_catalog (21,704 products)
- **Vector Dimensions**: 1024 (Cohere Embed English v3)

## Setup Instructions

### For Amazon Q Developer (VS Code/IDE)

1. Copy the MCP configuration to your Amazon Q settings:
   ```bash
   # macOS/Linux
   mkdir -p ~/.aws/amazonq/
   cp mcp-server-config.json ~/.aws/amazonq/mcp-servers.json
   ```

2. Restart your IDE to load the MCP server

3. The Aurora PostgreSQL database will now be available to Amazon Q for queries

### For Claude Desktop

1. Add to your Claude Desktop config:
   ```bash
   # macOS
   code ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. Merge the contents of `mcp-server-config.json` into your config

3. Restart Claude Desktop

## Available Capabilities

Once connected, you can ask the AI assistant to:

- **Query products**: "Show me all Bluetooth headphones with 5-star ratings"
- **Analyze data**: "What's the average price by category?"
- **Vector search**: "Find products similar to 'wireless earbuds' using embeddings"
- **Schema inspection**: "Describe the product_catalog table structure"
- **Aggregations**: "Show top 10 most reviewed products"

## Example Queries

```sql
-- Semantic search using pgvector
SELECT product_description, stars, price, 
       1 - (embedding <=> query_embedding) as similarity
FROM bedrock_integration.product_catalog
WHERE 1 - (embedding <=> query_embedding) > 0.6
ORDER BY embedding <=> query_embedding
LIMIT 10;

-- Category analysis
SELECT category_name, COUNT(*), AVG(price), AVG(stars)
FROM bedrock_integration.product_catalog
GROUP BY category_name
ORDER BY COUNT(*) DESC;
```

## Security Notes

- The connection string includes credentials - keep this file secure
- Consider using IAM authentication for production
- Restrict database user permissions to read-only if possible

## Troubleshooting

If the MCP server fails to connect:
1. Verify security group allows connections from your IP
2. Check that the Aurora cluster is running
3. Ensure Node.js is installed (required for npx)
4. Test connection manually: `psql postgresql://postgres:brVJ3SNrNtw9VEnG@apgpg-pgvector.cluster-chygmprofdnr.us-west-2.rds.amazonaws.com:5432/postgres`
