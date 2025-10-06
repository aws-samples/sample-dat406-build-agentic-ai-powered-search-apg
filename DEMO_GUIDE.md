# 🎯 Workshop Demo Guide - Interleaved Thinking

## Quick Demo Flow (5 minutes)

### 1. Show Standard Agent Response
```bash
curl -X POST 'http://localhost:8000/api/agents/query?query=What%20products%20need%20restocking&enable_thinking=false'
```
**Expected:** Quick, direct response

### 2. Show Extended Thinking Response
```bash
curl -X POST 'http://localhost:8000/api/agents/query?query=What%20products%20need%20restocking&enable_thinking=true'
```
**Expected:** More comprehensive, analytical response

### 3. Compare Results
Point out:
- **Standard**: Fast, direct answers
- **Extended Thinking**: Deeper analysis, better reasoning, more context

## Demo Queries

### Inventory Analysis
```bash
# Standard
curl -X POST 'http://localhost:8000/api/agents/query?query=What%20products%20need%20restocking&enable_thinking=false'

# Extended Thinking
curl -X POST 'http://localhost:8000/api/agents/query?query=What%20products%20need%20restocking&enable_thinking=true'
```

### Pricing Strategy
```bash
# Standard
curl -X POST 'http://localhost:8000/api/agents/query?query=What%20are%20the%20best%20deals&enable_thinking=false'

# Extended Thinking
curl -X POST 'http://localhost:8000/api/agents/query?query=What%20are%20the%20best%20deals&enable_thinking=true'
```

### Product Recommendations
```bash
# Standard
curl -X POST 'http://localhost:8000/api/agents/query?query=Recommend%20gaming%20accessories&enable_thinking=false'

# Extended Thinking
curl -X POST 'http://localhost:8000/api/agents/query?query=Recommend%20gaming%20accessories&enable_thinking=true'
```

## Key Talking Points

### What is Extended Thinking?
- Claude Sonnet 4's interleaved thinking capability
- Model "thinks" between tool calls
- Reflects on results and adapts strategy
- Provides more comprehensive responses

### When to Use Extended Thinking?
**Enable for:**
- Complex analysis tasks
- Multi-step reasoning
- Strategic recommendations
- When quality > speed

**Disable for:**
- Simple lookups
- Quick queries
- High-volume requests
- When speed > quality

### Technical Details
```python
# Configuration
BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    temperature=1,  # Required
    additional_request_fields={
        "anthropic_beta": ["interleaved-thinking-2025-05-14"],
        "reasoning_config": {
            "type": "enabled",
            "budget_tokens": 3000
        }
    }
)
```

### Performance Impact
- **Latency**: +1-2 seconds
- **Token Usage**: +3000 tokens max
- **Quality**: Significantly improved

## Live Demo Script

**Step 1: Introduction (30 seconds)**
"We've enhanced our orchestrator with Claude Sonnet 4's extended thinking capability. Let me show you the difference."

**Step 2: Standard Query (1 minute)**
"First, let's run a standard query about inventory..."
[Run standard query, show response]
"Notice it's fast and gives us the basics."

**Step 3: Extended Thinking Query (2 minutes)**
"Now let's enable extended thinking for the same query..."
[Run extended thinking query, show response]
"See how it provides deeper analysis, prioritization, and actionable recommendations?"

**Step 4: Explain the Difference (1 minute)**
"With extended thinking enabled, Claude:
- Thinks between tool calls
- Reflects on the data
- Adapts its strategy
- Provides more comprehensive insights"

**Step 5: Q&A (30 seconds)**
"This is configurable per request - you choose when to use it based on your needs."

## Frontend Integration (Optional)

Show participants how to add a toggle in the chat UI:
- Checkbox or toggle switch
- "Enable Extended Thinking" label
- Pass `enable_thinking` parameter to API

## Documentation Reference

- Full Guide: `lab2/backend/INTERLEAVED_THINKING.md`
- Comparison: `lab2/backend/THINKING_COMPARISON.md`
- Quick Start: `lab2/backend/QUICK_START_THINKING.md`

---

**© 2025 Shayon Sanyal | AWS re:Invent 2025 | DAT406 Workshop**
