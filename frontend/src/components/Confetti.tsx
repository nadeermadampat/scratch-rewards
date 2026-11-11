import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../lib/util";

interface Piece {
  x: number;
  y: number;
  vx: number;
  vy: number;
  w: number;
  h: number;
  rotation: number;
  spin: number;
  wobble: number;
  color: string;
}

const COLORS = ["#fbbf24", "#f472b6", "#60a5fa", "#34d399", "#a78bfa", "#ffffff", "#fb923c"];
const DURATION_MS = 4200;

/** Full-screen confetti burst, fired once when `fire` becomes true. */
export function Confetti({ fire }: { fire: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!fire || !canvas || !ctx || prefersReducedMotion()) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = window.innerWidth;
    const height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const count = width < 500 ? 110 : 180;
    const pieces: Piece[] = Array.from({ length: count }, (_, i) => {
      // Two cannons from the lower corners plus a shower from the top.
      const side = i % 3;
      const fromLeft = side === 0;
      const angle = side === 2 ? Math.PI / 2 + (Math.random() - 0.5) : (fromLeft ? -Math.PI / 3 : (-2 * Math.PI) / 3) + (Math.random() - 0.5) * 0.7;
      const speed = side === 2 ? 60 + Math.random() * 160 : 520 + Math.random() * 520;
      return {
        x: side === 2 ? Math.random() * width : fromLeft ? -10 : width + 10,
        y: side === 2 ? -20 - Math.random() * 120 : height * 0.72,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        w: 6 + Math.random() * 6,
        h: 8 + Math.random() * 8,
        rotation: Math.random() * Math.PI,
        spin: (Math.random() - 0.5) * 14,
        wobble: Math.random() * Math.PI * 2,
        color: COLORS[i % COLORS.length],
      };
    });

    const started = performance.now();
    let last = started;
    let frame = 0;
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const age = now - started;
      ctx.clearRect(0, 0, width, height);
      const fade = Math.min(1, Math.max(0, (DURATION_MS - age) / 900));
      for (const p of pieces) {
        p.vy += 900 * dt;
        p.vx *= 0.985;
        p.vy *= 0.985;
        p.wobble += dt * 8;
        p.x += (p.vx + Math.sin(p.wobble) * 40) * dt;
        p.y += p.vy * dt;
        p.rotation += p.spin * dt;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.scale(1, Math.cos(p.wobble)); // paper flutter
        ctx.globalAlpha = fade;
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
      if (age < DURATION_MS) frame = requestAnimationFrame(tick);
      else ctx.clearRect(0, 0, width, height);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [fire]);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-50 h-full w-full" />;
}
