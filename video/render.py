"""Render a ~21s vertical (1080x1920) promo video for the 'earth' repo."""
import math, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = sys.argv[1]            # scratchpad dir
OUT = sys.argv[2]          # output mp4
REPO = "/home/user/earth"
W, H, FPS, DUR = 1080, 1920, 30, 21.0
N = int(FPS * DUR)
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_fc = {}
def font(sz, bold=True):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(BOLD if bold else REG, sz)
    return _fc[k]

# ---------- easing helpers ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, t1): return clamp((t - t0) / (t1 - t0))
def ease_out(x): return 1 - (1 - x) ** 3
def ease_io(x): return 3 * x * x - 2 * x * x * x
def back_out(x, s=1.7):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x

# ---------- assets ----------
src = Image.open(f"{REPO}/The_Earth_seen_from_Apollo_17.jpg").convert("RGB")
cx, cy, r = 1493, 1490, 1345
earth = src.crop((cx - r, cy - r, cx + r, cy + r)).resize((1100, 1100), Image.LANCZOS)
mask = Image.new("L", (1100 * 2, 1100 * 2), 0)
ImageDraw.Draw(mask).ellipse((4, 4, 2196, 2196), fill=255)
mask = mask.resize((1100, 1100), Image.LANCZOS)
earth.putalpha(mask)
# atmospheric glow
glow = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse((200, 200, 1300, 1300), fill=(90, 170, 255, 170))
glow = glow.filter(ImageFilter.GaussianBlur(70))
hot = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
ImageDraw.Draw(hot).ellipse((180, 180, 1320, 1320), fill=(255, 120, 20, 230))
hot = hot.filter(ImageFilter.GaussianBlur(90))

site = Image.open(f"{S}/site.png").convert("RGB")  # 860x1864
pw, ph = 640, int(640 * site.height / site.width)
site_s = site.resize((pw, ph), Image.LANCZOS)
phone = Image.new("RGBA", (pw + 40, ph + 40), (0, 0, 0, 0))
pd = ImageDraw.Draw(phone)
pd.rounded_rectangle((0, 0, pw + 39, ph + 39), 60, fill=(20, 22, 28, 255))
smask = Image.new("L", (pw, ph), 0)
ImageDraw.Draw(smask).rounded_rectangle((0, 0, pw - 1, ph - 1), 42, fill=255)
phone.paste(site_s, (20, 20), smask)
pd.rounded_rectangle((pw // 2 - 70, 34, pw // 2 + 110, 64), 15, fill=(20, 22, 28, 255))

# starfield
random.seed(7)
stars = [(random.uniform(0, W), random.uniform(0, H * 1.5), random.choice([1, 1, 1, 2, 2, 3]),
          random.uniform(0.3, 1.0), random.uniform(0, 6.28)) for _ in range(420)]
bg_grad = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
xx = np.linspace(-1, 1, W)[None, :]
neb = np.exp(-((xx - 0.4) ** 2 / 0.5 + (yy - 0.3) ** 2 / 0.08))
bg_grad[..., 0] = 4 + 20 * neb
bg_grad[..., 1] = 6 + 8 * neb
bg_grad[..., 2] = 16 + 40 * neb + 10 * yy
bg_base = Image.fromarray(bg_grad.clip(0, 255).astype(np.uint8))

def background(t):
    im = bg_base.copy()
    d = ImageDraw.Draw(im)
    for (x, y, s, b, ph_) in stars:
        yy_ = (y - t * 18 * s) % (H * 1.5) - H * 0.25
        tw = 0.6 + 0.4 * math.sin(t * 3 + ph_)
        v = int(255 * b * tw)
        d.ellipse((x - s, yy_ - s, x + s, yy_ + s), fill=(v, v, min(255, v + 20)))
    return im

# ---------- earth keyframes: (time, cx, cy, diameter) ----------
EK = [(0.0, 540, 2400, 500), (1.8, 540, 2250, 700), (3.0, 540, 980, 980), (6.0, 540, 900, 920),
      (6.6, 540, 760, 780), (12.0, 540, 760, 780), (12.6, 540, 930, 900), (15.0, 540, 930, 940),
      (15.6, 540, -500, 600), (18.4, 540, -500, 600), (19.2, 540, 780, 620), (21.0, 540, 780, 660)]
def earth_state(t):
    for (a, b) in zip(EK, EK[1:]):
        if a[0] <= t <= b[0]:
            x = ease_io(prog(t, a[0], b[0]))
            return tuple(lerp(a[i], b[i], x) for i in (1, 2, 3))
    return EK[-1][1:]

def paste_center(im, layer, x, y):
    im.alpha_composite(layer, (int(x - layer.width / 2), int(y - layer.height / 2)))

def draw_earth(im, t, heat=0.0):
    x, y, d = earth_state(t)
    if y + d < -50 or y - d > H + 50:
        return
    g = glow.resize((int(d * 1.36), int(d * 1.36)))
    paste_center(im, g, x, y)
    if heat > 0:
        hh = hot.resize((int(d * 1.5), int(d * 1.5)))
        a = np.asarray(hh).copy(); a[..., 3] = (a[..., 3] * heat).astype(np.uint8)
        paste_center(im, Image.fromarray(a), x, y)
    e = earth.rotate(-t * 4.5, resample=Image.BICUBIC).resize((int(d), int(d)), Image.BILINEAR)
    paste_center(im, e, x, y)
    if heat > 0:  # warm tint
        tint = Image.new("RGBA", e.size, (255, 70, 0, 255))
        tm = e.getchannel("A")
        tint.putalpha(Image.fromarray((np.asarray(tm) * (0.22 * heat)).astype(np.uint8)))
        paste_center(im, tint, x, y)

# ---------- text ----------
def text(im, s, y, size, t, t_in, t_out=None, color=(255, 255, 255), bold=True, pop=True, dur=0.35):
    a_in = prog(t, t_in, t_in + dur)
    if a_in <= 0: return
    a_out = 1.0 if t_out is None else 1 - prog(t, t_out, t_out + 0.25)
    if a_out <= 0: return
    alpha = a_in * a_out
    sc = back_out(a_in) if pop else 1.0
    f = font(size, bold)
    bb = f.getbbox(s)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = 40
    layer = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1] + 6), s, font=f, fill=(0, 0, 0, 200))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    layer = Image.alpha_composite(sh, layer)
    ImageDraw.Draw(layer).text((pad - bb[0], pad - bb[1]), s, font=f, fill=color + (255,))
    if sc != 1.0:
        sc = max(0.05, sc)
        layer = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BILINEAR)
    if alpha < 1:
        a = np.asarray(layer).copy(); a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
        layer = Image.fromarray(a)
    dy = (1 - ease_out(a_in)) * 40
    paste_center(im, layer, W / 2, y + dy)

def fmt(n, sep="."):
    return f"{int(n):,}".replace(",", sep)

def frame(i):
    t = i / FPS
    im = background(t).convert("RGBA")

    heat = clamp(prog(t, 12.2, 13.0)) * (1 - prog(t, 14.8, 15.4))
    draw_earth(im, t, heat)

    # S1 hook 0-3
    text(im, "AHORA MISMO", 560, 64, t, 0.1, 2.75, (170, 210, 255))
    v = 107000 * ease_out(prog(t, 0.4, 1.6))
    text(im, f"{fmt(v)} km/h", 760, 122, t, 0.4, 2.75, pop=True)
    text(im, "vas a esta velocidad...", 930, 56, t, 1.4, 2.75, bold=False)
    text(im, "y ni lo notas.", 1030, 56, t, 2.0, 2.75, (255, 220, 120))

    # S2 3-6
    text(im, "Este es tu planeta", 260, 76, t, 3.2, 5.8)
    text(im, "4.500 millones", 1580, 110, t, 3.8, 5.8, (255, 220, 120))
    text(im, "de años dando vueltas", 1700, 56, t, 4.2, 5.8, bold=False)

    # S3 6-9 water
    pct = 71 * ease_out(prog(t, 6.6, 7.8))
    text(im, f"{int(pct)}%", 1390, 230, t, 6.6, 8.75, (110, 200, 255))
    text(im, "de su superficie es agua", 1590, 58, t, 7.2, 8.75, bold=False)

    # S4 9-12 species
    sp = 8.7 * ease_out(prog(t, 9.2, 10.4))
    text(im, f"{sp:.1f}".replace(".", ",") + " M", 1390, 210, t, 9.1, 11.75, (130, 230, 140))
    text(im, "de especies viven aquí", 1590, 58, t, 9.7, 11.75, bold=False)
    text(im, "...y contando", 1690, 50, t, 10.4, 11.75, (200, 200, 200), bold=False)

    # S5 12-15 core
    text(im, "Su núcleo arde", 230, 86, t, 12.4, 14.8)
    text(im, "como el Sol", 1580, 130, t, 13.0, 14.8, (255, 160, 60))
    text(im, "literalmente", 1720, 54, t, 13.6, 14.8, bold=False)

    # S6 15.4-18.6 website phone
    if 15.3 < t < 19.0:
        p_in = ease_out(prog(t, 15.4, 16.2))
        p_out = ease_io(prog(t, 18.2, 18.9))
        y = lerp(H + phone.height / 2, 1130, p_in) + p_out * (H)
        tilt = (1 - p_in) * 8
        ph_ = phone.rotate(tilt, resample=Image.BICUBIC, expand=True)
        # scroll the screenshot slightly inside the phone for life
        paste_center(im, ph_, W / 2, y)
    text(im, "Todo esto, en una web", 150, 72, t, 15.6, 18.3)
    text(im, "Planet Earth", 260, 60, t, 16.0, 18.3, (120, 230, 200), bold=False)

    # S7 outro 19-21
    text(im, "Nuestro único hogar", 1300, 82, t, 19.3)
    text(im, "Cuídalo.", 1430, 96, t, 19.8, None, (120, 230, 200))
    text(im, "github.com/jcastillopulla09-cmyk/earth", 1760, 36, t, 20.1, None, (190, 190, 200), bold=False, pop=False)

    # global fade in/out
    fade = min(prog(t, 0, 0.25), 1 - prog(t, DUR - 0.4, DUR))
    out = im.convert("RGB")
    if fade < 1:
        out = Image.fromarray((np.asarray(out) * fade).astype(np.uint8))
    return out

# ---------- audio: ambient pad + whooshes + hits ----------
def make_audio(path):
    sr = 44100
    n = int(sr * DUR)
    tt = np.arange(n) / sr
    out = np.zeros(n)
    chords = [(0, [110.0, 164.81, 220.0, 261.63]), (6, [87.31, 130.81, 174.61, 220.0]),
              (12, [98.0, 146.83, 196.0, 246.94]), (18, [110.0, 164.81, 220.0, 277.18])]
    for k, (st, fr) in enumerate(chords):
        en = chords[k + 1][0] if k + 1 < len(chords) else DUR
        env = np.clip((tt - st) / 1.0, 0, 1) * np.clip((en + 1.0 - tt) / 1.0, 0, 1)
        for f in fr:
            for det in (-0.6, 0.6):
                out += env * np.sin(2 * np.pi * (f + det) * tt) * 0.045
    # sub pulse (heartbeat-ish) every 0.75s
    for b in np.arange(0.0, DUR - 1, 0.75):
        i0 = int(b * sr); L = int(0.35 * sr)
        if i0 + L > n: break
        x = np.arange(L) / sr
        out[i0:i0 + L] += 0.25 * np.sin(2 * np.pi * (55 - 20 * x) * x) * np.exp(-x * 9)
    rng = np.random.default_rng(1)
    def whoosh(at, L=0.6, g=0.25):
        i0 = int((at - L * 0.7) * sr); Ls = int(L * sr)
        i0 = max(0, i0)
        noise = rng.standard_normal(Ls)
        # crude lowpass via cumulative moving average, sweeping
        k = np.convolve(noise, np.ones(30) / 30, mode="same")
        env = np.sin(np.linspace(0, np.pi, Ls)) ** 2
        seg = k * env * g * 3
        out[i0:i0 + Ls] += seg[: max(0, min(Ls, n - i0))]
    def hit(at, g=0.5):
        i0 = int(at * sr); L = int(1.2 * sr)
        x = np.arange(min(L, n - i0)) / sr
        out[i0:i0 + len(x)] += g * np.sin(2 * np.pi * (60 * np.exp(-x * 3) + 30) * x) * np.exp(-x * 3.5)
    for at in (3.0, 6.6, 9.1, 12.4, 15.4, 19.2):
        whoosh(at)
    for at in (0.4, 3.0, 6.6, 9.1, 12.4, 19.3):
        hit(at, 0.4)
    # ticking during counters
    for (a, b) in ((0.4, 1.6), (6.6, 7.8), (9.2, 10.4)):
        for c in np.arange(a, b, 0.06):
            i0 = int(c * sr); L = int(0.015 * sr)
            out[i0:i0 + L] += 0.12 * np.sin(2 * np.pi * 2400 * np.arange(L) / sr) * np.exp(-np.arange(L) / (0.004 * sr))
    fade = np.clip(tt / 0.3, 0, 1) * np.clip((DUR - tt) / 1.2, 0, 1)
    out *= fade
    out = out / (np.abs(out).max() + 1e-9) * 0.85
    pcm = (out * 32767).astype(np.int16)
    st = np.stack([pcm, pcm], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(st.tobytes())

if __name__ == "__main__":
    if len(sys.argv) > 3:  # preview frames
        for sec in sys.argv[3].split(","):
            frame(int(float(sec) * FPS)).save(f"{S}/prev_{sec}.png")
        sys.exit()
    make_audio(f"{S}/audio.wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", f"{S}/audio.wav",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT],
                         stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
        if i % 60 == 0: print(i, "/", N, flush=True)
    p.stdin.close(); p.wait()
    print("done", p.returncode)
