"""Web entry point for pygbag (https://pygame-web.github.io): ChemTris in the browser.

Build:  pygbag --build .     (writes build/web/: index.html + chemtris.apk)
The desktop game still starts with run_game.py; nothing here changes it.
"""
import asyncio

import pygame  # noqa: F401  (must be imported here so pygbag loads pygame)

from chemtris.app import App


async def main():
    await App().run_web()


asyncio.run(main())
