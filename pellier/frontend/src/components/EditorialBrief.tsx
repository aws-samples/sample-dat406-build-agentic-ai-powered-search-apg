/**
 * EditorialBrief — "About" section + colophon.
 *
 * Two-part closer before the footer:
 *
 *   1. About band — editorial portrait left, "About" eyebrow,
 *      Storefront/Pellier Labs positioning, and tech-stack chips.
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
          background: 'transparent',
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
                  style={{ color: 'var(--accent)', fontSize: '9px' }}
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
                    color: 'var(--accent)',
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
                  color: 'var(--ink-quiet)',
                }}
              >
                Storefront + Pellier Labs
              </div>

              {/* Philosophy */}
              <p
                className="font-sans"
                style={{
                  fontSize: '15px',
                  lineHeight: 1.7,
                  maxWidth: '520px',
                  color: 'var(--ink-soft)',
                }}
              >
                Pellier is a workshop boutique for agentic search on Aurora.
                The static floor uses a seeded catalog and explicit profile tag
                weights. Natural-language turns invoke specialist tools and
                retrieval paths that participants can inspect.
              </p>

              <p
                className="font-sans"
                style={{
                  fontSize: '15px',
                  lineHeight: 1.7,
                  maxWidth: '520px',
                  color: 'var(--ink-soft)',
                }}
              >
                Aurora PostgreSQL stores catalog vectors, relational context,
                working-memory turns, and action receipts. Pellier Labs
                distinguishes authored fixtures from live evidence so a
                recommendation never claims more provenance than the current
                session collected.
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
                  'Strands SDK',
                  'Claude',
                  'Cohere Embed v4',
                  'Cohere Rerank v3.5',
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
        style={{
          background: 'var(--cream)',
          borderTop: '1px solid var(--rule-1)',
          padding: '28px 24px',
        }}
      >
        <p
          className="font-display italic"
          style={{
            fontSize: '15px',
            lineHeight: 1.5,
            color: 'var(--ink-quiet)',
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
