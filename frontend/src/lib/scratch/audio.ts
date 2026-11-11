/**
 * Synthesised sound effects (no audio files): a filtered-noise scratch whose
 * volume follows scratch speed, plus short win / no-win jingles.
 */
const MUTE_KEY = "sr_muted";

export class ScratchAudio {
  private ctx: AudioContext | null = null;
  private scratchGain: GainNode | null = null;
  private _muted: boolean;

  constructor() {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(MUTE_KEY);
    } catch {
      /* storage unavailable */
    }
    this._muted = stored === "1";
  }

  get muted(): boolean {
    return this._muted;
  }

  setMuted(muted: boolean): void {
    this._muted = muted;
    try {
      localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
    } catch {
      /* storage unavailable */
    }
    if (muted) this.setScratchIntensity(0);
  }

  /** Must be called from a user gesture (browsers block audio otherwise). */
  unlock(): void {
    if (this.ctx) {
      if (this.ctx.state === "suspended") void this.ctx.resume();
      return;
    }
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    try {
      const ctx = new Ctor();
      const buffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
      const noise = ctx.createBufferSource();
      noise.buffer = buffer;
      noise.loop = true;
      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.value = 3800;
      filter.Q.value = 0.7;
      const gain = ctx.createGain();
      gain.gain.value = 0;
      noise.connect(filter).connect(gain).connect(ctx.destination);
      noise.start();
      this.ctx = ctx;
      this.scratchGain = gain;
    } catch {
      this.ctx = null;
    }
  }

  /** 0 = silent, 1 = fast scratch. */
  setScratchIntensity(intensity: number): void {
    if (!this.ctx || !this.scratchGain) return;
    const target = this._muted ? 0 : Math.min(1, Math.max(0, intensity)) * 0.09;
    this.scratchGain.gain.setTargetAtTime(target, this.ctx.currentTime, 0.035);
  }

  playWin(): void {
    this.playNotes([523.25, 659.25, 783.99, 1046.5, 1318.5], 0.085, "triangle", 0.16);
  }

  playNoWin(): void {
    this.playNotes([392, 329.63], 0.2, "sine", 0.1);
  }

  private playNotes(frequencies: number[], spacing: number, type: OscillatorType, volume: number): void {
    const ctx = this.ctx;
    if (!ctx || this._muted) return;
    frequencies.forEach((frequency, i) => {
      const start = ctx.currentTime + i * spacing;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.value = frequency;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(volume, start + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.45);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.5);
    });
  }
}
