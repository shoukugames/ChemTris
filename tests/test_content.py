"""Both languages are complete, every molecule has art, and progress saves."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from chemtris import art, storage  # noqa: E402
from chemtris.audio import ALL_SONGS  # noqa: E402
from chemtris.game import Game  # noqa: E402
from chemtris.i18n import STRINGS  # noqa: E402
from chemtris.molecules import ELEMENT_NAMES, MOLECULES  # noqa: E402


@pytest.fixture(autouse=True)
def display(tmp_path, monkeypatch):
    monkeypatch.setenv("CHEMTRIS_DATA", str(tmp_path))
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()


def test_every_string_has_english_and_japanese():
    for key, (en, ja) in STRINGS.items():
        assert en.strip() and ja.strip(), key
        assert en.count("{") == ja.count("{"), key


def test_every_molecule_is_complete():
    for m in MOLECULES:
        assert all(m.name) and all(m.fact)
        assert sorted(el for el, _, _ in m.atoms) == sorted(el for el, n in m.parts for _ in range(n))
        assert m.id in art.PICTURES
        assert art.picture(m.id, (200, 160)).get_size() == (200, 160)
        assert art.structure(m, (300, 200)).get_size() == (300, 200)
        for el in m.counts:
            assert el in ELEMENT_NAMES


def test_songs_line_up():
    for song in ALL_SONGS:
        assert song.length > 0
        for _, _, events in song.tracks:
            assert events and events[-1][0] < song.length


def test_progress_is_recorded_and_reset():
    g = Game(seed=1)
    g.score = 1234
    g.stats.molecules = 3
    g.stats.built["H2O"] = 3
    g.stats.wrong["H2O"] = 1
    g.stats.errors = 1
    g.stats.error_log.append((1, "H2O", "H3O"))
    g.stats.best_times["H2O"] = 12.5
    progress, best = storage.record_game(g)
    assert best and progress["high_score"] == 1234
    again = storage.load_progress()
    assert again["games"] == 1 and again["per_molecule"]["H2O"]["built"] == 3
    assert again["error_log"][0]["made"] == "H3O"
    storage.reset_progress()
    assert storage.load_progress()["games"] == 0


def test_settings_round_trip():
    s = storage.load_settings()
    s["language"] = "ja"
    storage.save_settings(s)
    assert storage.load_settings()["language"] == "ja"
