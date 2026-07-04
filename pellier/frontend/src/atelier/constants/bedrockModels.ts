/**
 * Workshop Bedrock inference profile IDs (single source for copy + Telemetry).
 *
 * Aligns session fixtures, Telemetry tab, and teaching surfaces with the
 * Opus + Sonnet global inference profiles used by the workshop stack.
 */
export const BEDROCK_INFERENCE_PROFILES = {
  CLAUDE_OPUS_48: 'global.anthropic.claude-opus-4-8',
  CLAUDE_SONNET_46: 'global.anthropic.claude-sonnet-4-6',
  COHERE_EMBED_V4: 'us.cohere.embed-v4:0',
  COHERE_RERANK_V35: 'cohere.rerank-v3-5:0',
} as const
