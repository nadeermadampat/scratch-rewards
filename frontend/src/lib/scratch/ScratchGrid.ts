/**
 * Tracks how much of the coating has been scratched without reading pixels back
 * from the canvas (getImageData is slow on phones). The surface is divided into
 * small cells; a cell counts as scratched once the brush covers its centre.
 */
export class ScratchGrid {
  readonly cols: number;
  readonly rows: number;
  private readonly cellW: number;
  private readonly cellH: number;
  private readonly cells: Uint8Array;
  private scratched = 0;

  constructor(
    readonly width: number,
    readonly height: number,
    cellSize = 8,
  ) {
    this.cols = Math.max(1, Math.ceil(width / cellSize));
    this.rows = Math.max(1, Math.ceil(height / cellSize));
    this.cellW = width / this.cols;
    this.cellH = height / this.rows;
    this.cells = new Uint8Array(this.cols * this.rows);
  }

  /** Fraction of the surface scratched, 0..1. */
  get progress(): number {
    return this.scratched / this.cells.length;
  }

  markCircle(x: number, y: number, radius: number): void {
    const c0 = Math.max(0, Math.floor((x - radius) / this.cellW));
    const c1 = Math.min(this.cols - 1, Math.floor((x + radius) / this.cellW));
    const r0 = Math.max(0, Math.floor((y - radius) / this.cellH));
    const r1 = Math.min(this.rows - 1, Math.floor((y + radius) / this.cellH));
    const r2 = radius * radius;
    for (let row = r0; row <= r1; row++) {
      const dy = (row + 0.5) * this.cellH - y;
      for (let col = c0; col <= c1; col++) {
        const dx = (col + 0.5) * this.cellW - x;
        const index = row * this.cols + col;
        if (this.cells[index] === 0 && dx * dx + dy * dy <= r2) {
          this.cells[index] = 1;
          this.scratched++;
        }
      }
    }
  }

  markLine(x0: number, y0: number, x1: number, y1: number, radius: number): void {
    const steps = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / (radius / 2)));
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      this.markCircle(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, radius);
    }
  }
}
