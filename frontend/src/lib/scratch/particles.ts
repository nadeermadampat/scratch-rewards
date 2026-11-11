/** Foil flakes that fall away from the scratch point. Runs only while flakes exist. */

interface Flake {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  rotation: number;
  spin: number;
  life: number; // 1 -> 0
  decay: number;
  color: string;
}

const COLORS = ["#eef0f4", "#c5c8d2", "#9da1ae", "#d9dbe2", "#b1b5c1"];
const MAX_FLAKES = 140;

export class ParticleSystem {
  private flakes: Flake[] = [];
  private frame = 0;
  private lastTime = 0;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly dpr: number,
  ) {}

  emit(x: number, y: number, count: number): void {
    for (let i = 0; i < count && this.flakes.length < MAX_FLAKES; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 30 + Math.random() * 90;
      this.flakes.push({
        x: x + (Math.random() - 0.5) * 14,
        y: y + (Math.random() - 0.5) * 14,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 40,
        size: 2 + Math.random() * 4,
        rotation: Math.random() * Math.PI,
        spin: (Math.random() - 0.5) * 12,
        life: 1,
        decay: 1.1 + Math.random() * 1.1,
        color: COLORS[(Math.random() * COLORS.length) | 0],
      });
    }
    if (!this.frame && this.flakes.length) {
      this.lastTime = performance.now();
      this.frame = requestAnimationFrame(this.tick);
    }
  }

  destroy(): void {
    cancelAnimationFrame(this.frame);
    this.frame = 0;
    this.flakes = [];
  }

  private tick = (now: number): void => {
    const dt = Math.min(0.05, (now - this.lastTime) / 1000);
    this.lastTime = now;
    const ctx = this.canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    this.flakes = this.flakes.filter((f) => f.life > 0);
    for (const f of this.flakes) {
      f.vy += 520 * dt; // gravity
      f.vx *= 0.985;
      f.x += f.vx * dt;
      f.y += f.vy * dt;
      f.rotation += f.spin * dt;
      f.life -= f.decay * dt;
      ctx.save();
      ctx.translate(f.x, f.y);
      ctx.rotate(f.rotation);
      ctx.globalAlpha = Math.max(0, f.life);
      ctx.fillStyle = f.color;
      ctx.fillRect(-f.size / 2, -f.size / 4, f.size, f.size / 2);
      ctx.restore();
    }
    this.frame = this.flakes.length ? requestAnimationFrame(this.tick) : 0;
  };
}
