import sys, subprocess, numpy as np
from PIL import Image
S, V, OUT = sys.argv[1:4]
W, H = 720, 1280; YS = W * H * 3 // 2
card = np.asarray(Image.open(f"{S}/work/card.png").convert("RGB")).astype(np.float32)
CUT_FIRST, FADE_FROM, CARD_FULL = 157, 188, 196   # 0-based frame indices

def rgb2yuv(rgb):   # exact BT.601 limited-range conversion via ffmpeg with accurate rounding
    r = subprocess.run(["ffmpeg","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-i","-",
        "-vf","scale=out_color_matrix=bt601:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
        "-f","rawvideo","-"], input=np.ascontiguousarray(rgb).tobytes(), capture_output=True, check=True)
    return r.stdout

dec = subprocess.Popen(["ffmpeg","-v","error","-i",V,"-f","rawvideo","-pix_fmt","yuv420p","-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","yuv420p","-s",f"{W}x{H}","-r","24","-i","-",
       "-i",V,"-map","0:v","-map","1:a","-c:a","copy",
       "-c:v","libx264","-preset","slow","-crf","15","-profile:v","high","-pix_fmt","yuv420p",
       "-colorspace","smpte170m","-color_primaries","bt709","-color_trc","iec61966-2-1","-color_range","tv",
       "-movflags","+faststart", OUT], stdin=subprocess.PIPE)
last = None
for i in range(240):
    orig = dec.stdout.read(YS)
    if i < CUT_FIRST:
        enc.stdin.write(orig); continue                       # untouched: original decoded YUV
    if i <= FADE_FROM:
        fr = np.asarray(Image.open(f"{S}/fixed/{i:03d}.png").convert("RGB")); last = fr.astype(np.float32)
    elif i < CARD_FULL:
        a = (i - FADE_FROM) / (CARD_FULL - FADE_FROM); a = a * a * (3 - 2 * a)   # 0.3 s eased fade
        fr = np.clip(last * (1 - a) + card * a + 0.5, 0, 255).astype(np.uint8)
    else:
        fr = card.astype(np.uint8)
    enc.stdin.write(rgb2yuv(fr))
enc.stdin.close(); enc.wait(); dec.wait(); print("encode exit", enc.returncode)
