"""Window, main loop, command line and the build smoke test."""
import argparse
import os
import sys
import time
import traceback

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from . import WEB, __version__, storage  # noqa: E402
from .art import Background  # noqa: E402
from .audio import Audio  # noqa: E402
from .config import FPS, HEIGHT, TITLE, WIDTH  # noqa: E402
from .i18n import resource, set_language  # noqa: E402


class App:
    def __init__(self, fullscreen=None):
        # Open the audio device in the format the synthesised sounds are made in (22050 Hz mono).
        # Without this, pygame.init() opens it at 44100 Hz stereo first and every sound plays 4x fast.
        from .audio import RATE
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(f"{TITLE} v{__version__}")
        self.settings = storage.load_settings()
        if fullscreen is not None:
            self.settings["fullscreen"] = fullscreen
        set_language(self.settings.get("language", "en"))
        try:
            icon = pygame.image.load(resource("assets", "icon.png"))
            pygame.display.set_icon(icon)
        except (pygame.error, FileNotFoundError):
            pass
        self.screen = self._open_window()
        self.clock = pygame.time.Clock()
        self.audio = Audio(self.settings)
        self.background = Background()
        self.scene = None
        self.running = True
        # On-screen buttons: on for touch screens, or as soon as a finger touches the game.
        from .touch import has_touch_screen
        self.touch = WEB and has_touch_screen()

    def _open_window(self):
        flags = pygame.SCALED | pygame.RESIZABLE
        if self.settings.get("fullscreen"):
            flags |= pygame.FULLSCREEN
        try:
            return pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except pygame.error:
            return pygame.display.set_mode((WIDTH, HEIGHT))

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings.get("fullscreen")
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            self.screen = self._open_window()

    def switch(self, scene):
        self.scene = scene

    def dispatch(self, event):
        if event.type == pygame.FINGERDOWN:
            self.touch = True
        if event.type == pygame.QUIT:
            self.running = WEB  # in a browser there is nothing to quit to
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.toggle_fullscreen()
            storage.save_settings(self.settings)
        elif self.scene:
            self.scene.handle(event)

    def step(self, dt):
        self.background.update(dt)
        self.audio.update(dt)
        self.scene.update(dt)
        self.scene.draw(self.screen)

    def frame(self):
        dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            self.dispatch(event)
        self.step(dt)
        pygame.display.flip()

    def _start(self):
        from .scenes import TitleScene
        if self.scene is None:
            self.switch(TitleScene(self))

    def _finish(self):
        if hasattr(self.scene, "leave"):
            self.scene.leave()
        storage.save_settings(self.settings)
        pygame.quit()

    def run(self):
        self._start()
        while self.running:
            self.frame()
        self._finish()

    async def run_web(self):
        """Browser main loop: hands control back to the page after every frame."""
        import asyncio
        self._start()
        while True:  # a web page has no "quit"; closing the tab ends the game
            self.running = True
            self.frame()
            await asyncio.sleep(0)


def _smoke_test(path):
    """Visit every screen in both languages and let the robot play for a while.

    The build scripts run this inside the finished package to prove that fonts,
    sound and graphics all work there. A windowed .exe has no console, so the
    result goes to a file.
    """
    from .autoplay import Autoplayer
    from .i18n import ENGLISH, JAPANESE, STRINGS, font
    from .molecules import ELEMENT_NAMES, MOLECULES
    from .play import PlayScene
    from .scenes import CreditsScene, HowToScene, ParentsScene, SettingsScene, TitleScene
    started = time.time()
    app = App(fullscreen=False)
    screens = (TitleScene, HowToScene, ParentsScene, SettingsScene, CreditsScene)
    for lang in (ENGLISH, JAPANESE):
        set_language(lang)
        for scene_type in screens:
            app.switch(scene_type(app))
            for _ in range(3):
                app.step(1 / FPS)
    set_language(ENGLISH)
    bot = Autoplayer(0.05)
    scene = PlayScene(app, seed=7)
    app.switch(scene)
    for _ in range(FPS * 25):
        if scene.game.over:
            break
        bot.update(1 / FPS, scene.game)
        app.step(1 / FPS)
    built = scene.game.stats.molecules
    scene.leave()
    # Every picture card and later-level card must draw
    for level in (20, 40):
        s = PlayScene(app, start_level=level, seed=level)
        app.switch(s)
        app.step(1 / FPS)
        s.leave()
    progress = storage.load_progress()
    app.switch(ParentsScene(app))
    for tab in range(4):
        app.scene.tab = tab
        app.step(1 / FPS)
    japanese = "".join(pair[1] for pair in STRINGS.values())
    japanese += "".join(m.name[1] + m.fact[1] for m in MOLECULES) + "".join(n[1] for n in ELEMENT_NAMES.values())
    missing = sorted({c for c in japanese if ord(c) >= 0x2E80 and font(40).metrics(c)[0] is None})
    report = (f"OK version={__version__} molecules={built} level={scene.game.level} games={progress['games']} "
              f"audio={app.audio.enabled} japanese_chars={len(set(japanese))} "
              f"seconds={time.time() - started:.1f}\n")
    pygame.quit()
    if built <= 0:
        report = "FAIL the robot built no molecules\n"
    elif missing:
        report = f"FAIL Japanese characters missing from the font: {''.join(missing)}\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report)
    return 0 if report.startswith("OK") else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="chemtris", description=f"{TITLE}: build molecules from falling atoms")
    parser.add_argument("--version", action="version", version=f"{TITLE} {__version__}")
    parser.add_argument("--fullscreen", action="store_true", help="start in full screen")
    parser.add_argument("--windowed", action="store_true", help="start in a window")
    parser.add_argument("--level", type=int, metavar="N", help="start directly on level N (for practice)")
    parser.add_argument("--smoke-test", metavar="FILE", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.smoke_test:
            return _smoke_test(args.smoke_test)
        fullscreen = True if args.fullscreen else (False if args.windowed else None)
        app = App(fullscreen)
        if args.level:
            from .play import PlayScene
            app.switch(PlayScene(app, start_level=max(1, args.level)))
        app.run()
        return 0
    except Exception:
        report = traceback.format_exc()
        try:
            with open(os.path.join(storage.data_dir(), "crash.log"), "w", encoding="utf-8") as handle:
                handle.write(report)
        except OSError:
            pass
        print(report, file=sys.stderr)
        return 1
