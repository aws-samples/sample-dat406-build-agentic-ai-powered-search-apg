/**
 * AgentTraceErrorBoundary — React Error Boundary for the Agent Trace canvas.
 *
 * Wraps the <Outlet /> in AgentTraceFrame so that if any surface component
 * throws during render, the sidebar and top bar remain functional while
 * the canvas shows an editorial error page.
 *
 * React Error Boundaries must be class components — there is no hook
 * equivalent for componentDidCatch / getDerivedStateFromError.
 *
 * Requirements: 19.2, 19.4
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { Eyebrow } from '../components/Eyebrow';

interface AgentTraceErrorBoundaryProps {
  children: React.ReactNode;
}

interface AgentTraceErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class AgentTraceErrorBoundary extends React.Component<
  AgentTraceErrorBoundaryProps,
  AgentTraceErrorBoundaryState
> {
  constructor(props: AgentTraceErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): AgentTraceErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log for debugging — could wire to telemetry in a future phase
    console.error('[AgentTraceErrorBoundary]', error, errorInfo);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '60vh',
            padding: '48px 24px',
            textAlign: 'center',
          }}
        >
          <Eyebrow label="Something went wrong" variant="burgundy" />

          <h1
            className="font-display italic text-espresso"
            style={{
              fontSize: 'clamp(36px, 4vw, 48px)',
              fontWeight: 400,
              lineHeight: 1.15,
              margin: '20px 0 16px',
              letterSpacing: '-0.015em',
            }}
          >
            The observatory hit a snag.
          </h1>

          {this.state.error?.message && (
            <p
              style={{
                fontFamily: 'var(--at-mono)',
                fontSize: 'var(--at-mono-size)',
                lineHeight: 'var(--at-mono-leading)',
                color: 'var(--at-ink-1)',
                backgroundColor: 'var(--at-cream-2)',
                padding: '12px 20px',
                borderRadius: '8px',
                maxWidth: '520px',
                wordBreak: 'break-word',
                margin: '0 0 32px',
              }}
            >
              {this.state.error.message}
            </p>
          )}

          <Link
            to="/pellier-labs/sessions"
            onClick={this.handleReset}
            style={{
              fontFamily: 'var(--at-mono)',
              fontSize: 'var(--at-eyebrow-size)',
              fontWeight: 500,
              letterSpacing: 'var(--at-eyebrow-tracking)',
              textTransform: 'uppercase',
              color: 'var(--at-red-1)',
              textDecoration: 'none',
              borderBottom: '1px solid var(--at-red-1)',
              paddingBottom: '2px',
            }}
          >
            Return to Sessions
          </Link>
        </div>
      );
    }

    return this.props.children;
  }
}

export default AgentTraceErrorBoundary;
