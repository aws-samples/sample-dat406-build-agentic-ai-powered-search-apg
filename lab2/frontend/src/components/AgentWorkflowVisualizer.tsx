/**
 * Agent Workflow Visualizer - Real-time agent orchestration display
 */
import { useEffect, useState } from 'react'
import { useTheme } from '../App'

interface AgentStep {
  agent: string
  action: string
  status: string
  timestamp: number
  duration_ms: number
}

interface ToolCall {
  tool: string
  params?: string
  timestamp: number
  duration_ms: number
  status: string
}

interface AgentExecution {
  agent_steps: AgentStep[]
  tool_calls: ToolCall[]
  reasoning_steps: Array<{step: string, content: string, timestamp: number}>
  total_duration_ms: number
  success_rate: number
}

interface Props {
  execution: AgentExecution | null
  isActive: boolean
}

const AgentWorkflowVisualizer = ({ execution, isActive }: Props) => {
  const { theme } = useTheme()
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    if (isActive && execution) {
      let step = 0
      const interval = setInterval(() => {
        step++
        setActiveStep(step)
        if (step >= execution.agent_steps.length) {
          clearInterval(interval)
        }
      }, 300)
      return () => clearInterval(interval)
    } else {
      setActiveStep(execution?.agent_steps.length || 0)
    }
  }, [isActive, execution])

  if (!execution) return null

  const getAgentIcon = (agent: string) => {
    if (agent.includes('Orchestrator')) return '🎯'
    if (agent.includes('Inventory')) return '📦'
    if (agent.includes('Recommendation')) return '⭐'
    if (agent.includes('Pricing')) return '💰'
    return '🤖'
  }

  return (
    <div className="mb-4 p-4 rounded-xl" style={{
      background: theme === 'dark' 
        ? 'rgba(106, 27, 154, 0.05)' 
        : 'rgba(106, 27, 154, 0.03)',
      border: '1px solid rgba(186, 104, 200, 0.2)'
    }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-text-primary">🔄 Agent Workflow</span>
          <span className="text-xs text-text-secondary">
            {execution.total_duration_ms}ms
          </span>
        </div>
        <div className="text-xs text-green-400">
          ✓ {execution.success_rate}% Success
        </div>
      </div>

      {/* Agent Steps */}
      <div className="space-y-2">
        {execution.agent_steps.map((step, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-3 p-2 rounded-lg transition-all duration-300 ${
              idx < activeStep ? 'opacity-100' : 'opacity-40'
            }`}
            style={{
              background: idx < activeStep 
                ? 'rgba(106, 27, 154, 0.1)' 
                : 'rgba(255, 255, 255, 0.02)',
              transform: idx < activeStep ? 'translateX(0)' : 'translateX(-10px)'
            }}
          >
            {/* Agent Icon */}
            <div className="text-2xl">{getAgentIcon(step.agent)}</div>
            
            {/* Agent Info */}
            <div className="flex-1">
              <div className="text-sm font-medium text-text-primary">{step.agent}</div>
              <div className="text-xs text-text-secondary">{step.action}</div>
            </div>

            {/* Duration */}
            <div className="text-xs text-purple-400">{step.duration_ms}ms</div>

            {/* Status */}
            {step.status === 'completed' && (
              <div className="text-green-400 text-sm">✓</div>
            )}
            {step.status === 'in_progress' && (
              <div className="animate-spin text-purple-400">⏳</div>
            )}
            {idx < activeStep && step.status !== 'completed' && step.status !== 'in_progress' && (
              <div className="text-green-400 text-sm">✓</div>
            )}
            {idx === activeStep && isActive && step.status !== 'in_progress' && (
              <div className="animate-spin text-purple-400">⏳</div>
            )}
          </div>
        ))}
      </div>

      {/* Tool Calls Timeline */}
      {execution.tool_calls.length > 0 && (
        <div className="mt-3 pt-3 border-t border-purple-500/20">
          <div className="text-xs font-semibold text-text-secondary mb-2">
            🔧 MCP Tool Calls
          </div>
          <div className="space-y-1">
            {execution.tool_calls.map((tool, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 text-xs p-2 rounded"
                style={{ background: 'rgba(106, 27, 154, 0.05)' }}
              >
                <span className="text-green-400">✓</span>
                <span className="text-text-primary font-mono">{tool.tool}</span>
                {tool.params && (
                  <span className="text-text-secondary">({tool.params})</span>
                )}
                <span className="ml-auto text-purple-400">{tool.duration_ms}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning Steps */}
      {execution.reasoning_steps.length > 0 && (
        <div className="mt-3 pt-3 border-t border-purple-500/20">
          <div className="text-xs font-semibold text-text-secondary mb-2">
            🧠 Claude 4 Reasoning
          </div>
          {execution.reasoning_steps.map((reasoning, idx) => (
            <div
              key={idx}
              className="text-xs p-2 rounded mb-1"
              style={{ background: 'rgba(186, 104, 200, 0.05)' }}
            >
              <div className="font-semibold text-purple-400 mb-1">{reasoning.step}</div>
              <div className="text-text-secondary italic">{reasoning.content}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AgentWorkflowVisualizer
