import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import type { ScratchAudio } from "../lib/scratch/audio";
import { paintCoating } from "../lib/scratch/coating";
import { ParticleSystem } from "../lib/scratch/particles";
import { ScratchGrid } from "../lib/scratch/ScratchGrid";
import { prefersReducedMotion } from "../lib/util";

interface Props {
  /** Fraction of the surface (0..1) that triggers the reveal. */
  threshold: number;
  /** True once the coating should be gone (revealed / completed). */
  cleared: boolean;
  /** True once the reward underneath is loaded; the reveal waits for it. */
  ready: boolean;
  audio: ScratchAudio;
  onFirstScratch: () => void;
  onStrokeChange: (active: boolean) => void;
  onProgress: (progress: number) => void;
  onThreshold: () => void;
  /** The reward face shown under the coating. */
  children: ReactNode;
}

interface Point {
  x: number;
  y: number;
}

const FX_PAD = 48; // flakes may fall this far outside the card

/**
 * Canvas scratch-off surface. Purely presentational: it reports gestures and
 * progress, and never knows what the reward is or decides the outcome.
 */
export function ScratchCard({
  threshold, cleared, ready, audio, onFirstScratch, onStrokeChange, onProgress, onThreshold, children,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const coatRef = useRef<HTMLCanvasElement>(null);
  const fxRef = useRef<HTMLCanvasElement>(null);
  const gridRef = useRef<ScratchGrid | null>(null);
  const particlesRef = useRef<ParticleSystem | null>(null);
  const state = useRef({
    active: false, touched: false, fired: false, last: null as Point | null,
    lastTime: 0, width: 0, height: 0, brush: 22, progressFrame: 0,
  });
  const [touched, setTouched] = useState(false);
  const [startedCleared] = useState(cleared); // already completed on load: no coating at all

  // Latest props for use inside pointer handlers without re-binding them.
  const live = useRef({ ready, threshold, onFirstScratch, onStrokeChange, onProgress, onThreshold });
  live.current = { ready, threshold, onFirstScratch, onStrokeChange, onProgress, onThreshold };

  useLayoutEffect(() => {
    if (startedCleared) return;
    const wrap = wrapRef.current;
    const coat = coatRef.current;
    const fx = fxRef.current;
    if (!wrap || !coat || !fx) return;
    const s = state.current;

    const paint = () => {
      const { width, height } = wrap.getBoundingClientRect();
      if (width < 2 || height < 2) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2); // cap for mobile GPU memory
      coat.width = Math.round(width * dpr);
      coat.height = Math.round(height * dpr);
      const ctx = coat.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      paintCoating(ctx, width, height);
      fx.width = Math.round((width + FX_PAD * 2) * dpr);
      fx.height = Math.round((height + FX_PAD * 2) * dpr);
      particlesRef.current?.destroy();
      particlesRef.current = prefersReducedMotion() ? null : new ParticleSystem(fx, dpr);
      gridRef.current = new ScratchGrid(width, height);
      s.width = width;
      s.height = height;
      s.brush = Math.min(30, Math.max(18, width * 0.068));
    };

    paint();
    // Repaint on layout changes only while untouched, so scratches are never lost.
    const observer = new ResizeObserver(() => {
      const { width, height } = wrap.getBoundingClientRect();
      if (!s.touched && (Math.abs(width - s.width) > 1 || Math.abs(height - s.height) > 1)) paint();
    });
    observer.observe(wrap);
    void document.fonts?.ready.then(() => {
      if (!s.touched) paint();
    });
    return () => {
      observer.disconnect();
      particlesRef.current?.destroy();
      cancelAnimationFrame(s.progressFrame);
    };
  }, [startedCleared]);

  const maybeFire = useCallback(() => {
    const s = state.current;
    const progress = gridRef.current?.progress ?? 0;
    if (!s.fired && live.current.ready && progress >= live.current.threshold) {
      s.fired = true;
      live.current.onThreshold();
    }
  }, []);

  // The threshold may be crossed before the reward has loaded.
  useEffect(() => {
    if (ready) maybeFire();
  }, [ready, maybeFire]);

  useEffect(() => {
    if (cleared) audio.setScratchIntensity(0);
  }, [cleared, audio]);

  const toPoint = (event: { clientX: number; clientY: number }): Point => {
    const rect = coatRef.current!.getBoundingClientRect();
    const s = state.current;
    return {
      x: ((event.clientX - rect.left) / rect.width) * s.width,
      y: ((event.clientY - rect.top) / rect.height) * s.height,
    };
  };

  const scratch = (from: Point, to: Point) => {
    const ctx = coatRef.current?.getContext("2d");
    const s = state.current;
    if (!ctx) return;
    ctx.globalCompositeOperation = "destination-out";
    // destination-out erases by the source alpha, so the brush must be fully opaque.
    ctx.strokeStyle = "#000";
    ctx.fillStyle = "#000";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = s.brush * 2;
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x + 0.01, to.y + 0.01); // zero-length lines don't render a dot everywhere
    ctx.stroke();
    // Ragged edge: a few small bites just outside the brush, like real foil.
    for (let i = 0; i < 2; i++) {
      const angle = Math.random() * Math.PI * 2;
      const distance = s.brush * (0.85 + Math.random() * 0.3);
      ctx.beginPath();
      ctx.arc(to.x + Math.cos(angle) * distance, to.y + Math.sin(angle) * distance, 2.5 + Math.random() * 4.5, 0, Math.PI * 2);
      ctx.fill();
    }
    gridRef.current?.markLine(from.x, from.y, to.x, to.y, s.brush);
  };

  const reportProgress = () => {
    const s = state.current;
    if (s.progressFrame) return;
    s.progressFrame = requestAnimationFrame(() => {
      s.progressFrame = 0;
      live.current.onProgress(gridRef.current?.progress ?? 0);
      maybeFire();
    });
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    if (cleared || (event.pointerType === "mouse" && event.button !== 0)) return;
    event.preventDefault();
    const s = state.current;
    event.currentTarget.setPointerCapture(event.pointerId);
    audio.unlock();
    if (!s.touched) {
      s.touched = true;
      setTouched(true);
      live.current.onFirstScratch();
    }
    const point = toPoint(event);
    s.active = true;
    s.last = point;
    s.lastTime = event.timeStamp;
    scratch(point, point);
    particlesRef.current?.emit(point.x + FX_PAD, point.y + FX_PAD, 4);
    live.current.onStrokeChange(true);
    reportProgress();
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const s = state.current;
    if (!s.active || !s.last || cleared) return;
    // Coalesced events give every sampled touch position, for smooth fast strokes.
    const native = event.nativeEvent;
    const samples = native.getCoalescedEvents?.() ?? [];
    let travelled = 0;
    for (const sample of samples.length ? samples : [native]) {
      const point = toPoint(sample);
      travelled += Math.hypot(point.x - s.last.x, point.y - s.last.y);
      scratch(s.last, point);
      s.last = point;
    }
    const elapsed = Math.max(1, event.timeStamp - s.lastTime);
    s.lastTime = event.timeStamp;
    audio.setScratchIntensity(Math.min(1, travelled / elapsed / 1.2));
    if (travelled > 2) {
      particlesRef.current?.emit(s.last.x + FX_PAD, s.last.y + FX_PAD, Math.min(4, 1 + Math.floor(travelled / 14)));
    }
    reportProgress();
  };

  const endStroke = () => {
    const s = state.current;
    if (!s.active) return;
    s.active = false;
    s.last = null;
    audio.setScratchIntensity(0);
    live.current.onStrokeChange(false);
  };

  return (
    <div ref={wrapRef} className="relative aspect-[8/5] w-full">
      <div className="absolute inset-0 overflow-hidden rounded-2xl">
        {children}
        {!startedCleared && (
          <canvas
            ref={coatRef}
            role="img"
            aria-label="Scratch-off coating. Drag across it to reveal your result."
            className={`scratch-surface absolute inset-0 h-full w-full transition-[opacity,transform] duration-700 ease-out ${
              cleared ? "pointer-events-none scale-105 opacity-0" : ""
            }`}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={endStroke}
            onPointerCancel={endStroke}
            onLostPointerCapture={endStroke}
            onContextMenu={(event) => event.preventDefault()}
          />
        )}
        {!touched && !cleared && (
          <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
            <div className="absolute inset-y-0 w-1/4 animate-sheen bg-gradient-to-r from-transparent via-white/45 to-transparent" />
            <div className="absolute left-[28%] top-[62%] animate-nudge text-4xl drop-shadow-lg">👆</div>
          </div>
        )}
      </div>
      {!startedCleared && (
        <canvas
          ref={fxRef}
          aria-hidden
          className="pointer-events-none absolute"
          style={{ inset: -FX_PAD, width: `calc(100% + ${FX_PAD * 2}px)`, height: `calc(100% + ${FX_PAD * 2}px)` }}
        />
      )}
    </div>
  );
}
