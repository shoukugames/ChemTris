#!/usr/bin/env python3
"""Render every screen to PNG files (default: build/screenshots/) without opening a window."""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("CHEMTRIS_DATA", tempfile.mkdtemp(prefix="chemtris-shots-"))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from chemtris.app import App  # noqa: E402
from chemtris.autoplay import play_one  # noqa: E402
from chemtris.i18n import ENGLISH, JAPANESE, set_language  # noqa: E402
from chemtris.play import PlayScene  # noqa: E402
from chemtris.scenes import CreditsScene, HowToScene, ParentsScene, SettingsScene, TitleScene  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "screenshots")
os.makedirs(out, exist_ok=True)
app = App(fullscreen=False)


def shot(name, frames=30):
    for _ in range(frames):
        app.step(1 / 60)
    pygame.image.save(app.screen, os.path.join(out, name + ".png"))


def played(level, seed, moves):
    scene = PlayScene(app, start_level=level, seed=seed)
    app.switch(scene)
    for _ in range(moves):
        if scene.game.over:
            break
        play_one(scene.game)
        scene._events()
    return scene


# Some history so the parents screens have something to show
for seed in range(6):
    s = played(1, seed, 60 + seed * 25)
    s.game.stats.seconds = 120 + seed * 60
    s.leave()
for lang in (ENGLISH, JAPANESE):
    set_language(lang)
    app.switch(TitleScene(app))
    shot(f"{lang}-title", 50)
    s = played(1, 3, 6)
    s.banner = None
    s.effects = []
    shot(f"{lang}-play-level1", 40)
    s = played(19, 5, 10)
    shot(f"{lang}-play-level19", 50)
    s = played(34, 8, 14)
    shot(f"{lang}-play-level34", 50)
    for name, scene in (("howto", HowToScene), ("credits", CreditsScene), ("settings", SettingsScene)):
        app.switch(scene(app))
        shot(f"{lang}-{name}")
    for tab in range(4):
        p = ParentsScene(app)
        p.tab = tab
        app.switch(p)
        shot(f"{lang}-parents-{tab}", 5)
    s = played(1, 2, 20)
    from chemtris.game import RUBBLE
    for r in range(3, 16):
        for c in range(10):
            if (r + c) % 4:
                s.game.board.grid[r][c] = RUBBLE
    s.game.board.grid[0][4] = "O"
    s.game._game_over()
    s._events()
    shot(f"{lang}-gameover", 150)
set_language(ENGLISH)
from chemtris import art  # noqa: E402
from chemtris.molecules import MOLECULES  # noqa: E402
sheet = pygame.Surface((6 * 210, 3 * 200))
sheet.fill((20, 30, 60))
for i, m in enumerate(MOLECULES):
    x, y = (i % 6) * 210, (i // 6) * 200
    sheet.blit(art.picture(m.id, (200, 160)), (x + 5, y + 5))
    art.text(sheet, m.formula, 22, (255, 255, 255), (x + 105, y + 170), "midtop")
pygame.image.save(sheet, os.path.join(out, "pictures.png"))
sheet.fill((20, 30, 60))
for i, m in enumerate(MOLECULES):
    x, y = (i % 6) * 210, (i // 6) * 200
    sheet.blit(art.structure(m, (200, 160)), (x + 5, y + 5))
    art.text(sheet, m.formula, 22, (255, 255, 255), (x + 105, y + 170), "midtop")
pygame.image.save(sheet, os.path.join(out, "structures.png"))
print("Saved screenshots to", out)
