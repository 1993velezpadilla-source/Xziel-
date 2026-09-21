#!/usr/bin/env python3
"""Generate original Enchanted audio cues with no third-party samples.

These are intentionally not copies of Call of Duty recordings or music. They
fill the same gameplay roles (round omen, cursed-box hum, game-over sting) so
we can practice the presentation pipeline safely. Authorized local WaW audio,
when explicitly supplied by the developer, may still override these cues in
the private reference build.
"""
from pathlib import Path
import math
import random
import struct
import sys
import wave

if len(sys.argv) != 2:
    raise SystemExit("usage: build_nacht_enchanted_audio.py <nzp-root>")

root = Path(sys.argv[1])
out = root / "sounds/xziel/enchant"
out.mkdir(parents=True, exist_ok=True)
SR = 44100

def write_wav(path: Path, samples):
    peak = max(1e-9, max(abs(x) for x in samples))
    gain = min(0.92 / peak, 1.0)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for x in samples:
            y = max(-1.0, min(1.0, x * gain))
            frames += struct.pack("<h", int(y * 32767))
        w.writeframes(frames)

def echo(samples, delays=((0.17, 0.32), (0.31, 0.19))):
    outv = list(samples)
    for seconds, amount in delays:
        d = int(seconds * SR)
        for i in range(d, len(outv)):
            outv[i] += samples[i-d] * amount
    return outv

def round_omen():
    dur = 3.2
    n = int(dur * SR)
    rng = random.Random(0xE11A)
    s = [0.0] * n
    # Three descending "ha" formant pulses: intentionally synthetic and
    # inhuman, avoiding imitation of an identifiable performance.
    starts = [0.35, 0.92, 1.52, 2.08]
    pitches = [132.0, 121.0, 111.0, 96.0]
    for start, f0 in zip(starts, pitches):
        a = int(start * SR)
        length = int(0.42 * SR)
        for j in range(length):
            i = a + j
            if i >= n:
                break
            t = j / SR
            env = math.sin(math.pi * min(1.0, t / 0.08)) * math.exp(-3.8 * max(0.0, t - 0.08))
            wobble = 1.0 + 0.045 * math.sin(2*math.pi*5.1*t)
            phase = 2*math.pi*f0*wobble*t
            formants = (
                0.42 * math.sin(phase) +
                0.28 * math.sin(phase * 3.45) +
                0.18 * math.sin(phase * 6.7)
            )
            breath = (rng.random()*2-1) * 0.12
            s[i] += env * (formants + breath)
    # Low omen underneath the laugh pulses.
    for i in range(n):
        t = i / SR
        env = min(1.0, t / 0.25) * min(1.0, (dur - t) / 0.7)
        s[i] += env * (0.12*math.sin(2*math.pi*55*t) + 0.07*math.sin(2*math.pi*82.5*t))
    return echo(s, ((0.19, 0.38), (0.43, 0.20)))

def box_hum():
    dur = 8.0
    n = int(dur * SR)
    s = [0.0] * n
    for i in range(n):
        t = i / SR
        drift = 1.0 + 0.012*math.sin(2*math.pi*0.17*t)
        hum = 0.12*math.sin(2*math.pi*73.4*drift*t) + 0.08*math.sin(2*math.pi*110.1*t)
        shimmer = 0.025*math.sin(2*math.pi*(523.25 + 9*math.sin(2*math.pi*0.21*t))*t)
        pulse = 0.65 + 0.35*math.sin(2*math.pi*0.42*t)
        s[i] = (hum + shimmer) * pulse
    # sparse original bell-like transients
    for start, freq in [(1.1, 659.25), (3.4, 783.99), (5.9, 587.33)]:
        a = int(start*SR)
        for j in range(int(1.2*SR)):
            i = a+j
            if i >= n: break
            t = j/SR
            s[i] += 0.10*math.exp(-4.0*t)*math.sin(2*math.pi*freq*t)
    return echo(s, ((0.23, 0.23), (0.51, 0.12)))

def gameover_guitar():
    dur = 5.5
    n = int(dur*SR)
    s = [0.0] * n
    # Original minor power-chord descent. No melody or recording is copied.
    chords = [(0.15, 82.41), (1.55, 73.42), (2.95, 65.41), (4.05, 55.00)]
    for start, rootf in chords:
        a = int(start*SR)
        length = int(1.6*SR)
        for j in range(length):
            i = a+j
            if i >= n: break
            t = j/SR
            env = math.exp(-1.75*t) * min(1.0, t/0.012)
            raw = (
                0.50*math.sin(2*math.pi*rootf*t) +
                0.34*math.sin(2*math.pi*rootf*1.5*t) +
                0.22*math.sin(2*math.pi*rootf*2.0*t) +
                0.12*math.sin(2*math.pi*rootf*3.0*t)
            )
            # soft-clipped distortion approximates an ominous guitar texture
            s[i] += env * math.tanh(raw*2.3) * 0.38
    return echo(s, ((0.14, 0.22), (0.29, 0.15), (0.57, 0.08)))

write_wav(out / "round_omen.wav", round_omen())
write_wav(out / "mystery_hum.wav", box_hum())
write_wav(out / "gameover_guitar.wav", gameover_guitar())
print("Generated original Enchanted round omen, Mystery Box hum and game-over guitar cue.")
