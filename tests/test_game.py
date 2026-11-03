"""Rules of the game: matching, rubble, rows, speed and the piece bag."""
from collections import Counter

from chemtris.autoplay import play_one
from chemtris.config import COLS, ROWS
from chemtris.game import RUBBLE, Board, Game, PieceFactory, fall_time, hint_tier, judge
from chemtris.molecules import BY_ID, INTRO_ORDER, MOLECULES, formula_of


def water():
    return BY_ID["H2O"]


def test_judge_exact_wrong_and_building():
    w = water()
    assert judge(Counter({"H": 2, "O": 1}), w) == "match"
    assert judge(Counter({"H": 3, "O": 1}), w) == "wrong"
    assert judge(Counter({"H": 2, "O": 2}), w) == "wrong"
    assert judge(Counter({"H": 2, "O": 1, "C": 1}), w) == "wrong"
    assert judge(Counter({"H": 1, "O": 1}), w) is None          # still building
    assert judge(Counter({"H": 5}), w) is None                  # no oxygen yet
    assert judge(Counter({"H": 4, "O": 1, "C": 3}), w) is None  # big clump, not an attempt


def test_speed_gets_at_least_one_second_faster_every_five_levels():
    for level in range(1, 56):
        assert fall_time(level) - fall_time(level + 5) >= 1.0
    assert fall_time(1000) > 0


def test_hint_tiers():
    assert hint_tier(1) == 1 and hint_tier(17) == 1
    assert hint_tier(18) == 2 and hint_tier(30) == 3 and hint_tier(500) == 3


def test_building_water_clears_it_and_moves_to_next_level():
    g = Game(seed=1)
    assert g.target.id == "H2O" and g.level == 1
    b = g.board
    b.grid[ROWS - 1][0] = "H"
    b.grid[ROWS - 1][1] = "O"
    g._resolve([(0, ROWS - 1), (1, ROWS - 1)])
    assert g.level == 1                       # H-O is not water yet
    b.grid[ROWS - 1][2] = "H"
    g._resolve([(2, ROWS - 1)])
    assert g.level == 2 and g.target.id == INTRO_ORDER[1]
    assert all(v is None for v in b.grid[ROWS - 1][:3])
    assert g.stats.molecules == 1 and g.stats.built["H2O"] == 1


def test_wrong_formula_becomes_rubble_and_is_logged():
    g = Game(seed=1)
    b = g.board
    for c, el in enumerate("HOO"):
        b.grid[ROWS - 1][c] = el
    g._resolve([(2, ROWS - 1)])
    assert b.grid[ROWS - 1][:3] == [RUBBLE] * 3
    assert g.stats.errors == 1
    assert g.stats.error_log == [(1, "H2O", "HO2")]


def test_building_blasts_neighbouring_rubble():
    g = Game(seed=1)
    b = g.board
    b.grid[ROWS - 1][3] = RUBBLE
    b.grid[ROWS - 2][1] = RUBBLE
    b.grid[ROWS - 2][5] = RUBBLE
    for c, el in enumerate("HOH"):
        b.grid[ROWS - 1][c] = el
    g._resolve([(2, ROWS - 1)])
    assert b.grid[ROWS - 1][3] is None and b.grid[ROWS - 1][1] is None
    assert b.grid[ROWS - 1][5] == RUBBLE      # not touching, so it only fell


def test_full_row_clears():
    g = Game(seed=1)
    for c in range(COLS):
        g.board.grid[ROWS - 1][c] = RUBBLE
    g.board.grid[ROWS - 2][0] = "C"
    g._resolve([(0, ROWS - 1)])
    assert g.stats.rows == 1
    assert g.board.grid[ROWS - 1][0] == "C"


def test_reaching_the_top_is_game_over():
    g = Game(seed=1)
    for r in range(1, ROWS):
        for c in range(COLS):
            if c != 9:
                g.board.grid[r][c] = RUBBLE
    for _ in range(40):
        if g.over:
            break
        g.hard_drop()
    assert g.over


def test_bag_always_holds_the_target_atoms():
    import random
    for mol in MOLECULES:
        f = PieceFactory(random.Random(3))
        f.refill(mol, 10)
        atoms = Counter(el for piece in f.bag for el in piece)
        for el, n in mol.counts.items():
            assert atoms[el] >= n
        # No single piece is already the whole molecule
        assert all(Counter(piece) != mol.counts for piece in f.bag)


def test_rotation_and_walls():
    g = Game(seed=2)
    for _ in range(12):
        g.move(-1)
    assert min(c for c, _, _ in g.current.cells()) == 0
    for _ in range(4):
        g.rotate(1)
    assert g.board.fits(g.current.cells())


def test_levels_are_unlimited_and_targets_vary():
    g = Game(seed=4, start_level=200)
    assert g.target in MOLECULES
    seen = set()
    for _ in range(30):
        seen.add(g._pick_target().id)
    assert len(seen) > 8


def test_robot_progresses():
    g = Game(seed=5)
    for _ in range(300):
        if g.over:
            break
        play_one(g)
    assert g.level > 10


def test_formula_text():
    assert formula_of(Counter({"H": 3, "O": 1})) == "H3O"
    assert formula_of(Counter({"C": 1, "H": 4})) == "CH4"
    assert [m.formula for m in MOLECULES][:3] == ["H2", "O2", "H2O"]


def test_board_gravity():
    b = Board()
    b.grid[0][0] = "H"
    b.grid[5][0] = "O"
    assert b.gravity()
    assert b.grid[ROWS - 1][0] == "O" and b.grid[ROWS - 2][0] == "H"
