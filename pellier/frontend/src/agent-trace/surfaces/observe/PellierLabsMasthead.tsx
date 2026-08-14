import { useEffect, useRef } from 'react';
import { Eyebrow } from '../../components';

type Particle = {
  x: number;
  y: number;
  radius: number;
  drift: number;
  phase: number;
  tone: 'ink' | 'red' | 'gold';
};

const PARTICLE_COUNT = 560;
const CORE_PARTICLE_COUNT = 160;
const TWO_PI = Math.PI * 2;
const COLORS = {
  ink: [66, 47, 39],
  red: [154, 52, 18],
  gold: [184, 138, 58],
} as const;

function buildParticles(): Particle[] {
  const field: Particle[] = Array.from({ length: PARTICLE_COUNT }, (_, index) => {
    const tone = index % 11 === 0 ? 'gold' : index % 3 === 0 ? 'red' : 'ink';
    return {
      x: Math.random(),
      y: Math.random() * 2 - 1,
      radius: 0.55 + Math.random() ** 2 * 1.2,
      drift: 0.01 + Math.random() * 0.018,
      phase: Math.random() * TWO_PI,
      tone,
    };
  });

  const core: Particle[] = Array.from({ length: CORE_PARTICLE_COUNT }, (_, index) => ({
    x: 0.06 + Math.random() * 0.94,
    y: (Math.random() * 2 - 1) * 0.18,
    radius: 0.7 + Math.random() ** 2 * 1.35,
    drift: 0.008 + Math.random() * 0.012,
    phase: Math.random() * TWO_PI,
    tone: index % 7 === 0 ? 'gold' : 'red',
  }));

  return [...field, ...core];
}

function waveY(x: number, phase: number, height: number) {
  const primary = Math.sin(x * TWO_PI * 1.08 + phase);
  const secondary = Math.sin(x * TWO_PI * 2.1 + phase * 1.45) * 0.24;
  return height * 0.5 + (primary + secondary) * height * 0.19;
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
    const envelope = 0.32 + particle.x ** 1.3 * 0.68;
    const y = waveY(particle.x, phase + particle.phase * 0.08, height)
      + particle.y * height * 0.34 * envelope;
    const [red, green, blue] = COLORS[particle.tone];
    const alpha = (particle.tone === 'gold' ? 0.58 : 0.4)
      * (0.62 + envelope * 0.38)
      * (1 - Math.min(0.58, Math.abs(particle.y) * 0.34));

    context.fillStyle = `rgb(${red} ${green} ${blue} / ${alpha.toFixed(3)})`;
    context.beginPath();
    context.arc(particle.x * width, y, particle.radius, 0, TWO_PI);
    context.fill();
  }
}

/**
 * A quiet decorative field for the Pellier Labs entry point.
 *
 * It is intentionally not derived from proof-board data. The data surfaces
 * below it remain the only source of operational measurements and receipts.
 */
export function PellierLabsMasthead() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // JSDOM exposes a canvas element without a drawing implementation.
    // Do not invoke it there; the masthead remains a quiet static band.
    if (typeof CanvasRenderingContext2D === 'undefined') return;

    let context: CanvasRenderingContext2D | null;
    try {
      context = canvas.getContext('2d');
    } catch {
      return;
    }
    if (!context) return;

    const particles = buildParticles();
    const motionQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    let reduceMotion = Boolean(motionQuery?.matches);
    let width = 0;
    let height = 0;
    let phase = 0;
    let frame = 0;
    let visible = true;
    let last = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const box = canvas.getBoundingClientRect();
      width = Math.max(1, Math.round(box.width));
      height = Math.max(1, Math.round(box.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      context?.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (context) paint(context, particles, width, height, phase);
    };

    const halt = () => {
      if (!frame) return;
      window.cancelAnimationFrame(frame);
      frame = 0;
    };

    const step = (now: number) => {
      const elapsed = last ? Math.min(now - last, 64) : 16;
      last = now;
      phase += elapsed * 0.00016;
      for (const particle of particles) {
        particle.x += particle.drift * (elapsed / 1000);
        if (particle.x > 1.02) particle.x -= 1.04;
      }
      if (context) paint(context, particles, width, height, phase);
      frame = window.requestAnimationFrame(step);
    };

    const run = () => {
      if (reduceMotion || frame || !visible || document.hidden) return;
      last = 0;
      frame = window.requestAnimationFrame(step);
    };

    const onVisibilityChange = () => (document.hidden ? halt() : run());
    const onMotionChange = () => {
      reduceMotion = Boolean(motionQuery?.matches);
      if (reduceMotion) halt();
      else run();
    };
    const onWindowResize = () => resize();

    const resizeObserver = typeof ResizeObserver === 'undefined'
      ? null
      : new ResizeObserver(resize);
    resizeObserver?.observe(canvas);
    window.addEventListener('resize', onWindowResize);
    document.addEventListener('visibilitychange', onVisibilityChange);

    const intersectionObserver = typeof IntersectionObserver === 'undefined'
      ? null
      : new IntersectionObserver((entries) => {
        visible = entries.some((entry) => entry.isIntersecting);
        if (visible) run();
        else halt();
      });
    intersectionObserver?.observe(canvas);

    if (motionQuery?.addEventListener) {
      motionQuery.addEventListener('change', onMotionChange);
    } else {
      motionQuery?.addListener?.(onMotionChange);
    }

    resize();
    run();

    return () => {
      halt();
      resizeObserver?.disconnect();
      intersectionObserver?.disconnect();
      window.removeEventListener('resize', onWindowResize);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      if (motionQuery?.removeEventListener) {
        motionQuery.removeEventListener('change', onMotionChange);
      } else {
        motionQuery?.removeListener?.(onMotionChange);
      }
    };
  }, []);

  return (
    <header className="pellier-labs-masthead">
      <div className="pellier-labs-masthead-copy">
        <Eyebrow label="Pellier Labs" />
        <h1 className="font-display">Proof Board</h1>
        <p>
          Trace one governed decision from verified data to a recorded receipt.
        </p>
      </div>
      <div className="pellier-labs-masthead-flow" aria-hidden="true">
        <canvas ref={canvasRef} />
      </div>
    </header>
  );
}
