---
name: audio
description: Pipeline stage 03 — audio polish to the Buwan loudness specs (dialogue −17 LUFS, peaks −6 dBFS, music bed −20 dB), measured, in any editing app. Use when an editor says audio, mix, loudness, levels, clean up audio, or after the proof gate passes.
argument-hint: "[project folder]"
---

# 03 Audio polish

Clean speech is the spine of the film. Targets: **dialogue −17 LUFS integrated**, **true peak ≤ −6 dBFS**, **music bed flat −20 dB** (opt-in), SFX under the dialogue.

1. **Check the gate** — the proof gate must have passed (or been overridden in the paper edit).
2. **Measure the speech clips** in the cut: for each source clip used on the speech tracks, `ffmpeg -i <clip> -af ebur128=peak=true -f null -` and list integrated LUFS, true peak and loudness range. Flag clips with noise floor above −50 dBFS, clipping, or wind/handling noise.
3. **Fix per app** (editor's playbook):
   - Premiere: Essential Sound → Dialogue → Repair (Reduce Noise ≤ 4, DeHum, DeReverb only if needed) → Loudness Auto-Match to −17 LUFS → Hard Limiter on the dialogue submix at −6 dB. Music clips: Essential Sound → Music → volume −20 dB.
   - Resolve (Fairlight): Noise Reduction on noisy clips → Normalize Audio Levels (BS.1770, −17 LUFS, true peak −6) on dialogue → Limiter on the dialogue bus at −6 → music clip gain −20 dB.
   - Final Cut: Voice Isolation ≤ 50% on noisy clips → Loudness effect / Adaptive Limiter on the Dialogue role (ceiling −6) → Music role −20 dB.
   - Taglish speech: never cut or "clean" words; only remove noise between words.
4. **Verify** — export a mixdown WAV of the timeline to `edit/audio/mix_vN.wav` and measure it. Report: integrated LUFS, true peak, LRA, and PASS/FAIL against the targets. Dialogue-only sections must read −17 ±1 LUFS.

Same-day mode: auto-match + limiter only, one measurement pass.
