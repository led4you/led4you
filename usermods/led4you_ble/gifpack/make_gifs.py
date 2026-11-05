"""LED4YOU GIF pack (77 GIFs): original 16x16 pixel-art animations for LED matrices.
Everything here is drawn from code (no external artwork). Output: gifs/*.gif + gifs/pack.json"""
import colorsys, json, math, os, random
from PIL import Image

W = H = 16
OUT = os.environ.get('L4Y_GIF_OUT') or os.path.join(os.path.dirname(__file__), 'gifs')
os.makedirs(OUT, exist_ok=True)
PACK = []


def blank(c=(0, 0, 0)):
    return [[c for _ in range(W)] for _ in range(H)]


def put(f, x, y, c):
    if 0 <= x < W and 0 <= y < H and c is not None:
        f[y][x] = c


def sprite(f, rows, pal, ox=0, oy=0):
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != '.' and ch in pal:
                put(f, ox + x, oy + y, pal[ch])


def scale(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def save(name, theme, title, frames, ms):
    imgs = []
    for f in frames:
        im = Image.new('RGB', (W, H))
        im.putdata([p for row in f for p in row])
        imgs.append(im.convert('P', palette=Image.ADAPTIVE, colors=64))
    fn = name + '.gif'
    dur = ms if isinstance(ms, list) else [ms] * len(imgs)
    imgs[0].save(os.path.join(OUT, fn), save_all=True, append_images=imgs[1:], duration=dur, loop=0, optimize=False, disposal=1)
    PACK.append({'t': theme, 'n': title, 'f': fn})


random.seed(4)

# ---------------- Halloween ----------------
PUMP = [
    "................",
    ".......gg.......",
    "......gg........",
    "...OOOOoOOOOO...",
    "..OOOOOoOOOOOO..",
    ".OOOOOOoOOOOOOO.",
    ".OOFFOOoOOOFFOO.",
    "OOFFFFOoOOFFFFOO",
    "OOOOOOOoOOOOOOOO",
    "OOOOOOFFFOOOOOOO",
    "OOFOOOOoOOOOOFOO",
    "OOFFFOFFFFOFFFOO",
    ".OOFFFFFFFFFFOO.",
    ".OOOOFOoOOFOOOO.",
    "..OOOOOoOOOOOO..",
    "....OOOOOOOO....",
]
frames = []
for i in range(12):
    f = blank()
    glow = 0.65 + 0.35 * abs(math.sin(i * 1.7)) * (0.6 + 0.4 * random.random())
    sprite(f, PUMP, {'g': (40, 140, 20), 'O': (230, 90, 0), 'o': (150, 50, 0), 'F': scale((255, 210, 40), glow)})
    frames.append(f)
save('hw-pumpkin', 'Halloween', 'Pumpkin', frames, 110)

GHOST_A = [
    "....WWWWWW....",
    "..WWWWWWWWWW..",
    ".WWWWWWWWWWWW.",
    ".WWWKKWWKKWWW.",
    "WWWWKKWWKKWWWW",
    "WWWWWWWWWWWWWW",
    "WWWWWWKKWWWWWW",
    "WWWWWWKKWWWWWW",
    "WWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWW",
    "WW.WWW.WWW.WWW",
    "W...W...W...W.",
]
GHOST_B = GHOST_A[:11] + ["WWW.WWW.WWW.WW", ".W...W...W...W"]
frames = []
for i in range(16):
    f = blank((0, 0, 12))
    dy = round(1.5 * math.sin(i * math.pi / 8))
    sprite(f, GHOST_A if i % 4 < 2 else GHOST_B, {'W': (230, 235, 255), 'K': (10, 10, 30)}, 1, 2 + dy)
    frames.append(f)
save('hw-ghost', 'Halloween', 'Ghost', frames, 90)

BAT_UP = [
    "W.....K..K.....W",
    "WW....KKKK....WW",
    "WWW...KRKR...WWW",
    "WWWW..KKKK..WWWW",
    ".WWWWWKKKKWWWWW.",
    "..WWW.KKKK.WWW..",
    "...W...KK...W...",
]
BAT_DN = [
    "......K..K......",
    "......KKKK......",
    "......KRKR......",
    "....WWKKKKWW....",
    "..WWWWKKKKWWWW..",
    ".WWWW.KKKK.WWWW.",
    "WWW....KK....WWW",
    "W..............W",
]
frames = []
for i in range(8):
    f = blank((5, 0, 20))
    for (x, y) in [(2, 2), (3, 2), (2, 3), (3, 3), (4, 3), (3, 4)]:
        put(f, x, y, (250, 240, 170))   # moon
    dy = 6 + (1 if i % 2 else 0)
    sprite(f, BAT_UP if i % 2 == 0 else BAT_DN, {'W': (60, 40, 70), 'K': (30, 20, 40), 'R': (255, 30, 30)}, 0, dy)
    frames.append(f)
save('hw-bat', 'Halloween', 'Bat', frames, 140)

SPIDER = [
    "K.K..K.K",
    ".K.KK.K.",
    "..KKKK..",
    "KKKRRKKK",
    "..KKKK..",
    ".K.KK.K.",
    "K..KK..K",
]
frames = []
for i in range(16):
    f = blank((0, 0, 0))
    for (x, y) in [(0, 0), (1, 1), (2, 2), (15, 0), (14, 1), (13, 2), (0, 15), (1, 14), (15, 15), (14, 14)]:
        put(f, x, y, (60, 60, 70))     # web corners
    y = int(2 + 7 * (1 - math.cos(i * math.pi / 8)) / 2 * 1.2)
    for t in range(0, y):
        put(f, 8, t, (120, 120, 130))
    sprite(f, SPIDER, {'K': (120, 0, 160), 'R': (255, 0, 0)}, 4, y)
    frames.append(f)
save('hw-spider', 'Halloween', 'Spider', frames, 100)

SKULL = [
    "....WWWWWWWW....",
    "..WWWWWWWWWWWW..",
    ".WWWWWWWWWWWWWW.",
    ".WWWWWWWWWWWWWW.",
    "WWWEEEWWWWEEEWWW",
    "WWWEEEWWWWEEEWWW",
    "WWWEEEWWWWEEEWWW",
    ".WWWWWWWWWWWWWW.",
    "..WWWWWKKWWWWW..",
    "...WWWKKKKWWW...",
    "....WWWWWWWW....",
    "....W.W.W.W.....",
    "....WWWWWWWW....",
    ".....WWWWWW.....",
]
frames = []
for i in range(12):
    f = blank()
    k = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(i * math.pi / 6))
    sprite(f, SKULL, {'W': (220, 220, 210), 'K': (20, 20, 20), 'E': scale((255, 20, 0), k)}, 0, 1)
    frames.append(f)
save('hw-skull', 'Halloween', 'Skull', frames, 100)

POT = [
    ".KKKKKKKKKKKKKK.",
    "KKKKKKKKKKKKKKKK",
    ".KKKKKKKKKKKKKK.",
    ".KKKKKKKKKKKKKK.",
    "..KKKKKKKKKKKK..",
    "...KKKKKKKKKK...",
    "...K........K...",
]
frames = []
bub = [(random.randint(3, 12), random.randint(0, 9), random.choice([1, 1, 2])) for _ in range(7)]
for i in range(16):
    f = blank((4, 0, 10))
    for x in range(3, 13):   # flames
        put(f, x, 15, (255, 80 + 60 * ((x + i) % 3), 0))
    sprite(f, POT, {'K': (40, 40, 50)}, 0, 8)
    for x in range(1, 15):
        put(f, x, 8, (60, 220, 40) if (x + i) % 3 else (150, 255, 90))
    for (bx, by0, sp) in bub:
        by = 7 - ((by0 + i * sp) % 9)
        if by >= 0:
            put(f, bx, by, (90, 255, 60) if by > 3 else (60, 160, 40))
    frames.append(f)
save('hw-cauldron', 'Halloween', 'Cauldron', frames, 110)

frames = []
eyes = [(2, 3, (255, 220, 0)), (10, 2, (255, 40, 0)), (5, 8, (120, 255, 0)), (11, 11, (255, 140, 0)), (1, 12, (200, 0, 255))]
for i in range(20):
    f = blank()
    for k, (x, y, c) in enumerate(eyes):
        ph = (i + k * 4) % 20
        if ph in (0, 1):
            continue                     # blink
        cc = scale(c, 0.6 + 0.4 * ((ph % 5) / 4))
        for dx in (0, 3):
            put(f, x + dx, y, cc); put(f, x + dx + 1, y, cc)
    frames.append(f)
save('hw-eyes', 'Halloween', 'Eyes in the dark', frames, 120)

# ---------------- Christmas ----------------
TREE = [
    ".......S........",
    "......SSS.......",
    ".......G........",
    "......GGG.......",
    ".....GGGGG......",
    "......GGG.......",
    ".....GGGGG......",
    "....GGGGGGG.....",
    ".....GGGGG......",
    "....GGGGGGG.....",
    "...GGGGGGGGG....",
    "..GGGGGGGGGGG...",
    ".GGGGGGGGGGGGG..",
    "......TTT.......",
    "......TTT.......",
]
lights = [(7, 4), (6, 6), (8, 7), (5, 8), (9, 9), (6, 10), (4, 11), (8, 11), (10, 11), (3, 12), (7, 12), (12, 12), (5, 9)]
LC = [(255, 0, 0), (0, 80, 255), (255, 200, 0), (255, 0, 200), (255, 255, 255)]
frames = []
for i in range(12):
    f = blank((0, 0, 8))
    sprite(f, TREE, {'G': (0, 120, 30), 'T': (110, 60, 20), 'S': scale((255, 220, 60), 0.6 + 0.4 * (i % 2))}, 0, 1)
    for k, (x, y) in enumerate(lights):
        on = (i + k) % 3 != 0
        put(f, x, y + 1, LC[(k + i // 3) % 5] if on else (0, 60, 15))
    frames.append(f)
save('xm-tree', 'Christmas', 'Christmas tree', frames, 220)

frames = []
flakes = [(random.randint(0, 15), random.randint(0, 15), random.choice([1, 1, 2])) for _ in range(22)]
for i in range(16):
    f = blank((0, 0, 25))
    for x in range(16):
        put(f, x, 15, (200, 210, 230))
        if (x * 7) % 5 == 0:
            put(f, x, 14, (200, 210, 230))
    for (x, y0, sp) in flakes:
        y = (y0 + i * sp) % 16
        xx = (x + (1 if (i + y) % 6 < 3 else 0)) % 16
        put(f, xx, y, (255, 255, 255) if sp == 2 else (170, 190, 230))
    frames.append(f)
save('xm-snow', 'Christmas', 'Snowfall', frames, 120)

SNOWMAN = [
    ".....KKKK.......",
    ".....KKKK.......",
    "....KKKKKK......",
    ".....WWWW.......",
    "....WKWWKW......",
    "....WWOOWW......",
    ".....WWWW.......",
    "...RRRRRRR......",
    "...WWWWWWWW.....",
    "..WWWWKWWWWW....",
    "..WWWWWWWWWW....",
    "..WWWWKWWWWW....",
    "...WWWWWWWW.....",
]
frames = []
fl = [(random.randint(0, 15), random.randint(0, 15)) for _ in range(10)]
for i in range(12):
    f = blank((0, 5, 30))
    for x in range(16):
        put(f, x, 15, (210, 220, 235))
    sprite(f, SNOWMAN, {'K': (30, 30, 40), 'W': (235, 240, 255), 'O': (255, 120, 0), 'R': (220, 0, 0)}, 2, 2)
    arm = (120, 70, 20)
    for k in range(3):
        put(f, 11 + k, 10 - k - (i % 2), arm); put(f, 3 - k, 10 - k, arm)
    for (x, y0) in fl:
        put(f, x, (y0 + i) % 15, (255, 255, 255))
    frames.append(f)
save('xm-snowman', 'Christmas', 'Snowman', frames, 160)

GIFT = [
    "....YY..YY......",
    ".....YYYY.......",
    "..RRRRYYRRRRR...",
    "..RRRRYYRRRRR...",
    "..RRRRYYRRRRR...",
    "..YYYYYYYYYYY...",
    "..RRRRYYRRRRR...",
    "..RRRRYYRRRRR...",
    "..RRRRYYRRRRR...",
    "..RRRRYYRRRRR...",
]
frames = []
for i in range(12):
    f = blank((0, 0, 10))
    jump = 1 if i in (0, 1) else 0
    sprite(f, GIFT, {'R': (220, 0, 30), 'Y': (255, 210, 0)}, 1, 5 - jump)
    for k in range(4):
        a = (i * 30 + k * 90) * math.pi / 180
        put(f, int(7.5 + 6.5 * math.cos(a)), int(5 + 4 * math.sin(a)), (255, 255, 200) if k % 2 else (120, 200, 255))
    frames.append(f)
save('xm-gift', 'Christmas', 'Present', frames, 110)

frames = []
for i in range(8):
    f = blank((0, 0, 0))
    # cane: hook at top, staff down, stripes move
    pts = [(9, 2), (8, 1), (7, 1), (6, 1), (5, 2), (4, 3), (4, 4)] + [(9, y) for y in range(3, 15)]
    pts2 = [(10, 2), (8, 2), (7, 2), (6, 2), (5, 3), (5, 4)] + [(10, y) for y in range(3, 15)]
    for k, (x, y) in enumerate(pts):
        put(f, x, y, (230, 0, 20) if ((k + i) // 2) % 2 else (255, 255, 255))
    for k, (x, y) in enumerate(pts2):
        put(f, x, y, (230, 0, 20) if ((k + i + 1) // 2) % 2 else (255, 255, 255))
    frames.append(f)
save('xm-candycane', 'Christmas', 'Candy cane', frames, 130)

frames = []
for i in range(12):
    f = blank((0, 0, 15))
    k = 0.55 + 0.45 * math.sin(i * math.pi / 6)
    gold = scale((255, 210, 40), k)
    cx, cy = 7.5, 7.5
    for y in range(16):
        for x in range(16):
            dx, dy = x - cx, y - cy
            r = math.hypot(dx, dy)
            ang = math.atan2(dy, dx)
            lim = 3 + 4.5 * (0.5 + 0.5 * math.cos(5 * ang + math.pi / 2)) ** 2
            if r <= lim:
                put(f, x, y, gold if r > 1.6 else (255, 255, 220))
    for (x, y) in [(1, 2), (14, 3), (2, 13), (13, 13)]:
        if (i + x) % 4 == 0:
            put(f, x, y, (255, 255, 255))
    frames.append(f)
save('xm-star', 'Christmas', 'Star', frames, 100)

BELL = [
    "...YY...",
    "..YYYY..",
    ".YYYYYY.",
    ".YYYYYY.",
    ".YYYYYY.",
    "YYYYYYYY",
    "YYYYYYYY",
    "...RR...",
]
frames = []
for i, sh in enumerate([0, 1, 2, 1, 0, -1, -2, -1]):
    f = blank((10, 0, 0))
    for x in range(3, 13):
        put(f, x, 1, (0, 140, 40))
    put(f, 7, 2, (220, 0, 0)); put(f, 8, 2, (220, 0, 0))
    sprite(f, BELL, {'Y': (240, 190, 0), 'R': (160, 90, 0)}, 4 + sh, 4)
    if abs(sh) == 2:
        for d in (1, 3):
            put(f, 4 + sh + (9 if sh > 0 else -1) * 1 + (d if sh > 0 else -d), 6 + d, (255, 255, 255))
    frames.append(f)
save('xm-bell', 'Christmas', 'Bell', frames, 140)

# ---------------- Other celebrations ----------------
HEART = [
    ".RRR...RRR.",
    "RRRRR.RRRRR",
    "RRRRRRRRRRR",
    "RRRRRRRRRRR",
    ".RRRRRRRRR.",
    "..RRRRRRR..",
    "...RRRRR...",
    "....RRR....",
    ".....R.....",
]
HEART_BIG = [
    "..RRRR...RRRR..",
    ".RRRRRR.RRRRRR.",
    "RRRRRRRRRRRRRRR",
    "RRRRRRRRRRRRRRR",
    "RRRRRRRRRRRRRRR",
    ".RRRRRRRRRRRRR.",
    "..RRRRRRRRRRR..",
    "...RRRRRRRRR...",
    "....RRRRRRR....",
    ".....RRRRR.....",
    "......RRR......",
    ".......R.......",
]
frames = []
for i in range(8):
    f = blank()
    if i in (0, 2):
        sprite(f, HEART_BIG, {'R': (255, 20, 60)}, 0, 2)
    else:
        sprite(f, HEART, {'R': (220, 0, 50)}, 2, 4)
    frames.append(f)
save('ev-heart', 'Celebrations', 'Heart', frames, [120, 120, 120, 500, 120, 120, 120, 500])

frames = []
bursts = [(4, 5, (255, 60, 60), 0), (11, 4, (80, 160, 255), 6), (8, 9, (255, 220, 0), 12), (3, 11, (200, 80, 255), 17)]
for i in range(24):
    f = blank((0, 0, 6))
    for (cx, cy, c, t0) in bursts:
        t = (i - t0) % 24
        if t < 4:   # rocket going up
            put(f, cx, 15 - int((15 - cy) * t / 4), (255, 200, 120))
        elif t < 12:
            r = (t - 4) * 0.8
            k = 1 - (t - 4) / 8
            for a in range(0, 360, 45):
                put(f, int(round(cx + r * math.cos(math.radians(a)))), int(round(cy + r * math.sin(math.radians(a)))), scale(c, k))
            if t < 6:
                put(f, cx, cy, (255, 255, 255))
    frames.append(f)
save('ev-fireworks', 'Celebrations', 'Fireworks', frames, 90)

EGG = [
    "....PPPP....",
    "...PPPPPP...",
    "..PPPPPPPP..",
    "..YYYYYYYY..",
    ".PPPPPPPPPP.",
    ".GPGPGPGPGP.",
    ".PPPPPPPPPP.",
    ".YYYYYYYYYY.",
    ".PPPPPPPPPP.",
    "..PPPPPPPP..",
    "...PPPPPP...",
]
frames = []
for i, r in enumerate([0, 1, 0, -1, 0, 0, 0, 0]):
    f = blank((0, 30, 0))
    for x in range(16):
        put(f, x, 15, (40, 160, 40)); put(f, x, 14, (40, 160, 40) if x % 2 else (0, 0, 0))
    sprite(f, EGG, {'P': (255, 140, 200), 'Y': (255, 230, 60), 'G': (60, 200, 255)}, 2 + r, 3)
    frames.append(f)
save('ev-egg', 'Celebrations', 'Easter egg', frames, 150)

frames = []
conf = [(random.randint(0, 15), random.randint(0, 15), random.choice([(255, 0, 80), (0, 200, 255), (255, 220, 0), (120, 255, 0), (200, 80, 255)]), random.choice([1, 2])) for _ in range(26)]
for i in range(16):
    f = blank()
    for (x, y0, c, sp) in conf:
        y = (y0 + i * sp) % 16
        put(f, (x + (i // 4 if sp == 1 else 0)) % 16, y, c)
    frames.append(f)
save('ev-confetti', 'Celebrations', 'Confetti', frames, 90)

CLOVER = [
    "...GGG..GGG...",
    "..GGGGGGGGGG..",
    "..GGGGGGGGGG..",
    "...GGGGGGGG...",
    "GGG..GGGG..GGG",
    "GGGGGGGGGGGGGG",
    "GGGGGGGGGGGGGG",
    ".GGGGGGGGGGGG.",
    "..GGG.GG.GGG..",
    "......GG......",
    ".......GG.....",
    "........GG....",
]
frames = []
for i in range(10):
    f = blank()
    k = 0.7 + 0.3 * math.sin(i * math.pi / 5)
    sprite(f, CLOVER, {'G': scale((20, 200, 60), k)}, 1, 2)
    if i % 5 == 0:
        put(f, 3, 3, (255, 255, 200))
    frames.append(f)
save('ev-clover', 'Celebrations', 'Lucky clover', frames, 120)


# ================= more animations (pack v2) =================
FONT = {  # 3x5 digits
    '0': ["XXX", "X.X", "X.X", "X.X", "XXX"], '1': [".X.", "XX.", ".X.", ".X.", "XXX"], '2': ["XXX", "..X", "XXX", "X..", "XXX"],
    '3': ["XXX", "..X", ".XX", "..X", "XXX"], '4': ["X.X", "X.X", "XXX", "..X", "..X"], '5': ["XXX", "X..", "XXX", "..X", "XXX"],
    '6': ["XXX", "X..", "XXX", "X.X", "XXX"], '7': ["XXX", "..X", ".X.", ".X.", ".X."], '8': ["XXX", "X.X", "XXX", "X.X", "XXX"],
    '9': ["XXX", "X.X", "XXX", "..X", "XXX"],
}

def text(f, s, x, y, c):
    for ch in s:
        sprite(f, FONT[ch], {'X': c}, x, y)
        x += 4

# ---- Halloween ----
CAT = [
    ".K.....K.",
    ".KK...KK.",
    ".KKKKKKK.",
    "KKEKKKEKK",
    "KKKKKKKKK",
    ".KKKPKKK.",
    "..KKKKK..",
    ".KKKKKKK.",
    "KKKKKKKKK",
    "KKKKKKKKK",
    "KKKKKKKKK",
    ".KK...KK.",
]
frames = []
for i in range(16):
    f = blank((10, 0, 25))
    for (x, y) in [(13, 1), (14, 1), (13, 2), (14, 2), (12, 2)]:
        put(f, x, y, (250, 240, 170))
    blink = i in (5, 6)
    sprite(f, CAT, {'K': (70, 60, 95), 'E': (70, 60, 95) if blink else (255, 220, 0), 'P': (255, 120, 160)}, 2, 3)
    tail = [(11, 13), (12, 12), (13, 11), (13, 10)] if (i // 4) % 2 == 0 else [(11, 13), (12, 13), (13, 12), (14, 11)]
    for (x, y) in tail:
        put(f, x, y, (70, 60, 95))
    for x in range(16):
        put(f, x, 15, (60, 30, 80))
    frames.append(f)
save('hw-cat', 'Halloween', 'Black cat', frames, 120)

GRAVE = [
    "..GGGG..",
    ".GGGGGG.",
    "GGGGGGGG",
    "GGDGGDGG",
    "GDDDDDDG",
    "GGDGGDGG",
    "GGGGGGGG",
    "GGGGGGGG",
]
frames = []
for i in range(16):
    f = blank((0, 0, 15))
    sprite(f, GRAVE, {'G': (120, 120, 130), 'D': (70, 70, 80)}, 4, 5)
    for x in range(16):
        put(f, x, 13, (30, 60, 20)); put(f, x, 14, (30, 60, 20)); put(f, x, 15, (40, 25, 10))
    for x in range(16):   # drifting fog
        k = 0.5 + 0.5 * math.sin((x + i) * 0.7)
        put(f, x, 12, mix(f[12][x], (140, 140, 170), 0.6 * k))
        if (x + i) % 5 == 0:
            put(f, x, 11, mix(f[11][x], (110, 110, 140), 0.5))
    if i in (3, 4, 11):
        put(f, 1, 2, (200, 255, 200)); put(f, 14, 4, (200, 255, 200))
    frames.append(f)
save('hw-grave', 'Halloween', 'Graveyard', frames, 140)

frames = []
HAND = ["G.G.G", "G.G.G", "GGGGG", "GGGGG", ".GGG.", ".GGG.", ".GGG."]
for i in range(16):
    f = blank((5, 0, 15))
    rise = min(7, i) if i < 12 else 7 - (i - 11) * 2
    sprite(f, HAND, {'G': (110, 170, 90)}, 6, 15 - max(0, rise) - 1)
    if i >= 7 and i < 12 and i % 2:   # wave
        put(f, 5, 15 - rise, (110, 170, 90))
    for x in range(16):
        put(f, x, 14, (60, 40, 20)); put(f, x, 15, (45, 30, 15))
    for (x, y) in [(3, 13), (11, 13), (12, 12)]:
        put(f, x, y, (60, 40, 20))
    frames.append(f)
save('hw-hand', 'Halloween', 'Zombie hand', frames, 140)

CORN = [
    "......WW......",
    ".....WWWW.....",
    "....OOOOOO....",
    "...OOOOOOOO...",
    "..YYYYYYYYYY..",
    ".YYYYYYYYYYYY.",
]
frames = []
for i in range(8):
    f = blank((20, 0, 30))
    for k, dy in enumerate([0, 1, 0, -1]):
        pass
    bob = [0, 1, 1, 0, 0, -1, -1, 0][i]
    sprite(f, CORN, {'W': (255, 255, 235), 'O': (255, 120, 0), 'Y': (255, 210, 0)}, 1, 5 + bob)
    for k in range(5):
        a = (i * 45 + k * 72) * math.pi / 180
        put(f, int(7.5 + 7 * math.cos(a)), int(8 + 6 * math.sin(a)), (255, 150, 0) if k % 2 else (180, 0, 255))
    frames.append(f)
save('hw-candycorn', 'Halloween', 'Candy corn', frames, 120)

HAT = [
    "......KK........",
    ".....KKK........",
    "....KKKK........",
    "....KKKKK.......",
    "...KKKKKK.......",
    "...KKKKKKK......",
    "..KPPPPPPPK.....",
    "..KKKKKKKKK.....",
    "KKKKKKKKKKKKK...",
]
frames = []
for i in range(12):
    f = blank((15, 0, 30))
    for k in range(6):
        sx, sy = (k * 5 + 3) % 16, (k * 7 + 1) % 6
        if (i + k) % 4:
            put(f, sx, sy, (200, 200, 255))
    sprite(f, HAT, {'K': (95, 50, 140), 'P': scale((160, 0, 255), 0.6 + 0.4 * (i % 2))}, 2, 6)
    b = (i % 6)
    for x in range(16):
        put(f, x, 15, (70, 35, 0))
    put(f, 13 - b, 13, (255, 230, 120))   # sparkles from the hat
    put(f, 14 - b // 2, 12 - b // 3, (255, 160, 255))
    frames.append(f)
save('hw-witchhat', 'Halloween', 'Witch hat', frames, 130)

frames = []
for i in range(16):
    f = blank((0, 0, 20))
    for y in range(16):
        for x in range(16):
            if math.hypot(x - 8, y - 7) <= 5.5:
                put(f, x, y, (240, 235, 190))
            if math.hypot(x - 6, y - 6) < 1.2 or math.hypot(x - 10, y - 9) < 1.1:
                put(f, x, y, (200, 195, 150))
    cx = (i * 1.2) % 26 - 6
    for dx in range(7):
        for dy in range(2):
            x = int(cx + dx)
            put(f, x, 9 + dy, mix(f[9 + dy][x % 16] if 0 <= x < 16 else (0, 0, 0), (70, 70, 100), 0.85))
    frames.append(f)
save('hw-moon', 'Halloween', 'Full moon', frames, 120)

# ---- Christmas ----
frames = []
for i, sh in enumerate([0, 1, 1, 0, 0, -1, -1, 0]):
    f = blank((0, 0, 10))
    for y in range(0, 4):
        put(f, 8, y, (180, 180, 180))
    put(f, 7, 4, (220, 200, 60)); put(f, 8, 4, (220, 200, 60))
    cx, cy = 7.5 + sh, 9.5
    for y in range(16):
        for x in range(16):
            r = math.hypot(x - cx, y - cy)
            if r <= 5:
                c = (220, 0, 40)
                if abs(y - cy) < 1: c = (255, 210, 0)
                if r < 2.2 and x < cx and y < cy: c = (255, 140, 150)
                put(f, x, y, c)
    if i % 4 == 0:
        put(f, int(cx - 2), int(cy - 3), (255, 255, 255))
    frames.append(f)
save('xm-ornament', 'Christmas', 'Ornament', frames, 160)

GINGER = [
    "....BBBB....",
    "...BBBBBB...",
    "...BWBBWB...",
    "...BBBBBB...",
    "....BRRB....",
    ".BBBBBBBBBB.",
    "BBBBBWBBBBBB",
    "BB.BBBBBB.BB",
    "...BBWBBB...",
    "...BBBBBB...",
    "..BBB..BBB..",
    "..BB....BB..",
    ".BBB....BBB.",
]
frames = []
for i in range(8):
    f = blank((15, 0, 0))
    hop = 1 if i % 4 in (1, 2) else 0
    sprite(f, GINGER, {'B': (170, 90, 30), 'W': (255, 255, 255), 'R': (230, 0, 30)}, 2, 2 - hop)
    for x in range(16):
        put(f, x, 15, (255, 255, 255) if (x + i) % 2 else (230, 0, 30))
    frames.append(f)
save('xm-gingerbread', 'Christmas', 'Gingerbread', frames, 150)

HOLLY = [
    "..GG......GG..",
    ".GGGG....GGGG.",
    "GGGGGG..GGGGGG",
    ".GGGGGRRGGGGG.",
    "..GGGRRRRGGG..",
    "...GG.RR.GG...",
]
frames = []
for i in range(10):
    f = blank((0, 0, 0))
    k = 0.7 + 0.3 * math.sin(i * math.pi / 5)
    sprite(f, HOLLY, {'G': (0, 140, 40), 'R': scale((255, 0, 20), k)}, 1, 5)
    if i % 5 == 0:
        put(f, 7, 8, (255, 220, 220))
    for x in range(16):
        if (x + i) % 4 == 0:
            put(f, x, 1, (255, 215, 0)); put(f, (x + 2) % 16, 14, (255, 215, 0))
    frames.append(f)
save('xm-holly', 'Christmas', 'Holly', frames, 140)

frames = []
pts = [(int(round(7.5 + 6 * math.cos(a * math.pi / 12))), int(round(7.5 + 6 * math.sin(a * math.pi / 12)))) for a in range(24)]
for i in range(12):
    f = blank((0, 0, 0))
    for k, (x, y) in enumerate(pts):
        put(f, x, y, (0, 130, 30))
        for (dx, dy) in [(1, 0), (0, 1)]:
            put(f, x + dx, y + dy, (0, 100, 20))
    for k in range(0, 24, 3):
        x, y = pts[k]
        put(f, x, y, LC[(k // 3 + i) % 5] if (k // 3 + i) % 2 else (0, 130, 30))
    for (x, y, c) in [(6, 13, (220, 0, 0)), (7, 13, (220, 0, 0)), (8, 13, (220, 0, 0)), (9, 13, (220, 0, 0)), (6, 14, (220, 0, 0)), (9, 14, (220, 0, 0))]:
        put(f, x, y, c)
    frames.append(f)
save('xm-wreath', 'Christmas', 'Wreath', frames, 180)

SOCK = [
    "WWWWWW...",
    "WWWWWW...",
    "RRRRRR...",
    "RRGRRR...",
    "RRRRRR...",
    "RRRGRR...",
    "RRRRRR...",
    "RRRRRRRR.",
    "RRRRRRRRR",
    ".RRRRRRRR",
    "..RRRRRR.",
]
frames = []
for i, sw in enumerate([0, 0, 1, 1, 0, 0, -1, -1]):
    f = blank((30, 10, 0))
    for x in range(16):
        put(f, x, 2, (110, 60, 20))
    sprite(f, SOCK, {'W': (240, 240, 240), 'R': (210, 0, 30), 'G': (0, 160, 40)}, 4 + sw, 3)
    if i % 4 == 0:
        put(f, 5 + sw, 2, (255, 230, 0))
    for x in range(3, 13):
        put(f, x, 15, (255, 100 + 50 * ((x + i) % 3), 0))
    frames.append(f)
save('xm-stocking', 'Christmas', 'Stocking', frames, 150)

# ---- Celebrations ----
CAKE = [
    "................",
    "................",
    "................",
    "..PPPPPPPPPPPP..",
    "..WPWPWPWPWPWP..",
    "..PPPPPPPPPPPP..",
    "..YYYYYYYYYYYY..",
    ".BBBBBBBBBBBBBB.",
    ".BWBWBWBWBWBWBW.",
    ".BBBBBBBBBBBBBB.",
    ".BBBBBBBBBBBBBB.",
    "GGGGGGGGGGGGGGGG",
]
frames = []
for i in range(10):
    f = blank()
    sprite(f, CAKE, {'P': (255, 120, 180), 'W': (255, 255, 255), 'Y': (255, 220, 0), 'B': (130, 60, 30), 'G': (150, 150, 160)}, 0, 4)
    for k, x in enumerate([4, 7, 10]):
        for y in (4, 5, 6):
            put(f, x, y, (100, 180, 255))
        fl = (255, 220, 60) if (i + k) % 3 else (255, 120, 0)
        put(f, x, 3, fl); put(f, x, 2, scale(fl, 0.5) if (i + k) % 2 else (0, 0, 0))
    frames.append(f)
save('ev-cake', 'Celebrations', 'Birthday cake', frames, 120)

frames = []
bal = [(2, (255, 0, 60), 0), (7, (0, 160, 255), 5), (12, (255, 210, 0), 10), (5, (160, 60, 255), 13)]
for i in range(16):
    f = blank((0, 0, 10))
    for (x, c, t0) in bal:
        y = 16 - ((i + t0) % 16) * 1.4
        yy = int(y)
        for (dx, dy) in [(0, 0), (1, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (-1, 2), (0, 2), (1, 2), (2, 2), (0, 3), (1, 3)]:
            put(f, x + dx, yy + dy, c)
        put(f, x, yy + 1, scale(c, 1.4) if True else c)
        for k in range(4, 7):
            put(f, x + (k % 2), yy + k, (200, 200, 200))
    frames.append(f)
save('ev-balloons', 'Celebrations', 'Balloons', frames, 110)

frames = []
for i in range(20):
    f = blank((0, 0, 10))
    c = [(255, 210, 0), (255, 255, 255), (0, 200, 255), (255, 60, 160)][(i // 5) % 4]
    text(f, '2027', 0, 5, c)
    for k in range(6):
        if (i + k * 3) % 5 == 0:
            put(f, (k * 5 + i) % 16, (k * 3) % 4, (255, 255, 255))
            put(f, (k * 7 + i) % 16, 12 + (k % 4), (255, 200, 0))
    frames.append(f)
save('ev-newyear', 'Celebrations', 'New Year 2027', frames, 120)

frames = []
hearts = [(2, 0, (255, 30, 90)), (9, 6, (255, 100, 160)), (5, 11, (220, 0, 60)), (12, 3, (255, 60, 120))]
SMALLH = ["X.X", "XXX", ".X."]
for i in range(16):
    f = blank((20, 0, 10))
    for (x, t0, c) in hearts:
        y = 15 - ((i + t0) % 16)
        xx = x + (1 if ((i + t0) // 3) % 2 else 0)
        sprite(f, SMALLH, {'X': c}, xx, y)
    frames.append(f)
save('ev-hearts', 'Celebrations', 'Floating hearts', frames, 110)

BUNNY = [
    "..W...W...",
    "..WP..WP..",
    "..WP..WP..",
    "..WW..WW..",
    ".WWWWWWW..",
    "WWKWWWKWW.",
    "WWWWPWWWW.",
    ".WWWWWWW..",
    "..WWWWWW..",
    ".WWWWWWWW.",
    ".WWWWWWWWW",
    "..WW..WW..",
]
frames = []
for i in range(8):
    f = blank((40, 120, 255))
    hop = [0, 1, 2, 2, 1, 0, 0, 0][i]
    for x in range(16):
        put(f, x, 15, (40, 170, 40)); put(f, x, 14, (40, 170, 40) if x % 3 else (255, 220, 0))
    sprite(f, BUNNY, {'W': (245, 245, 245), 'P': (255, 150, 180), 'K': (20, 20, 20)}, 3, 2 - hop)
    frames.append(f)
save('ev-bunny', 'Celebrations', 'Bunny', frames, 130)

frames = []
RB = [(255, 0, 0), (255, 120, 0), (255, 220, 0), (0, 200, 40), (0, 120, 255), (130, 40, 220)]
for i in range(12):
    f = blank((90, 170, 255))
    for k, c in enumerate(RB):
        r = 8 - k
        for a in range(0, 181, 6):
            x = int(round(7.5 + r * math.cos(math.radians(a))))
            y = int(round(13 - r * math.sin(math.radians(a))))
            put(f, x, y, c)
    for (x, y) in [(0, 12), (1, 12), (1, 11), (2, 12), (14, 12), (15, 12), (14, 11), (13, 12)]:
        put(f, x, y, (255, 255, 255))
    if i % 3 == 0:
        put(f, 7 + (i % 5) - 2, 7, (255, 255, 255))
    frames.append(f)
save('ev-rainbow', 'Celebrations', 'Rainbow', frames, 140)

frames = []
for i in range(12):
    f = blank((40, 140, 255))
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - 7.5, y - 7.5)
            if d <= 3.6:
                put(f, x, y, (255, 230, 40))
            else:
                a = math.atan2(y - 7.5, x - 7.5) + i * math.pi / 24
                if d <= 7 and (math.cos(8 * a) > 0.55):
                    put(f, x, y, (255, 170, 0))
    put(f, 6, 7, (60, 40, 0)); put(f, 9, 7, (60, 40, 0))
    for x in (6, 7, 8, 9):
        put(f, x, 9 if x in (7, 8) else 8, (60, 40, 0))
    frames.append(f)
save('ev-sun', 'Celebrations', 'Sun', frames, 110)

# ================= more GIFs (pack 2): 9 Halloween + 9 Christmas =================
FONT = {'B': ["110", "101", "110", "101", "110"], 'O': ["010", "101", "101", "101", "010"], '!': ["1", "1", "1", "0", "1"],
        'H': ["101", "101", "111", "101", "101"], ' ': ["00", "00", "00", "00", "00"]}


def text_cols(s):
    cols = []
    for ch in s:
        g = FONT[ch]
        for x in range(len(g[0])):
            cols.append([g[y][x] == '1' for y in range(5)])
        cols.append([False] * 5)
    return cols


def scroll_text(s, colour_at, bg=(0, 0, 0), extra=None):
    cols = text_cols(s)
    frames = []
    total = len(cols) * 2 + W
    for i in range(0, total, 1):
        f = blank(bg)
        if extra:
            extra(f, i)
        for x in range(W):
            cx = (x + i - W) // 2
            if 0 <= cx < len(cols):
                for y in range(5):
                    if cols[cx][y]:
                        for dy in (0, 1):
                            put(f, x, 3 + y * 2 + dy, colour_at(x, y, i))
        frames.append(f)
    return frames


def disc(f, cx, cy, r, c):
    for y in range(H):
        for x in range(W):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                put(f, x, y, c)


def flame(f, x0, ytop, i, seed):
    rnd = random.Random(seed * 100 + i)
    h = 3 + rnd.randint(0, 1)
    sway = rnd.choice([-1, 0, 0, 1])
    for k in range(h):
        y = ytop + 3 - k
        c = (255, 240, 120) if k < 1 else (255, 170, 20) if k < h - 1 else (255, 90, 0)
        put(f, x0, y, c); put(f, x0 + 1, y, c)
    put(f, x0 + (1 if sway > 0 else 0), ytop + 3 - h, (255, 90, 0))


def candle(name, theme, title, body, trim, bg, decor=None):
    frames = []
    for i in range(14):
        f = blank(bg)
        glow = 0.5 + 0.25 * random.Random(i).random()
        for y in range(16):
            for x in range(16):
                d = math.hypot(x - 7.5, y - 5)
                if d < 6:
                    f[y][x] = mix(bg, (90, 45, 0), glow * (1 - d / 6))
        for y in range(8, 16):
            for x in range(6, 10):
                put(f, x, y, body if x < 9 else scale(body, 0.7))
        put(f, 6, 9, trim); put(f, 6, 10, trim); put(f, 9, 9, trim)
        put(f, 7, 7, (40, 40, 40))
        flame(f, 7, 3, i, 3)
        if decor:
            decor(f, i)
        frames.append(f)
    save(name, theme, title, frames, 90)


# ---- Halloween: witch flying past the moon ----
WITCH = [
    "......K.........",
    "......KK........",
    "......KKK.......",
    ".....KKKKK......",
    ".....gK.........",
    ".....KKKK.......",
    "..KKKKKKKKKKBBB.",
    ".....K.K...BBBB.",
]
frames = []
for i in range(34):
    f = blank((10, 10, 40))
    disc(f, 9.5, 6.5, 5.2, (250, 235, 160))
    put(f, 8, 4, (225, 210, 140)); put(f, 11, 8, (225, 210, 140)); put(f, 10, 5, (225, 210, 140))
    for (x, y) in [(1, 1), (3, 12), (14, 14), (13, 0), (2, 6)]:
        if (i + x) % 7: put(f, x, y, (200, 200, 255))
    sprite(f, WITCH, {'K': (0, 0, 0), 'g': (60, 160, 40), 'B': (150, 90, 30)}, 17 - i, 4 + int(round(math.sin(i / 3) * 1.5)))
    frames.append(f)
save('hw-witch', 'Halloween', 'Flying witch', frames, 80)

# ---- Halloween: mummy ----
frames = []
for i in range(16):
    f = blank()
    for y in range(1, 16):
        for x in range(2, 14):
            if (y == 1 and x in (2, 13)) or (y == 2 and x in (2, 13)):
                continue
            c = (165, 150, 120) if (y + x // 6) % 3 == 0 else (225, 215, 185)
            put(f, x, y, c)
    for x in range(3, 13):
        put(f, x, 6, (40, 30, 20)); put(f, x, 7, (40, 30, 20)); put(f, x, 8, (40, 30, 20))
    blink = i in (7, 8)
    eye = (255, 40, 30) if not blink else (40, 30, 20)
    g = 0.7 + 0.3 * math.sin(i)
    for (x, y) in [(5, 7), (6, 7), (9, 7), (10, 7)]:
        put(f, x, y, scale(eye, g) if not blink else eye)
    if not blink:
        put(f, 5, 6, scale(eye, 0.5)); put(f, 10, 6, scale(eye, 0.5))
    for x in range(6, 10):
        put(f, x, 12, (40, 30, 20))
    put(f, 14 if i % 8 < 4 else 15, 10 + (i % 4), (225, 215, 185))
    frames.append(f)
save('hw-mummy', 'Halloween', 'Mummy', frames, 120)

# ---- Halloween: spooky candle ----
candle('hw-candle', 'Halloween', 'Spooky candle', (235, 230, 210), (255, 255, 240), (8, 0, 18),
       lambda f, i: [put(f, x, 15, (60, 0, 80)) for x in range(16)])

# ---- Halloween: owl ----
frames = []
for i in range(16):
    f = blank((5, 10, 35))
    disc(f, 13, 2, 1.6, (240, 240, 200))
    for x in range(16):
        put(f, x, 14, (90, 55, 20)); put(f, x, 15, (60, 35, 10))
    for y in range(3, 14):
        for x in range(3, 13):
            if (y == 3 and x in (5, 6, 7, 8, 9, 10)) or (y == 13 and x in (3, 12)):
                continue
            put(f, x, y, (140, 90, 45) if y < 10 or (x + y) % 2 else (190, 140, 80))
    put(f, 3, 2, (140, 90, 45)); put(f, 12, 2, (140, 90, 45)); put(f, 4, 3, (140, 90, 45)); put(f, 11, 3, (140, 90, 45))
    blink = i in (10, 11)
    look = [0, 0, 0, 1, 1, 1, 0, 0, 0, -1, -1, -1, 0, 0, 0, 0][i]
    for cx in (5.5, 10.5):
        if blink:
            for x in range(int(cx) - 1, int(cx) + 2):
                put(f, x, 6, (60, 35, 10))
        else:
            disc(f, cx, 6, 2.2, (255, 210, 40))
            put(f, int(cx) + (1 if look > 0 else 0) + (-1 if look < 0 else 0), 6, (0, 0, 0))
    put(f, 7, 8, (240, 160, 30)); put(f, 8, 8, (240, 160, 30)); put(f, 7, 9, (200, 120, 20))
    for x in (5, 7, 9):
        put(f, x, 14, (240, 160, 30))
    frames.append(f)
save('hw-owl', 'Halloween', 'Owl', frames, 140)

# ---- Halloween: bubbling potion ----
frames = []
bub = []
rnd = random.Random(9)
for i in range(18):
    f = blank((10, 0, 20))
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - 7.5, y - 10)
            if d <= 5.3:
                put(f, x, y, (60, 230, 60) if y >= 8 else (90, 90, 120))
                if y == 8:
                    put(f, x, y, (160, 255, 120))
            elif d <= 5.9:
                put(f, x, y, (150, 150, 180))
    for y in range(2, 5):
        put(f, 6, y, (150, 150, 180)); put(f, 9, y, (150, 150, 180)); put(f, 7, y, (90, 90, 120)); put(f, 8, y, (90, 90, 120))
    for x in (6, 7, 8, 9):
        put(f, x, 1, (140, 80, 30))
    put(f, 7, 0, (140, 80, 30)); put(f, 8, 0, (140, 80, 30))
    if i % 2 == 0:
        bub.append([rnd.randint(4, 11), 13])
    nb = []
    for b in bub:
        b[1] -= 1
        if b[1] >= 8:
            put(f, b[0], b[1], (200, 255, 200))
            nb.append(b)
    bub = nb
    put(f, 5, 11, (120, 255, 120)); put(f, 4, 10, (120, 255, 120))
    frames.append(f)
save('hw-potion', 'Halloween', 'Magic potion', frames, 100)

# ---- Halloween: haunted house with lightning ----
HOUSE = [
    "......K.........",
    ".....KKK.....K..",
    "....KKKKK...KKK.",
    "...KKKKKKK..KKK.",
    "..KKKKKKKKK.KKK.",
    "...KyKKKyK..KyK.",
    "...KyKKKyK..KKK.",
    "...KKKKKKKKKKKK.",
    "...KKKKyyKKKKKK.",
    "...KKKKyyKKKyKK.",
    "...KKKKKKKKKKKK.",
]
frames = []
for i in range(24):
    flash = i in (6, 8, 17)
    f = blank((200, 200, 255) if flash else (25, 0, 45))
    if not flash:
        disc(f, 2.5, 2.5, 1.6, (230, 230, 180))
    if i in (6, 7, 8):
        for (x, y) in [(10, 0), (9, 1), (10, 2), (11, 3), (10, 4)]:
            put(f, x, y, (255, 255, 160))
    for x in range(16):
        put(f, x, 15, (20, 40, 10))
    win = (255, 200, 40) if (i // 3) % 4 else (255, 120, 0)
    sprite(f, HOUSE, {'K': (0, 0, 0), 'y': win}, 0, 4)
    frames.append(f)
save('hw-haunted', 'Halloween', 'Haunted house', frames, 110)

# ---- Halloween: BOO! ----
save('hw-boo', 'Halloween', 'BOO!', scroll_text(' BOO!', lambda x, y, i: (255, 120, 0) if (x + i) % 6 else (255, 220, 0)), 70)

# ---- Halloween: flock of bats ----
BAT_UP = ["K...K", "KK.KK", ".KKK."]
BAT_DN = [".KKK.", "KK.KK", "K...K"]
frames = []
for i in range(32):
    f = blank((40, 10, 60))
    disc(f, 11.5, 4.5, 3.2, (255, 190, 80))
    for k, (sx, sy, sp) in enumerate([(0, 3, 1), (-6, 8, 1), (-12, 5, 1), (-3, 12, 1)]):
        x = (sx + i * sp) % 40 - 8
        y = sy + int(round(math.sin((i + k * 3) / 2.5)))
        sprite(f, BAT_UP if (i + k) % 4 < 2 else BAT_DN, {'K': (0, 0, 0)}, x, y)
    frames.append(f)
save('hw-bats', 'Halloween', 'Bats', frames, 90)

# ---- Halloween: eyeball ----
frames = []
path = [(0, 0), (1, 0), (2, 0), (2, 1), (1, 2), (0, 2), (-1, 2), (-2, 1), (-2, 0), (-2, -1), (-1, -2), (0, -2), (1, -2), (0, 0), (0, 0), (0, 0)]
for i, (dx, dy) in enumerate(path):
    f = blank()
    disc(f, 7.5, 7.5, 7.3, (240, 240, 235))
    for (x, y) in [(1, 7), (2, 6), (2, 8), (13, 9), (14, 8), (12, 10), (6, 1), (5, 2), (9, 14), (10, 13)]:
        put(f, x, y, (220, 40, 40))
    disc(f, 7.5 + dx, 7.5 + dy, 3.3, (40, 160, 90))
    disc(f, 7.5 + dx, 7.5 + dy, 1.6, (0, 0, 0))
    put(f, 6 + dx, 6 + dy, (255, 255, 255))
    if i in (14, 15):
        for y in range(0, 16 if i == 15 else 8):
            for x in range(16):
                if (x - 7.5) ** 2 + (y - 7.5) ** 2 <= 7.3 ** 2:
                    put(f, x, y, (200, 120, 110))
    frames.append(f)
save('hw-eyeball', 'Halloween', 'Eyeball', frames, 130)

# ---- Christmas: Santa ----
frames = []
for i in range(16):
    f = blank((0, 30, 10))
    for y in range(0, 6):
        for x in range(4 + y // 2 - 1, 13 - (0 if y > 1 else 2)):
            put(f, x, y, (220, 20, 30))
    disc(f, 13, 1, 1.5, (255, 255, 255))
    for x in range(2, 14):
        put(f, x, 5, (255, 255, 255)); put(f, x, 6, (255, 255, 255))
    for y in range(7, 11):
        for x in range(3, 13):
            put(f, x, y, (255, 200, 160))
    blink = i in (11, 12)
    for x in (5, 10):
        put(f, x, 8, (30, 30, 30) if not blink else (230, 170, 130))
    put(f, 4, 9, (255, 140, 140)); put(f, 11, 9, (255, 140, 140))
    put(f, 7, 9, (240, 150, 120)); put(f, 8, 9, (240, 150, 120))
    for y in range(10, 16):
        for x in range(2 + max(0, y - 13), 14 - max(0, y - 13)):
            put(f, x, y, (255, 255, 255) if (x + y + i) % 7 else (215, 215, 225))
    open_m = i % 4 < 2
    for x in (6, 7, 8, 9):
        put(f, x, 11, (150, 30, 30) if open_m and x in (7, 8) else (255, 255, 255))
    if open_m:
        put(f, 7, 12, (150, 30, 30)); put(f, 8, 12, (150, 30, 30))
    frames.append(f)
save('xm-santa', 'Christmas', 'Santa', frames, 150)

# ---- Christmas: reindeer ----
frames = []
for i in range(16):
    f = blank((10, 20, 60))
    for (x, y) in [(1, 13), (14, 12), (2, 2), (13, 1)]:
        if (i + x) % 5: put(f, x, y, (255, 255, 255))
    ant = (200, 160, 90)
    for (x, y) in [(4, 0), (4, 1), (3, 1), (5, 2), (5, 3), (2, 2), (11, 0), (11, 1), (12, 1), (10, 2), (10, 3), (13, 2)]:
        put(f, x, y, ant)
    for y in range(4, 13):
        for x in range(4, 12):
            if (y > 9 and x in (4, 11)):
                continue
            put(f, x, y, (140, 85, 40))
    put(f, 3, 5, (140, 85, 40)); put(f, 2, 5, (140, 85, 40)); put(f, 12, 5, (140, 85, 40)); put(f, 13, 5, (140, 85, 40))
    for y in range(9, 14):
        for x in range(5, 11):
            put(f, x, y, (190, 140, 90))
    blink = i in (9, 10)
    for x in (6, 9):
        put(f, x, 7, (0, 0, 0) if not blink else (110, 65, 30))
    put(f, 7, 11, (40, 25, 15)); put(f, 8, 11, (40, 25, 15)); put(f, 7, 10, (40, 25, 15)); put(f, 8, 10, (40, 25, 15))
    for x in range(5, 11):
        put(f, x, 14, (200, 0, 30) if x % 2 else (40, 140, 40))
    put(f, 7, 15, (255, 210, 40) if i % 4 < 2 else (200, 150, 20)); put(f, 8, 15, (255, 210, 40) if i % 4 < 2 else (200, 150, 20))
    frames.append(f)
save('xm-reindeer', 'Christmas', 'Reindeer', frames, 140)

# ---- Christmas: string of lights ----
BULBS = [(255, 30, 30), (40, 220, 60), (40, 120, 255), (255, 200, 0), (255, 80, 220)]
frames = []
for i in range(10):
    f = blank()
    for row, base in ((0, 3), (1, 10)):
        for x in range(16):
            y = base + int(round(1.2 * math.sin((x + row * 3) / 2.6)))
            put(f, x, y, (20, 70, 20))
            if (x + row) % 3 == 1:
                k = (x // 3 + row * 2) % len(BULBS)
                on = (x // 3 + i + row) % 3 != 0
                c = BULBS[k] if on else scale(BULBS[k], 0.25)
                put(f, x, y + 1, c); put(f, x, y + 2, c)
                if on:
                    put(f, x - 1, y + 2, scale(c, 0.3)); put(f, x + 1, y + 2, scale(c, 0.3)); put(f, x, y + 3, scale(c, 0.35))
    frames.append(f)
save('xm-lights', 'Christmas', 'Christmas lights', frames, 220)


# ---- Christmas: candle with holly ----
def holly(f, i):
    for (x, y) in [(3, 14), (4, 13), (4, 14), (5, 14), (10, 14), (11, 13), (11, 14), (12, 14), (2, 15), (13, 15)]:
        put(f, x, y, (30, 150, 50))
    put(f, 6, 15, (230, 20, 30)); put(f, 9, 15, (230, 20, 30)); put(f, 7, 15, (200, 10, 20))


candle('xm-candle', 'Christmas', 'Christmas candle', (210, 20, 30), (255, 210, 60), (0, 12, 4), holly)

# ---- Christmas: sleigh in the sky ----
SLEIGH = [
    "...........gg..",
    "..R.......gPPg.",
    "..RR.....RRRRR.",
    "..RRRRRRRRRRRR.",
    "...RRRRRRRRRR..",
    ".Y..Y......Y...",
    "YYYYYYYYYYYYYY.",
]
frames = []
for i in range(36):
    f = blank((5, 10, 40))
    for (x, y) in [(1, 1), (5, 3), (9, 0), (13, 2), (3, 6), (11, 5), (15, 7), (7, 13), (2, 14), (14, 13)]:
        put(f, x, y, (255, 255, 255) if (i + x * y) % 6 else (120, 120, 160))
    disc(f, 13, 12, 1.5, (240, 240, 210))
    sx = i - 16
    yy = 6 + int(round(math.sin(i / 4)))
    for k in range(1, 7):
        if (i + k) % 2:
            put(f, sx - k, yy + 5 + (k % 2), (255, 220, 120))
    sprite(f, SLEIGH, {'R': (210, 20, 30), 'Y': (255, 200, 40), 'g': (40, 180, 60), 'P': (255, 80, 200)}, sx, yy)
    frames.append(f)
save('xm-sleigh', 'Christmas', 'Sleigh', frames, 80)

# ---- Christmas: snowflake ----
FLAKE = [
    ".......*........",
    "......***.......",
    ".....*.*.*......",
    "..*....*....*...",
    "...*...*...*....",
    "*...*..*..*...*.",
    ".*...*.*.*...*..",
    "..*...***...*...",
    "*******o*******.",
    "..*...***...*...",
    ".*...*.*.*...*..",
    "*...*..*..*...*.",
    "...*...*...*....",
    "..*....*....*...",
    ".....*.*.*......",
    "......***.......",
]
frames = []
for i in range(12):
    f = blank((0, 20, 60))
    for y, row in enumerate(FLAKE):
        for x, ch in enumerate(row):
            if ch != '.':
                d = math.hypot(x - 7, y - 8)
                k = 0.5 + 0.5 * math.cos(d / 1.4 - i * math.pi / 3)
                put(f, x, y, (255, 255, 255) if ch == 'o' else mix((80, 160, 255), (255, 255, 255), k))
    if i % 3 == 0:
        rnd = random.Random(i)
        put(f, rnd.choice([1, 13, 14, 2]), rnd.choice([1, 14, 15, 2]), (220, 240, 255))
    frames.append(f)
save('xm-snowflake', 'Christmas', 'Snowflake', frames, 110)

# ---- Christmas: penguin ----
PENG = [
    "....KKKKK...",
    "...KKKKKKK..",
    "...KWKKKWK..",
    "...KWwKwWK..",
    "...KWWOWWK..",
    "...RRRRRRR..",
    "..KKRRWWWKK.",
    ".KKKWWWWWKKK",
    ".KK.WWWWW.KK",
    "..K.WWWWW.K.",
    "....WWWWW...",
    "....KWWWK...",
    "...OO...OO..",
]
frames = []
for i in range(16):
    f = blank((20, 40, 80))
    for k in range(6):
        x = (k * 5 + 3) % 16; y = (k * 7 + i) % 16
        put(f, x, y, (230, 240, 255))
    for x in range(16):
        put(f, x, 15, (240, 245, 255)); put(f, x, 14, (220, 230, 245) if x % 4 else (240, 245, 255))
    sway = [0, 0, 1, 1, 0, 0, -1, -1][i % 8]
    sprite(f, PENG, {'K': (10, 10, 20), 'W': (245, 245, 245), 'w': (0, 0, 0), 'O': (255, 150, 0), 'R': (220, 20, 30)}, 2 + sway, 2)
    frames.append(f)
save('xm-penguin', 'Christmas', 'Penguin', frames, 130)

# ---- Christmas: fireplace ----
frames = []
for i in range(14):
    f = blank()
    for y in range(16):
        for x in range(16):
            if x < 2 or x > 13 or y < 3:
                brick = (150, 50, 30) if ((y % 2 == 0) ^ (x % 4 == 0)) else (110, 35, 20)
                put(f, x, y, brick)
    for x in range(0, 16):
        put(f, x, 2, (230, 220, 200)); put(f, x, 1, (230, 220, 200))
    for x in (4, 11):
        put(f, x, 0, (220, 20, 30)); put(f, x + 1, 0, (220, 20, 30))
    rnd = random.Random(i * 7)
    for x in range(3, 13):
        h = 2 + rnd.randint(0, 6) - abs(x - 7.5) // 2
        for k in range(int(max(1, h))):
            y = 13 - k
            c = (255, 230, 120) if k < 1 else (255, 160, 20) if k < h * 0.6 else (230, 50, 0)
            put(f, x, y, c)
    for x in range(3, 13):
        put(f, x, 14, (90, 50, 20)); put(f, x, 15, (60, 30, 10))
    frames.append(f)
save('xm-fireplace', 'Christmas', 'Fireplace', frames, 100)

# ---- Christmas: HO HO HO ----
def snow_bg(f, i):
    for k in range(7):
        put(f, (k * 5 + 2) % 16, (k * 3 + i // 2) % 16, (60, 70, 90))


save('xm-hohoho', 'Christmas', 'HO HO HO', scroll_text(' HO HO HO', lambda x, y, i: (230, 20, 30) if ((x + i) // 4) % 2 else (255, 255, 255), (0, 25, 8), snow_bg), 70)


# ================= pack 3 (v3): 8 Halloween + 8 Christmas + 6 celebrations, with Portuguese text =================
F35 = {  # 3x5 capitals for the scrolling Portuguese messages
    'A': ["010", "101", "111", "101", "101"], 'B': ["110", "101", "110", "101", "110"], 'C': ["011", "100", "100", "100", "011"],
    'D': ["110", "101", "101", "101", "110"], 'E': ["111", "100", "110", "100", "111"], 'F': ["111", "100", "110", "100", "100"],
    'I': ["111", "010", "010", "010", "111"], 'L': ["100", "100", "100", "100", "111"], 'N': ["1001", "1101", "1011", "1001", "1001"],
    'O': ["010", "101", "101", "101", "010"], 'P': ["110", "101", "110", "100", "100"], 'R': ["110", "101", "110", "101", "101"],
    'S': ["011", "100", "010", "001", "110"], 'T': ["111", "010", "010", "010", "010"], 'U': ["101", "101", "101", "101", "111"],
    'V': ["101", "101", "101", "101", "010"], 'Z': ["111", "001", "010", "100", "111"], '!': ["1", "1", "1", "0", "1"],
    ' ': ["00", "00", "00", "00", "00"],
}


def wh(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1, 1, 1)
    return (int(r * 255), int(g * 255), int(b * 255))


def scroll35(s, colour_at, bg=(0, 0, 0), extra=None, y0=3, step=1):
    """a message moving right to left, letters 2x tall (10 rows) starting at row y0"""
    cols = []
    for ch in s:
        g = F35[ch]
        for x in range(len(g[0])):
            cols.append([g[y][x] == '1' for y in range(5)])
        cols.append([False] * 5)
    frames = []
    for i in range(0, len(cols) + W, step):
        f = blank(bg)
        if extra:
            extra(f, i)
        for x in range(W):
            cx = x + i - W
            if 0 <= cx < len(cols):
                for y in range(5):
                    if cols[cx][y]:
                        for dy in (0, 1):
                            put(f, x, y0 + y * 2 + dy, colour_at(x, y, i))
        frames.append(f)
    return frames


def rect(f, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(f, x, y, c)


def stars_bg(f, i, seed=1, n=10, base=(70, 70, 110)):
    rnd = random.Random(seed)
    for k in range(n):
        x, y, ph = rnd.randrange(16), rnd.randrange(16), rnd.random() * 6.28
        put(f, x, y, scale(base, 0.4 + 0.6 * (0.5 + 0.5 * math.sin(i * 0.6 + ph))))


# ---- Halloween: jack-o'-lantern whose face glows and flickers ----
JACK = [
    "................",
    ".......gg.......",
    "......gg........",
    "...OOOOOOOOOO...",
    "..OOOOOOOOOOOO..",
    ".OOOOOOOOOOOOOO.",
    ".OOYYOOOOOOYYOO.",
    "OOOYYYOOOOYYYOOO",
    "OOOOOOOYYOOOOOOO",
    "OOOOOOOYYOOOOOOO",
    "OOYOOOOOOOOOOYOO",
    "OOYYYOYYYYOYYYOO",
    ".OOYYYYYYYYYYOO.",
    ".OOOOOYYYYOOOOO.",
    "..OOOOOOOOOOOO..",
    "....OOOOOOOO....",
]
frames = []
for i in range(16):
    f = blank()
    k = 0.55 + 0.45 * random.Random(i * 13).random()
    sprite(f, JACK, {'O': (230, 100, 0), 'g': (40, 160, 40), 'Y': scale((255, 220, 60), k)})
    frames.append(f)
save('hw-jack', 'Halloween', 'Jack-o\'-lantern', frames, 110)

# ---- Halloween: Frankenstein's monster blinking ----
FRANK = [
    "..KKKKKKKKKKKK..",
    "..KKKKKKKKKKKK..",
    "..GGGGGGGGGGGG..",
    "..GGKKGGGGKKGG..",
    "..GGWBGGGGWBGG..",
    "..GGGGGGGGGGGG..",
    "SSGGGGGkkGGGGGSS",
    "SSGGGGGGGGGGGGSS",
    "..GGKKKKKKKKGG..",
    "..GGGGGGGGGGGG..",
    "..GGgGgGgGgGGG..",
    "..GGGGGGGGGGGG..",
    "...GGGGGGGGGG...",
    "....KKKKKKKK....",
    "...KKKKKKKKKK...",
    "..KKKKKKKKKKKK..",
]
frames = []
for i in range(20):
    f = blank()
    rows = [r[:] for r in FRANK]
    if i in (8, 9, 17):   # blink
        rows[4] = "..GGKKGGGGKKGG.."
    sprite(f, rows, {'K': (25, 25, 30), 'G': (90, 170, 70), 'W': (240, 240, 240), 'B': (20, 20, 20), 'S': (160, 160, 170),
                     'k': (60, 110, 45), 'g': (40, 40, 40)})
    if i % 10 == 4:   # spark on a bolt
        put(f, 0, 6, (255, 255, 120)); put(f, 15, 7, (255, 255, 120))
    frames.append(f)
save('hw-frank', 'Halloween', 'Monster', frames, 140)

# ---- Halloween: vampire with a swishing cape ----
VAMP = [
    "................",
    ".....KKKKKK.....",
    "....KKKKKKKK....",
    "....KWWKKWWK....",
    "....WWWWWWWW....",
    "....WRWWWWRW....",
    "....WWWWWWWW....",
    "....WWKKKKWW....",
    ".....WVWWVW.....",
    "......WWWW......",
]
frames = []
for i in range(16):
    f = blank((8, 0, 18))
    stars_bg(f, i, 5, 6)
    sw = int(round(1.5 * math.sin(i * 0.4)))
    for y in range(9, 16):
        half = 3 + (y - 9) + (sw if y > 11 else 0)
        for x in range(8 - half, 8 + half):
            inner = abs(x - 7.5) < (y - 8) * 0.6
            put(f, x, y, (170, 0, 20) if inner else (20, 20, 25))
    sprite(f, VAMP, {'K': (20, 20, 25), 'W': (225, 220, 210), 'R': (230, 0, 0), 'V': (255, 255, 255)})
    frames.append(f)
save('hw-vampire', 'Halloween', 'Vampire', frames, 110)

# ---- Halloween: spider web with dew drops sparkling ----
def line(f, x0, y0, x1, y1, c):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for k in range(n + 1):
        t = k / n
        put(f, int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), c)


frames = []
for i in range(18):
    f = blank()
    web = (85, 85, 105)
    pts = lambda r: [(7.5 + math.cos(a * math.pi / 4) * r, 7.5 + math.sin(a * math.pi / 4) * r) for a in range(8)]
    for (x, y) in pts(11):
        line(f, 7.5, 7.5, x, y, web)
    for r in (3.5, 7):
        p = pts(r)
        for k in range(8):
            line(f, p[k][0], p[k][1], p[(k + 1) % 8][0], p[(k + 1) % 8][1], web)
    for k, (x, y) in enumerate(pts(7)[::2] + pts(3.5)[1::2]):
        put(f, int(round(x)), int(round(y)), scale((190, 230, 255), 0.35 + 0.65 * max(0, math.sin(i * 0.5 + k * 1.7))))
    sy = 6 + int(round(3 * math.sin(i * 0.35)))   # the spider goes up and down its thread
    line(f, 11, 0, 11, sy - 1, (150, 150, 160))
    rect(f, 10, sy, 12, sy + 2, (190, 60, 0)); put(f, 11, sy + 3, (190, 60, 0))
    put(f, 10, sy, (255, 230, 0)); put(f, 12, sy, (255, 230, 0))
    for d in (0, 2):
        put(f, 9, sy + d, (150, 40, 0)); put(f, 13, sy + d, (150, 40, 0))
    frames.append(f)
save('hw-web', 'Halloween', 'Spider web', frames, 110)

# ---- Halloween: crow flapping on a branch ----
CROW_UP = ["..KK....", ".KKKK...", "KKKKKK.."]
CROW_DN = ["........", "KKKKKK..", ".KKKK..."]
frames = []
for i in range(12):
    f = blank((10, 5, 25))
    disc(f, 12, 3, 2.6, (230, 230, 190))
    for x in range(0, 16):
        put(f, x, 13 + (1 if x > 11 else 0), (80, 45, 20))
    put(f, 3, 12, (80, 45, 20)); put(f, 2, 11, (80, 45, 20))
    # body
    rect(f, 6, 9, 9, 12, (20, 20, 28)); rect(f, 9, 8, 10, 9, (20, 20, 28))
    put(f, 11, 9, (240, 180, 0)); put(f, 10, 8, (255, 255, 255))
    put(f, 5, 11, (20, 20, 28)); put(f, 4, 12, (20, 20, 28))
    wing = CROW_UP if (i // 2) % 3 else CROW_DN
    sprite(f, wing, {'K': (45, 45, 60)}, 4, 6)
    put(f, 7, 13, (240, 180, 0)); put(f, 9, 13, (240, 180, 0))
    frames.append(f)
save('hw-crow', 'Halloween', 'Crow', frames, 130)

# ---- Halloween: coffin opening, two eyes inside ----
frames = []
for i in range(20):
    f = blank()
    op = min(1, max(0, (i - 4) / 6)) if i < 15 else max(0, 1 - (i - 15) / 3)
    shape = lambda y: 2 + (y if y < 4 else 4 - (y - 4) // 3)
    for y in range(1, 16):
        w = shape(y - 1)
        for x in range(8 - w, 8 + w):
            put(f, x, y, (25, 10, 5))
    if op > 0.2:
        put(f, 6, 6, scale((255, 40, 0), op)); put(f, 9, 6, scale((255, 40, 0), op))
    lid = int(round(op * 8))
    for y in range(1, 16):
        w = shape(y - 1)
        for x in range(8 - w, 8 + w):
            xx = x + lid
            put(f, xx, y, (110, 60, 25) if (x + y) % 7 else (90, 45, 18))
    for y in (5, 6, 7):
        put(f, 7 + lid, y, (210, 200, 180)); put(f, 8 + lid, y, (210, 200, 180))
    put(f, 6 + lid, 6, (210, 200, 180)); put(f, 9 + lid, 6, (210, 200, 180))
    frames.append(f)
save('hw-coffin', 'Halloween', 'Coffin', frames, 120)

# ---- Halloween: zombie rising from the ground ----
ZOMB = [
    ".GGGG.",
    "GRGGRG",
    "GGGGGG",
    "GKKKKG",
    ".GGGG.",
    "..BB..",
    "BBBBBB",
    "GBBBBG",
    "GBBBBG",
    ".BBBB.",
]
frames = []
for i in range(24):
    f = blank((5, 5, 20))
    stars_bg(f, i, 9, 7)
    rise = min(10, i) if i < 18 else 10 - (i - 18) * 2
    y0 = 15 - rise
    sprite(f, ZOMB, {'G': (110, 160, 80), 'R': (230, 30, 30), 'K': (30, 30, 30), 'B': (70, 60, 120)}, 5, y0)
    if i % 4 < 2 and rise >= 8:
        put(f, 4, y0 + 6, (110, 160, 80)); put(f, 11, y0 + 6, (110, 160, 80))
    for x in range(16):
        put(f, x, 14, (60, 35, 15)); put(f, x, 15, (45, 25, 10))
    put(f, 1, 12, (120, 120, 130)); rect(f, 0, 10, 2, 13, (120, 120, 130)); put(f, 1, 11, (60, 60, 70))
    frames.append(f)
save('hw-zombie', 'Halloween', 'Zombie', frames, 120)

# ---- Halloween: "DOCES OU TRAVESSURAS" ----
save('hw-doces', 'Halloween', 'Doces ou travessuras', scroll35(' DOCES OU TRAVESSURAS! ',
     lambda x, y, i: (255, 120, 0) if ((x + i) // 3) % 2 else (170, 60, 255), (8, 0, 14),
     lambda f, i: [put(f, (k * 5 + i // 2) % 16, 14 + k % 2, (40, 30, 60)) for k in range(4)]), 60)

# ---- Christmas: angel with glowing halo and flapping wings ----
ANGEL = [
    "......YYYY......",
    ".....Y....Y.....",
    "......YYYY......",
    "......SSSS......",
    "......SBSB......",
    "......SSSS......",
    ".......SS.......",
    "......WWWW......",
    ".....WWWWWW.....",
    ".....WWWWWW.....",
    "....WWWWWWWW....",
    "....WWWWWWWW....",
    "...WWWWWWWWWW...",
    "...WWWWWWWWWW...",
    "....YYYYYYYY....",
]
frames = []
for i in range(14):
    f = blank((0, 6, 24))
    stars_bg(f, i, 11, 8, (120, 120, 80))
    up = (i // 2) % 2
    for y in range(7, 13):
        for d in range(1, 4 - (y - 7) // 2):
            put(f, 5 - d, y - up, (200, 220, 255)); put(f, 10 + d, y - up, (200, 220, 255))
    k = 0.6 + 0.4 * math.sin(i * 0.45)
    sprite(f, ANGEL, {'Y': scale((255, 220, 80), k), 'S': (245, 200, 160), 'B': (40, 40, 80), 'W': (245, 245, 255)}, 0, 1)
    frames.append(f)
save('xm-angel', 'Christmas', 'Angel', frames, 120)

# ---- Christmas: hot chocolate with steam ----
frames = []
for i in range(16):
    f = blank((20, 10, 5))
    rect(f, 3, 8, 11, 14, (200, 30, 40))
    for x in range(3, 12):
        put(f, x, 10 + (x % 2), (255, 255, 255))   # white zig-zag
    rect(f, 4, 8, 10, 8, (90, 45, 20))
    for y in (9, 10, 11, 12):
        put(f, 12, y, (200, 30, 40)); put(f, 13, y, (200, 30, 40) if y in (9, 12) else None)
    put(f, 13, 10, (200, 30, 40)); put(f, 14, 10, (200, 30, 40)); put(f, 14, 11, (200, 30, 40)); put(f, 13, 11, (200, 30, 40))
    put(f, 13, 10, None)
    rect(f, 2, 15, 12, 15, (150, 150, 160))
    put(f, 6, 7, (245, 240, 230)); put(f, 8, 7, (245, 240, 230))   # marshmallows
    for s in range(3):
        for k in range(5):
            y = 6 - k - ((i + s * 5) % 16) // 4
            x = 5 + s * 2 + int(round(math.sin((i + k) * 0.7 + s)))
            if 0 <= y < 7:
                put(f, x, y, scale((200, 200, 210), 0.3 + 0.12 * (5 - k)))
    frames.append(f)
save('xm-cocoa', 'Christmas', 'Hot chocolate', frames, 120)

# ---- Christmas: toy train crossing ----
frames = []
for i in range(32):
    f = blank((0, 10, 30))
    for k in range(6):
        put(f, (k * 7 + 3) % 16, (k * 5 + i // 3) % 11, (180, 190, 210))
    for x in range(16):
        put(f, x, 14, (90, 60, 40))
        if x % 2 == 0:
            put(f, x, 15, (60, 40, 25))
    ox = 18 - i
    def car(x0, c):
        rect(f, x0, 9, x0 + 4, 12, c)
        put(f, x0 + 1, 13, (40, 40, 40)); put(f, x0 + 3, 13, (40, 40, 40))
    # engine
    rect(f, ox, 8, ox + 4, 12, (30, 120, 40)); rect(f, ox + 3, 6, ox + 4, 7, (30, 120, 40))
    rect(f, ox, 6, ox + 1, 8, (220, 180, 30)); put(f, ox - 1, 12, (200, 30, 30))
    put(f, ox + 1, 13, (40, 40, 40)); put(f, ox + 3, 13, (40, 40, 40))
    put(f, ox + 3, 5 - (i % 2), (200, 200, 210)); put(f, ox + 4, 4 - (i % 2), (150, 150, 160))
    car(ox + 6, (200, 30, 40)); put(f, ox + 8, 8, (255, 220, 40))
    car(ox + 12, (40, 90, 220)); put(f, ox + 14, 8, (40, 200, 60))
    frames.append(f)
save('xm-train', 'Christmas', 'Toy train', frames, 80)

# ---- Christmas: polar bear waving ----
BEAR = [
    "..WW......WW..",
    ".WWWWWWWWWWWW.",
    ".WWWWWWWWWWWW.",
    ".WWKWWWWWWKWW.",
    ".WWWWWKKWWWWW.",
    "..WWWWKKWWWW..",
    "..WWWWWWWWWW..",
    ".RRRRRRRRRRRR.",
    "WWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWW",
    ".WWWWWWWWWWWW.",
    ".WWWW....WWWW.",
]
frames = []
for i in range(14):
    f = blank((10, 30, 60))
    for k in range(6):
        put(f, (k * 5 + 1) % 16, (k * 3 + i) % 16, (200, 220, 240))
    sprite(f, BEAR, {'W': (240, 245, 250), 'K': (20, 20, 30), 'R': (210, 30, 40)}, 1, 4)
    wave = (i // 2) % 2
    put(f, 15, 11 - wave * 2, (240, 245, 250)); put(f, 15, 12 - wave * 2, (240, 245, 250)); put(f, 14, 12, (240, 245, 250))
    frames.append(f)
save('xm-polarbear', 'Christmas', 'Polar bear', frames, 140)

# ---- Christmas: snow globe being shaken ----
frames = []
for i in range(24):
    f = blank()
    disc(f, 7.5, 7, 6.6, (20, 50, 110))
    for y in range(4, 12):   # a little Christmas tree
        w = 1 + (y - 4) // 2
        for x in range(8 - w, 8 + w):
            put(f, x, y, (30, 140, 50))
    put(f, 7, 3, (255, 220, 40)); put(f, 8, 3, (255, 220, 40)); put(f, 6, 8, (230, 30, 30)); put(f, 9, 10, (60, 160, 255))
    rect(f, 7, 12, 8, 12, (110, 60, 20))
    for x in range(3, 13):
        put(f, x, 13, (230, 235, 245))
    rect(f, 3, 14, 12, 15, (150, 80, 30))
    rnd = random.Random(31)
    shake = i < 6
    for k in range(14):
        x0, y0 = rnd.random() * 12 + 2, rnd.random() * 12 + 1
        y = (y0 + (i * 0.4 if not shake else rnd.random() * 10)) % 12 + 1
        x = x0 + math.sin(i * 0.5 + k) * (2 if shake else 0.7)
        xi, yi = int(round(x)), int(round(y))
        if (xi - 7.5) ** 2 + (yi - 7) ** 2 <= 36 and yi < 13:
            put(f, xi, yi, (255, 255, 255))
    frames.append(f)
save('xm-globe', 'Christmas', 'Snow globe', frames, 100)

# ---- Christmas: shooting star over the stable ----
frames = []
for i in range(20):
    f = blank((0, 0, 20))
    stars_bg(f, i, 21, 10, (90, 90, 130))
    sx, sy = 14 - i * 0.6, 1 + i * 0.25
    for k in range(5):
        put(f, int(round(sx + k)), int(round(sy - k * 0.4)), scale((255, 230, 140), 1 - k / 5))
    # stable
    for y in range(9, 16):
        w = min(7, y - 6)
        for x in range(8 - w, 8 + w):
            put(f, x, y, (100, 55, 20) if y < 11 else (70, 40, 15))
    rect(f, 6, 12, 9, 15, (25, 15, 5))
    put(f, 7, 13, (255, 200, 80)); put(f, 8, 13, (255, 200, 80))
    big = 0.6 + 0.4 * math.sin(i * 0.6)
    for d in ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)):
        put(f, 8 + d[0], 5 + d[1], scale((255, 240, 160), big if d != (0, 0) else 1))
    frames.append(f)
save('xm-shootingstar', 'Christmas', 'Star of Bethlehem', frames, 110)

# ---- Christmas: "FELIZ NATAL" and "BOAS FESTAS" ----
xmbg = lambda f, i: [put(f, (k * 5 + 2) % 16, (k * 3 + i // 2) % 16, (55, 65, 90)) for k in range(7)]
save('xm-feliznatal', 'Christmas', 'Feliz Natal', scroll35(' FELIZ NATAL! ', lambda x, y, i: (230, 20, 30) if ((x + i) // 3) % 2 else (40, 200, 60), (0, 0, 0), xmbg), 65)
save('xm-boasfestas', 'Christmas', 'Boas festas', scroll35(' BOAS FESTAS! ', lambda x, y, i: (255, 210, 60) if y < 3 else (255, 255, 255), (0, 15, 40), xmbg), 65)

# ---- Celebrations: "PARABENS" with confetti ----
def confetti_bg(f, i):
    rnd = random.Random(2)
    for k in range(10):
        x0, sp, c = rnd.randrange(16), 1 + rnd.random(), rnd.choice([(255, 60, 60), (60, 200, 255), (255, 220, 40), (120, 255, 90), (255, 90, 220)])
        put(f, x0, int(i * sp + k * 3) % 16, scale(c, 0.5))
save('ev-parabens', 'Celebrations', 'Parabéns', scroll35(' PARABENS! ', lambda x, y, i: wh((x + i) / 16.0), (0, 0, 0), confetti_bg), 65)

# ---- Celebrations: cupcake with a flickering candle ----
frames = []
for i in range(14):
    f = blank((15, 0, 20))
    for y in range(10, 16):
        w = 5 - (y - 10) // 3
        for x in range(8 - w, 8 + w):
            put(f, x, y, (230, 150, 60) if x % 2 else (200, 120, 40))
    for y in range(6, 10):
        w = 6 - abs(y - 8)
        for x in range(8 - w, 8 + w):
            put(f, x, y, (255, 150, 200))
    for k, (x, y) in enumerate(((4, 8), (7, 7), (10, 8), (6, 9), (9, 9), (12, 9))):
        put(f, x, y, [(255, 50, 50), (60, 200, 255), (255, 230, 40), (120, 255, 90)][k % 4])
    rect(f, 7, 3, 8, 5, (90, 170, 255))
    flame(f, 7, -1, i, 9)
    frames.append(f)
save('ev-cupcake', 'Celebrations', 'Cupcake', frames, 100)

# ---- Celebrations: flower blooming ----
frames = []
for i in range(20):
    f = blank((0, 10, 25))
    rect(f, 7, 9, 8, 15, (40, 150, 50))
    put(f, 5, 12, (50, 180, 60)); put(f, 6, 12, (50, 180, 60)); put(f, 9, 11, (50, 180, 60)); put(f, 10, 11, (50, 180, 60))
    op = min(1, i / 10)
    r = 1 + op * 3.5
    disc(f, 7.5, 5.5, r * 0.75, (255, 110, 175))
    for a in range(5):
        ang = a * 2 * math.pi / 5 + i * 0.05
        disc(f, 7.5 + math.cos(ang) * r * 0.9, 5.5 + math.sin(ang) * r * 0.9, max(1, r * 0.55), (255, 90, 160) if a % 2 else (255, 130, 190))
    disc(f, 7.5, 5.5, 1.3, (255, 210, 40))
    frames.append(f)
frames += [frames[-1]] * 6
save('ev-flower', 'Celebrations', 'Flower', frames, 110)

# ---- Celebrations: butterfly ----
frames = []
for i in range(12):
    f = blank((0, 20, 35))
    open_ = 0.3 + 0.7 * abs(math.cos(i * math.pi / 6))
    span = 2 + int(round(open_ * 4))
    for y in range(3, 13):
        top = y < 8
        for d in range(1, span + 1):
            if (top and abs(y - 5) <= d * 0.6 + 1) or (not top and abs(y - 10) <= d * 0.5 + 0.5):
                c = (255, 140, 0) if top else (255, 70, 160)
                if d == span or (d + y) % 5 == 0:
                    c = (40, 20, 60)
                put(f, 7 - d + 1, y, c); put(f, 8 + d - 1, y, c)
    rect(f, 7, 3, 8, 12, (40, 25, 20))
    put(f, 6, 1, (40, 25, 20)); put(f, 9, 1, (40, 25, 20)); put(f, 7, 2, (40, 25, 20)); put(f, 8, 2, (40, 25, 20))
    frames.append(f)
save('ev-butterfly', 'Celebrations', 'Butterfly', frames, 90)

# ---- Celebrations: rocket ----
frames = []
for i in range(24):
    f = blank((0, 0, 18))
    stars_bg(f, i, 41, 12, (120, 120, 160))
    for k in range(12):
        x, y = (k * 9 + 3) % 16, (k * 5 + i) % 16
        put(f, x, y, (60, 60, 90))
    y0 = 3 + int(round(math.sin(i * 0.5)))
    rect(f, 6, y0 + 2, 9, y0 + 8, (230, 230, 240))
    put(f, 7, y0, (220, 40, 40)); put(f, 8, y0, (220, 40, 40)); rect(f, 6, y0 + 1, 9, y0 + 1, (220, 40, 40))
    put(f, 7, y0 + 4, (60, 160, 255)); put(f, 8, y0 + 4, (60, 160, 255))
    rect(f, 4, y0 + 7, 5, y0 + 9, (220, 40, 40)); rect(f, 10, y0 + 7, 11, y0 + 9, (220, 40, 40))
    for k in range(4):
        c = [(255, 255, 160), (255, 200, 40), (255, 110, 0), (200, 30, 0)][k]
        w = 2 if k < 2 else 1 + (i + k) % 2
        for x in range(8 - w, 8 + w):
            put(f, x, y0 + 9 + k, c if random.Random(i * 5 + k + x).random() > 0.2 else None)
    frames.append(f)
save('ev-rocket', 'Celebrations', 'Rocket', frames, 80)

# ---- Celebrations: disco ball ----
frames = []
for i in range(16):
    f = blank()
    rect(f, 7, 0, 8, 2, (130, 130, 140))
    for y in range(3, 15):
        for x in range(16):
            dx, dy = x - 7.5, y - 8.5
            if dx * dx + dy * dy <= 30:
                tile = ((x + i) // 2 + y // 2) % 4
                c = [(90, 90, 110), (170, 170, 190), (230, 230, 255), (130, 130, 150)][tile]
                if random.Random(x * 31 + y * 7 + i).random() > 0.93:
                    c = wh((x + y + i) / 12.0)
                put(f, x, y, c)
    for k in range(4):   # light spots on the floor and walls
        ang = i * 0.4 + k * 1.57
        x, y = int(round(7.5 + math.cos(ang) * 7)), int(round(8.5 + math.sin(ang) * 7))
        if not (0 <= (x - 7.5) ** 2 + (y - 8.5) ** 2 <= 30):
            put(f, x, y, wh(k / 4))
    frames.append(f)
save('ev-disco', 'Celebrations', 'Disco ball', frames, 90)

with open(os.path.join(OUT, 'pack.json'), 'w') as fp:
    json.dump(PACK, fp, separators=(',', ':'))
print(len(PACK), 'gifs')
