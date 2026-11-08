"""Builds the new LABMEDICAL end card (720x1280) as a crisp PNG.

Text, shapes and icons are drawn at 3x and downsampled; the lab photo and the
logo icon are reused 1:1 from the original end-card frame (no rescaling).
"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = sys.argv[1]
SRC = f"{S}/all/230.png"            # clean original end-card frame
OUT = sys.argv[2]
FONTS = f"{S}/fonts"
W, H, K = 720, 1280, 3              # K = supersampling factor

# ---- palette sampled from the original end-card frames --------------------
NAVY   = (31, 45, 70)       # "LABMEDICAL" wordmark
TEAL   = (35, 81, 106)      # microscope blue
GOLD   = (201, 172, 112)    # swoosh curves (slightly deepened for definition)
GOLD_D = (150, 112, 46)     # deep gold for the marketing line (readable on cream)
TEXT   = (79, 75, 68)       # headline gray
TEXT_L = (106, 101, 92)     # tagline / address gray
CREAM_T = (233, 228, 215)   # background, top
CREAM_B = (238, 239, 236)   # background, bottom

def font(weight, size, italic=False):
    return ImageFont.truetype(f"{FONTS}/M_{weight}_{1 if italic else 0}.ttf" if italic
                              else f"{FONTS}/M_{weight}_0.ttf", size * K)

# Google Fonts returns [italic, regular] order for ital,wght@0,w;1,w -> check names
def pick(weight, italic):
    for i in (0, 1):
        f = ImageFont.truetype(f"{FONTS}/M_{weight}_{i}.ttf", 10)
        if ("Italic" in f.getname()[1]) == italic:
            return f"{FONTS}/M_{weight}_{i}.ttf"
def F(weight, size, italic=False):
    return ImageFont.truetype(pick(weight, italic), int(size * K))

src = Image.open(SRC).convert("RGB")

# ---- 1. background --------------------------------------------------------
y = np.linspace(0, 1, H)[:, None, None]
bg = (np.array(CREAM_T) * (1 - y) + np.array(CREAM_B) * y) * np.ones((H, W, 3))
# soft light bloom behind the logo
yy, xx = np.mgrid[0:H, 0:W]
bloom = np.exp(-(((xx - 360) / 380) ** 2 + ((yy - 300) / 230) ** 2))[..., None]
bg = bg * (1 - 0.35 * bloom) + np.array([246, 243, 235]) * 0.35 * bloom
card = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))

def bezier(p0, p1, p2, n=400):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2))

def stroke_layer(curves):
    """curves: list of (points[720-space], width_px, color, alpha)."""
    lay = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for pts, wpx, col, a in curves:
        d.line([tuple(p * K) for p in pts], fill=col + (a,), width=int(wpx * K), joint="curve")
    return lay.resize((W, H), Image.LANCZOS)

# decorative gold swooshes in the top band (no information in the top 15 %)
top_curves = [
    (bezier((-20, 178), (300, 40), (740, 18)), 2.4, GOLD, 255),
    (bezier((-20, 150), (330, 70), (740, 60)), 1.0, GOLD, 150),
]
card.paste(stroke_layer(top_curves), (0, 0), stroke_layer(top_curves))

# decorative gold swooshes in the bottom band (decoration only, no information)
bot_curves = [
    (bezier((-20, 1214), (380, 1250), (740, 1120)), 2.4, GOLD, 255),
    (bezier((-20, 1236), (400, 1262), (740, 1150)), 1.0, GOLD, 150),
]
bl = stroke_layer(bot_curves); card.paste(bl, (0, 0), bl)

# ---- 2. lab photo (1:1 crop of the original) -------------------------------
PH_SRC_Y0, PH_Y0, PH_H = 468, 500, 352           # source top, dest top, height
photo = src.crop((0, PH_SRC_Y0, W, PH_SRC_Y0 + PH_H))
bottom_curve = bezier((-20, PH_Y0 + PH_H - 4), (300, PH_Y0 + PH_H + 6), (740, PH_Y0 + PH_H - 70))
m = Image.new("L", (W * K, H * K), 0)
md = ImageDraw.Draw(m)
poly = [(-20, PH_Y0 - 10)] + [tuple(p) for p in bottom_curve] + [(740, PH_Y0 - 10)]
md.polygon([(x * K, yv * K) for x, yv in poly], fill=255)
m = m.resize((W, H), Image.LANCZOS)
ma = np.asarray(m).astype(float) / 255
fade = np.clip((np.arange(H) - PH_Y0) / 60.0, 0, 1)[:, None]          # soft top fade into cream
fade = fade ** 1.6
ma = ma * fade
full = Image.new("RGB", (W, H)); full.paste(photo, (0, PH_Y0))
c = np.asarray(card).astype(float); p = np.asarray(full).astype(float)
c = c * (1 - ma[..., None]) + p * ma[..., None]
card = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))

# gold swoosh along the photo's bottom edge (as in the original)
b2 = bezier((-20, PH_Y0 + PH_H + 10), (300, PH_Y0 + PH_H + 20), (740, PH_Y0 + PH_H - 52))
sw = stroke_layer([(bottom_curve, 3.2, GOLD, 255), (b2, 1.2, GOLD, 170)])
card.paste(sw, (0, 0), sw)

# ---- 3. logo icon (from the original, alpha-keyed off the cream) ------------
ix0, iy0, ix1, iy1 = 140, 136, 256, 270
icon = np.asarray(src.crop((ix0, iy0, ix1, iy1))).astype(float)
border = np.concatenate([icon[:3].reshape(-1, 3), icon[-3:].reshape(-1, 3),
                         icon[:, :3].reshape(-1, 3), icon[:, -3:].reshape(-1, 3)])
bgc = np.median(border, 0)
dist = np.sqrt(((icon - bgc) ** 2).sum(2))
alpha = np.clip((dist - 10) / 28, 0, 1)
# un-premultiply against the old cream so edges don't carry a halo
a3 = np.maximum(alpha, 1e-3)[..., None]
rgb = np.clip((icon - bgc * (1 - a3)) / a3, 0, 255)
icon_rgba = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")
icon_rgba = icon_rgba.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))

# ---- 4. text layer (3x) ----------------------------------------------------
txt = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
d = ImageDraw.Draw(txt)

def tw(s, f, spacing=0):
    if spacing == 0:
        return d.textlength(s, font=f)
    return sum(d.textlength(ch, font=f) for ch in s) + spacing * K * (len(s) - 1)

def draw_spaced(x, yv, s, f, fill, spacing):
    for ch in s:
        d.text((x, yv), ch, font=f, fill=fill, anchor="ls")
        x += d.textlength(ch, font=f) + spacing * K

def center(s, yv, f, fill, spacing=0):
    w = tw(s, f, spacing)
    x = (W * K - w) / 2
    if spacing:
        draw_spaced(x, yv * K, s, f, fill, spacing)
    else:
        d.text((x, yv * K), s, font=f, fill=fill, anchor="ls")

# logo lockup: icon + "LABMEDICAL / CENTER"
f_logo = F(800, 50)
f_center = F(600, 23)
w_logo = tw("LABMEDICAL", f_logo, 0.5)
w_center = tw("CENTER", f_center, 9.5)
icon_w = icon_rgba.width
gap = 14
block_w = icon_w + gap + w_logo / K
bx = (W - block_w) / 2
LOGO_TOP = 204
card.paste(icon_rgba, (int(round(bx)), LOGO_TOP), icon_rgba)
wx = (bx + icon_w + gap) * K
draw_spaced(wx, (LOGO_TOP + 72) * K, "LABMEDICAL", f_logo, NAVY + (255,), 0.5)
draw_spaced(wx + (w_logo - w_center) / 2, (LOGO_TOP + 108) * K, "CENTER", f_center, NAVY + (255,), 9.5)

# subtitle
center("Laboratorio Clínico y Salud Ocupacional", 378, F(600, 25), TEAL + (255,))
# small gold divider
d.line([((W / 2 - 34) * K, 397 * K), ((W / 2 + 34) * K, 397 * K)], fill=GOLD + (255,), width=int(2 * K))

# headline (spelling fixed: OCUPACIONALES) + original tagline
f_head = F(700, 26)
center("PROGRAMA LOS EXÁMENES", 433, f_head, TEXT + (255,), 0.3)
center("OCUPACIONALES DE TU EMPRESA", 466, f_head, TEXT + (255,), 0.3)
center("La salud de tu equipo merece la mejor atención.", 496, F(500, 18), TEXT_L + (255,))

# marketing line (accent gold, a bit smaller than the subtitle)
center("Rapidez y precisión en cada análisis.", 892, F(600, 22, italic=True), GOLD_D + (255,))

# phone (once) with a WhatsApp-style glyph
f_phone = F(700, 37)
phone = "+593 99 783 0129"
pw = tw(phone, f_phone) / K
ic = 40
gx = (W - (ic + 14 + pw)) / 2
PY = 948                                   # baseline of phone number
cx, cy, R = gx + ic / 2, PY - 13, ic / 2 - 2
# ring + tail
d.ellipse([((cx - R) * K, (cy - R) * K), ((cx + R) * K, (cy + R) * K)], outline=NAVY + (255,), width=int(3.2 * K))
tail = [(cx - R * 0.80, cy + R * 0.45), (cx - R * 1.08, cy + R * 1.10), (cx - R * 0.35, cy + R * 0.92)]
d.polygon([(x * K, yv * K) for x, yv in tail], fill=NAVY + (255,))
d.ellipse([((cx - R + 3.2) * K, (cy - R + 3.2) * K), ((cx + R - 3.2) * K, (cy + R - 3.2) * K)], fill=(0, 0, 0, 0))
# handset: thick arc with rounded ends
hr = R * 0.56
hc = (cx + R * 0.10, cy - R * 0.10)
d.arc([((hc[0] - hr) * K, (hc[1] - hr) * K), ((hc[0] + hr) * K, (hc[1] + hr) * K)],
      start=100, end=170, fill=NAVY + (255,), width=int(4.6 * K))
for ang in (100, 170):
    ex = hc[0] + hr * math.cos(math.radians(ang)) - 2.0 * math.cos(math.radians(ang))
    ey = hc[1] + hr * math.sin(math.radians(ang)) - 2.0 * math.sin(math.radians(ang))
    rr = 3.9
    d.ellipse([((ex - rr) * K, (ey - rr) * K), ((ex + rr) * K, (ey + rr) * K)], fill=NAVY + (255,))
d.text(((gx + ic + 14) * K, PY * K), phone, font=f_phone, fill=NAVY + (255,), anchor="ls")

# address (cleaned, two lines) with a location pin
f_addr = F(500, 18)
l1 = "Gral. Leónidas Plaza Gutiérrez 3138,"
l2 = "Centro, 090302 Guayaquil"
aw = max(tw(l1, f_addr), tw(l2, f_addr)) / K
pin_w = 18
ax = (W - (pin_w + 12 + aw)) / 2
AY1, AY2 = 990, 1015
# pin
pcx, pcy, pr = ax + pin_w / 2, (AY1 + AY2) / 2 - 12, 8
d.ellipse([((pcx - pr) * K, (pcy - pr) * K), ((pcx + pr) * K, (pcy + pr) * K)], fill=TEAL + (255,))
d.polygon([((pcx - pr * 0.86) * K, (pcy + pr * 0.5) * K), ((pcx + pr * 0.86) * K, (pcy + pr * 0.5) * K),
           (pcx * K, (pcy + pr * 2.15) * K)], fill=TEAL + (255,))
d.ellipse([((pcx - 3) * K, (pcy - 3) * K), ((pcx + 3) * K, (pcy + 3) * K)], fill=CREAM_B + (255,))
d.text(((ax + pin_w + 12) * K, AY1 * K), l1, font=f_addr, fill=TEXT_L + (255,), anchor="ls")
d.text(((ax + pin_w + 12) * K, AY2 * K), l2, font=f_addr, fill=TEXT_L + (255,), anchor="ls")

txt = txt.resize((W, H), Image.LANCZOS)
card.paste(txt, (0, 0), txt)
card.save(OUT)

# safe-zone check: any text/logo pixels outside 15 %..80 % ?
a = np.asarray(txt)[..., 3]
rows = np.where(a.max(1) > 8)[0]
print("text rows:", rows.min(), rows.max(), "| safe zone:", int(H * 0.15), int(H * 0.80))
print("logo icon rows:", LOGO_TOP, LOGO_TOP + icon_rgba.height)
