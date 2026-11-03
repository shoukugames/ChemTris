"""Title screen, How to Play, Settings, Credits and the For Parents report."""
import math
import random

import pygame

from . import RELEASE_DATE, __version__, art, storage
from .audio import FUR_ELISE, NACHTMUSIK
from .config import (ACCENT, BAD, ELEMENTS, GOLD, GOOD, HEIGHT, TEXT, TEXT_DIM, WIDTH, PANEL_EDGE)
from .i18n import ENGLISH, JAPANESE, language, pick, set_language, t
from .molecules import BY_ID, ELEMENT_NAMES, INTRO_ORDER
from .ui import LanguageToggle, Menu

URL = "https://shoukugames.org/"
EMAIL = "info@shoukugames.org"


class Falling:
    """Atoms tumbling down behind the title."""

    def __init__(self, rng):
        self.rng = rng
        self.reset(True)

    def reset(self, anywhere=False):
        rng = self.rng
        self.el = rng.choice(ELEMENTS)
        self.size = rng.choice((30, 36, 44, 52))
        self.x = rng.uniform(20, WIDTH - 20)
        self.y = rng.uniform(-HEIGHT, HEIGHT) if anywhere else rng.uniform(-200, -50)
        self.v = rng.uniform(30, 80)

    def update(self, dt):
        self.y += self.v * dt
        if self.y > HEIGHT + 60:
            self.reset()

    def draw(self, surf):
        img = art.atom(self.el, self.size).copy()
        img.set_alpha(110)
        surf.blit(img, (self.x, self.y))


class BaseScene:
    music = FUR_ELISE

    def __init__(self, app):
        self.app = app
        self.time = 0.0
        app.audio.music(self.music)

    def back(self):
        self.app.audio.play("select")
        self.app.switch(TitleScene(self.app))

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.back()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.back_rect().collidepoint(event.pos):
            self.back()

    def update(self, dt):
        self.time += dt

    def back_rect(self):
        return pygame.Rect(24, HEIGHT - 76, 170, 52)

    def draw_frame(self, surf, title):
        self.app.background.draw(surf)
        art.text(surf, title, 50, TEXT, (WIDTH // 2, 22), "midtop", outline=(20, 40, 100))
        r = self.back_rect()
        hover = r.collidepoint(pygame.mouse.get_pos())
        art.panel(surf, r, (40, 70, 140) if hover else (24, 36, 76), ACCENT if hover else PANEL_EDGE, radius=16)
        art.text(surf, "← " + t("back"), 24, TEXT, r.center, "center")
        art.text(surf, t("back_hint"), 16, TEXT_DIM, (24, 20))


class TitleScene:
    def __init__(self, app):
        self.app = app
        self.time = 0.0
        self.rng = random.Random()
        self.falling = [Falling(self.rng) for _ in range(26)]
        self.menu = Menu([("play", lambda: t("play")), ("how", lambda: t("how_to")),
                          ("parents", lambda: t("parents")), ("settings", lambda: t("settings")),
                          ("credits", lambda: t("credits")), ("quit", lambda: t("quit"))],
                         (WIDTH // 2, 470), 340, 50, 10)
        self.toggle = LanguageToggle()
        app.audio.music(NACHTMUSIK)

    def _set_language(self, lang):
        set_language(lang)
        self.app.settings["language"] = lang
        storage.save_settings(self.app.settings)
        self.app.audio.play("select")

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
            self._set_language(JAPANESE if language() == ENGLISH else ENGLISH)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.running = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lang = self.toggle.clicked(event.pos)
            if lang:
                self._set_language(lang)
                return
        choice = self.menu.handle(event, self.app.audio)
        if choice == "play":
            from .play import PlayScene
            self.app.switch(PlayScene(self.app))
        elif choice == "how":
            self.app.switch(HowToScene(self.app))
        elif choice == "parents":
            self.app.switch(ParentsScene(self.app))
        elif choice == "settings":
            self.app.switch(SettingsScene(self.app))
        elif choice == "credits":
            self.app.switch(CreditsScene(self.app))
        elif choice == "quit":
            self.app.running = False

    def update(self, dt):
        self.time += dt
        self.menu.update(dt)
        for f in self.falling:
            f.update(dt)

    def draw(self, surf):
        self.app.background.draw(surf)
        for f in self.falling:
            f.draw(surf)
        self._logo(surf, (WIDTH // 2, 140))
        art.text(surf, t("subtitle"), 28, ACCENT, (WIDTH // 2, 232), "midtop")
        self.menu.draw(surf)
        self.toggle.draw(surf)
        art.text(surf, t("menu_hint"), 16, TEXT_DIM, (WIDTH // 2, HEIGHT - 14), "midbottom")
        art.text(surf, f"v{__version__}", 16, TEXT_DIM, (WIDTH - 16, HEIGHT - 14), "bottomright")

    def _logo(self, surf, center):
        word = "ChemTris"
        f = art.font(108)
        colors = [(255, 110, 90), (255, 190, 70), (255, 236, 90), (120, 230, 120),
                  (90, 200, 255), (120, 140, 255), (200, 120, 255), (255, 120, 200)]
        widths = [f.size(ch)[0] for ch in word]
        x = center[0] - sum(widths) // 2
        for i, ch in enumerate(word):
            dy = math.sin(self.time * 2.5 + i * 0.6) * 8
            art.text(surf, ch, 108, colors[i], (x + widths[i] // 2, center[1] + dy), "center", outline=(15, 20, 50))
            x += widths[i]
        # Little water molecule orbiting the logo
        a = self.time * 1.2
        px, py = center[0] + math.cos(a) * 330, center[1] + math.sin(a) * 50
        img = art.structure(BY_ID["H2O"], (110, 80))
        surf.blit(img, img.get_rect(center=(px, py)))
        if language() == JAPANESE:
            art.text(surf, "ケムトリス", 24, TEXT_DIM, (center[0], center[1] + 62), "midtop")


class HowToScene(BaseScene):
    def draw(self, surf):
        self.draw_frame(surf, t("how_title"))
        box = pygame.Rect(40, 100, 760, 520)
        art.panel(surf, box)
        y = box.top + 22
        for i in range(1, 8):
            img = art.atom(ELEMENTS[(i - 1) % len(ELEMENTS)], 30)
            surf.blit(img, (box.left + 20, y + 2))
            y = art.text_block(surf, t(f"how_{i}"), 19, TEXT, (box.left + 62, y), box.w - 90, 0) + 8
        art.text(surf, t("how_controls"), 21, ACCENT, (box.left + 24, y + 2))
        art.text_block(surf, t("controls"), 17, TEXT_DIM, (box.left + 24, y + 32), box.w - 48, 2)
        side = pygame.Rect(824, 100, 416, 520)
        art.panel(surf, side)
        art.text(surf, t("atoms_title"), 24, ACCENT, (side.centerx, side.top + 16), "midtop")
        for i, el in enumerate(ELEMENTS):
            yy = side.top + 64 + i * 50
            surf.blit(art.atom(el, 42), (side.left + 30, yy))
            art.text(surf, el, 24, TEXT, (side.left + 90, yy + 6))
            art.text(surf, pick(ELEMENT_NAMES[el]), 24, TEXT_DIM, (side.left + 150, yy + 6))
        # A tiny example: H + H + O = water
        yy = side.bottom - 76
        x = side.left + 30
        for el in ("H", "O", "H"):
            surf.blit(art.atom(el, 40), (x, yy))
            x += 40
        art.text(surf, "→", 34, GOLD, (x + 16, yy - 4))
        f = art.formula_surface([("H", 2), ("O", 1)], 40, GOLD)
        surf.blit(f, (x + 62, yy - 4))
        art.text(surf, pick(BY_ID["H2O"].name), 24, TEXT, (x + 80 + f.get_width(), yy + 4))


class SettingsScene(BaseScene):
    def __init__(self, app):
        super().__init__(app)
        self.menu = Menu([("music", lambda: self._label("music")), ("sound", lambda: self._label("sound")),
                          ("fullscreen", lambda: self._label("fullscreen")),
                          ("language", lambda: f"{t('language')}: {'日本語' if language() == JAPANESE else 'English'}"),
                          ("back", lambda: t("back"))], (WIDTH // 2, HEIGHT // 2 + 20), 460)

    def _label(self, key):
        on = self.app.settings.get(key, False)
        return f"{t(key)}: {t('on') if on else t('off')}"

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return
        choice = self.menu.handle(event, self.app.audio)
        s = self.app.settings
        if choice == "music":
            self.app.audio.set_music_enabled(not s.get("music", True))
        elif choice == "sound":
            s["sound"] = not s.get("sound", True)
        elif choice == "fullscreen":
            self.app.toggle_fullscreen()
        elif choice == "language":
            lang = ENGLISH if language() == JAPANESE else JAPANESE
            set_language(lang)
            s["language"] = lang
        elif choice == "back":
            self.back()
        if choice:
            storage.save_settings(s)

    def update(self, dt):
        super().update(dt)
        self.menu.update(dt)

    def draw(self, surf):
        self.app.background.draw(surf)
        art.text(surf, t("settings_title"), 50, TEXT, (WIDTH // 2, 60), "midtop", outline=(20, 40, 100))
        self.menu.draw(surf)


class CreditsScene(BaseScene):
    def draw(self, surf):
        self.draw_frame(surf, t("credits_title"))
        box = pygame.Rect(0, 0, 820, 540)
        box.midtop = (WIDTH // 2, 96)
        art.panel(surf, box)
        rows = [
            (t("created_by"), t("creators"), GOLD),
            (t("website"), URL, ACCENT),
            (t("email"), EMAIL, ACCENT),
            (t("version"), f"v{__version__}", TEXT),
            (t("date"), RELEASE_DATE, TEXT),
        ]
        y = box.top + 30
        for label, value, color in rows:
            art.text(surf, label, 22, TEXT_DIM, (box.left + 50, y + 6))
            art.text(surf, value, 30, color, (box.left + 260, y))
            y += 58
        pygame.draw.line(surf, PANEL_EDGE, (box.left + 40, y + 4), (box.right - 40, y + 4), 2)
        y += 20
        art.text(surf, t("music_credit"), 22, TEXT_DIM, (box.left + 50, y + 4))
        y = art.text_block(surf, t("music_list"), 20, TEXT, (box.left + 260, y + 4), box.w - 300, 4) + 10
        art.text(surf, t("font_credit"), 22, TEXT_DIM, (box.left + 50, y + 4))
        art.text(surf, "M+ 1p (SIL Open Font License)", 20, TEXT, (box.left + 260, y + 4))
        y += 44
        art.text(surf, t("license"), 22, TEXT_DIM, (box.left + 50, y + 4))
        art.text(surf, "GNU GPL v3", 20, TEXT, (box.left + 260, y + 4))
        a = self.time
        for i, el in enumerate(("H", "O", "C", "N", "Na", "Cl", "S")):
            img = art.atom(el, 40)
            x = WIDTH // 2 - 380 + i * 50 if i < 3 else WIDTH // 2 + 230 + (i - 3) * 50
            surf.blit(img, (x, 34 + math.sin(a * 3 + i) * 6))


def _duration(seconds):
    m = int(seconds // 60)
    if m >= 60:
        return t("hours", h=m // 60, m=m % 60)
    return t("minutes", m=m)


class ParentsScene(BaseScene):
    TABS = ("tab_overview", "tab_molecules", "tab_history", "tab_errors")

    def __init__(self, app):
        super().__init__(app)
        self.tab = 0
        self.progress = storage.load_progress()
        self.reset_armed = 0.0
        self.message = None

    def tab_rects(self):
        w = 230
        x = WIDTH // 2 - (w * len(self.TABS) + 12 * (len(self.TABS) - 1)) // 2
        return [pygame.Rect(x + i * (w + 12), 92, w, 46) for i in range(len(self.TABS))]

    def reset_rect(self):
        return pygame.Rect(WIDTH - 324, HEIGHT - 76, 300, 52)

    def handle(self, event):
        super().handle(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.tab = (self.tab - 1) % len(self.TABS)
                self.app.audio.play("menu")
            elif event.key == pygame.K_RIGHT:
                self.tab = (self.tab + 1) % len(self.TABS)
                self.app.audio.play("menu")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.tab_rects()):
                if r.collidepoint(event.pos):
                    self.tab = i
                    self.app.audio.play("menu")
            if self.reset_rect().collidepoint(event.pos):
                if self.reset_armed > 0:
                    storage.reset_progress()
                    self.progress = storage.load_progress()
                    self.reset_armed = 0
                    self.message = (t("reset_done"), 2.5)
                    self.app.audio.play("wrong")
                else:
                    self.reset_armed = 3.0
                    self.app.audio.play("menu")

    def update(self, dt):
        super().update(dt)
        self.reset_armed = max(0.0, self.reset_armed - dt)
        if self.message:
            self.message = (self.message[0], self.message[1] - dt) if self.message[1] > dt else None

    def draw(self, surf):
        self.draw_frame(surf, t("parents_title"))
        for i, (r, key) in enumerate(zip(self.tab_rects(), self.TABS)):
            on = i == self.tab
            art.panel(surf, r, (50, 90, 170) if on else (24, 36, 76), ACCENT if on else PANEL_EDGE, radius=14)
            art.text(surf, t(key), 22, TEXT if on else TEXT_DIM, r.center, "center")
        area = pygame.Rect(40, 150, WIDTH - 80, 470)
        art.panel(surf, area)
        p = self.progress
        if p["games"] == 0:
            art.text(surf, t("no_data"), 30, TEXT_DIM, area.center, "center")
        else:
            [self._overview, self._molecules, self._history, self._errors][self.tab](surf, area, p)
        r = self.reset_rect()
        armed = self.reset_armed > 0
        art.panel(surf, r, (120, 30, 40) if armed else (60, 26, 40), BAD, radius=16)
        art.text(surf, t("reset_confirm") if armed else t("reset"), 18 if armed else 22, TEXT, r.center, "center")
        art.text(surf, t("parents_note"), 16, TEXT_DIM, (WIDTH // 2, HEIGHT - 50), "midtop")
        if self.message:
            art.text(surf, self.message[0], 26, GOOD, (WIDTH // 2, HEIGHT - 96), "midtop")

    def _overview(self, surf, area, p):
        built, errors = p["molecules"], p["errors"]
        accuracy = f"{100 * built / (built + errors):.0f}%" if built + errors else "–"
        cards = [
            (t("high_score"), f"{p['high_score']:,}", GOLD), (t("best_level"), str(p["best_level"]), TEXT),
            (t("games_played"), str(p["games"]), TEXT), (t("play_time"), _duration(p["seconds"]), TEXT),
            (t("total_molecules"), str(built), GOOD), (t("total_errors"), str(errors), BAD if errors else TEXT),
            (t("accuracy"), accuracy, ACCENT), (t("total_rows"), str(p["rows"]), TEXT),
        ]
        cw, ch = 270, 92
        for i, (label, value, color) in enumerate(cards):
            r = pygame.Rect(area.left + 24 + (i % 4) * (cw + 14), area.top + 20 + (i // 4) * (ch + 14), cw, ch)
            pygame.draw.rect(surf, (14, 22, 50), r, border_radius=14)
            art.text(surf, label, 18, TEXT_DIM, (r.left + 16, r.top + 10))
            art.text(surf, value, 34, color, (r.left + 16, r.bottom - 10), "bottomleft")
        # Score chart of recent games
        chart = pygame.Rect(area.left + 24, area.top + 240, area.w - 48, area.h - 260)
        pygame.draw.rect(surf, (14, 22, 50), chart, border_radius=14)
        art.text(surf, t("score_chart"), 18, TEXT_DIM, (chart.left + 16, chart.top + 8))
        sessions = p["sessions"][-20:]
        top = max(1, max(s["score"] for s in sessions))
        plot = pygame.Rect(chart.left + 70, chart.top + 40, chart.w - 100, chart.h - 66)
        for k in range(5):
            y = plot.bottom - plot.h * k / 4
            pygame.draw.line(surf, (40, 56, 100), (plot.left, y), (plot.right, y))
            art.text(surf, f"{int(top * k / 4):,}", 14, TEXT_DIM, (plot.left - 8, y), "midright", shadow=False)
        bw = plot.w / max(1, len(sessions))
        for i, s in enumerate(sessions):
            h = max(2, plot.h * s["score"] / top)
            r = pygame.Rect(plot.left + i * bw + bw * 0.15, plot.bottom - h, bw * 0.7, h)
            pygame.draw.rect(surf, (90, 180, 255) if i < len(sessions) - 1 else GOLD, r,
                             border_top_left_radius=6, border_top_right_radius=6)
            if bw > 34:
                art.text(surf, f"L{s['level']}", 13, TEXT_DIM, (r.centerx, plot.bottom + 4), "midtop", shadow=False)

    def _table(self, surf, area, headers, widths, rows, empty):
        x0, y = area.left + 30, area.top + 18
        x = x0
        for h, w in zip(headers, widths):
            art.text(surf, h, 19, ACCENT, (x, y))
            x += w
        y += 38
        pygame.draw.line(surf, PANEL_EDGE, (x0, y - 6), (area.right - 30, y - 6), 2)
        if not rows:
            art.text(surf, empty, 24, TEXT_DIM, (area.centerx, area.centery), "center")
        for row in rows:
            if y > area.bottom - 34:
                break
            x = x0
            for cell, w in zip(row, widths):
                if isinstance(cell, pygame.Surface):
                    surf.blit(cell, (x, y - 4))
                else:
                    value, color = cell if isinstance(cell, tuple) else (cell, TEXT)
                    art.text(surf, str(value), 19, color, (x, y), shadow=False)
                x += w
            y += 34

    def _molecules(self, surf, area, p):
        rows = []
        for mid in INTRO_ORDER:
            m = p["per_molecule"].get(mid)
            if not m:
                continue
            mol = BY_ID[mid]
            b, e = m.get("built", 0), m.get("errors", 0)
            acc = f"{100 * b / (b + e):.0f}%" if b + e else "–"
            best = f"{m['best']:.1f} s" if m.get("best") is not None else "–"
            rows.append([art.formula_surface(mol.parts, 22, GOLD), pick(mol.name), (b, GOOD),
                         (e, BAD if e else TEXT), acc, best])
        self._table(surf, area, [t("col_molecule"), "", t("col_built"), t("col_errors"), t("col_accuracy"),
                                 t("col_best")], [130, 380, 150, 150, 170, 150], rows, t("no_data"))

    def _history(self, surf, area, p):
        rows = []
        for s in reversed(p["sessions"]):
            rows.append([s["date"], (f"{s['score']:,}", GOLD), s["level"], (s["molecules"], GOOD),
                         (s["errors"], BAD if s["errors"] else TEXT), s["rows"], _duration(s["seconds"])])
        self._table(surf, area, [t("col_date"), t("col_score"), t("col_level"), t("molecules").title()
                                 if language() == ENGLISH else t("molecules"), t("col_errors"), t("rows").title()
                                 if language() == ENGLISH else t("rows"), t("col_time")],
                    [230, 160, 110, 150, 140, 120, 160], rows, t("no_data"))

    def _errors(self, surf, area, p):
        rows = []
        for e in reversed(p["error_log"]):
            mol = BY_ID.get(e["target"])
            if not mol:
                continue
            rows.append([e["date"], e["level"], art.formula_surface(mol.parts, 22, GOOD), pick(mol.name),
                         art.formula_surface(art.parse_formula(e["made"]), 22, BAD)])
        self._table(surf, area, [t("col_date"), t("col_level"), t("col_target"), "", t("col_made")],
                    [230, 110, 140, 380, 200], rows, t("no_errors"))
