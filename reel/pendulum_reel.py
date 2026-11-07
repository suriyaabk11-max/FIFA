#!/usr/bin/env python3
"""
Pendulum "Need ...? -> Sorted." reel for a Website + AI Automation service.

A red ball on a string swings across a black screen. The string wipes each client
problem (grey, right of the string) into a white "Sorted." (left of the string),
with the ball landing as its full stop. It ends on "DM us." and an Instagram card.

Usage:
  python3 reel/pendulum_reel.py --audio reference.mp4
  python3 reel/pendulum_reel.py --audio ref.mp4 --brand "your brand" --handle "@YOURHANDLE"
"""
import argparse
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# all layout numbers are authored on a 720x1280 grid and scaled by S
S = 1.5
W, H, FPS = int(720 * S), int(1280 * S), 30
TOTAL_F = 600  # 20 s

FONT_DIR = "/usr/share/fonts/opentype/inter"
BG = (11, 10, 12)
WHITE = (242, 239, 238)
GREY = (140, 140, 142)
RED = (240, 20, 34)

QUESTIONS = [
    ("Need a", "website?"),
    ("Missing", "leads?"),
    ("Slow DM", "replies?"),
    ("Manual", "follow-ups?"),
    ("Booking", "chaos?"),
    ("Need all", "of it?"),
]

# pendulum (measured from the reference): x = CX - AMP*cos(2*pi*f/PERIOD)
CX, AMP, PERIOD = 336.85, 243.35, 72
PIVOT_Y, LENGTH = -1010.0, 1650.0
BALL_R = 15
STOP_F = 396            # ball comes to rest at the right on "DM us."
ZOOM_F0, ZOOM_F1 = 411, 465
ZOOM_S, ZOOM_C = 1.23, (362.0, 568.0)
CARD_F = 480            # cut to the Instagram card
BASELINE = 634          # baseline of "Sorted." / "DM us."
TEXT_RIGHT = 562        # right edge of "Sorted." / "DM us." (ball sits just after)


def s(v):
    return v * S


def font(weight, size, display=True):
    name = f"InterDisplay-{weight}.otf" if display else f"Inter-{weight}.otf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(round(s(size))))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ----------------------------------------------------------------- text drawing with tracking
def tracked_width(text, f, tracking):
    return sum(f.getlength(ch) for ch in text) + tracking * f.size * (len(text) - 1)


def draw_tracked(d, x, y_base, text, f, fill, tracking):
    """Draw text with letter-spacing (em units); y_base is the baseline."""
    asc = f.getmetrics()[0]
    for ch in text:
        d.text((x, y_base - asc), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking * f.size


# ----------------------------------------------------------------- static layers
F_Q = font("Bold", 80)
F_BIG = font("Bold", 152)
F_BRAND = font("SemiBold", 31)
F_TAG = font("Medium", 12.5, display=False)
F_HANDLE_S = font("SemiBold", 13.5, display=False)
F_HANDLE_L = font("Bold", 25, display=False)


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def question_layer(l1, l2):
    L = layer()
    d = ImageDraw.Draw(L)
    for txt, base in ((l1, 556), (l2, 641)):
        w = tracked_width(txt, F_Q, -0.035)
        draw_tracked(d, s(360) - w / 2, s(base), txt, F_Q, GREY, -0.035)
    return L


def big_layer(txt):
    L = layer()
    d = ImageDraw.Draw(L)
    w = tracked_width(txt, F_BIG, -0.045)
    draw_tracked(d, s(TEXT_RIGHT) - w, s(BASELINE), txt, F_BIG, WHITE, -0.045)
    return L


def brand_layer(brand, tagline):
    L = layer()
    d = ImageDraw.Draw(L)
    w = tracked_width(brand, F_BRAND, -0.02)
    dot_r = s(2.6)
    x0 = s(360) - (w + dot_r * 2.6) / 2
    draw_tracked(d, x0, s(886), brand, F_BRAND, (255, 255, 255), -0.02)
    cx = x0 + w + dot_r * 1.6
    d.ellipse([cx - dot_r, s(886) - dot_r * 2, cx + dot_r, s(886)], fill=RED)
    tw = tracked_width(tagline, F_TAG, 0.28)
    draw_tracked(d, s(360) - tw / 2, s(930), tagline, F_TAG, GREY, 0.28)
    return L


def ig_icon(size, color=(255, 255, 255)):
    """Instagram-style glyph (rounded square, lens, dot) as an RGBA image."""
    k = 4
    n = int(size * k)
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    lw = int(n * 0.085)
    d.rounded_rectangle([lw / 2, lw / 2, n - lw / 2, n - lw / 2], radius=n * 0.28, outline=255, width=lw)
    r = n * 0.215
    d.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r], outline=255, width=lw)
    rd = n * 0.055
    d.ellipse([n * 0.745 - rd, n * 0.255 - rd, n * 0.745 + rd, n * 0.255 + rd], fill=255)
    mask = im.resize((int(size), int(size)), Image.LANCZOS)
    out = Image.new("RGBA", mask.size, (*color, 255))
    out.putalpha(mask)
    return out


def gradient_icon(size, phase):
    """Icon filled with a moving Instagram-like gradient."""
    base = ig_icon(size)
    mask = base.split()[3]
    n = base.size[0]
    stops = [(255, 214, 0), (255, 122, 0), (255, 1, 105), (211, 0, 197), (118, 56, 250), (255, 214, 0)]
    yy, xx = np.mgrid[0:n, 0:n] / max(1, n - 1)
    t = ((xx * 0.5 + (1 - yy) * 0.5) + phase) % 1.0 * (len(stops) - 1)
    i = np.floor(t).astype(int)
    fr = (t - i)[..., None]
    st = np.array(stops, dtype=float)
    col = st[i] * (1 - fr) + st[np.minimum(i + 1, len(stops) - 1)] * fr
    g = Image.fromarray(col.astype(np.uint8), "RGB").convert("RGBA")
    g.putalpha(mask)
    return g


def small_badge(handle, align):
    """Small icon + handle. align='right' (top-right corner) or 'left' (bottom-left)."""
    L = layer()
    d = ImageDraw.Draw(L)
    ic = ig_icon(s(31))
    hw = tracked_width(handle, F_HANDLE_S, -0.01)
    if align == "right":
        L.paste(ic, (int(s(663) - ic.size[0]), int(s(343) - ic.size[1] / 2)), ic)
        draw_tracked(d, s(663) - hw, s(406), handle, F_HANDLE_S, WHITE, -0.01)
    else:
        L.paste(ic, (int(s(62)), int(s(723) - ic.size[1] / 2)), ic)
        draw_tracked(d, s(58), s(784), handle, F_HANDLE_S, WHITE, -0.01)
    return L


# ----------------------------------------------------------------- pendulum
def ball_pos(f):
    fx = min(f, STOP_F)
    x = CX - AMP * math.cos(2 * math.pi * fx / PERIOD)
    sin_t = (x - CX) / LENGTH
    y = PIVOT_Y + LENGTH * math.cos(math.asin(sin_t))
    return x, y


def split_mask(bx, by):
    """White = left of the string line (pivot -> ball, extended down)."""
    px, py = CX, PIVOT_Y
    # extend the line to the bottom of the frame
    t_bot = (1280 - py) / (by - py)
    xb = px + (bx - px) * t_bot
    t_top = (0 - py) / (by - py)
    xt = px + (bx - px) * t_top
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([(0, 0), (s(xt), 0), (s(xb), H), (0, H)], fill=255)
    return m


def scale_layer(L, k, c):
    """Scale an RGBA layer by k about point c (in 720-grid units)."""
    if abs(k - 1) < 1e-4:
        return L
    cx, cy = s(c[0]), s(c[1])
    a = 1 / k
    return L.transform((W, H), Image.AFFINE, (a, 0, cx - a * cx, 0, a, cy - a * cy), resample=Image.BICUBIC)


def dim(L, amount):
    """Fade an RGBA layer's alpha by amount (0..1)."""
    if amount <= 0:
        return L
    r, g, b, a = L.split()
    a = a.point(lambda v: int(v * (1 - amount)))
    return Image.merge("RGBA", (r, g, b, a))


# ----------------------------------------------------------------- frame renderer
class Reel:
    def __init__(self, brand, tagline, handle):
        self.q = [question_layer(*q) for q in QUESTIONS]
        self.sorted = big_layer("Sorted")
        self.dm = big_layer("DM us")
        self.brand = brand_layer(brand, tagline)
        self.badge_tr = small_badge(handle, "right")
        self.badge_bl = small_badge(handle, "left")
        self.handle = handle

    def text_frame(self, f):
        """Main text (question / Sorted / DM us) with the string wipe; returns RGBA layer."""
        bx, by = ball_pos(f)
        # right side: question that is current for this swing
        qi = min(len(self.q) - 1, max(0, (f + PERIOD // 2) // PERIOD))
        right = self.q[qi]
        left = self.dm if f >= 5 * PERIOD else self.sorted
        if f >= STOP_F:
            return left.copy(), (bx, by)
        m = split_mask(bx, by)
        out = layer()
        out.paste(right, (0, 0), right)
        cleared = Image.composite(layer(), out, m)
        cleared.alpha_composite(Image.composite(left, layer(), m))
        return cleared, (bx, by)

    def render(self, f):
        img = Image.new("RGBA", (W, H), (*BG, 255))
        txt, (bx, by) = self.text_frame(f)

        # ball + string drawn on the text layer so the zoom affects the ball too
        d = ImageDraw.Draw(txt)
        string_a = 1.0 if f < ZOOM_F0 else 1 - ease_io((f - ZOOM_F0) / 20)
        if string_a > 0:
            px, py = CX, PIVOT_Y
            t_top = (0 - py) / (by - py)
            d.line([(s(px + (bx - px) * t_top), 0), (s(bx), s(by))],
                   fill=(255, 255, 255, int(235 * string_a)), width=max(1, int(s(1.3))))
        r = s(BALL_R)
        d.ellipse([s(bx) - r, s(by) - r, s(bx) + r, s(by) + r], fill=(*RED, 255))

        k = 1 + (ZOOM_S - 1) * ease_io((f - ZOOM_F0) / (ZOOM_F1 - ZOOM_F0)) if f >= ZOOM_F0 else 1
        content = layer()
        content.alpha_composite(txt)
        content.alpha_composite(self.brand)
        content = scale_layer(content, k, ZOOM_C)

        if f >= CARD_F:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            content = dim(content, 0.72)
        img.alpha_composite(content)

        # small corner badge
        if f < CARD_F:
            if f < 264:
                a = clamp((f - 6) / 10)
                if a > 0:
                    img.alpha_composite(dim(self.badge_tr, 1 - a))
            else:
                a = clamp((f - 264) / 8)
                img.alpha_composite(dim(self.badge_bl, 1 - a))

        # Instagram card
        if f >= CARD_F:
            p = ease_out_back((f - CARD_F) / 14)
            size = s(104) * max(0.01, p)
            cf = f - (CARD_F + 20)
            if 0 <= cf < 75:
                ic = gradient_icon(size, cf / 40)
            else:
                ic = ig_icon(size)
            cx, cy = s(360), s(610)
            if p > 0.02:
                img.alpha_composite(ic, (int(cx - ic.size[0] / 2), int(cy - ic.size[1] / 2)))
            ha = clamp((f - CARD_F - 4) / 8)
            if ha > 0:
                hl = layer()
                hw = tracked_width(self.handle, F_HANDLE_L, -0.01)
                draw_tracked(ImageDraw.Draw(hl), s(360) - hw / 2, s(748), self.handle, F_HANDLE_L,
                             (255, 255, 255, int(255 * ha)), -0.01)
                img.alpha_composite(hl)
        return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, help="audio source (e.g. the reference reel)")
    ap.add_argument("--audio-offset", type=float, default=0.0)
    ap.add_argument("--out", default="reel/output/pendulum_reel.mp4")
    ap.add_argument("--brand", default="your brand")
    ap.add_argument("--tagline", default="WEBSITES · AI CHATBOTS · AUTOMATION · CRM")
    ap.add_argument("--handle", default="@YOURHANDLE")
    ap.add_argument("--stills", default="", help="comma-separated frame numbers to save as PNG")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    reel = Reel(a.brand, a.tagline, a.handle.upper())
    stills = {int(x) for x in a.stills.split(",") if x.strip()}
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", str(a.audio_offset), "-i", a.audio,
           "-map", "0:v", "-map", "1:a:0", "-t", str(TOTAL_F / FPS),
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(TOTAL_F):
        im = reel.render(f)
        p.stdin.write(im.tobytes())
        if f in stills:
            im.save(os.path.join(os.path.dirname(a.out), f"pstill_{f:03d}.png"))
        if f % 100 == 0:
            print(f"frame {f}/{TOTAL_F}", flush=True)
    p.stdin.close()
    p.wait()
    print("done ->", a.out)


if __name__ == "__main__":
    main()
