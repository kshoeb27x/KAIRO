import { useEffect, useRef } from 'react';
import type { AppState } from '../app/stateMachine';

interface SphereProps {
  state: AppState;
  /** Measured microphone level (0..1). Only nonzero while listening. */
  audioLevel: number;
  /** Increments on real SpeechSynthesis boundary events. */
  speechPulse: number;
}

interface Node3D {
  x: number;
  y: number;
  z: number;
  links: number[];
}

const NODE_COUNT = 170;
const LINKS_PER_NODE = 3;

interface StateStyle {
  speed: number; // rotation radians/sec
  brightness: number; // 0..1
  convergence: number; // 1 = normal radius, <1 pulls nodes inward
  hue: 'cyan' | 'amber';
  ring: boolean;
}

const STATE_STYLES: Record<AppState, StateStyle> = {
  booting: { speed: 0.05, brightness: 0.3, convergence: 1, hue: 'cyan', ring: false },
  idle: { speed: 0.08, brightness: 0.45, convergence: 1, hue: 'cyan', ring: false },
  listening: { speed: 0.16, brightness: 0.75, convergence: 1, hue: 'cyan', ring: true },
  transcribing: { speed: 0.22, brightness: 0.7, convergence: 0.96, hue: 'cyan', ring: false },
  routing: { speed: 0.5, brightness: 0.8, convergence: 0.92, hue: 'cyan', ring: false },
  thinking: { speed: 0.65, brightness: 0.9, convergence: 0.85, hue: 'cyan', ring: false },
  executing: { speed: 0.45, brightness: 0.95, convergence: 1.02, hue: 'cyan', ring: false },
  permission: { speed: 0, brightness: 0.55, convergence: 1, hue: 'amber', ring: true },
  speaking: { speed: 0.3, brightness: 1, convergence: 1.05, hue: 'cyan', ring: false },
  error: { speed: 0.03, brightness: 0.35, convergence: 1, hue: 'amber', ring: false },
};

function buildNodes(): Node3D[] {
  // Fibonacci sphere distribution.
  const nodes: Node3D[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < NODE_COUNT; i += 1) {
    const y = 1 - (i / (NODE_COUNT - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = golden * i;
    nodes.push({ x: Math.cos(theta) * radius, y, z: Math.sin(theta) * radius, links: [] });
  }
  // Precompute nearest-neighbor links once.
  for (let i = 0; i < nodes.length; i += 1) {
    const a = nodes[i]!;
    const distances = nodes
      .map((b, j) => ({
        j,
        d: (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2,
      }))
      .filter((entry) => entry.j !== i)
      .sort((p, q) => p.d - q.d)
      .slice(0, LINKS_PER_NODE);
    a.links = distances.map((entry) => entry.j);
  }
  return nodes;
}

/**
 * Canvas 2D neural sphere. Motion parameters derive from the application
 * state machine (never decorative timers); listening reacts to measured mic
 * input, and speaking pulses ride real SpeechSynthesis boundary events.
 * Honors prefers-reduced-motion by rendering a static frame per state.
 */
export function NeuralSphere({ state, audioLevel, speechPulse }: SphereProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef(state);
  const levelRef = useRef(audioLevel);
  const pulseRef = useRef(0);
  const lastPulseCount = useRef(speechPulse);

  stateRef.current = state;
  levelRef.current = audioLevel;
  if (speechPulse !== lastPulseCount.current) {
    lastPulseCount.current = speechPulse;
    pulseRef.current = 1;
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    const nodes = buildNodes();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let rotation = 0;
    let lastTime = performance.now();
    let frame = 0;

    const resize = (): void => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = (now: number): void => {
      const style = STATE_STYLES[stateRef.current];
      const dt = Math.min(0.1, (now - lastTime) / 1000);
      lastTime = now;

      if (!reducedMotion.matches) {
        rotation += style.speed * dt;
      }
      pulseRef.current = Math.max(0, pulseRef.current - dt * 2.2);

      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const speakBoost = stateRef.current === 'speaking' ? pulseRef.current * 0.1 : 0;
      const listenBoost = stateRef.current === 'listening' ? levelRef.current * 0.08 : 0;
      const baseRadius = Math.min(w, h) * 0.36 * (style.convergence + speakBoost + listenBoost);
      const bright = style.brightness + speakBoost + listenBoost * 2;
      const [r, g, b] =
        style.hue === 'amber' ? [240, 182, 74] : [63, 208, 255];

      context.clearRect(0, 0, w, h);

      const cosR = Math.cos(rotation);
      const sinR = Math.sin(rotation);
      const tilt = 0.35;
      const cosT = Math.cos(tilt);
      const sinT = Math.sin(tilt);

      const projected = nodes.map((n) => {
        const x1 = n.x * cosR + n.z * sinR;
        const z1 = -n.x * sinR + n.z * cosR;
        const y2 = n.y * cosT - z1 * sinT;
        const z2 = n.y * sinT + z1 * cosT;
        return {
          x: cx + x1 * baseRadius,
          y: cy + y2 * baseRadius,
          depth: (z2 + 1) / 2, // 0 back .. 1 front
        };
      });

      // Links
      context.lineWidth = Math.max(1, w / 700);
      for (let i = 0; i < nodes.length; i += 1) {
        const from = projected[i]!;
        for (const j of nodes[i]!.links) {
          if (j < i) continue;
          const to = projected[j]!;
          const depth = (from.depth + to.depth) / 2;
          const alpha = (0.04 + depth * 0.2) * bright;
          context.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
          context.beginPath();
          context.moveTo(from.x, from.y);
          context.lineTo(to.x, to.y);
          context.stroke();
        }
      }

      // Nodes
      for (const p of projected) {
        const size = (0.8 + p.depth * 1.8) * (w / 340);
        const alpha = (0.15 + p.depth * 0.6) * bright;
        context.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        context.beginPath();
        context.arc(p.x, p.y, size, 0, Math.PI * 2);
        context.fill();
      }

      // Listening/permission ring
      if (style.ring) {
        const ringRadius =
          baseRadius * (1.12 + (stateRef.current === 'listening' ? levelRef.current * 0.15 : 0));
        context.strokeStyle = `rgba(${r}, ${g}, ${b}, ${0.35 + levelRef.current * 0.5})`;
        context.lineWidth = Math.max(1.5, w / 400);
        context.beginPath();
        context.arc(cx, cy, ringRadius, 0, Math.PI * 2);
        context.stroke();
      }

      if (!reducedMotion.matches) {
        frame = requestAnimationFrame(draw);
      }
    };

    frame = requestAnimationFrame(draw);

    // With reduced motion we still re-render one static frame per state
    // change, driven by a low-frequency check instead of continuous RAF.
    let staticTimer: number | undefined;
    if (reducedMotion.matches) {
      staticTimer = window.setInterval(() => {
        frame = requestAnimationFrame(draw);
      }, 400);
    }

    return () => {
      cancelAnimationFrame(frame);
      if (staticTimer !== undefined) window.clearInterval(staticTimer);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="sphere-canvas"
      role="img"
      aria-label={`JARVIS state: ${state}`}
      data-state={state}
    />
  );
}
