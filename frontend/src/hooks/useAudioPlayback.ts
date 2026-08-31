import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Queued, non-overlapping playback of interviewer audio.
 *
 * The backend streams interviewer speech as binary audio chunks terminated by a
 * text `audio.end` event. We buffer the chunks for one speech burst, decode the
 * whole burst, and play it through a FIFO queue so bursts never overlap and
 * stale audio is dropped when the interview ends.
 */
export interface UseAudioPlaybackReturn {
  /** True while interviewer audio is actually playing. */
  isPlaying: boolean;
  /** Accumulate a binary audio chunk for the current speech burst. */
  addChunk: (chunk: ArrayBuffer) => void;
  /** Finalize the current burst: decode + enqueue for playback. */
  endBurst: () => void;
  /** Stop all playback and clear queued + buffered audio. */
  stop: () => void;
  /** Drop buffered-but-unflushed chunks without playing them. */
  clearBuffered: () => void;
  /**
   * Create/resume the AudioContext. Must be called from a user gesture
   * (e.g. the "Start interview" click) so autoplay-blocking browsers
   * (Chrome/Brave) allow playback later.
   */
  unlock: () => void;
}

export function useAudioPlayback(): UseAudioPlaybackReturn {
  const ctxRef = useRef<AudioContext | null>(null);
  const bufferRef = useRef<Uint8Array | null>(null);
  const queueRef = useRef<AudioBuffer[]>([]);
  const activeSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const playingRef = useRef(false);
  const [isPlaying, setIsPlaying] = useState(false);

  const ensureCtx = useCallback(() => {
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext();
    }
    return ctxRef.current;
  }, []);

  const unlock = useCallback(() => {
    const ctx = ensureCtx();
    if (ctx.state === "suspended") {
      void ctx.resume().catch(() => {
        // Autoplay still blocked — audio will be skipped silently.
      });
    }
  }, [ensureCtx]);

  const clearBuffered = useCallback(() => {
    bufferRef.current = null;
  }, []);

  const addChunk = useCallback((chunk: ArrayBuffer) => {
    const incoming = new Uint8Array(chunk);
    const existing = bufferRef.current;
    if (!existing) {
      bufferRef.current = incoming;
      return;
    }
    const merged = new Uint8Array(existing.length + incoming.length);
    merged.set(existing, 0);
    merged.set(incoming, existing.length);
    bufferRef.current = merged;
  }, []);

  const playBuffer = useCallback(
    (ctx: AudioContext, buffer: AudioBuffer) => {
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(ctx.destination);
      activeSourceRef.current = src;
      playingRef.current = true;
      setIsPlaying(true);
      src.onended = () => {
        activeSourceRef.current = null;
        playingRef.current = false;
        playNext();
      };
      src.start();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- playNext is stable via refs
    []
  );

  const playNext = useCallback(() => {
    if (playingRef.current) return;
    const next = queueRef.current.shift();
    if (!next) {
      setIsPlaying(false);
      return;
    }
    const ctx = ensureCtx();
    const start = () => playBuffer(ctx, next);
    if (ctx.state === "suspended") {
      // Resume is only granted after a user gesture (see `unlock`). If it is
      // still blocked, skip this burst rather than crashing.
      ctx.resume().then(start).catch(() => setIsPlaying(false));
    } else {
      start();
    }
  }, [ensureCtx, playBuffer]);

  const endBurst = useCallback(() => {
    const raw = bufferRef.current;
    bufferRef.current = null;
    if (!raw || raw.length === 0) return;
    const ctx = ensureCtx();
    void ctx
      .decodeAudioData(raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength))
      .then((audioBuffer) => {
        queueRef.current.push(audioBuffer);
        playNext();
      })
      .catch(() => {
        // Skip undecodable audio; the interviewer text is still shown.
      });
  }, [ensureCtx, playNext]);

  const stop = useCallback(() => {
    playingRef.current = false;
    queueRef.current = [];
    bufferRef.current = null;
    const active = activeSourceRef.current;
    if (active) {
      try {
        active.onended = null;
        active.stop();
      } catch {
        // Already stopped.
      }
      activeSourceRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  // Dispose the shared AudioContext on unmount.
  useEffect(() => {
    return () => {
      const ctx = ctxRef.current;
      if (ctx && ctx.state !== "closed") void ctx.close();
      ctxRef.current = null;
    };
  }, []);

  return { isPlaying, addChunk, endBurst, stop, clearBuffered, unlock };
}