import { describe, expect, it } from "vitest";
import { ScratchGrid } from "./ScratchGrid";

describe("ScratchGrid", () => {
  it("starts untouched", () => {
    expect(new ScratchGrid(320, 200).progress).toBe(0);
  });

  it("reaches 100% when the whole surface is covered", () => {
    const grid = new ScratchGrid(320, 200);
    grid.markCircle(160, 100, 1000);
    expect(grid.progress).toBe(1);
  });

  it("a horizontal stroke through the middle covers a proportional band", () => {
    const grid = new ScratchGrid(320, 200);
    grid.markLine(0, 100, 320, 100, 25);
    // Band of height ~50 on a 200-high card.
    expect(grid.progress).toBeGreaterThan(0.2);
    expect(grid.progress).toBeLessThan(0.3);
  });

  it("does not count the same area twice", () => {
    const grid = new ScratchGrid(320, 200);
    grid.markLine(20, 50, 300, 50, 20);
    const once = grid.progress;
    for (let i = 0; i < 10; i++) grid.markLine(20, 50, 300, 50, 20);
    expect(grid.progress).toBe(once);
  });

  it("ignores strokes outside the surface", () => {
    const grid = new ScratchGrid(320, 200);
    grid.markLine(-500, -500, -100, -100, 20);
    grid.markCircle(5000, 5000, 20);
    expect(grid.progress).toBe(0);
  });

  it("covering the left half gives about 50%", () => {
    const grid = new ScratchGrid(320, 200);
    for (let y = 0; y <= 200; y += 5) grid.markLine(0, y, 150, y, 10);
    expect(grid.progress).toBeGreaterThan(0.45);
    expect(grid.progress).toBeLessThan(0.55);
  });
});
