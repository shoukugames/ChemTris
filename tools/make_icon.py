#!/usr/bin/env python3
"""Draw the game icon from the game's own artwork: assets/icon.png and assets/icon.ico.

Run this only when the design changes. Needs Pillow for the .ico file.
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

from chemtris import art  # noqa: E402
from chemtris.molecules import BY_ID  # noqa: E402

pygame.init()
pygame.display.set_mode((16, 16))
SIZE = 512
canvas = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
back = art.gradient((SIZE, SIZE), (40, 70, 170), (10, 16, 50)).convert_alpha()
mask = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=110)
back.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
canvas.blit(back, (0, 0))
pygame.draw.rect(canvas, (110, 200, 255), canvas.get_rect().inflate(-8, -8), 8, border_radius=106)
# A stack of atom blocks along the bottom
for i, el in enumerate(("Cl", "C", "N", "S")):
    canvas.blit(art.atom(el, 96), (40 + i * 108, 380))
# The water molecule
water = art.structure(BY_ID["H2O"], (470, 330), max_unit=400)
canvas.blit(water, water.get_rect(center=(SIZE // 2, 205)))
path = os.path.join(ROOT, "assets", "icon.png")
pygame.image.save(canvas, path)
Image.open(path).save(os.path.join(ROOT, "assets", "icon.ico"),
                      sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Wrote assets/icon.png and assets/icon.ico")
