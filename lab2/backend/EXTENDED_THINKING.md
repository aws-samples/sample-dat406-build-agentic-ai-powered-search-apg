# Claude Sonnet 4 Extended Thinking

## Overview

The orchestrator supports **Claude Sonnet 4's extended thinking** - an opt-in capability that enables deeper reasoning and better decision-making.

## Quick Start

```python
from agents.orchestrator import create_orchestrator

# Standard mode (default - faster)
orchestrator = create_orchestrator(enable_interleaved_thinking=False)

# Extended thinking mode (better quality)
orchestrator = create_orchestrator(enable_interleaved_thinking=True)
```

## API Usage

```bash
# Standard mode
curl -X POST 'http://localhost:8000/api/agents/query?query=YOUR_QUERY&enable_thinking=false'

# Extended thinking mode
curl -X POST 'http://localhost:8000/api/agents/query?query=YOUR_QUERY&enable_thinking=true'
```

## When to Use

### Enable Extended Thinking For:
- Complex analysis tasks
- Strategic recommendations
- Multi-step reasoning
- When quality > speed

### Use Standard Mode For:
- Simple lookups
- Quick queries
- High-volume requests
- When speed > quality

## Configuration

```python
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

## Performance

- **Latency**: +1-2 seconds
- **Token Usage**: +3000 tokens max
- **Quality**: Significantly improved

## Default Behavior

Extended thinking is **DISABLED by default** for faster responses.

---

**© 2025 Shayon Sanyal | AWS re:Invent 2025 | DAT406 Workshop**
