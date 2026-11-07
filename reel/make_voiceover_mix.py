#!/usr/bin/env python3
"""Cut the ElevenLabs voiceover into lines and place each one on the pendulum timeline.

Usage: python3 reel/make_voiceover_mix.py VOICE.mp3 MUSIC_SOURCE VIDEO_IN VIDEO_OUT
Line boundaries (seconds in VOICE.mp3) come from ffmpeg silencedetect on take 1.
"""
import subprocess
import sys

voice, music, video_in, video_out = sys.argv[1:5]
PAD = 0.04
# (start, end) in the voice file  ->  start time in the reel
LINES = [
    ((0.00, 0.875), 0.05),    # Need a website?
    ((1.649, 2.239), 1.00),   # Sorted.
    ((3.453, 4.218), 1.95),   # Missing leads?
    ((5.039, 5.540), 3.40),   # Sorted.
    ((6.615, 7.969), 4.30),   # Slow DM replies?
    ((8.618, 9.176), 5.80),   # Sorted.
    ((10.249, 11.256), 6.70), # Manual follow-ups?
    ((11.843, 12.395), 8.20), # Sorted.
    ((13.511, 14.156), 9.10), # Need an app?
    ((14.931, 15.451), 10.60),# Sorted.
    ((16.567, 17.268), 11.50),# Need all of it?
    ((18.177, 19.093), 13.00),# DM us.
    ((20.650, 21.701), 16.20),# Visionary ByteWorks.
    ((22.626, 23.413), 17.60),# Follow for more.
]

parts, labels = [], []
for i, ((a, b), at) in enumerate(LINES):
    a2, b2 = max(0, a - PAD), b + PAD
    d = b2 - a2
    ms = int(at * 1000)
    parts.append(f"[0:a]atrim={a2}:{b2},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,"
                 f"afade=t=out:st={d - 0.04:.3f}:d=0.04,adelay={ms}|{ms}[v{i}]")
    labels.append(f"[v{i}]")
fc = ";".join(parts)
fc += f";{''.join(labels)}amix=inputs={len(LINES)}:normalize=0,volume=1.6[vo]"
fc += ";[1:a]volume=0.32[mus];[mus][vo]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]"
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", voice, "-i", music, "-i", video_in,
       "-filter_complex", fc, "-map", "2:v", "-map", "[a]", "-t", "20",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", video_out]
subprocess.run(cmd, check=True)
print("done ->", video_out)
