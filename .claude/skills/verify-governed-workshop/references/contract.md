# Flagship contract

## Title

Build governed agentic AI search with Aurora, RDS, & Bedrock AgentCore

## Abstract

Build a governed agentic AI search application with Amazon Aurora PostgreSQL
and Amazon Bedrock AgentCore. Explore a retail shopping scenario where a
Strands SDK dispatcher routes shoppers to specialist agents. Aurora powers
hybrid search with PostgreSQL full-text search for lexical retrieval, pgvector
for semantic retrieval, and Cohere Rerank for relevance ranking, while
managing inventory, orders, customer records, and a queryable JSONB audit
ledger. AgentCore Runtime, Memory, Gateway, and Policy orchestrate agents,
preserve context, expose tools, and apply Cedar authorization to sensitive
actions. Leave with reusable patterns for auditable, policy-aware agentic
search applications.

## Required evidence map

| Contract claim | Minimum evidence |
|---|---|
| Strands dispatcher | One shopper turn routes to one named specialist |
| PostgreSQL full-text search | Lexical query or plan over the catalog |
| pgvector semantic retrieval | Vector query using the catalog embedding |
| Cohere Rerank | Comparison output names the configured rerank model |
| Inventory and orders | Aurora rows plus a tool result grounded in them |
| Customer records and memory | Named source and persona-scoped result |
| JSONB audit ledger | Queryable `pellier.tool_audit` row |
| AgentCore Runtime | Managed invocation receipt or trace |
| AgentCore Memory | Live source status and ordered session readback |
| AgentCore Gateway | Gateway receipt with caller-bound request |
| AgentCore Policy | Cedar ALLOW/DENY decision |
| Denied action did not execute | DENY receipt plus verified row absence |

## Required path

1. Core Lab 1: Build and Trace
2. Core Lab 2: Measure Retrieval
3. Core Lab 3: Query Evidence
4. Core Lab 4: Enforce Policy
