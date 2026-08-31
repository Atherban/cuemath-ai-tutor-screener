/** Target sample rate for candidate audio sent to the backend (WAV 16 kHz). */
export const TARGET_SAMPLE_RATE = 16000;

/**
 * Resample a planar mono Float32 buffer to a target sample rate using linear
 * interpolation. No-op when rates already match.
 */
export function resampleTo(samples: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate || samples.length === 0) return samples;
  const ratio = samples.length / toRate;
  const out = new Float32Array(Math.max(1, Math.floor(samples.length * (toRate / fromRate))));
  for (let i = 0; i < out.length; i++) {
    const pos = i * ratio;
    const idx = Math.floor(pos);
    const frac = pos - idx;
    const next = Math.min(samples.length - 1, idx + 1);
    out[i] = samples[idx] * (1 - frac) + samples[next] * frac;
  }
  return out;
}

/**
 * Encode 16-bit PCM samples (range [-1, 1]) into a WAV file (mono).
 */
export function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const numSamples = samples.length;
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  // RIFF header
  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + numSamples * 2, true);
  writeAscii(view, 8, "WAVE");
  // fmt chunk
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  // data chunk
  writeAscii(view, 36, "data");
  view.setUint32(40, numSamples * 2, true);

  let offset = 44;
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return buffer;
}

function writeAscii(view: DataView, offset: number, text: string): void {
  for (let i = 0; i < text.length; i++) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}

/**
 * Root-mean-square level of a sample buffer, in the range [0, 1].
 * Used for the live audio level indicator and voice-activity detection.
 */
export function rmsLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) {
    sum += samples[i] * samples[i];
  }
  const rms = Math.sqrt(sum / samples.length);
  // Rough scaling to make speech levels land near 1.0 on the UI meter.
  return Math.min(1, rms * 4);
}
