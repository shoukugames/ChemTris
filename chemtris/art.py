"""Everything drawn in code: atoms, ball-and-stick diagrams, picture cards and text helpers."""
import math
import random

import pygame

from .config import (ELEMENT_COLORS, ELEMENT_TEXT, PANEL, PANEL_EDGE, RUBBLE, TEXT, BG_TOP, BG_BOTTOM,
                     WIDTH, HEIGHT)
from .i18n import font

_cache = {}


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def clamp_color(c):
    return tuple(max(0, min(255, int(v))) for v in c)


# ----- text -----
def text(surf, s, size, color, pos, anchor="topleft", shadow=True, outline=None):
    f = font(size)
    img = f.render(s, True, color)
    rect = img.get_rect(**{anchor: pos})
    if outline:
        o = f.render(s, True, outline)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            surf.blit(o, rect.move(dx, dy))
    elif shadow:
        sh = f.render(s, True, (0, 0, 0))
        sh.set_alpha(110)
        surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def wrap(s, size, width):
    """Split text into lines that fit `width`. Handles Japanese (no spaces) too."""
    f = font(size)
    lines = []
    for para in s.split("\n"):
        line = ""
        tokens = para.split(" ") if " " in para else list(para)
        joiner = " " if " " in para else ""
        for tok in tokens:
            trial = tok if not line else line + joiner + tok
            if f.size(trial)[0] <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = tok
        lines.append(line)
    return lines


def text_block(surf, s, size, color, pos, width, line_gap=4, anchor="topleft"):
    x, y = pos
    for line in wrap(s, size, width):
        if anchor == "center":
            text(surf, line, size, color, (x, y), "midtop")
        else:
            text(surf, line, size, color, (x, y))
        y += font(size).get_linesize() + line_gap
    return y


def formula_surface(parts, size, color=TEXT):
    """A formula like H₂O with real subscripts, from [(element, count)]."""
    big, small = font(size), font(int(size * 0.62))
    pieces = []
    for el, n in parts:
        pieces.append((big.render(el, True, color), 0))
        if n > 1:
            pieces.append((small.render(str(n), True, color), int(size * 0.45)))
    w = sum(p.get_width() for p, _ in pieces) + 2
    h = big.get_height() + int(size * 0.25)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    x = 0
    for img, dy in pieces:
        out.blit(img, (x, dy))
        x += img.get_width()
    return out


def parse_formula(s):
    """'H3O' -> [('H', 3), ('O', 1)]"""
    parts, i = [], 0
    while i < len(s):
        el = s[i]
        i += 1
        if i < len(s) and s[i].islower():
            el += s[i]
            i += 1
        num = ""
        while i < len(s) and s[i].isdigit():
            num += s[i]
            i += 1
        parts.append((el, int(num or 1)))
    return parts


# ----- panels and background -----
def panel(surf, rect, color=PANEL, edge=PANEL_EDGE, radius=18, alpha=225):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    sheen = min(rect.h, 90)
    shine = pygame.Surface((rect.w - 6, sheen), pygame.SRCALPHA)
    for y in range(radius // 2, sheen):
        pygame.draw.line(shine, (255, 255, 255, int(18 * (1 - y / sheen))), (0, y), (rect.w - 7, y))
    s.blit(shine, (3, 0))
    pygame.draw.rect(s, (*edge, 200), s.get_rect(), 2, border_radius=radius)
    surf.blit(s, rect)


def gradient(size, top, bottom):
    w, h = size
    s = pygame.Surface((1, h))
    for y in range(h):
        s.set_at((0, y), mix(top, bottom, y / max(1, h - 1)))
    return pygame.transform.scale(s, (w, h))


class Background:
    """A deep blue lab with drifting hexagon rings and rising bubbles."""

    def __init__(self, seed=3):
        rng = random.Random(seed)
        self.base = gradient((WIDTH, HEIGHT), BG_TOP, BG_BOTTOM)
        self.hexes = [[rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT), rng.uniform(26, 70),
                       rng.uniform(-8, 8), rng.uniform(-6, 6), rng.uniform(0, 6.28), rng.uniform(-0.2, 0.2)]
                      for _ in range(14)]
        self.bubbles = [[rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT), rng.uniform(2, 7), rng.uniform(15, 45)]
                        for _ in range(40)]
        self.layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def update(self, dt):
        for h in self.hexes:
            h[0] = (h[0] + h[3] * dt) % (WIDTH + 160)
            h[1] = (h[1] + h[4] * dt) % (HEIGHT + 160)
            h[5] += h[6] * dt
        for b in self.bubbles:
            b[1] -= b[3] * dt
            if b[1] < -10:
                b[1] = HEIGHT + 10

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        for x, y, r, _, _, a, _ in self.hexes:
            pts = [(x - 80 + r * math.cos(a + i * math.pi / 3), y - 80 + r * math.sin(a + i * math.pi / 3))
                   for i in range(6)]
            pygame.draw.polygon(layer, (90, 140, 255, 26), pts, 3)
            for p in pts:
                pygame.draw.circle(layer, (120, 170, 255, 30), p, 5)
        for x, y, r, _ in self.bubbles:
            pygame.draw.circle(layer, (140, 200, 255, 40), (x, y), r, 1)
        surf.blit(layer, (0, 0))


# ----- atoms -----
def sphere(radius, color):
    """A shiny ball with a highlight, drawn once and cached."""
    key = ("sphere", radius, color)
    if key in _cache:
        return _cache[key]
    scale = 3
    R = radius * scale
    s = pygame.Surface((R * 2 + 2, R * 2 + 2), pygame.SRCALPHA)
    c = (R + 1, R + 1)
    dark = clamp_color([v * 0.45 for v in color])
    light = clamp_color([v + (255 - v) * 0.55 for v in color])
    steps = 28
    for i in range(steps):
        t = i / (steps - 1)
        r = R * (1 - t * 0.92)
        off = R * 0.32 * t
        col = mix(dark, color, min(1, t * 1.6)) if t < 0.6 else mix(color, light, (t - 0.6) / 0.4)
        pygame.draw.circle(s, col, (c[0] - off, c[1] - off), max(1, r))
    hl = pygame.Surface((R, R // 2 + 2), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (255, 255, 255, 120), hl.get_rect())
    s.blit(hl, (c[0] - R * 0.75, c[1] - R * 0.78))
    out = pygame.transform.smoothscale(s, (radius * 2, radius * 2))
    _cache[key] = out
    return out


def atom(element, size):
    """An atom ball with its symbol, `size` pixels across."""
    key = ("atom", element, size)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 2
    shadow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (0, 0, 0, 90), (r + 2, r + 3), r - 2)
    s.blit(shadow, (0, 0))
    s.blit(sphere(r - 2, ELEMENT_COLORS[element]), (2, 2))
    color = ELEMENT_TEXT.get(element, (255, 255, 255))
    fs = int(size * (0.46 if len(element) == 1 else 0.38))
    img = font(fs).render(element, True, color)
    s.blit(img, img.get_rect(center=(r + 1, r + 1)))
    _cache[key] = s
    return s


def rubble(size):
    key = ("rubble", size)
    if key in _cache:
        return _cache[key]
    rng = random.Random(size)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = s.get_rect().inflate(-4, -4)
    pygame.draw.rect(s, RUBBLE, rect, border_radius=6)
    pygame.draw.rect(s, (130, 130, 140), rect.inflate(-8, -8).move(-2, -2), border_radius=5)
    pygame.draw.rect(s, (110, 110, 120), rect.inflate(-10, -10), border_radius=4)
    for _ in range(3):
        x = rng.randint(rect.left + 4, rect.right - 4)
        y = rng.randint(rect.top + 4, rect.bottom - 4)
        pts = [(x, y)]
        for _ in range(3):
            x += rng.randint(-8, 8)
            y += rng.randint(-8, 8)
            pts.append((max(rect.left, min(rect.right, x)), max(rect.top, min(rect.bottom, y))))
        pygame.draw.lines(s, (60, 60, 68), False, pts, 2)
    pygame.draw.rect(s, (60, 60, 68), rect, 2, border_radius=6)
    _cache[key] = s
    return s


def bond_rod(surf, p1, p2, order=1, width=8, color=(200, 206, 222)):
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    if order == 0:  # ionic: dashed
        n = int(length // 12)
        for i in range(0, n, 2):
            a, b = i / n, min(1, (i + 1) / n)
            pygame.draw.line(surf, (255, 230, 120), (x1 + dx * a, y1 + dy * a), (x1 + dx * b, y1 + dy * b), 4)
        return
    gap = width * 1.1
    offsets = [0] if order == 1 else ([-gap / 2, gap / 2] if order == 2 else [-gap, 0, gap])
    w = width if order == 1 else max(3, int(width * 0.7))
    for o in offsets:
        a = (x1 + nx * o, y1 + ny * o)
        b = (x2 + nx * o, y2 + ny * o)
        pygame.draw.line(surf, mix(color, (0, 0, 0), 0.5), a, b, w + 2)
        pygame.draw.line(surf, color, a, b, w)
        pygame.draw.line(surf, (255, 255, 255), a, b, max(1, w // 3))


ATOM_SCALE = {"H": 0.72, "O": 1.0, "C": 1.0, "N": 1.0, "Na": 1.15, "Cl": 1.12, "S": 1.12}


def structure(mol, size, max_unit=110):
    """Ball-and-stick diagram of a molecule, fitted into `size`."""
    key = ("structure", mol.id, size, max_unit)
    if key in _cache:
        return _cache[key]
    w, h = size
    s = pygame.Surface(size, pygame.SRCALPHA)
    xs = [a[1] for a in mol.atoms]
    ys = [a[2] for a in mol.atoms]
    span_x = max(xs) - min(xs) + 1.4
    span_y = max(ys) - min(ys) + 1.4
    unit = min(w / span_x, h / span_y, max_unit)
    cx = w / 2 - (max(xs) + min(xs)) / 2 * unit
    cy = h / 2 - (max(ys) + min(ys)) / 2 * unit
    pos = [(cx + x * unit, cy + y * unit) for _, x, y in mol.atoms]
    for i, j, order in mol.bonds:
        bond_rod(s, pos[i], pos[j], order, width=max(5, int(unit * 0.1)))
    for (el, _, _), p in zip(mol.atoms, pos):
        d = int(unit * 0.62 * ATOM_SCALE[el])
        img = atom(el, d)
        s.blit(img, img.get_rect(center=p))
    _cache[key] = s
    return s


# ----- picture cards: an everyday object for every molecule -----
def picture(mol_id, size):
    key = ("picture", mol_id, size)
    if key in _cache:
        return _cache[key]
    big = pygame.Surface((400, 320), pygame.SRCALPHA)
    PICTURES[mol_id](big)
    out = pygame.transform.smoothscale(big, size)
    _cache[key] = out
    return out


def _sky(s, top=(120, 190, 255), bottom=(200, 235, 255)):
    g = gradient((400, 320), top, bottom)
    mask = pygame.Surface((400, 320), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=28)
    g = g.convert_alpha() if pygame.display.get_surface() else g
    g.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(g, (0, 0))


def _bubbles(s, rng, area, n, color=(255, 255, 255)):
    x0, y0, x1, y1 = area
    for _ in range(n):
        r = rng.randint(4, 12)
        p = (rng.randint(x0, x1), rng.randint(y0, y1))
        pygame.draw.circle(s, color, p, r, 2)
        pygame.draw.circle(s, color, (p[0] - r // 3, p[1] - r // 3), max(1, r // 4))


def pic_rocket(s):
    _sky(s, (20, 30, 80), (70, 60, 140))
    rng = random.Random(1)
    for _ in range(40):
        pygame.draw.circle(s, (255, 255, 255), (rng.randint(10, 390), rng.randint(10, 310)), rng.choice((1, 1, 2)))
    pygame.draw.polygon(s, (255, 150, 40), [(170, 230), (230, 230), (200, 312)])
    pygame.draw.polygon(s, (255, 230, 90), [(182, 230), (218, 230), (200, 290)])
    pygame.draw.polygon(s, (220, 40, 50), [(160, 180), (140, 240), (175, 220)])
    pygame.draw.polygon(s, (220, 40, 50), [(240, 180), (260, 240), (225, 220)])
    pygame.draw.ellipse(s, (235, 238, 245), (165, 40, 70, 200))
    pygame.draw.polygon(s, (220, 40, 50), [(200, 22), (172, 80), (228, 80)])
    pygame.draw.ellipse(s, (235, 238, 245), (167, 60, 66, 60))
    pygame.draw.circle(s, (60, 140, 230), (200, 130), 18)
    pygame.draw.circle(s, (180, 220, 255), (194, 124), 6)
    pygame.draw.circle(s, (120, 130, 150), (200, 130), 18, 4)
    pygame.draw.rect(s, (200, 50, 60), (178, 222, 44, 14), border_radius=4)


def pic_tree(s):
    _sky(s)
    pygame.draw.rect(s, (90, 200, 90), (0, 260, 400, 60), border_bottom_left_radius=28, border_bottom_right_radius=28)
    pygame.draw.rect(s, (120, 80, 40), (180, 160, 40, 110), border_radius=8)
    for x, y, r in ((200, 110, 70), (140, 140, 50), (260, 140, 50), (170, 80, 45), (235, 80, 45), (200, 150, 55)):
        pygame.draw.circle(s, (40, 150, 60), (x, y), r)
    for x, y, r in ((185, 90, 20), (150, 125, 14), (245, 110, 16)):
        pygame.draw.circle(s, (90, 200, 100), (x, y), r)
    rng = random.Random(2)
    for _ in range(9):
        x, y = rng.randint(290, 380), rng.randint(30, 200)
        pygame.draw.circle(s, (255, 255, 255), (x, y), rng.randint(8, 16), 3)
        pygame.draw.circle(s, (255, 255, 255), (x - 4, y - 4), 3)


def pic_water(s):
    _sky(s, (200, 230, 255), (240, 248, 255))
    glass = [(120, 60), (280, 60), (260, 290), (140, 290)]
    pygame.draw.polygon(s, (60, 150, 240), [(127, 120), (273, 120), (260, 290), (140, 290)])
    pygame.draw.ellipse(s, (120, 190, 255), (127, 108, 146, 26))
    pygame.draw.polygon(s, (255, 255, 255), [(140, 80), (152, 80), (160, 270), (150, 270)])
    pygame.draw.polygon(s, (90, 110, 140), glass, 6)
    pygame.draw.circle(s, (60, 150, 240), (325, 120), 26)
    pygame.draw.polygon(s, (60, 150, 240), [(302, 108), (348, 108), (325, 60)])
    pygame.draw.circle(s, (200, 230, 255), (316, 112), 7)
    _bubbles(s, random.Random(3), (150, 150, 250, 270), 6)


def pic_salt(s):
    _sky(s, (255, 240, 220), (250, 220, 190))
    pygame.draw.rect(s, (160, 110, 70), (0, 270, 400, 50), border_bottom_left_radius=28, border_bottom_right_radius=28)
    pygame.draw.rect(s, (235, 240, 250), (140, 100, 120, 180), border_radius=26)
    pygame.draw.rect(s, (255, 255, 255), (155, 112, 22, 150), border_radius=10)
    pygame.draw.rect(s, (190, 196, 210), (140, 100, 120, 180), 4, border_radius=26)
    pygame.draw.rect(s, (180, 186, 200), (132, 60, 136, 56), border_radius=22)
    pygame.draw.rect(s, (215, 220, 232), (140, 64, 120, 20), border_radius=10)
    for x in (170, 200, 230):
        for y in (78, 98):
            pygame.draw.circle(s, (90, 96, 110), (x, y), 5)
    rng = random.Random(4)
    for _ in range(30):
        x, y = rng.randint(80, 320), rng.randint(274, 300)
        pygame.draw.rect(s, (255, 255, 255), (x, y, 5, 5))


def pic_stomach(s):
    _sky(s, (255, 230, 235), (255, 210, 220))
    pygame.draw.line(s, (230, 120, 140), (170, 20), (190, 90), 26)
    body = [(185, 80), (230, 70), (280, 100), (300, 160), (280, 230), (220, 270), (150, 280),
            (100, 260), (90, 220), (130, 210), (180, 200), (200, 160), (180, 120)]
    pygame.draw.polygon(s, (240, 120, 150), body)
    pygame.draw.polygon(s, (190, 70, 100), body, 6)
    pygame.draw.line(s, (230, 120, 140), (110, 250), (70, 300), 26)
    pygame.draw.polygon(s, (190, 240, 80), [(140, 250), (180, 225), (240, 215), (270, 200), (260, 240),
                                            (210, 262), (150, 268)])
    _bubbles(s, random.Random(5), (160, 215, 260, 255), 7, (250, 255, 200))
    pygame.draw.circle(s, (255, 255, 255), (300, 70), 26)
    pygame.draw.polygon(s, (255, 210, 0), [(300, 50), (320, 85), (280, 85)])
    pygame.draw.line(s, (40, 40, 40), (300, 60), (300, 74), 4)
    pygame.draw.circle(s, (40, 40, 40), (300, 80), 2)


def pic_soda(s):
    _sky(s, (255, 220, 200), (255, 245, 230))
    pygame.draw.rect(s, (120, 60, 40), (150, 110, 100, 190), border_radius=24)
    pygame.draw.rect(s, (120, 60, 40), (178, 50, 44, 80), border_radius=10)
    pygame.draw.rect(s, (220, 40, 40), (172, 38, 56, 22), border_radius=6)
    pygame.draw.rect(s, (230, 60, 60), (150, 170, 100, 60))
    pygame.draw.rect(s, (255, 255, 255), (150, 192, 100, 8))
    pygame.draw.rect(s, (255, 255, 255), (162, 120, 12, 160), border_radius=6)
    _bubbles(s, random.Random(6), (110, 20, 300, 120), 12, (255, 255, 255))
    _bubbles(s, random.Random(7), (170, 240, 240, 290), 5, (230, 200, 180))


def pic_car(s):
    _sky(s, (190, 200, 210), (225, 230, 235))
    pygame.draw.rect(s, (90, 90, 100), (0, 260, 400, 60), border_bottom_left_radius=28, border_bottom_right_radius=28)
    for x, y, r in ((70, 190, 36), (45, 150, 30), (95, 140, 34), (60, 105, 26), (30, 205, 22)):
        pygame.draw.circle(s, (110, 110, 118), (x, y), r)
        pygame.draw.circle(s, (140, 140, 148), (x - 6, y - 6), r // 2)
    pygame.draw.rect(s, (40, 120, 220), (120, 180, 230, 66), border_radius=18)
    pygame.draw.polygon(s, (40, 120, 220), [(170, 184), (200, 130), (300, 130), (330, 184)])
    pygame.draw.polygon(s, (200, 230, 255), [(184, 180), (206, 140), (246, 140), (246, 180)])
    pygame.draw.polygon(s, (200, 230, 255), [(256, 180), (256, 140), (296, 140), (316, 180)])
    for x in (170, 300):
        pygame.draw.circle(s, (30, 30, 34), (x, 248), 28)
        pygame.draw.circle(s, (170, 170, 180), (x, 248), 11)
    pygame.draw.rect(s, (60, 60, 66), (104, 226, 22, 10), border_radius=3)
    pygame.draw.circle(s, (255, 240, 140), (342, 200), 8)


def pic_frost(s):
    _sky(s, (190, 230, 255), (235, 248, 255))
    pygame.draw.rect(s, (160, 170, 190), (140, 120, 120, 180), border_radius=30)
    pygame.draw.rect(s, (200, 210, 225), (154, 132, 20, 150), border_radius=10)
    pygame.draw.rect(s, (120, 130, 150), (165, 96, 70, 34), border_radius=8)
    for x, y, r in ((200, 70, 34), (165, 50, 26), (240, 46, 28), (205, 25, 22)):
        pygame.draw.circle(s, (245, 250, 255), (x, y), r)
    for cx, cy, R in ((80, 110, 40), (325, 220, 46)):
        for i in range(6):
            a = i * math.pi / 3
            end = (cx + R * math.cos(a), cy + R * math.sin(a))
            pygame.draw.line(s, (90, 160, 230), (cx, cy), end, 6)
            for k in (0.55,):
                m = (cx + R * k * math.cos(a), cy + R * k * math.sin(a))
                for b in (-0.6, 0.6):
                    pygame.draw.line(s, (90, 160, 230), m,
                                     (m[0] + R * 0.35 * math.cos(a + b), m[1] + R * 0.35 * math.sin(a + b)), 5)


def pic_pool(s):
    _sky(s, (150, 210, 255), (210, 240, 255))
    pygame.draw.rect(s, (230, 220, 200), (0, 120, 400, 200), border_bottom_left_radius=28, border_bottom_right_radius=28)
    pygame.draw.rect(s, (40, 180, 230), (40, 150, 320, 150), border_radius=14)
    for y in range(170, 300, 26):
        pts = [(x, y + 6 * math.sin(x / 20)) for x in range(50, 352, 6)]
        pygame.draw.lines(s, (150, 230, 255), False, pts, 3)
    for x in (290, 330):
        pygame.draw.line(s, (200, 205, 215), (x, 90), (x, 200), 8)
        pygame.draw.arc(s, (200, 205, 215), (x - 30, 70, 30, 40), 0, math.pi, 8)
    for y in (130, 160, 190):
        pygame.draw.line(s, (200, 205, 215), (290, y), (330, y), 6)
    pygame.draw.circle(s, (255, 90, 90), (120, 200), 28, 12)
    pygame.draw.circle(s, (255, 255, 255), (120, 200), 28, 4)


def pic_earth(s):
    _sky(s, (10, 10, 40), (30, 20, 70))
    pygame.draw.circle(s, (255, 220, 80), (60, 60), 34)
    for i in range(8):
        a = i * math.pi / 4
        pygame.draw.line(s, (255, 220, 80), (60 + 42 * math.cos(a), 60 + 42 * math.sin(a)),
                         (60 + 58 * math.cos(a), 60 + 58 * math.sin(a)), 5)
    for k in range(4):
        sx, sy = 110 + k * 22, 90 + k * 14
        pygame.draw.line(s, (200, 120, 255), (sx, sy), (sx + 40, sy + 26), 4)
    shield = pygame.Surface((400, 320), pygame.SRCALPHA)
    pygame.draw.circle(shield, (120, 200, 255, 90), (230, 190), 128)
    pygame.draw.circle(shield, (160, 230, 255, 160), (230, 190), 128, 8)
    s.blit(shield, (0, 0))
    pygame.draw.circle(s, (40, 110, 220), (230, 190), 100)
    for pts in ([(170, 140), (210, 120), (230, 150), (200, 190), (170, 180)],
                [(240, 200), (290, 180), (310, 220), (270, 260), (240, 240)],
                [(200, 230), (215, 250), (190, 270)]):
        pygame.draw.polygon(s, (60, 180, 90), pts)
    pygame.draw.circle(s, (255, 255, 255), (230, 190), 100, 3)


def pic_spray(s):
    _sky(s, (220, 240, 255), (240, 250, 255))
    pygame.draw.rect(s, (80, 200, 230), (140, 130, 120, 170), border_radius=26)
    pygame.draw.rect(s, (255, 255, 255), (156, 180, 88, 70), border_radius=10)
    pygame.draw.rect(s, (60, 160, 200), (165, 105, 70, 34), border_radius=8)
    pygame.draw.polygon(s, (240, 240, 245), [(150, 60), (250, 60), (250, 100), (170, 100), (140, 80)])
    pygame.draw.polygon(s, (240, 240, 245), [(240, 95), (262, 145), (248, 150), (228, 100)])
    pygame.draw.rect(s, (200, 200, 210), (110, 70, 40, 16), border_radius=4)
    for i in range(10):
        a = math.pi + (i - 4.5) * 0.12
        pygame.draw.circle(s, (120, 200, 255), (108 + 70 * math.cos(a), 78 + 70 * math.sin(a)), 4)
    for i, c in enumerate(((255, 220, 0), (120, 200, 255))):
        x = 175 + i * 50
        pygame.draw.polygon(s, c, [(x, 228), (x + 10, 206), (x + 20, 228)])
    pygame.draw.line(s, (255, 230, 120), (300, 120), (330, 100), 5)
    pygame.draw.line(s, (255, 230, 120), (300, 160), (340, 160), 5)


def pic_egg(s):
    _sky(s, (240, 250, 220), (225, 240, 200))
    pygame.draw.ellipse(s, (240, 235, 220), (60, 250, 280, 40))
    pygame.draw.ellipse(s, (245, 240, 225), (140, 110, 130, 170))
    pygame.draw.ellipse(s, (180, 175, 150), (140, 110, 130, 170), 4)
    pygame.draw.lines(s, (120, 110, 90), False, [(150, 190), (175, 175), (190, 195), (210, 172), (230, 194),
                                                  (250, 176), (262, 190)], 4)
    for x in (120, 200, 280):
        pts = [(x + 10 * math.sin(y / 10), y) for y in range(40, 100, 4)]
        pygame.draw.lines(s, (130, 160, 40), False, pts, 6)
    pygame.draw.circle(s, (130, 160, 40), (320, 120), 10)
    pygame.draw.circle(s, (130, 160, 40), (90, 150), 8)


def pic_laugh(s):
    _sky(s, (255, 235, 245), (250, 220, 240))
    pygame.draw.line(s, (120, 120, 140), (200, 260), (200, 316), 4)
    pygame.draw.circle(s, (255, 214, 60), (200, 150), 108)
    pygame.draw.circle(s, (230, 170, 30), (200, 150), 108, 5)
    for x in (160, 240):
        pygame.draw.arc(s, (60, 40, 20), (x - 22, 98, 44, 36), 0.2, math.pi - 0.2, 7)
    pygame.draw.polygon(s, (120, 30, 40), [(130, 168), (270, 168), (240, 222), (200, 236), (160, 222)])
    pygame.draw.polygon(s, (255, 255, 255), [(136, 170), (264, 170), (258, 182), (142, 182)])
    pygame.draw.ellipse(s, (255, 120, 140), (176, 204, 48, 24))
    for x in (110, 290):
        pygame.draw.ellipse(s, (255, 150, 140), (x - 18, 150, 36, 18))
    pygame.draw.circle(s, (120, 200, 255), (100, 120), 10)
    pygame.draw.polygon(s, (120, 200, 255), [(91, 116), (109, 116), (100, 96)])


def pic_soap(s):
    _sky(s, (225, 245, 255), (240, 250, 255))
    pygame.draw.polygon(s, (255, 170, 210), [(110, 200), (290, 200), (320, 250), (80, 250)])
    pygame.draw.rect(s, (255, 150, 200), (80, 250, 240, 40), border_radius=12)
    pygame.draw.polygon(s, (255, 210, 235), [(130, 208), (270, 208), (290, 240), (110, 240)])
    rng = random.Random(9)
    for x, y, r in ((150, 150, 34), (230, 120, 44), (300, 160, 24), (110, 100, 20), (200, 60, 26), (310, 70, 18)):
        b = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(b, (200, 230, 255, 90), (r + 2, r + 2), r)
        pygame.draw.circle(b, (150, 120, 255, 200), (r + 2, r + 2), r, 3)
        pygame.draw.circle(b, (255, 255, 255, 230), (r // 2 + 2, r // 2 + 2), max(2, r // 5))
        s.blit(b, (x - r, y - r))
    rng.random()


def pic_flame(s):
    _sky(s, (40, 40, 60), (70, 60, 80))
    pygame.draw.rect(s, (60, 60, 66), (60, 250, 280, 50), border_radius=10)
    pygame.draw.rect(s, (30, 30, 34), (130, 230, 140, 26), border_radius=6)
    for i in range(9):
        x = 140 + i * 15
        h = 70 + (i % 3) * 18
        pygame.draw.polygon(s, (60, 120, 255), [(x - 9, 232), (x + 9, 232), (x, 232 - h)])
        pygame.draw.polygon(s, (150, 210, 255), [(x - 4, 232), (x + 4, 232), (x, 232 - h * 0.55)])
    pygame.draw.ellipse(s, (150, 150, 160), (110, 220, 180, 22), 6)
    for x in (100, 300):
        pygame.draw.circle(s, (200, 200, 205), (x, 276), 12)


def pic_bottle(s):
    _sky(s, (235, 245, 255), (250, 252, 255))
    pygame.draw.rect(s, (120, 70, 40), (140, 110, 120, 190), border_radius=22)
    pygame.draw.rect(s, (120, 70, 40), (172, 70, 56, 50), border_radius=8)
    pygame.draw.rect(s, (245, 245, 250), (166, 42, 68, 34), border_radius=8)
    pygame.draw.rect(s, (255, 255, 255), (152, 160, 96, 90), border_radius=10)
    pygame.draw.rect(s, (230, 40, 40), (190, 176, 20, 58))
    pygame.draw.rect(s, (230, 40, 40), (171, 195, 58, 20))
    pygame.draw.rect(s, (170, 110, 70), (150, 120, 12, 160), border_radius=6)
    _bubbles(s, random.Random(10), (270, 60, 360, 200), 8, (180, 210, 240))


def pic_banana(s):
    _sky(s, (255, 250, 220), (255, 240, 200))
    pts_outer = [(200 + 150 * math.cos(a), 30 + 200 * math.sin(a)) for a in [i * 0.05 + 0.35 for i in range(48)]]
    pts_inner = [(200 + 110 * math.cos(a), 30 + 150 * math.sin(a)) for a in [i * 0.05 + 0.35 for i in range(48)]]
    pygame.draw.polygon(s, (255, 214, 50), pts_outer + pts_inner[::-1])
    pygame.draw.polygon(s, (200, 150, 20), pts_outer + pts_inner[::-1], 4)
    rng = random.Random(11)
    for _ in range(9):
        i = rng.randint(6, 40)
        a = i * 0.05 + 0.35
        rr = rng.uniform(118, 145)
        pygame.draw.circle(s, (130, 90, 30), (200 + rr * math.cos(a), 30 + rr * 1.35 * math.sin(a)), rng.randint(3, 6))
    pygame.draw.line(s, (110, 80, 30), pts_outer[0], (pts_outer[0][0] + 14, pts_outer[0][1] - 18), 10)
    pygame.draw.circle(s, (80, 60, 30), pts_outer[-1], 7)


PICTURES = {
    "H2": pic_rocket, "O2": pic_tree, "H2O": pic_water, "NaCl": pic_salt, "HCl": pic_stomach,
    "CO2": pic_soda, "CO": pic_car, "N2": pic_frost, "Cl2": pic_pool, "O3": pic_earth,
    "NH3": pic_spray, "H2S": pic_egg, "N2O": pic_laugh, "NaOH": pic_soap, "CH4": pic_flame,
    "H2O2": pic_bottle, "C2H4": pic_banana,
}
