import { useEffect, useRef } from 'react';

/**
 * Decorative particle field for the Pellier Labs landing masthead.
 *
 * The field carries no telemetry or measurement. It pauses when offscreen or
 * hidden, draws one static frame for reduced motion, and uses a fixed seed so
 * workshop screenshots and projector framing remain reproducible.
 */

type Particle = {
  x: number;
  spread: number;
  radius: number;
  drift: number;
  band: number;
};

const BAND_COUNT = 4;
const PARTICLES_PER_BAND = 190;
const CORE_PARTICLES = 170;
const TWO_PI = Math.PI * 2;
const CORE = [168, 66, 58];
const FRINGE = [107, 112, 92];

function seededRandom() {
  let state = 0x50454c4c;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function buildParticles(): Particle[] {
  const random = seededRandom();
  const particles: Particle[] = [];

  for (let band = 0; band < BAND_COUNT; band += 1) {
    for (let index = 0; index < PARTICLES_PER_BAND; index += 1) {
      particles.push({
        x: random(),
        spread: (random() * 2 - 1) * (0.45 + random() ** 2 * 0.55),
        radius: 0.65 + random() ** 2 * 1.25,
        drift: 0.006 + random() * 0.014,
        band,
      });
    }
  }

  for (let index = 0; index < CORE_PARTICLES; index += 1) {
    particles.push({
      x: random(),
      spread: (random() * 2 - 1) * 0.14,
      radius: 0.6 + random() ** 2,
      drift: 0.005 + random() * 0.01,
      band: -1,
    });
  }

  return particles;
}

function envelope(x: number) {
  const distanceFromCenter = Math.abs(x - 0.5) * 2;
  return 0.42 + distanceFromCenter ** 1.35 * 0.58;
}

function centerline(x: number, phase: number, band: number, height: number) {
  const bandPhase = phase + band * 0.5;
  const primary = Math.sin(x * TWO_PI * 1.1 + bandPhase);
  const secondary = Math.sin(x * TWO_PI * 2.2 + bandPhase * 1.6) * 0.2;
  return height * 0.5 + (primary + secondary) * height * 0.23;
}

function paint(
  context: CanvasRenderingContext2D,
  particles: Particle[],
  width: number,
  height: number,
  phase: number,
) {
  context.clearRect(0, 0, width, height);

  for (const particle of particles) {
    const spread = particle.spread * envelope(particle.x);
    const y =
      centerline(particle.x, phase, Math.max(particle.band, 0), height) +
      spread * height * 0.34;
    const distance = Math.min(1, Math.abs(spread) / 0.56);
    const mix = particle.band < 0 ? 0 : distance;
    const alpha =
      (particle.band < 0 ? 0.5 : 0.44) *
      (1 - distance * 0.62) *
      (0.48 + envelope(particle.x) * 0.52);
    const channel = (index: number) =>
      Math.round(CORE[index] + (FRINGE[index] - CORE[index]) * mix);

    context.fillStyle =
      `rgb(${channel(0)} ${channel(1)} ${channel(2)} / ${alpha.toFixed(3)})`;
    context.beginPath();
    context.arc(particle.x * width, y, particle.radius, 0, TWO_PI);
    context.fill();
  }
}

export function PellierLabsFlow() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    const particles = buildParticles();
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    let width = 0;
    let height = 0;
    let phase = 0;
    let frame = 0;
    let visible = true;
    let lastFrameAt = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(1, Math.round(bounds.width));
      height = Math.max(1, Math.round(bounds.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      paint(context, particles, width, height, phase);
    };

    const step = (now: number) => {
      const elapsed = lastFrameAt ? Math.min(now - lastFrameAt, 64) : 16;
      lastFrameAt = now;
      phase += elapsed * 0.0001;

      for (const particle of particles) {
        particle.x += particle.drift * (elapsed / 1000);
        if (particle.x > 1.03) particle.x -= 1.06;
      }

      paint(context, particles, width, height, phase);
      frame = window.requestAnimationFrame(step);
    };

    const start = () => {
      if (reducedMotion || frame || !visible || document.hidden) return;
      lastFrameAt = 0;
      frame = window.requestAnimationFrame(step);
    };

    const stop = () => {
      if (!frame) return;
      window.cancelAnimationFrame(frame);
      frame = 0;
    };

    const resizeObserver =
      typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
    resizeObserver?.observe(canvas);
    window.addEventListener('resize', resize);

    const intersectionObserver =
      typeof IntersectionObserver === 'undefined'
        ? null
        : new IntersectionObserver((entries) => {
            visible = entries.some((entry) => entry.isIntersecting);
            if (visible) start();
            else stop();
          });
    intersectionObserver?.observe(canvas);

    const onVisibilityChange = () => (document.hidden ? stop() : start());
    document.addEventListener('visibilitychange', onVisibilityChange);

    resize();
    start();

    return () => {
      stop();
      resizeObserver?.disconnect();
      intersectionObserver?.disconnect();
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  return (
    <div className="pellier-labs-flow" aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}
