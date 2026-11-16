"""On-screen buttons for phones and tablets.

Shown in the controls panel while playing on a touch screen. Each button stands in for
a key, so the game logic is exactly the keyboard's: holding left/right repeats the move,
holding down soft-drops.
"""
import math

import pygame

from . import art
from .config import ACCENT, TEXT, TEXT_DIM

# (key, icon) for the two rows, top to bottom.
ROWS = (
    ((pygame.K_z, "rot_ccw"), (pygame.K_UP, "rot_cw"), (pygame.K_p, "pause"), (pygame.K_m, "music")),
    ((pygame.K_LEFT, "left"), (pygame.K_DOWN, "down"), (pygame.K_RIGHT, "right"), (pygame.K_SPACE, "drop")),
)


def has_touch_screen():
    """True when the browser reports a touch screen (pygbag only)."""
    try:
        import platform  # pygbag's bridge to the page
        return int(platform.window.navigator.maxTouchPoints) > 0
    except Exception:
        return False


class TouchPad:
    def __init__(self):
        self.buttons = []           # [(rect, key, icon)]
        self.down = None            # key currently pressed by a finger

    def layout(self, area):
        """Fit the buttons into `area` (a pygame.Rect)."""
        gap = 8
        pad = 12
        cols = len(ROWS[0])
        w = (area.width - 2 * pad - (cols - 1) * gap) // cols
        h = (area.height - 2 * pad - (len(ROWS) - 1) * gap) // len(ROWS)
        self.buttons = []
        for r, row in enumerate(ROWS):
            for c, (key, icon) in enumerate(row):
                rect = pygame.Rect(area.left + pad + c * (w + gap), area.top + pad + r * (h + gap), w, h)
                self.buttons.append((rect, key, icon))

    def hit(self, pos):
        for rect, key, _ in self.buttons:
            if rect.inflate(6, 6).collidepoint(pos):
                return key
        return None

    def draw(self, surf, music_on=True):
        for rect, key, icon in self.buttons:
            pressed = key == self.down
            art.panel(surf, rect, (60, 90, 170) if pressed else (32, 48, 100), (110, 160, 255), radius=12, alpha=235)
            color = TEXT if pressed else (205, 220, 255)
            if icon == "music" and not music_on:
                color = TEXT_DIM
            _icon(surf, icon, rect.center, min(rect.width, rect.height) * 0.36, color)
            if icon == "music" and not music_on:
                pygame.draw.line(surf, ACCENT, (rect.centerx - 14, rect.centery + 14), (rect.centerx + 14, rect.centery - 14), 4)


def _icon(surf, name, center, s, color):
    cx, cy = center
    if name in ("left", "right"):
        d = -1 if name == "left" else 1
        pygame.draw.polygon(surf, color, [(cx + d * s, cy), (cx - d * s * 0.7, cy - s), (cx - d * s * 0.7, cy + s)])
    elif name == "down":
        pygame.draw.polygon(surf, color, [(cx, cy + s), (cx - s, cy - s * 0.7), (cx + s, cy - s * 0.7)])
    elif name == "drop":
        for dy in (-s * 0.55, s * 0.35):
            pygame.draw.polygon(surf, color, [(cx, cy + dy + s * 0.55), (cx - s, cy + dy - s * 0.35), (cx + s, cy + dy - s * 0.35)])
        pygame.draw.line(surf, color, (cx - s, cy + s * 1.05), (cx + s, cy + s * 1.05), 4)
    elif name in ("rot_cw", "rot_ccw"):
        # Clockwise: arc open on the right, arrow head at the top right. Back: its mirror image.
        m = 1 if name == "rot_cw" else -1
        r = int(s * 0.9)
        rect = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
        if m == 1:
            pygame.draw.arc(surf, color, rect, math.radians(40), math.radians(320), 5)
        else:
            pygame.draw.arc(surf, color, rect, math.radians(220), math.radians(500), 5)
        ang = math.radians(40)
        tip = (cx + m * r * math.cos(ang), cy - r * math.sin(ang))
        pts = [(tip[0] + m * 9, tip[1] - 2), (tip[0] - m * 7, tip[1] - 9), (tip[0] - m * 2, tip[1] + 9)]
        pygame.draw.polygon(surf, color, pts)
    elif name == "pause":
        bw = max(5, int(s * 0.35))
        pygame.draw.rect(surf, color, (cx - s * 0.6, cy - s, bw, 2 * s), border_radius=2)
        pygame.draw.rect(surf, color, (cx + s * 0.6 - bw, cy - s, bw, 2 * s), border_radius=2)
    elif name == "music":
        art.text(surf, "♪", int(s * 2.2), color, (cx, cy), "center", shadow=False)
