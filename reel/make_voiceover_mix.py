#!/usr/bin/env python3
"""Cut the ElevenLabs voiceover into lines, slow it slightly, and place each line on the
pendulum timeline over a soft bed of original sound effects (swing whooshes + landing ticks).

The reference reel's audio is its creator's own voiceover, so it is NOT used except for
the short impact hit at 16.2 s (no speech in it).

Usage: python3 reel/make_voiceover_mix.py VOICE.mp3 REFERENCE.mp4 VIDEO_IN VIDEO_OUT [TEMPO]
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

voice, ref, video_in, video_out = sys.argv[1:5]
TEMPO = float(sys.argv[5]) if len(sys.argv) > 5 else 0.9   # <1 = slower speech, same pitch
PAD = 0.04
SR = 44100
DUR = 20.0
PERIOD = 2.4

# (start, end) of each line in the voice file  ->  start time in the reel
LINES = [
    ((0.000, 0.875), 0.05),   # Need a website?
    ((1.649, 2.239), 1.15),   # Sorted.
    ((3.453, 4.218), 1.95),   # Missing leads?
    ((5.039, 5.540), 3.45),   # Sorted.
    ((6.615, 7.969), 4.15),   # Slow DM replies?
    ((8.618, 9.176), 5.90),   # Sorted.
    ((10.249, 11.256), 6.70), # Manual follow-ups?
    ((11.843, 12.395), 8.25), # Sorted.
    ((13.511, 14.156), 9.05), # Need an app?
    ((14.931, 15.451), 10.65),# Sorted.
    ((16.567, 17.268), 11.45),# Need all of it?
    ((18.177, 19.093), 12.95),# DM us.
    ((20.650, 21.701), 16.45),# Visionary ByteWorks.
    ((22.626, 23.413), 17.75),# Follow for more.
]


def sfx_bed(path):
    """Soft whoosh on every half swing, a tick when the ball lands, a low pad."""
    n = int(DUR * SR)
    out = np.zeros(n)
    rng = np.random.RandomState(5)

    def add(sig, t):
        s = int(t * SR)
        e = min(n, s + len(sig))
        if 0 <= s < n:
            out[s:e] += sig[: e - s]

    # whoosh: band-limited noise swelling to the middle of each half swing
    L = int(1.0 * SR)
    x = np.arange(L) / SR
    nz = rng.randn(L)
    k = np.exp(-np.linspace(-3, 3, 41) ** 2)
    nz = np.convolve(nz, k / k.sum(), mode="same")
    env = np.sin(np.pi * x / 1.0) ** 3
    whoosh = 0.10 * nz * env
    for i in range(11):                    # 11 half swings until the ball stops at 13.2 s
        add(whoosh, i * PERIOD / 2 + 0.1)

    # tick when the ball lands on the right ("Sorted." / "DM us.")
    Lt = int(0.08 * SR)
    xt = np.arange(Lt) / SR
    tick = 0.35 * np.sin(2 * np.pi * 1800 * xt) * np.exp(-xt * 70)
    for t in [1.2, 3.6, 6.0, 8.4, 10.8, 13.2]:
        add(tick, t)

    # very quiet low pad under everything until the end card
    pad = 0.025 * (np.sin(2 * np.pi * 55 * np.arange(n) / SR) + 0.6 * np.sin(2 * np.pi * 82.4 * np.arange(n) / SR))
    fade = np.clip(np.arange(n) / (1.0 * SR), 0, 1) * np.clip((DUR - np.arange(n) / SR) / 1.5, 0, 1)
    out += pad * fade

    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


tmp = tempfile.mkdtemp()
bed = os.path.join(tmp, "bed.wav")
sfx_bed(bed)

parts, labels = [], []
for i, ((a, b), at) in enumerate(LINES):
    a2, b2 = max(0, a - PAD), b + PAD
    d = (b2 - a2) / TEMPO
    ms = int(at * 1000)
    parts.append(f"[0:a]atrim={a2}:{b2},asetpts=PTS-STARTPTS,atempo={TEMPO},afade=t=in:d=0.02,"
                 f"afade=t=out:st={d - 0.05:.3f}:d=0.05,adelay={ms}|{ms}[v{i}]")
    labels.append(f"[v{i}]")
fc = ";".join(parts)
fc += f";{''.join(labels)}amix=inputs={len(LINES)}:normalize=0,volume=1.5[vo]"
# impact hit from the reference (16.2-17.6 s, no speech in it)
fc += ";[1:a]atrim=16.15:17.6,asetpts=PTS-STARTPTS,volume=0.55,adelay=16150|16150[hit]"
fc += ";[2:a]volume=1.0[bed]"
fc += ";[bed][hit][vo]amix=inputs=3:normalize=0:duration=longest,atrim=0:20,alimiter=limit=0.95[a]"
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", voice, "-i", ref, "-i", bed, "-i", video_in,
       "-filter_complex", fc, "-map", "3:v", "-map", "[a]", "-t", str(DUR),
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", video_out]
subprocess.run(cmd, check=True)

# overlap check: each line must end before the next starts
ends = []
for (a, b), at in LINES:
    ends.append((at, at + (b - a + 2 * PAD) / TEMPO))
for (s1, e1), (s2, _) in zip(ends, ends[1:]):
    assert e1 < s2, f"overlap: line ending {e1:.2f}s runs into line starting {s2:.2f}s"
print("no overlaps; done ->", video_out)
