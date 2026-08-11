/**
 * EditorialBrief — "About" section + colophon.
 *
 * Two-part closer before the footer:
 *
 *   1. About band — editorial portrait left, "About" eyebrow,
 *      Boutique/Agent Trace positioning, and tech-stack chips.
 *   2. Colophon strip — single centered italic line on a slightly
 *      darker warm ground, doubling as the visual page-end signal.
 */

const BRIEF_IMAGE = '/products/hero-fresh-2.png'

export default function EditorialBrief() {
  return (
    <>
      {/* ── About band ── */}
      <section
        id="about"
        data-testid="editorial-brief"
        aria-label="About this workshop"
        className="w-full"
        style={{
          background: 'linear-gradient(180deg, #F7F3EE 0%, #EDE4D6 100%)',
          scrollMarginTop: 84,
        }}
      >
        <div className="max-w-[1440px] mx-auto px-container-x py-20 md:py-28">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            {/* Left: editorial illustration */}
            <div
              className="relative rounded-2xl overflow-hidden shadow-warm-md"
              style={{ aspectRatio: '16 / 10' }}
            >
              <img
                src={BRIEF_IMAGE}
                alt="Pellier editorial still life"
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
              <div
                className="absolute inset-0 pointer-events-none"
                aria-hidden
                style={{
                  background:
                    'linear-gradient(135deg, rgba(247,243,238,0.05) 0%, rgba(59,47,47,0.08) 100%)',
                }}
              />
            </div>

            {/* Right: editorial text */}
            <div className="flex flex-col gap-6">
              {/* Eyebrow */}
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  style={{ color: '#a8423a', fontSize: '9px' }}
                >
                  &#9679;
                </span>
                <span
                  className="font-sans"
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    letterSpacing: '0.22em',
                    textTransform: 'uppercase',
                    color: '#a8423a',
                  }}
                >
                  About
                </span>
              </div>

              {/* Headline */}
              <h2
                className="font-display italic text-espresso"
                style={{
                  fontSize: 'clamp(28px, 3.5vw, 44px)',
                  lineHeight: 1.1,
                  letterSpacing: '-0.01em',
                  fontWeight: 400,
                }}
              >
                A boutique surface.
                <br />
                A proof surface.
              </h2>

              {/* Brand mark */}
              <div
                className="font-sans text-espresso"
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  letterSpacing: '0.2em',
                  textTransform: 'uppercase',
                  color: 'rgba(31, 20, 16, 0.68)',
                }}
              >
                Boutique + Agent Trace
              </div>

              {/* Philosophy */}
              <p
                className="font-sans"
                style={{
                  fontSize: '15px',
                  lineHeight: 1.7,
                  maxWidth: '520px',
                  color: '#4a3a2e',
                }}
              >
                Pellier is a working boutique built to show governed agentic
                search in motion. Shoppers ask in natural language: a linen
                shirt for Goa, a thoughtful gift, a slow-craft object for home.
                The storefront answers with pieces that feel personal, while the
                Agent Trace shows how each answer was built.
              </p>

              <p
                className="font-sans"
                style={{
                  fontSize: '15px',
                  lineHeight: 1.7,
                  maxWidth: '520px',
                  color: '#4a3a2e',
                }}
              >
                Every recommendation is grounded in Aurora PostgreSQL, shaped
                by specialist agents, checked against tools and inventory, and
                traceable back to the signals that produced it. The promise is
                simple: recommendations can feel personal without becoming
                invisible.
              </p>

              {/* Stack */}
              <div
                className="flex flex-wrap gap-2 mt-2"
                style={{ maxWidth: '520px' }}
              >
                {[
                  'Aurora PostgreSQL',
                  'pgvector',
                  'Amazon Bedrock',
                  'AgentCore',
                  'Strands SDK',
                  'Claude',
                  'Cohere Embed v4',
                  'Amazon Transcribe',
                  'Cedar',
                ].map((tech) => (
                  <span
                    key={tech}
                    className="font-mono"
                    style={{
                      fontSize: '11px',
                      fontWeight: 500,
                      letterSpacing: '0.06em',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      background: 'rgba(31, 20, 16, 0.06)',
                      color: 'var(--ink-soft)',
                    }}
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Colophon strip ── */}
      <div
        className="w-full text-center"
        style={{ background: '#E8DFD4', padding: '28px 24px' }}
      >
        <p
          className="font-display italic"
          style={{
            fontSize: '15px',
            lineHeight: 1.5,
            color: '#6b5a4e',
            letterSpacing: '0.01em',
          }}
        >
          Built for teams who want agentic experiences that are practical,
          governed, and inspectable.
        </p>
      </div>
    </>
  )
}
