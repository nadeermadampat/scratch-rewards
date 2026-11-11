/** Paints the metallic scratch-off foil. Coordinates are CSS pixels. */

function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function sparkle(ctx: CanvasRenderingContext2D, x: number, y: number, size: number): void {
  ctx.beginPath();
  ctx.moveTo(x, y - size);
  ctx.quadraticCurveTo(x, y, x + size, y);
  ctx.quadraticCurveTo(x, y, x, y + size);
  ctx.quadraticCurveTo(x, y, x - size, y);
  ctx.quadraticCurveTo(x, y, x, y - size);
  ctx.fill();
}

export function paintCoating(ctx: CanvasRenderingContext2D, w: number, h: number, label = "SCRATCH HERE"): void {
  const rand = mulberry32(20261111); // fixed seed: the foil looks the same on every repaint
  ctx.globalCompositeOperation = "source-over";
  ctx.clearRect(0, 0, w, h);

  // Brushed-silver base.
  const base = ctx.createLinearGradient(0, 0, w, h);
  const stops: [number, string][] = [
    [0, "#b4b8c4"], [0.2, "#f1f2f6"], [0.42, "#a1a5b2"], [0.6, "#e2e4ea"], [0.8, "#979bab"], [1, "#d3d6de"],
  ];
  stops.forEach(([at, color]) => base.addColorStop(at, color));
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, w, h);

  // Horizontal brushing streaks.
  for (let i = 0; i < h * 1.5; i++) {
    const alpha = 0.03 + rand() * 0.07;
    ctx.fillStyle = rand() > 0.5 ? `rgba(255,255,255,${alpha})` : `rgba(40,44,62,${alpha})`;
    ctx.fillRect(0, rand() * h, w, rand() > 0.8 ? 2 : 1);
  }

  // Fine grain.
  const grains = Math.floor((w * h) / 9);
  for (let i = 0; i < grains; i++) {
    const alpha = 0.04 + rand() * 0.13;
    ctx.fillStyle = rand() > 0.5 ? `rgba(255,255,255,${alpha})` : `rgba(30,32,48,${alpha})`;
    ctx.fillRect(rand() * w, rand() * h, 1, 1);
  }

  // Embossed sparkle pattern, like a printed security pattern.
  const step = 34;
  for (let row = 0, y = 18; y < h; row++, y += step) {
    for (let x = row % 2 ? 18 + step / 2 : 18; x < w; x += step) {
      const size = 3.5 + rand() * 2.5;
      ctx.fillStyle = "rgba(48,52,72,0.16)";
      sparkle(ctx, x + 0.8, y + 0.8, size);
      ctx.fillStyle = "rgba(255,255,255,0.34)";
      sparkle(ctx, x, y, size);
    }
  }

  // Diagonal light band.
  const sheen = ctx.createLinearGradient(0, 0, w, h * 0.7);
  sheen.addColorStop(0.3, "rgba(255,255,255,0)");
  sheen.addColorStop(0.5, "rgba(255,255,255,0.38)");
  sheen.addColorStop(0.7, "rgba(255,255,255,0)");
  ctx.fillStyle = sheen;
  ctx.fillRect(0, 0, w, h);

  // Dashed guide border.
  ctx.setLineDash([6, 5]);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = "rgba(58,62,84,0.45)";
  roundedRect(ctx, 10, 10, w - 20, h - 20, 14);
  ctx.stroke();
  ctx.setLineDash([]);

  // Embossed label on a clear plate so it stays readable over the pattern.
  const size = Math.round(Math.min(w * 0.088, h * 0.17));
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `800 ${size}px "Baloo 2", system-ui, sans-serif`;
  if ("letterSpacing" in ctx) (ctx as unknown as { letterSpacing: string }).letterSpacing = "0.1em";
  const plateW = Math.min(w - 44, ctx.measureText(label).width + 44);
  const plateH = size * 2.5;
  const plate = ctx.createLinearGradient(0, h / 2 - plateH / 2, 0, h / 2 + plateH / 2);
  plate.addColorStop(0, "rgba(236,238,243,0.9)");
  plate.addColorStop(1, "rgba(196,199,210,0.9)");
  ctx.fillStyle = plate;
  roundedRect(ctx, (w - plateW) / 2, h / 2 - plateH / 2, plateW, plateH, plateH / 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(58,62,84,0.25)";
  ctx.lineWidth = 1;
  ctx.stroke();

  const labelY = h / 2 - size * 0.28;
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.fillText(label, w / 2 + 0.5, labelY + 1.5);
  ctx.fillStyle = "#4a4f63";
  ctx.fillText(label, w / 2, labelY);

  if ("letterSpacing" in ctx) (ctx as unknown as { letterSpacing: string }).letterSpacing = "0.04em";
  ctx.font = `600 ${Math.round(size * 0.46)}px Inter, system-ui, sans-serif`;
  ctx.fillStyle = "#5d6277";
  ctx.fillText("use your finger or mouse", w / 2, h / 2 + size * 0.7);
  if ("letterSpacing" in ctx) (ctx as unknown as { letterSpacing: string }).letterSpacing = "0px";

  // Soft vignette for depth.
  const vignette = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.max(w, h) * 0.75);
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, "rgba(20,22,40,0.22)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, w, h);
}
