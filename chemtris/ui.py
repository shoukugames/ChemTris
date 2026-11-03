"""Menus that work with the keyboard and the mouse, and the language toggle."""
import math

import pygame

from . import art
from .config import ACCENT, TEXT, WIDTH, PANEL_EDGE
from .i18n import ENGLISH, JAPANESE, LANGUAGE_NAMES, language


class Menu:
    """A vertical list of buttons. `items` is [(key, label_function)]."""

    def __init__(self, items, center, width=360, height=56, gap=14):
        self.items = items
        self.index = 0
        self.center = center
        self.width, self.height, self.gap = width, height, gap
        self.time = 0.0

    def rects(self):
        cx, cy = self.center
        total = len(self.items) * self.height + (len(self.items) - 1) * self.gap
        top = cy - total // 2
        return [pygame.Rect(cx - self.width // 2, top + i * (self.height + self.gap), self.width, self.height)
                for i in range(len(self.items))]

    def handle(self, event, audio=None):
        """Returns the chosen key, or None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.items)
                audio and audio.play("menu")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.items)
                audio and audio.play("menu")
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                audio and audio.play("select")
                return self.items[self.index][0]
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects()):
                if r.collidepoint(event.pos) and i != self.index:
                    self.index = i
                    audio and audio.play("menu")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects()):
                if r.collidepoint(event.pos):
                    self.index = i
                    audio and audio.play("select")
                    return self.items[i][0]
        return None

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        for i, (rect, (_, label)) in enumerate(zip(self.rects(), self.items)):
            selected = i == self.index
            grow = 6 + 3 * math.sin(self.time * 6) if selected else 0
            r = rect.inflate(grow, grow * 0.4)
            color = (40, 70, 140) if selected else (24, 36, 76)
            edge = ACCENT if selected else PANEL_EDGE
            art.panel(surf, r, color, edge, radius=16, alpha=235)
            art.text(surf, label(), 28, TEXT if selected else (200, 210, 235), r.center, "center")
            if selected:
                img = art.atom("H" if i % 2 else "O", 30)
                surf.blit(img, img.get_rect(midright=(r.left - 10, r.centery)))


class LanguageToggle:
    """The EN | 日本語 pill in the top right corner of the title screen."""

    def __init__(self, pos=(WIDTH - 24, 24)):
        self.pos = pos

    def rects(self):
        right, top = self.pos
        ja = pygame.Rect(0, 0, 100, 44)
        ja.topright = (right, top)
        en = pygame.Rect(0, 0, 70, 44)
        en.topright = (ja.left, top)
        return {ENGLISH: en, JAPANESE: ja}

    def draw(self, surf):
        rects = self.rects()
        whole = rects[ENGLISH].union(rects[JAPANESE])
        art.panel(surf, whole.inflate(8, 8), (18, 28, 60), PANEL_EDGE, radius=26)
        for lang, r in rects.items():
            on = language() == lang
            if on:
                pygame.draw.rect(surf, (60, 150, 230), r, border_radius=22)
            art.text(surf, LANGUAGE_NAMES[lang], 22, TEXT if on else (150, 165, 200), r.center, "center",
                     shadow=False)

    def clicked(self, pos):
        for lang, r in self.rects().items():
            if r.collidepoint(pos):
                return lang
        return None
