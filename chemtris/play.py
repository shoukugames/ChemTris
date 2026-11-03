"""The game screen: target card, playing field, next-piece preview and effects."""
import math
import random

import pygame

from . import art, storage
from .audio import game_song
from .config import (ACCENT, BAD, CELL, COLS, FIELD_H, FIELD_W, FIELD_X, FIELD_Y, GOLD, GOOD, GRID_LINE,
                     HEIGHT, LEFT_PANEL, ROWS, TEXT, TEXT_DIM, WIDTH, ELEMENT_COLORS, FIELD_BG)
from .game import RUBBLE, Game, fall_time
from .i18n import pick, t
from .molecules import ELEMENT_NAMES
from .ui import Menu

RIGHT_X = FIELD_X + FIELD_W + 24
RIGHT_W = WIDTH - RIGHT_X - 24
DAS_DELAY, DAS_REPEAT = 0.16, 0.05


def cell_center(c, r):
    return FIELD_X + c * CELL + CELL // 2, FIELD_Y + r * CELL + CELL // 2


class Particle:
    def __init__(self, x, y, color, rng, speed=260):
        a = rng.uniform(0, math.tau)
        v = rng.uniform(0.3, 1) * speed
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * v, math.sin(a) * v - 80
        self.color = color
        self.life = self.max_life = rng.uniform(0.5, 1.1)
        self.size = rng.uniform(3, 7)

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 420 * dt
        self.vx *= 0.98

    def draw(self, surf):
        k = max(0.0, self.life / self.max_life)
        pygame.draw.circle(surf, self.color, (self.x, self.y), max(1, self.size * k))


class FloatText:
    def __init__(self, s, pos, color, size=28, life=1.4, rise=50):
        self.s, self.x, self.y = s, pos[0], pos[1]
        self.color, self.size = color, size
        self.life = self.max_life = life
        self.rise = rise

    def update(self, dt):
        self.life -= dt
        self.y -= self.rise * dt

    def draw(self, surf):
        img = art.font(self.size).render(self.s, True, self.color)
        out = art.font(self.size).render(self.s, True, (0, 0, 0))
        k = max(0.0, min(1.0, self.life / self.max_life * 2))
        img.set_alpha(int(255 * k))
        out.set_alpha(int(200 * k))
        r = img.get_rect(center=(self.x, self.y))
        r.clamp_ip(pygame.Rect(FIELD_X - 60, 0, FIELD_W + 120, HEIGHT))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surf.blit(out, r.move(dx, dy))
        surf.blit(img, r)


class Ghost:
    """An atom that just reacted, swelling and fading away."""

    def __init__(self, element, pos, life=0.45):
        self.element, self.pos = element, pos
        self.life = self.max_life = life

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        k = max(0.0, self.life / self.max_life)
        size = int(CELL * (1 + (1 - k) * 0.8))
        img = pygame.transform.smoothscale(art.atom(self.element, CELL), (size, size))
        img.set_alpha(int(255 * k))
        surf.blit(img, img.get_rect(center=self.pos))


class PlayScene:
    def __init__(self, app, start_level=1, seed=None):
        self.app = app
        self.game = Game(seed=seed, start_level=start_level)
        self.rng = random.Random(seed)
        self.effects = []
        self.flashes = []           # [(rect, color, life, max)]
        self.banner = None          # (title, subtitle, life)
        self.shake = 0.0
        self.time = 0.0
        self.paused = False
        self.pause_menu = Menu([("resume", lambda: t("resume")), ("title", lambda: t("to_title"))],
                               (FIELD_X + FIELD_W // 2, HEIGHT // 2 + 40), 300)
        self.over_menu = Menu([("again", lambda: t("play_again")), ("title", lambda: t("to_title"))],
                              (WIDTH // 2, HEIGHT // 2 + 150), 300)
        self.over_time = 0.0
        self.recorded = False
        self.new_best = False
        self.held = {}              # key -> time held
        self.glow = set()
        self.card_anim = 0.0
        self.danger = 0.0
        self._refresh_glow()
        self._music()

    # ----- helpers -----
    def _music(self):
        level = self.game.level
        self.app.audio.music(game_song(level), 1.0 + min(0.6, (level - 1) * 0.02))

    def _refresh_glow(self):
        self.glow = set()
        if self.game.tier >= 3:
            return
        target = self.game.target
        board = self.game.board
        for group in board.all_groups():
            if len(group) < 2:
                continue
            counts = board.counts(group)
            if all(el in target.counts and counts[el] <= target.counts[el] for el in counts):
                self.glow |= group

    def _record(self, reason):
        if self.recorded or self.game.stats.pieces == 0:
            return
        self.recorded = True
        _, self.new_best = storage.record_game(self.game, reason)

    def leave(self):
        """Called when the player quits to the title or closes the window."""
        self._record("quit")

    # ----- input -----
    def handle(self, event):
        g = self.game
        audio = self.app.audio
        if g.over:
            if self.over_time > 1.2:
                choice = self.over_menu.handle(event, audio)
                if choice == "again":
                    self.app.switch(PlayScene(self.app))
                elif choice == "title":
                    from .scenes import TitleScene
                    self.app.switch(TitleScene(self.app))
            return
        if self.paused:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.paused = False
                return
            choice = self.pause_menu.handle(event, audio)
            if choice == "resume":
                self.paused = False
            elif choice == "title":
                self.leave()
                from .scenes import TitleScene
                self.app.switch(TitleScene(self.app))
            return
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_LEFT, pygame.K_a):
                if g.move(-1):
                    audio.play("move")
                self.held = {k: 0.0}
            elif k in (pygame.K_RIGHT, pygame.K_d):
                if g.move(1):
                    audio.play("move")
                self.held = {k: 0.0}
            elif k in (pygame.K_UP, pygame.K_x, pygame.K_w):
                if g.rotate(1):
                    audio.play("rotate")
            elif k == pygame.K_z:
                if g.rotate(-1):
                    audio.play("rotate")
            elif k in (pygame.K_DOWN, pygame.K_s):
                g.soft = True
            elif k == pygame.K_SPACE:
                g.hard_drop()
            elif k in (pygame.K_p, pygame.K_ESCAPE):
                self.paused = True
                self.pause_menu.index = 0
            elif k == pygame.K_m:
                self.app.audio.set_music_enabled(not self.app.settings.get("music", True))
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                g.soft = False
            self.held.pop(event.key, None)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.paused = True

    # ----- update -----
    def update(self, dt):
        self.time += dt
        self.card_anim = min(1.0, self.card_anim + dt * 2.5)
        g = self.game
        for e in self.effects:
            e.update(dt)
        self.effects = [e for e in self.effects if e.life > 0]
        self.flashes = [(r, c, life - dt, m) for r, c, life, m in self.flashes if life - dt > 0]
        if self.banner:
            title, sub, life = self.banner
            self.banner = (title, sub, life - dt) if life - dt > 0 else None
        self.shake = max(0.0, self.shake - dt)
        if g.over:
            self.over_time += dt
            self.over_menu.update(dt)
            return
        if self.paused:
            self.pause_menu.update(dt)
            return
        for key in list(self.held):
            before = self.held[key]
            self.held[key] = before + dt
            if self.held[key] >= DAS_DELAY:
                repeats = int((self.held[key] - DAS_DELAY) / DAS_REPEAT) - int(max(0, before - DAS_DELAY) / DAS_REPEAT)
                if before < DAS_DELAY:
                    repeats += 1
                for _ in range(repeats):
                    if g.move(-1 if key in (pygame.K_LEFT, pygame.K_a) else 1):
                        self.app.audio.play("move")
        g.update(dt)
        self._events()
        h = g.board.height()
        self.danger = min(1.0, max(0.0, (h - (ROWS - 5)) / 4))

    def _events(self):
        g = self.game
        audio = self.app.audio
        changed = False
        for ev in g.take_events():
            kind = ev[0]
            changed = True
            if kind == "lock":
                audio.play("lock")
            elif kind == "drop":
                if ev[1] > 0:
                    audio.play("drop")
                    self.shake = max(self.shake, 0.08)
            elif kind == "built":
                _, mol, atoms, blasted, gained, _ = ev
                audio.play("built")
                cx = sum(c for c, _, _ in atoms) / len(atoms)
                cy = sum(r for _, r, _ in atoms) / len(atoms)
                for c, r, el in atoms:
                    pos = cell_center(c, r)
                    self.effects.append(Ghost(el, pos))
                    for _ in range(14):
                        self.effects.append(Particle(*pos, ELEMENT_COLORS[el], self.rng))
                for c, r in blasted:
                    pos = cell_center(c, r)
                    for _ in range(6):
                        self.effects.append(Particle(*pos, (170, 170, 180), self.rng, 200))
                center = cell_center(cx, cy)
                self.effects.append(FloatText(f"+{gained}", center, GOLD, 30))
                self.banner = (t("built", name=pick(mol.name)), t("next_level", n=g.level), 2.4)
                self.flashes.append((pygame.Rect(FIELD_X, FIELD_Y, FIELD_W, FIELD_H), (255, 255, 255), 0.25, 0.25))
            elif kind == "level":
                audio.play("level")
                self.card_anim = 0.0
                self._music()
            elif kind == "wrong":
                _, cells, made = ev
                audio.play("wrong")
                self.shake = 0.35
                for c, r in cells:
                    self.flashes.append((pygame.Rect(FIELD_X + c * CELL, FIELD_Y + r * CELL, CELL, CELL),
                                         BAD, 0.6, 0.6))
                c = sum(x for x, _ in cells) / len(cells)
                r = min(y for _, y in cells)
                self.effects.append(FloatText(t("wrong", made=made), cell_center(c, r - 0.5), BAD, 24, 2.0, 30))
            elif kind == "rows":
                _, rows, snapshot, gained = ev
                audio.play("rows")
                for r in rows:
                    self.flashes.append((pygame.Rect(FIELD_X, FIELD_Y + r * CELL, FIELD_W, CELL),
                                         (255, 255, 255), 0.4, 0.4))
                    for c, v in enumerate(snapshot[r]):
                        if v and v != RUBBLE:
                            self.effects.append(Ghost(v, cell_center(c, r), 0.35))
                self.effects.append(FloatText(f"{t('rows_cleared')} +{gained}",
                                              cell_center(COLS / 2 - 0.5, rows[0]), ACCENT, 26))
            elif kind == "gameover":
                audio.stop_music()
                audio.play("gameover")
                self._record("gameover")
        if changed:
            self._refresh_glow()

    # ----- drawing -----
    def draw(self, surf):
        self.app.background.draw(surf)
        ox = oy = 0
        if self.shake > 0:
            ox = int(self.rng.uniform(-6, 6) * self.shake / 0.35)
            oy = int(self.rng.uniform(-4, 4) * self.shake / 0.35)
        self._draw_card(surf)
        self._draw_right(surf)
        field = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._draw_field(field)
        surf.blit(field, (ox, oy))
        if self.paused:
            self._draw_pause(surf)
        if self.game.over:
            self._draw_over(surf)

    def _draw_field(self, surf):
        g = self.game
        frame = pygame.Rect(FIELD_X - 8, FIELD_Y - 8, FIELD_W + 16, FIELD_H + 16)
        art.panel(surf, frame, FIELD_BG, (90, 140, 230), radius=14, alpha=240)
        for c in range(1, COLS):
            x = FIELD_X + c * CELL
            pygame.draw.line(surf, GRID_LINE, (x, FIELD_Y), (x, FIELD_Y + FIELD_H))
        for r in range(1, ROWS):
            y = FIELD_Y + r * CELL
            pygame.draw.line(surf, GRID_LINE, (FIELD_X, y), (FIELD_X + FIELD_W, y))
        if self.danger > 0:
            pulse = 0.5 + 0.5 * math.sin(self.time * 8)
            warn = pygame.Surface((FIELD_W, CELL), pygame.SRCALPHA)
            warn.fill((255, 60, 60, int(90 * self.danger * pulse)))
            surf.blit(warn, (FIELD_X, FIELD_Y))
        board = g.board
        # Glow behind atoms that are on the way to the target
        if self.glow:
            k = 0.5 + 0.5 * math.sin(self.time * 4)
            for c, r in self.glow:
                cx, cy = cell_center(c, r)
                gl = pygame.Surface((CELL + 16, CELL + 16), pygame.SRCALPHA)
                pygame.draw.circle(gl, (120, 255, 170, int(50 + 50 * k)), (CELL // 2 + 8, CELL // 2 + 8), CELL // 2 + 6)
                surf.blit(gl, (cx - CELL // 2 - 8, cy - CELL // 2 - 8))
        # Bonds between touching atoms
        for r in range(ROWS):
            for c in range(COLS):
                if not board.is_atom(c, r):
                    continue
                if c + 1 < COLS and board.is_atom(c + 1, r):
                    art.bond_rod(surf, cell_center(c, r), cell_center(c + 1, r), 1, 7)
                if r + 1 < ROWS and board.is_atom(c, r + 1):
                    art.bond_rod(surf, cell_center(c, r), cell_center(c, r + 1), 1, 7)
        for r in range(ROWS):
            for c in range(COLS):
                v = board.grid[r][c]
                if v is None:
                    continue
                img = art.rubble(CELL) if v == RUBBLE else art.atom(v, CELL)
                if self.game.over and self.over_time * ROWS * 1.5 > ROWS - r:
                    img = img.copy()
                    img.fill((90, 90, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(img, (FIELD_X + c * CELL, FIELD_Y + r * CELL))
        if not g.over:
            p = g.current
            gy = g.ghost_y()
            for x, y, el in p.cells(p.x, gy):
                if y >= 0:
                    cx, cy = cell_center(x, y)
                    pygame.draw.circle(surf, (*ELEMENT_COLORS[el], 120), (cx, cy), CELL // 2 - 4, 3)
            self._draw_piece(surf, p.cells(), lambda c, r: cell_center(c, r))
        for rect, color, life, m in self.flashes:
            fl = pygame.Surface(rect.size, pygame.SRCALPHA)
            fl.fill((*color, int(160 * life / m)))
            surf.blit(fl, rect)
        for e in self.effects:
            e.draw(surf)
        if self.banner:
            title, sub, life = self.banner
            k = min(1.0, life / 0.4, (2.4 - life) / 0.2 + 0.3)
            y = FIELD_Y + FIELD_H * 0.33
            box = pygame.Rect(0, 0, FIELD_W + 40, 104)
            box.center = (FIELD_X + FIELD_W // 2, y)
            b = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(b, (10, 20, 50, int(210 * k)), b.get_rect(), border_radius=18)
            pygame.draw.rect(b, (*GOLD, int(255 * k)), b.get_rect(), 3, border_radius=18)
            surf.blit(b, box)
            fs = 34 if art.font(34).size(title)[0] < box.w - 30 else 26
            art.text(surf, title, fs, GOLD, (box.centerx, box.top + 10), "midtop", outline=(40, 30, 0))
            art.text(surf, f"{sub}  ·  {t('faster')}", 24, TEXT, (box.centerx, box.bottom - 12), "midbottom")

    def _draw_piece(self, surf, cells, to_screen, size=CELL):
        coords = {(c, r): el for c, r, el in cells}
        for (c, r), el in coords.items():
            for dc, dr in ((1, 0), (0, 1)):
                if (c + dc, r + dr) in coords:
                    art.bond_rod(surf, to_screen(c, r), to_screen(c + dc, r + dr), 1, max(4, size // 6))
        for (c, r), el in coords.items():
            if r < 0 and to_screen is cell_center:
                continue
            img = art.atom(el, size)
            surf.blit(img, img.get_rect(center=to_screen(c, r)))

    def _draw_card(self, surf):
        g = self.game
        mol = g.target
        tier = g.tier
        x, y, w, h = LEFT_PANEL
        slide = (1 - self.card_anim) ** 3
        x -= int(slide * 420)
        art.panel(surf, (x, y, w, h))
        header = t("target") if tier == 1 else (t("target_name_only") if tier == 2 else t("target_picture"))
        art.text(surf, header, 22, ACCENT, (x + w // 2, y + 16), "midtop")
        badge = pygame.Rect(0, 0, 110, 30)
        badge.topright = (x + w - 16, y + 50)
        pic_rect = pygame.Rect(x + 20, y + 56, w - 40, 250)
        if tier == 1:
            inner = pygame.Surface(pic_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(inner, (8, 14, 36, 230), inner.get_rect(), border_radius=16)
            surf.blit(inner, pic_rect)
            pygame.draw.rect(surf, (70, 100, 180), pic_rect, 2, border_radius=16)
            bob = math.sin(self.time * 2) * 4
            img = art.structure(mol, (pic_rect.w - 30, pic_rect.h - 70))
            surf.blit(img, img.get_rect(center=(pic_rect.centerx, pic_rect.centery - 24 + bob)))
            small = art.picture(mol.id, (100, 80))
            surf.blit(small, (pic_rect.right - 108, pic_rect.bottom - 88))
        else:
            img = art.picture(mol.id, pic_rect.size)
            surf.blit(img, pic_rect)
            pygame.draw.rect(surf, (200, 220, 255), pic_rect, 3, border_radius=28)
        yy = pic_rect.bottom + 14
        if tier <= 2:
            name = pick(mol.name)
            fs = 30 if art.font(30).size(name)[0] < w - 30 else 24
            art.text(surf, name, fs, TEXT, (x + w // 2, yy), "midtop")
            yy += 44
        if tier == 1:
            f = art.formula_surface(mol.parts, 58, GOLD)
            surf.blit(f, f.get_rect(midtop=(x + w // 2, yy)))
            yy += f.get_height() + 6
            # Recipe: the atoms needed, as chips
            chips = []
            for el, n in mol.parts:
                chips.append((el, n))
            chip_w = 104
            total = len(chips) * chip_w + (len(chips) - 1) * 10
            cx = x + (w - total) // 2
            for el, n in chips:
                r = pygame.Rect(cx, yy, chip_w, 48)
                pygame.draw.rect(surf, (30, 46, 92), r, border_radius=24)
                surf.blit(art.atom(el, 40), (r.left + 4, r.top + 4))
                art.text(surf, f"× {n}", 26, TEXT, (r.left + 50, r.centery), "midleft")
                cx += chip_w + 10
            yy += 60
            names = [t("recipe_item", n=n, name=pick(ELEMENT_NAMES[el])) for el, n in mol.parts]
            recipe = t("recipe", list=t("recipe_join").join(names))
            yy = art.text_block(surf, recipe, 20, GOOD, (x + w // 2, yy), w - 40, anchor="center")
            art.text_block(surf, pick(mol.fact), 18, TEXT_DIM, (x + w // 2, yy + 6), w - 40, anchor="center")
        elif tier == 2:
            q = art.font(64).render("? ? ?", True, GOLD)
            surf.blit(q, q.get_rect(midtop=(x + w // 2, yy + 10)))
            art.text_block(surf, t("guess_hint"), 20, TEXT_DIM, (x + w // 2, yy + 130), w - 50, anchor="center")
        else:
            bob = math.sin(self.time * 3) * 6
            q = art.font(110).render("?", True, GOLD)
            surf.blit(q, q.get_rect(midtop=(x + w // 2, yy + 10 + bob)))
            art.text_block(surf, t("guess_hint"), 20, TEXT_DIM, (x + w // 2, yy + 190), w - 50, anchor="center")

    def _draw_right(self, surf):
        g = self.game
        x, w = RIGHT_X, RIGHT_W
        # Next piece preview, top right
        box = pygame.Rect(x, 24, w, 176)
        art.panel(surf, box)
        art.text(surf, t("next"), 24, ACCENT, (box.centerx, box.top + 12), "midtop")
        p = g.next_piece
        xs = [dx for dx, _, _ in p.atoms]
        ys = [dy for _, dy, _ in p.atoms]
        mx = (max(xs) + min(xs)) / 2
        my = (max(ys) + min(ys)) / 2
        size = 44
        center = (box.centerx, box.top + 104)
        self._draw_piece(surf, [(dx, dy, el) for dx, dy, el in p.atoms],
                         lambda c, r: (center[0] + (c - mx) * size, center[1] + (r - my) * size), size)
        # Stats
        stats = pygame.Rect(x, box.bottom + 16, w, 300)
        art.panel(surf, stats)
        rows = [
            (t("score"), f"{g.score:,}", GOLD),
            (t("level"), str(g.level), TEXT),
            (t("fall_time"), t("seconds", n=f"{fall_time(g.level):.2f}"), TEXT),
            (t("molecules"), str(g.stats.molecules), GOOD),
            (t("errors"), str(g.stats.errors), BAD if g.stats.errors else TEXT),
            (t("rows"), str(g.stats.rows), TEXT),
        ]
        yy = stats.top + 16
        for label, value, color in rows:
            art.text(surf, label, 20, TEXT_DIM, (stats.left + 22, yy + 6))
            art.text(surf, value, 30 if label == t("score") else 26, color, (stats.right - 22, yy), "topright")
            yy += 46
        # Controls
        ctl = pygame.Rect(x, stats.bottom + 16, w, HEIGHT - 24 - stats.bottom - 16)
        art.panel(surf, ctl)
        art.text_block(surf, t("controls"), 17, TEXT_DIM, (ctl.left + 18, ctl.top + 14), w - 36, 6)
        music = "♪ M" if self.app.settings.get("music", True) else "♪ M ×"
        art.text(surf, music, 16, TEXT_DIM, (ctl.right - 16, ctl.bottom - 12), "bottomright")

    def _draw_pause(self, surf):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 20, 170))
        surf.blit(shade, (0, 0))
        art.text(surf, t("paused"), 64, TEXT, (FIELD_X + FIELD_W // 2, HEIGHT // 2 - 110), "center",
                 outline=(20, 40, 90))
        self.pause_menu.draw(surf)

    def _draw_over(self, surf):
        k = min(1.0, self.over_time / 1.2)
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 20, int(180 * k)))
        surf.blit(shade, (0, 0))
        if self.over_time < 1.0:
            return
        g = self.game
        box = pygame.Rect(0, 0, 560, 470)
        box.center = (WIDTH // 2, HEIGHT // 2 + 10)
        art.panel(surf, box, (24, 30, 70), BAD)
        art.text(surf, t("game_over"), 64, BAD, (box.centerx, box.top + 26), "midtop", outline=(60, 0, 0))
        art.text(surf, f"{t('final_score')}  {g.score:,}", 38, GOLD, (box.centerx, box.top + 120), "midtop")
        art.text(surf, t("reached", n=g.level), 26, TEXT, (box.centerx, box.top + 176), "midtop")
        art.text(surf, t("made_list", n=g.stats.molecules), 22, TEXT_DIM, (box.centerx, box.top + 214), "midtop")
        if self.new_best:
            pulse = 1 + 0.06 * math.sin(self.time * 6)
            art.text(surf, t("new_best"), int(28 * pulse), GOOD, (box.centerx, box.top + 250), "midtop")
        self.over_menu.draw(surf)
