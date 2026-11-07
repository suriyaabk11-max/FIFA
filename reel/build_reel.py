#!/usr/bin/env python3
"""
Build a 9:16 Instagram Reel: "Website + AI Automation" — client problems -> solutions.

Usage:
  python3 reel/build_reel.py                          # original synth beat
  python3 reel/build_reel.py --audio ref_audio.mp3    # use your own / reference audio
  python3 reel/build_reel.py --brand "Your Brand" --handle "@yourhandle" --keyword AUTOMATE

Requires: python3, numpy, pillow, ffmpeg.
"""
import argparse
import math
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BPM = 120
BEAT = 60.0 / BPM
SR = 44100
FONT_DIR = "/usr/share/fonts/opentype/inter"

# ----------------------------------------------------------------- palette
BG_TOP = (8, 10, 28)
BG_BOT = (20, 8, 40)
CYAN = (0, 229, 255)
VIOLET = (155, 92, 255)
RED = (255, 64, 96)
GREEN = (40, 230, 140)
WHITE = (255, 255, 255)
GREY = (170, 178, 200)

# ----------------------------------------------------------------- script
HOOK = ("Your business is", "losing clients.", "Every. Single. Day.")
PROBLEMS = [
    ("No website", "Customers can't find you —\nor don't trust you."),
    ("Missed calls & DMs", "Every unanswered message\nis a lost sale."),
    ("Same questions, 100x a day", "Price? Timing? Location?\nAgain. And again."),
    ("Leads lost in chats", "No system. No follow-up.\nNo sale."),
    ("Booking back-and-forth", "No-shows, double bookings,\nwasted hours."),
]
TURN = ("What if it all ran", "on autopilot?")
SOLUTIONS = [
    ("High-converting website", "Fast, mobile-first, built\nto turn visitors into leads."),
    ("AI assistant, 24/7", "Answers WhatsApp, Instagram\n& website chat instantly."),
    ("Auto lead capture + CRM", "Every lead saved, tagged\nand followed up for you."),
    ("Auto booking & reminders", "Clients book themselves.\nReminders cut no-shows."),
]

# timeline (seconds) — every boundary sits on a beat (0.5 s)
T_HOOK = (0.0, 2.5)
T_PROB = (2.5, 12.5)        # 5 x 2.0 s
T_TURN = (12.5, 14.5)
T_SOL = (14.5, 22.5)        # 4 x 2.0 s
T_CTA = (22.5, 27.0)
DURATION = T_CTA[1]


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"InterDisplay-{weight}.otf"), size)


F_HUGE = font("Black", 120)
F_BIG = font("ExtraBold", 92)
F_MED = font("Bold", 64)
F_SUB = font("Medium", 46)
F_SMALL = font("SemiBold", 36)
F_TAG = font("Bold", 34)


# ----------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# ----------------------------------------------------------------- background
def make_bg():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array(BG_TOP), np.array(BG_BOT)
    grad = (top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None])
    grad = np.repeat(grad, W, axis=1)
    return grad.astype(np.float32)


BG = make_bg()
random.seed(7)
PARTICLES = [(random.random() * W, random.random() * H, random.uniform(1.5, 4), random.uniform(10, 40))
             for _ in range(70)]


def background(t, accent):
    img = Image.fromarray(BG.astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    # moving perspective grid
    off = (t * 120) % 120
    for i in range(-1, 18):
        yy = int(1250 + i * 60 + off * 0.5)
        if yy < H:
            d.line([(0, yy), (W, yy)], fill=(*accent, 22), width=2)
    for i in range(-10, 11):
        d.line([(W / 2 + i * 40, 1250), (W / 2 + i * 260, H)], fill=(*accent, 18), width=2)
    # particles
    for (px, py, r, sp) in PARTICLES:
        yy = (py - t * sp) % H
        d.ellipse([px - r, yy - r, px + r, yy + r], fill=(*accent, 90))
    # glow blob
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = W / 2 + math.sin(t * 0.8) * 160, 760 + math.cos(t * 0.6) * 90
    gd.ellipse([cx - 420, cy - 420, cx + 420, cy + 420], fill=(*accent, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.paste(glow, (0, 0), glow)
    return img


# ----------------------------------------------------------------- text helpers
def text_layer(lines, fonts, colors, spacing=24):
    """Render centred lines onto a transparent layer sized to fit; returns layer."""
    sizes = []
    for ln, f in zip(lines, fonts):
        b = f.getbbox(ln)
        sizes.append((b[2] - b[0], b[3] - b[1], b[1]))
    lw = max(s[0] for s in sizes) + 40
    lh = sum(s[1] for s in sizes) + spacing * (len(lines) - 1) + 40
    layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 20
    for (ln, f, c), (sw, sh, top) in zip(zip(lines, fonts, colors), sizes):
        d.text(((lw - sw) / 2, y - top), ln, font=f, fill=c)
        y += sh + spacing
    return layer


def paste_center(img, layer, cx, cy, scale=1.0, alpha=1.0, glow=None):
    if scale <= 0.01 or alpha <= 0.01:
        return
    lw, lh = layer.size
    nw, nh = max(1, int(lw * scale)), max(1, int(lh * scale))
    L = layer.resize((nw, nh), Image.LANCZOS)
    if alpha < 1:
        a = L.split()[3].point(lambda v: int(v * alpha))
        L.putalpha(a)
    x, y = int(cx - nw / 2), int(cy - nh / 2)
    if glow:
        g = Image.new("RGBA", L.size, (*glow, 0))
        g.putalpha(L.split()[3].point(lambda v: int(v * 0.8)))
        g = g.filter(ImageFilter.GaussianBlur(18))
        img.paste(g, (x, y), g)
    img.paste(L, (x, y), L)


def multiline_sub(text, f=F_SUB, color=GREY):
    return text_layer(text.split("\n"), [f] * len(text.split("\n")), [color] * len(text.split("\n")), 14)


def badge(img, cx, cy, kind, prog):
    """Red X or green check in a circle, pops in."""
    s = ease_out_back(prog)
    if s <= 0:
        return
    R = int(95 * s)
    col = RED if kind == "x" else GREEN
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - R - 18, cy - R - 18, cx + R + 18, cy + R + 18], fill=(*col, 40))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col, width=max(2, int(10 * s)))
    k = R * 0.45
    w = max(2, int(16 * s))
    if kind == "x":
        d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=col, width=w)
        d.line([(cx - k, cy + k), (cx + k, cy - k)], fill=col, width=w)
    else:
        d.line([(cx - k, cy + 2), (cx - k * 0.2, cy + k * 0.75), (cx + k, cy - k * 0.7)],
               fill=col, width=w, joint="curve")


def pill(img, cx, cy, text, col, f=F_TAG):
    b = f.getbbox(text)
    tw, th = b[2] - b[0], b[3] - b[1]
    d = ImageDraw.Draw(img, "RGBA")
    pw, ph = tw + 60, th + 34
    d.rounded_rectangle([cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2], radius=ph / 2,
                        fill=(*col, 45), outline=(*col, 200), width=3)
    d.text((cx - tw / 2, cy - th / 2 - b[1]), text, font=f, fill=WHITE)


def counter_bar(img, idx, total, col, t_local):
    d = ImageDraw.Draw(img, "RGBA")
    seg, gap = 120, 18
    full = total * seg + (total - 1) * gap
    x0 = (W - full) / 2
    for i in range(total):
        x = x0 + i * (seg + gap)
        d.rounded_rectangle([x, 300, x + seg, 312], radius=6, fill=(255, 255, 255, 50))
        if i < idx:
            d.rounded_rectangle([x, 300, x + seg, 312], radius=6, fill=col)
        elif i == idx:
            d.rounded_rectangle([x, 300, x + seg * clamp(t_local / 2.0), 312], radius=6, fill=col)


# ----------------------------------------------------------------- mock UI for AI chat
def chat_mock(img, t_local, brand):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = 170, 1180, 910, 1700
    d.rounded_rectangle([x0, y0, x1, y1], radius=40, fill=(255, 255, 255, 18), outline=(*CYAN, 120), width=3)
    d.text((x0 + 40, y0 + 28), f"{brand} AI  •  online", font=F_SMALL, fill=GREEN)
    msgs = [
        (0.15, "user", "Hi, price for a website?"),
        (0.55, "bot", "Plans start from a starter pack."),
        (0.85, "bot", "Want me to book a free call?"),
        (1.25, "user", "Yes, tomorrow 11am"),
        (1.55, "bot", "Booked! Reminder sent ✓"),
    ]
    y = y0 + 95
    for (ts, who, txt) in msgs:
        p = ease_out((t_local - ts) / 0.2)
        if p <= 0:
            continue
        b = F_SMALL.getbbox(txt)
        tw, th = b[2] - b[0], b[3] - b[1]
        bw, bh = tw + 44, th + 30
        if who == "user":
            bx = x1 - 30 - bw
            col = (*VIOLET, int(200 * p))
        else:
            bx = x0 + 30
            col = (*CYAN, int(70 * p))
        by = y + (1 - p) * 30
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=24, fill=col)
        d.text((bx + 22, by + 15 - b[1]), txt, font=F_SMALL, fill=(255, 255, 255, int(255 * p)))
        y += bh + 16


# ----------------------------------------------------------------- website mock
def site_mock(img, t_local):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = 190, 1190, 890, 1690
    p = ease_out(t_local / 0.4)
    d.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=(255, 255, 255, 20), outline=(*CYAN, 120), width=3)
    d.rounded_rectangle([x0, y0, x1, y0 + 56], radius=30, fill=(255, 255, 255, 30))
    for i, c in enumerate([RED, (255, 200, 60), GREEN]):
        d.ellipse([x0 + 30 + i * 36, y0 + 18, x0 + 52 + i * 36, y0 + 40], fill=c)
    blocks = [(0.1, (x0 + 50, y0 + 100, x1 - 50, y0 + 150), VIOLET),
              (0.25, (x0 + 50, y0 + 175, x1 - 200, y0 + 205), GREY),
              (0.35, (x0 + 50, y0 + 225, x1 - 280, y0 + 255), GREY),
              (0.5, (x0 + 50, y0 + 300, x0 + 330, y0 + 370), CYAN),
              (0.65, (x0 + 50, y0 + 400, x0 + 320, y1 - 40), (255, 255, 255)),
              (0.75, (x0 + 360, y0 + 400, x1 - 50, y1 - 40), (255, 255, 255))]
    for ts, (a, b, c, e), col in blocks:
        q = ease_out((t_local - ts) / 0.25) * p
        if q > 0:
            d.rounded_rectangle([a, b, a + (c - a) * q, e], radius=14, fill=(*col, int(150 * q)))
    if t_local > 0.5:
        bb = F_SMALL.getbbox("Book Now")
        d.text((x0 + 190 - (bb[2] - bb[0]) / 2, y0 + 335 - (bb[3] - bb[1]) / 2 - bb[1]), "Book Now",
               font=F_SMALL, fill=(10, 10, 30))


def flow_mock(img, t_local):
    d = ImageDraw.Draw(img, "RGBA")
    nodes = [("Lead", 230), ("AI", 540), ("CRM", 850)]
    cy = 1430
    for i, (name, cx) in enumerate(nodes):
        p = ease_out_back((t_local - i * 0.2) / 0.3)
        if p <= 0:
            continue
        r = 105 * p
        col = [VIOLET, CYAN, GREEN][i]
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, 50), outline=col, width=5)
        b = F_MED.getbbox(name)
        if p > 0.6:
            d.text((cx - (b[2] - b[0]) / 2, cy - (b[3] - b[1]) / 2 - b[1]), name, font=F_MED, fill=WHITE)
    for i in range(2):
        a, b = nodes[i][1] + 110, nodes[i + 1][1] - 110
        q = clamp((t_local - 0.3 - i * 0.2) / 0.3)
        if q > 0:
            d.line([(a, cy), (a + (b - a) * q, cy)], fill=WHITE, width=6)
            dot = a + ((t_local * 300) % (b - a))
            if q >= 1:
                d.ellipse([dot - 10, cy - 10, dot + 10, cy + 10], fill=CYAN)


def calendar_mock(img, t_local):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0 = 220, 1200
    cell, gap = 110, 14
    for r in range(4):
        for c in range(5):
            i = r * 5 + c
            q = ease_out((t_local - i * 0.025) / 0.2)
            if q <= 0:
                continue
            x, y = x0 + c * (cell + gap), y0 + r * (cell + gap)
            booked = i in (2, 6, 9, 13, 17)
            col = GREEN if booked else (255, 255, 255)
            alpha = 170 if booked else 30
            d.rounded_rectangle([x, y, x + cell, y + cell], radius=18, fill=(*col, int(alpha * q)))
            if booked and q > 0.8:
                k = 22
                cx, cy = x + cell / 2, y + cell / 2
                d.line([(cx - k, cy), (cx - 5, cy + k * 0.7), (cx + k, cy - k * 0.6)], fill=(10, 30, 20), width=9)


# ----------------------------------------------------------------- scenes
def scene_hook(img, t):
    l1 = text_layer([HOOK[0]], [F_BIG], [WHITE])
    l2 = text_layer([HOOK[1]], [F_HUGE], [RED])
    paste_center(img, l1, W / 2, 780, ease_out_back(t / 0.35))
    paste_center(img, l2, W / 2, 920, ease_out_back((t - 0.4) / 0.35), glow=RED)
    words = HOOK[2].split(" ")
    space = 26
    widths = [F_MED.getbbox(wd)[2] - F_MED.getbbox(wd)[0] for wd in words]
    x = W / 2 - (sum(widths) + space * (len(words) - 1)) / 2
    for i, (wd, ww) in enumerate(zip(words, widths)):
        tt = 1.0 + i * 0.25
        if t > tt:
            lw = text_layer([wd], [F_MED], [WHITE])
            paste_center(img, lw, x + ww / 2, 1120, ease_out_back((t - tt) / 0.2))
        x += ww + space


def scene_item(img, t, idx, total, title, sub, kind, brand):
    col = RED if kind == "x" else GREEN
    label = f"PROBLEM {idx + 1}/{total}" if kind == "x" else f"SOLUTION {idx + 1}/{total}"
    counter_bar(img, idx, total, col, t)
    pill(img, W / 2, 400, label, col)
    badge(img, W / 2, 620, kind, t / 0.3)
    lt = text_layer([title], [F_BIG if len(title) < 20 else F_MED], [WHITE])
    paste_center(img, lt, W / 2, 850, ease_out_back((t - 0.15) / 0.3), glow=col)
    ls = multiline_sub(sub)
    paste_center(img, ls, W / 2, 1020, 1.0, alpha=ease_out((t - 0.35) / 0.3))
    if kind == "x":
        # strike / glitch shake handled globally; add crossed visuals
        d = ImageDraw.Draw(img, "RGBA")
        if t > 0.6:
            q = ease_out((t - 0.6) / 0.25)
            d.rounded_rectangle([170, 1240, 170 + 740 * q, 1252], radius=6, fill=(*RED, 160))
            lost = text_layer(["LOST REVENUE"], [F_MED], [(*RED, 255)])
            paste_center(img, lost, W / 2, 1360, ease_out_back((t - 0.75) / 0.25))
    else:
        mock = [site_mock, chat_mock, flow_mock, calendar_mock][idx]
        if mock is chat_mock:
            chat_mock(img, t - 0.3, brand)
        else:
            mock(img, t - 0.3)


def scene_turn(img, t):
    l1 = text_layer([TURN[0]], [F_BIG], [WHITE])
    l2 = text_layer([TURN[1]], [F_HUGE], [CYAN])
    paste_center(img, l1, W / 2, 840, ease_out_back(t / 0.3))
    paste_center(img, l2, W / 2, 990, ease_out_back((t - 0.5) / 0.35), glow=CYAN)
    if t > 1.0:
        pill(img, W / 2, 1200, "WEBSITE  +  AI AUTOMATION", VIOLET)


def scene_cta(img, t, brand, handle, keyword):
    l0 = text_layer(["Stop losing clients."], [F_BIG], [WHITE])
    paste_center(img, l0, W / 2, 560, ease_out_back(t / 0.3))
    l1 = text_layer(["Website + AI Automation"], [F_MED], [CYAN])
    paste_center(img, l1, W / 2, 690, ease_out_back((t - 0.25) / 0.3))
    l2 = text_layer(["Comment"], [F_MED], [GREY])
    paste_center(img, l2, W / 2, 900, ease_out((t - 0.6) / 0.3))
    pulse = 1 + 0.05 * math.sin(t * 2 * math.pi / BEAT) if t > 1 else 1
    l3 = text_layer([f"“{keyword}”"], [F_HUGE], [GREEN])
    paste_center(img, l3, W / 2, 1040, ease_out_back((t - 0.8) / 0.3) * pulse, glow=GREEN)
    l4 = multiline_sub("& get a FREE automation audit\nfor your business")
    paste_center(img, l4, W / 2, 1230, 1.0, alpha=ease_out((t - 1.2) / 0.3))
    if t > 1.6:
        pill(img, W / 2, 1460, f"{brand}  •  {handle}", VIOLET, F_SMALL)


def render_frame(t, brand, handle, keyword):
    if T_HOOK[0] <= t < T_HOOK[1]:
        accent = RED
    elif T_PROB[0] <= t < T_PROB[1]:
        accent = RED
    elif T_TURN[0] <= t < T_TURN[1]:
        accent = CYAN
    elif T_SOL[0] <= t < T_SOL[1]:
        accent = GREEN
    else:
        accent = VIOLET
    img = background(t, accent)  # RGB base so RGBA drawing blends

    if t < T_HOOK[1]:
        scene_hook(img, t - T_HOOK[0])
    elif t < T_PROB[1]:
        i = int((t - T_PROB[0]) // 2.0)
        scene_item(img, (t - T_PROB[0]) - i * 2.0, i, len(PROBLEMS), *PROBLEMS[i], "x", brand)
    elif t < T_TURN[1]:
        scene_turn(img, t - T_TURN[0])
    elif t < T_SOL[1]:
        i = int((t - T_SOL[0]) // 2.0)
        scene_item(img, (t - T_SOL[0]) - i * 2.0, i, len(SOLUTIONS), *SOLUTIONS[i], "check", brand)
    else:
        scene_cta(img, t - T_CTA[0], brand, handle, keyword)

    # beat punch-zoom + flash at scene cuts
    beat_phase = (t % BEAT) / BEAT
    zoom = 1 + 0.018 * (1 - beat_phase) ** 4
    cuts = [T_HOOK[1]] + [T_PROB[0] + 2 * k for k in range(1, 5)] + [T_PROB[1], T_TURN[1]] + \
           [T_SOL[0] + 2 * k for k in range(1, 4)] + [T_SOL[1]]
    flash = 0.0
    for c in cuts:
        if 0 <= t - c < 0.12:
            flash = max(flash, 1 - (t - c) / 0.12)
    img = img.convert("RGB")
    if zoom > 1.001:
        nw, nh = int(W * zoom), int(H * zoom)
        img = img.resize((nw, nh), Image.BILINEAR).crop(((nw - W) // 2, (nh - H) // 2,
                                                         (nw - W) // 2 + W, (nh - H) // 2 + H))
    # glitch shift during problem section on cuts
    if T_PROB[0] <= t < T_PROB[1] and ((t - T_PROB[0]) % 2.0) < 0.1:
        arr = np.array(img)
        arr[..., 0] = np.roll(arr[..., 0], 14, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -14, axis=1)
        img = Image.fromarray(arr)
    if flash > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), flash * 0.55)
    # fade out at end
    if t > DURATION - 0.4:
        img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), clamp((t - (DURATION - 0.4)) / 0.4))
    return img


# ----------------------------------------------------------------- music (original, synthesised)
def synth_music(path):
    n = int(DURATION * SR)
    out = np.zeros(n, dtype=np.float64)
    tt = np.arange(n) / SR

    def add(sig, start):
        s = int(start * SR)
        e = min(n, s + len(sig))
        if s < n:
            out[s:e] += sig[: e - s]

    def kick():
        L = int(0.35 * SR)
        x = np.arange(L) / SR
        f = 45 + 110 * np.exp(-x * 30)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return 0.9 * np.sin(ph) * np.exp(-x * 9)

    def clap():
        L = int(0.25 * SR)
        x = np.arange(L) / SR
        nz = np.random.RandomState(1).randn(L)
        return 0.35 * nz * np.exp(-x * 22)

    def hat():
        L = int(0.06 * SR)
        x = np.arange(L) / SR
        nz = np.random.RandomState(2).randn(L)
        nz = np.diff(np.concatenate([[0], nz]))
        return 0.12 * nz * np.exp(-x * 70)

    def impact():
        L = int(1.5 * SR)
        x = np.arange(L) / SR
        nz = np.random.RandomState(3).randn(L) * np.exp(-x * 4) * 0.3
        boom = np.sin(2 * np.pi * (40 + 60 * np.exp(-x * 8)) * x) * np.exp(-x * 2.5)
        return nz + boom

    def riser(dur):
        L = int(dur * SR)
        x = np.arange(L) / SR
        nz = np.random.RandomState(4).randn(L)
        env = (x / dur) ** 2
        sweep = np.sin(2 * np.pi * (200 + 1800 * (x / dur) ** 2) * x)
        return 0.18 * nz * env + 0.12 * sweep * env

    # chord progression Am - F - C - G (one bar = 4 beats = 2 s)
    roots = [55.0, 43.65, 65.41, 49.0]
    chords = [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392], [196, 246.94, 293.66]]

    beats = int(DURATION / BEAT)
    for b in range(beats):
        t0 = b * BEAT
        in_turn = T_TURN[0] <= t0 < T_TURN[1]
        in_cta_end = t0 >= DURATION - 1.0
        if t0 >= T_HOOK[1] and not in_turn and not in_cta_end:
            add(kick(), t0)
            if b % 2 == 1:
                add(clap(), t0)
        if t0 < T_HOOK[1] and b % 2 == 0:
            add(kick() * 0.7, t0)
        if t0 >= T_HOOK[1] and not in_turn and not in_cta_end:
            add(hat(), t0 + BEAT / 2)
            if t0 >= T_SOL[0]:
                add(hat() * 0.7, t0 + BEAT / 4)
                add(hat() * 0.7, t0 + 3 * BEAT / 4)

    # bass + pad
    bar = 4 * BEAT
    for k in range(int(math.ceil(DURATION / bar))):
        s = k * bar
        ci = k % 4
        L = int(bar * SR)
        x = np.arange(L) / SR
        # pad
        pad = sum(np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 1.005 * x) for f in chords[ci])
        pad *= 0.045 * np.minimum(1, x / 0.3) * np.minimum(1, (bar - x) / 0.3)
        add(pad, s)
        # bass on 8ths, sidechain-ish pump
        if s >= T_HOOK[1] and not (T_TURN[0] <= s < T_TURN[1]):
            f = roots[ci]
            bs = np.sign(np.sin(2 * np.pi * f * x)) * 0.5 + np.sin(2 * np.pi * f * x)
            pump = 1 - 0.8 * np.exp(-((x % BEAT)) * 12)
            add(0.13 * bs * pump, s)

    add(riser(T_TURN[1] - T_TURN[0]), T_TURN[0])
    add(impact() * 0.7, T_PROB[0])
    add(impact(), T_SOL[0])
    add(impact() * 0.8, T_CTA[0])
    add(impact() * 0.6, DURATION - 1.0)

    # soft clip + normalise + fade out
    out = np.tanh(out * 1.2)
    out /= np.max(np.abs(out)) + 1e-9
    out *= 0.89
    fade = int(0.6 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    pcm = (out * 32767).astype(np.int16)
    stereo = np.stack([pcm, pcm], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reel/output/website_ai_automation_reel.mp4")
    ap.add_argument("--audio", help="optional audio file to use instead of the built-in beat")
    ap.add_argument("--audio-offset", type=float, default=0.0, help="seconds to skip into --audio")
    ap.add_argument("--brand", default="Your Brand")
    ap.add_argument("--handle", default="@yourhandle")
    ap.add_argument("--keyword", default="AUTOMATE")
    ap.add_argument("--preview", action="store_true", help="also save PNG stills of key moments")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    audio = a.audio
    if not audio:
        audio = os.path.join(os.path.dirname(a.out), "beat.wav")
        synth_music(audio)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", str(a.audio_offset), "-i", audio,
           "-map", "0:v", "-map", "1:a", "-t", str(DURATION),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={DURATION - 0.6}:d=0.6",
           "-movflags", "+faststart", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    stills = {int(x * FPS) for x in (1.8, 3.6, 7.6, 13.8, 17.2, 21.2, 25.0)}
    for f in range(total):
        img = render_frame(f / FPS, a.brand, a.handle, a.keyword)
        p.stdin.write(img.tobytes())
        if a.preview and f in stills:
            img.save(os.path.join(os.path.dirname(a.out), f"still_{f / FPS:05.1f}s.png"))
        if f % 90 == 0:
            print(f"frame {f}/{total}", flush=True)
    p.stdin.close()
    p.wait()
    print("done ->", a.out)


if __name__ == "__main__":
    main()
