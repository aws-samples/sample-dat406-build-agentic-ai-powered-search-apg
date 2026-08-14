import { useEffect, useRef } from 'react';
import { Eyebrow } from '../../components';
import './PellierLabsWorkbench.css';

type Particle = {
  x: number;
  spread: number;
  radius: number;
  drift: number;
  band: number;
  tint: number;
};

const BANDS = 4;
const PER_BAND = 360;
const CORE_COUNT = 320;
const TWO_PI = Math.PI * 2;
const CORE_DEEP = [43, 13, 19];
const CORE = [126, 36, 49];
const FRINGE = [201, 112, 58];
const HIGHLIGHT = [246, 224, 198];

function mixChannel(a: number[], b: number[], t: number, index: number) {
  return a[index] + (b[index] - a[index]) * Math.min(1, Math.max(0, t));
}

function buildParticles(): Particle[] {
  const particles: Particle[] = [];
  for (let band = 0; band < BANDS; band += 1) {
    for (let index = 0; index < PER_BAND; index += 1) {
      particles.push({
        x: Math.random(),
        spread: (Math.random() * 2 - 1) * (0.5 + Math.random() ** 2 * 0.5),
        radius: 0.65 + Math.random() ** 2 * 1.45,
        drift: 0.012 + Math.random() * 0.035,
        band,
        tint: (Math.random() * 2 - 1) * 0.08,
      });
    }
  }
  for (let index = 0; index < CORE_COUNT; index += 1) {
    particles.push({
      x: 0.16 + Math.random() ** 0.72 * 0.84,
      spread: (Math.random() * 2 - 1) * 0.16,
      radius: 0.55 + Math.random() ** 2 * 1.1,
      drift: 0.01 + Math.random() * 0.02,
      band: -1,
      tint: Math.random() * 0.3,
    });
  }
  return particles;
}

function envelope(x: number) {
  return 0.28 + x ** 1.2 * 0.92;
}

function centreline(x: number, phase: number, band: number, height: number) {
  const bandPhase = phase + band * 0.42;
  const primary = Math.sin(x * TWO_PI * 1.15 + bandPhase);
  const secondary = Math.sin(x * TWO_PI * 2.3 + bandPhase * 1.7) * 0.22;
  return height * 0.5 + (primary + secondary) * height * 0.25;
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
    const y = centreline(particle.x, phase, Math.max(particle.band, 0), height)
      + spread * height * 0.36;
    const distance = Math.min(1, Math.abs(spread) / 0.55);
    const alpha = (particle.band < 0 ? 0.58 : 0.5)
      * (1 - distance * 0.66)
      * (0.25 + envelope(particle.x) * 0.75);
    const channel = (index: number) => {
      if (particle.band < 0) {
        const warmth = Math.min(1, particle.tint + envelope(particle.x) * 0.55);
        return Math.round(mixChannel(CORE, HIGHLIGHT, warmth, index));
      }
      const mix = Math.min(1, Math.max(0, distance + particle.tint));
      const value = mix < 0.5
        ? mixChannel(CORE_DEEP, CORE, mix * 2, index)
        : mixChannel(CORE, FRINGE, (mix - 0.5) * 2, index);
      return Math.round(value);
    };
    context.fillStyle =
      `rgb(${channel(0)} ${channel(1)} ${channel(2)} / ${alpha.toFixed(3)})`;
    context.beginPath();
    context.arc(particle.x * width, y, particle.radius, 0, TWO_PI);
    context.fill();
  }
}

export interface PellierLabsMastheadProps {
  eyebrow?: string;
  title?: string;
  deck?: string;
  status?: string;
}

/**
 * Decorative Labs masthead. The particle field encodes no metric or runtime
 * state; all inspectable evidence is rendered below from the current live run.
 */
export function PellierLabsMasthead({
  eyebrow = 'Inspection surface',
  title = 'Proof Board',
  deck = 'Run a live agent turn and inspect the evidence it emits.',
  status,
}: PellierLabsMastheadProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || typeof CanvasRenderingContext2D === 'undefined') return;

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
      phase += elapsed * 0.00021;
      for (const particle of particles) {
        particle.x += particle.drift * (elapsed / 1000);
        if (particle.x > 1.04) particle.x -= 1.08;
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
        <Eyebrow label={eyebrow} />
        <h1 className="font-display">{title}</h1>
        <p>{deck}</p>
        {status ? (
          <span className="pellier-labs-masthead-status">
            <span aria-hidden="true" />
            {status}
          </span>
        ) : null}
      </div>
      <div className="pellier-labs-masthead-flow" aria-hidden="true">
        <canvas ref={canvasRef} data-testid="pellier-labs-particle-canvas" />
      </div>
    </header>
  );
}
