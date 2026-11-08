"""Render an interactive-style trivia video (1080x1920) for social media.

Usage: python3 render_quiz.py <workdir-with-site.png> <out.mp4> [preview_secs]
Reuses assets/helpers from render.py.
"""
import math, subprocess, sys, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from render import W, H, FPS, clamp, prog, ease_out, ease_io, back_out, lerp, font, paste_center

WORK, OUT = sys.argv[1], sys.argv[2]
DUR = 25.0
N = int(DUR * FPS)
EMOJI = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
_ec = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _ec:
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=EMOJI, embedded_color=True)
        im = im.crop(im.getbbox())
        _ec[k] = im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)
    return _ec[k]

def with_alpha(layer, a):
    if a >= 1: return layer
    arr = np.asarray(layer).copy(); arr[..., 3] = (arr[..., 3] * a).astype(np.uint8)
    return Image.fromarray(arr)

def text(im, s, y, size, t, t_in, t_out=None, color=(255, 255, 255), bold=True, pop=True, x=W / 2, dur=0.35):
    a_in = prog(t, t_in, t_in + dur)
    if a_in <= 0: return
    a_out = 1.0 if t_out is None else 1 - prog(t, t_out, t_out + 0.25)
    if a_out <= 0: return
    f = font(size, bold)
    bb = f.getbbox(s)
    pad = 40
    layer = Image.new("RGBA", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1] + 6), s, font=f, fill=(0, 0, 0, 210))
    layer = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), layer)
    ImageDraw.Draw(layer).text((pad - bb[0], pad - bb[1]), s, font=f, fill=color + (255,))
    sc = max(0.05, back_out(a_in)) if pop else 1.0
    if sc != 1.0:
        layer = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BILINEAR)
    paste_center(im, with_alpha(layer, a_in * a_out), x, y + (1 - ease_out(a_in)) * 40)

def put_emoji(im, ch, x, y, size, t, t_in, t_out=None, wobble=0.0):
    a_in = prog(t, t_in, t_in + 0.35)
    if a_in <= 0: return
    a_out = 1.0 if t_out is None else 1 - prog(t, t_out, t_out + 0.25)
    if a_out <= 0: return
    e = emoji(ch, size)
    sc = max(0.05, back_out(a_in))
    e = e.resize((max(1, int(e.width * sc)), max(1, int(e.height * sc))), Image.BILINEAR)
    if wobble: e = e.rotate(math.sin(t * 8) * wobble, resample=Image.BICUBIC, expand=True)
    paste_center(im, with_alpha(e, a_in * a_out), x, y)

def pill(im, s, y, t, t_in, t_out, fill=(255, 255, 255), fg=(10, 20, 40), size=38):
    a = prog(t, t_in, t_in + 0.3) * (1 - prog(t, t_out, t_out + 0.25))
    if a <= 0: return
    f = font(size)
    bb = f.getbbox(s)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 34
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=fill + (255,))
    d.text((30 - bb[0], 17 - bb[1]), s, font=f, fill=fg)
    paste_center(im, with_alpha(layer, a), W / 2, y)

def progress_dots(im, idx, t, t_in, t_out):
    a = prog(t, t_in, t_in + 0.3) * (1 - prog(t, t_out, t_out + 0.25))
    if a <= 0: return
    layer = Image.new("RGBA", (W, 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    segw, gap = 220, 20
    x0 = (W - (3 * segw + 2 * gap)) / 2
    for k in range(3):
        col = (255, 255, 255, 255) if k <= idx else (255, 255, 255, 70)
        d.rounded_rectangle((x0 + k * (segw + gap), 4, x0 + k * (segw + gap) + segw, 14), 5, fill=col)
    paste_center(im, with_alpha(layer, a), W / 2, 120)

# ---------- answer card ----------
CARD_W, CARD_H = 860, 132
def card(im, letter, label, y, t, t_in, t_reveal, correct, t_out):
    a_in = prog(t, t_in, t_in + 0.35)
    if a_in <= 0: return
    a_out = 1 - prog(t, t_out, t_out + 0.25)
    if a_out <= 0: return
    r = prog(t, t_reveal, t_reveal + 0.25)
    base = (255, 255, 255)
    if correct:
        fill = tuple(int(lerp(c, g, r)) for c, g in zip(base, (46, 204, 113)))
        fg = tuple(int(lerp(c, g, r)) for c, g in zip((15, 25, 45), (255, 255, 255)))
        alpha = 1.0
    else:
        fill, fg = base, (15, 25, 45)
        alpha = lerp(1.0, 0.35, r)
    layer = Image.new("RGBA", (CARD_W + 40, CARD_H + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 28, CARD_W + 20, CARD_H + 28), 34, fill=(0, 0, 0, 140))
    layer = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), layer)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((20, 20, CARD_W + 20, CARD_H + 20), 34, fill=fill + (255,))
    cx_, cy_ = 20 + 76, 20 + CARD_H // 2
    circ = (20, 60, 110) if not (correct and r > 0.5) else (255, 255, 255)
    d.ellipse((cx_ - 44, cy_ - 44, cx_ + 44, cy_ + 44), fill=circ)
    lf = font(48)
    lb = lf.getbbox(letter)
    lc = (255, 255, 255) if circ != (255, 255, 255) else (46, 160, 90)
    d.text((cx_ - (lb[2] + lb[0]) / 2, cy_ - (lb[3] + lb[1]) / 2), letter, font=lf, fill=lc)
    tf = font(50)
    tb = tf.getbbox(label)
    d.text((20 + 150, cy_ - (tb[3] + tb[1]) / 2), label, font=tf, fill=fg)
    if correct and r > 0:
        ck = emoji("✅", 70)
        ck = ck.resize((max(1, int(70 * back_out(r))), max(1, int(70 * back_out(r)))), Image.BILINEAR)
        layer.alpha_composite(ck, (CARD_W + 20 - 50 - ck.width // 2, cy_ - ck.height // 2))
    sc = back_out(a_in, 1.4)
    if correct and r > 0:
        sc *= 1 + 0.06 * math.sin(math.pi * prog(t, t_reveal, t_reveal + 0.4))
    if sc != 1.0:
        layer = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BILINEAR)
    x = W / 2 + (1 - ease_out(a_in)) * 300
    paste_center(im, with_alpha(layer, alpha * a_out * min(1, a_in * 2)), x, y)

def timer_ring(im, cx, cy, rad, t, t0, t1, t_out):
    if t < t0 - 0.2 or t > t_out + 0.25: return
    a = prog(t, t0 - 0.2, t0) * (1 - prog(t, t_out, t_out + 0.25))
    frac = 1 - prog(t, t0, t1)
    layer = Image.new("RGBA", (int(rad * 2 + 40), int(rad * 2 + 40)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    box = (20, 20, 20 + rad * 2, 20 + rad * 2)
    d.arc(box, 0, 360, fill=(255, 255, 255, 60), width=14)
    col = (255, 210, 80) if frac > 0.34 else (255, 90, 80)
    if frac > 0:
        d.arc(box, -90, -90 + 360 * frac, fill=col + (255,), width=14)
    paste_center(im, with_alpha(layer, a), cx, cy)
    # number badge
    if t0 <= t < t1:
        n = int(math.ceil(t1 - t))
        beat = (t1 - t) % 1.0
        sc = 1 + 0.25 * max(0, beat - 0.75) / 0.25
        f = font(int(64 * sc))
        s = str(n)
        b = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        bd = ImageDraw.Draw(b)
        bd.ellipse((15, 15, 135, 135), fill=col + (255,))
        bb = f.getbbox(s)
        bd.text((75 - (bb[2] + bb[0]) / 2, 75 - (bb[3] + bb[1]) / 2), s, font=f, fill=(20, 20, 30))
        paste_center(im, with_alpha(b, a), cx + rad * 0.72, cy - rad * 0.72)

# ---------- content ----------
QUESTIONS = [
    dict(q=["¿A qué velocidad viaja", "la Tierra alrededor del Sol?"],
         opts=[("A", "1.600 km/h"), ("B", "107.000 km/h"), ("C", "30 km/h")], ok=1,
         fact="¡Más rápido que una bala!", heat=0),
    dict(q=["¿Qué parte de la superficie", "de la Tierra es agua?"],
         opts=[("A", "71%"), ("B", "50%"), ("C", "90%")], ok=0,
         fact="Casi 3 de cada 4 partes", heat=0),
    dict(q=["¿Qué tan caliente es", "el núcleo de la Tierra?"],
         opts=[("A", "Como un horno"), ("B", "Como la lava"), ("C", "Como el Sol")], ok=2,
         fact="Unos 5.500 °C", heat=1),
]
Q_START, Q_LEN = 2.4, 6.2
EARTH_Y, EARTH_D = 680, 400

def earth_at(im, t, x, y, d, heat=0.0, spin=4.5):
    g = R.glow.resize((int(d * 1.36), int(d * 1.36)))
    paste_center(im, g, x, y)
    if heat > 0:
        hh = R.hot.resize((int(d * 1.5), int(d * 1.5)))
        paste_center(im, with_alpha(hh, heat), x, y)
    e = R.earth.rotate(-t * spin, resample=Image.BICUBIC).resize((int(d), int(d)), Image.BILINEAR)
    paste_center(im, e, x, y)
    if heat > 0:
        tint = Image.new("RGBA", e.size, (255, 70, 0, 255))
        tint.putalpha(Image.fromarray((np.asarray(e.getchannel("A")) * 0.22 * heat).astype(np.uint8)))
        paste_center(im, tint, x, y)

def frame(i):
    t = i / FPS
    im = R.background(t).convert("RGBA")

    # ----- intro 0-2.4 -----
    if t < Q_START + 0.6:
        x = ease_io(prog(t, 1.9, Q_START + 0.4))
        d = lerp(lerp(300, 620, ease_out(prog(t, 0, 1.6))), EARTH_D, x)
        y = lerp(1080, EARTH_Y, x)
        earth_at(im, t, W / 2, y, d)
    text(im, "TRIVIA DEL PLANETA", 300, 80, t, 0.05, 2.15, (120, 230, 200))
    text(im, "¿Aciertas las 3?", 1560, 96, t, 0.5, 2.15)
    put_emoji(im, "\U0001F914", W / 2, 1720, 120, t, 0.9, 2.15, wobble=8)
    text(im, "Responde antes de que acabe el tiempo", 430, 40, t, 0.8, 2.15, (220, 220, 230), bold=False, pop=False)

    # ----- questions -----
    for qi, Q in enumerate(QUESTIONS):
        T = Q_START + qi * Q_LEN
        T_end = T + Q_LEN - 0.3
        t_timer0, t_timer1 = T + 1.4, T + 4.4
        t_rev = t_timer1
        if T - 0.1 <= t <= T + Q_LEN + 0.1 or (qi == 0 and t >= T - 0.3 and t <= T + Q_LEN):
            heat = Q["heat"] * prog(t, t_rev, t_rev + 0.5)
            spin = 4.5 if qi != 0 else 4.5 + 30 * prog(t, t_rev, t_rev + 0.3) * (1 - prog(t, T_end - 0.6, T_end))
            if qi > 0 or t >= Q_START + 0.4:
                earth_at(im, t, W / 2, EARTH_Y, EARTH_D, heat, spin)
        progress_dots(im, qi, t, T, T_end if qi < 2 else T_end)
        pill(im, f"PREGUNTA {qi + 1}/3", 200, t, T, T_end)
        text(im, Q["q"][0], 320, 58, t, T + 0.1, T_end)
        text(im, Q["q"][1], 395, 58, t, T + 0.2, T_end)
        timer_ring(im, W / 2, EARTH_Y, EARTH_D / 2 + 40, t, t_timer0, t_timer1, t_rev + 0.3)
        for k, (L, lab) in enumerate(Q["opts"]):
            card(im, L, lab, 1060 + k * 160, t, T + 0.55 + 0.15 * k, t_rev, k == Q["ok"], T_end)
        text(im, Q["fact"], 935, 50, t, t_rev + 0.3, T_end, (255, 220, 120))
        if qi == 0:
            text(im, "Comenta tu respuesta antes de verla", 1560, 38, t, T + 1.4, t_rev, (200, 200, 210), bold=False, pop=False)

    # ----- outro -----
    T = Q_START + 3 * Q_LEN  # 21.0
    if t >= T - 0.3:
        x = ease_out(prog(t, T - 0.3, T + 0.6))
        earth_at(im, t, W / 2, lerp(-300, 520, x), 360)
    text(im, "¿Cuántas acertaste?", 860, 84, t, T + 0.2)
    labels = ["0/3", "1/3", "2/3", "3/3"]
    for k, lab in enumerate(labels):
        xk = W / 2 + (k - 1.5) * 220
        a = prog(t, T + 0.6 + 0.1 * k, T + 0.9 + 0.1 * k)
        if a > 0:
            layer = Image.new("RGBA", (190, 110), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            hl = k == 3
            d.rounded_rectangle((0, 0, 189, 109), 30, fill=(46, 204, 113, 255) if hl else (255, 255, 255, 235))
            f = font(50)
            bb = f.getbbox(lab)
            d.text((95 - (bb[2] + bb[0]) / 2, 55 - (bb[3] + bb[1]) / 2), lab, font=f,
                   fill=(255, 255, 255) if hl else (15, 25, 45))
            sc = max(0.05, back_out(a))
            layer = layer.resize((int(190 * sc) or 1, int(110 * sc) or 1), Image.BILINEAR)
            paste_center(im, with_alpha(layer, min(1, a * 2)), xk, 1010)
    text(im, "Déjalo en los comentarios", 1150, 52, t, T + 1.2, None, (230, 230, 240), bold=False)
    put_emoji(im, "\U0001F447", W / 2, 1260, 100, t, T + 1.4, None, wobble=0)
    text(im, "Sigue para la parte 2", 1420, 66, t, T + 2.0, None, (120, 230, 200))
    text(im, "github.com/jcastillopulla09-cmyk/earth", 1530, 32, t, T + 2.4, None, (170, 170, 185), bold=False, pop=False)

    fade = min(prog(t, 0, 0.2), 1 - prog(t, DUR - 0.4, DUR))
    out = im.convert("RGB")
    if fade < 1:
        out = Image.fromarray((np.asarray(out) * fade).astype(np.uint8))
    return out

# ---------- audio ----------
def make_audio(path):
    sr = 44100
    n = int(sr * DUR)
    tt = np.arange(n) / sr
    out = np.zeros(n)
    rng = np.random.default_rng(3)
    # pad
    chords = [(0, [110.0, 164.81, 220.0]), (Q_START, [87.31, 130.81, 174.61]),
              (Q_START + Q_LEN, [98.0, 146.83, 196.0]), (Q_START + 2 * Q_LEN, [82.41, 123.47, 164.81]),
              (Q_START + 3 * Q_LEN, [110.0, 164.81, 220.0, 277.18])]
    for k, (st, fr) in enumerate(chords):
        en = chords[k + 1][0] if k + 1 < len(chords) else DUR
        env = np.clip((tt - st) / 0.6, 0, 1) * np.clip((en + 0.6 - tt) / 0.6, 0, 1)
        for f in fr:
            for det in (-0.7, 0.7):
                out += env * np.sin(2 * np.pi * (f + det) * tt) * 0.04
    # groove: kick on beats (120 bpm) + hat on offbeats
    for b in np.arange(0, DUR - 0.5, 0.5):
        i0 = int(b * sr); L = int(0.3 * sr)
        x = np.arange(min(L, n - i0)) / sr
        out[i0:i0 + len(x)] += 0.32 * np.sin(2 * np.pi * (50 + 90 * np.exp(-x * 30)) * x) * np.exp(-x * 10)
        j0 = int((b + 0.25) * sr); Lh = int(0.04 * sr)
        if j0 + Lh < n:
            hn = rng.standard_normal(Lh); hn = np.diff(hn, prepend=0)
            out[j0:j0 + Lh] += 0.05 * hn * np.exp(-np.arange(Lh) / (0.008 * sr))
    def tone(at, f, L, g, decay=6):
        i0 = int(at * sr); x = np.arange(min(int(L * sr), n - i0)) / sr
        out[i0:i0 + len(x)] += g * (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * decay)
    def whoosh(at, L=0.5, g=0.6):
        i0 = max(0, int((at - L * 0.6) * sr)); Ls = min(int(L * sr), n - i0)
        k = np.convolve(rng.standard_normal(Ls), np.ones(25) / 25, mode="same")
        out[i0:i0 + Ls] += k * np.sin(np.linspace(0, np.pi, Ls)) ** 2 * g
    tone(0.05, 880, 0.6, 0.18); tone(0.2, 1318.5, 0.8, 0.15)
    for qi in range(3):
        T = Q_START + qi * Q_LEN
        whoosh(T)
        for s in range(3):  # countdown ticks
            tone(T + 1.4 + s, 1000 if s < 2 else 1400, 0.12, 0.22, decay=40)
        rev = T + 4.4
        tone(rev, 1046.5, 0.5, 0.22); tone(rev + 0.09, 1318.5, 0.5, 0.2); tone(rev + 0.18, 1568, 0.9, 0.2)
    T = Q_START + 3 * Q_LEN
    whoosh(T)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        tone(T + 0.6 + 0.1 * k, f, 0.6, 0.15)
    out *= np.clip(tt / 0.2, 0, 1) * np.clip((DUR - tt) / 1.0, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(np.stack([pcm, pcm], 1).tobytes())

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for sec in sys.argv[3].split(","):
            frame(int(float(sec) * FPS)).save(f"{WORK}/q_{sec}.png")
        sys.exit()
    make_audio(f"{WORK}/quiz_audio.wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", f"{WORK}/quiz_audio.wav",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT],
                         stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
        if i % 90 == 0: print(i, "/", N, flush=True)
    p.stdin.close(); p.wait()
    print("done", p.returncode)
