"""The rules of ChemTris, with no drawing or sound, so tests and the robot can use them.

Atoms fall in small pieces. When a group of touching atoms contains every element
of the target molecule and has at least as many atoms as it (but no more than
two extra), the group is checked: an exact match is a new bond (it vanishes and the next level starts),
anything else is a wrong formula and turns into grey rubble. Full rows clear,
like in classic falling-block games. A block in the top row ends the game.
"""
import random
from collections import Counter

from .config import (COLS, ROWS, FALL_TIME_START, FALL_TIME_STEP, FALL_TIME_MIN, LOCK_DELAY,
                     LOCK_RESETS, SOFT_DROP_INTERVAL, ELEMENTS, FULL_HINT_LEVELS, NAME_HINT_LEVELS)
from .molecules import BY_ID, INTRO_ORDER, MOLECULES

RUBBLE = "#"
# A group up to this many atoms bigger than the target counts as an attempt at it
ATTEMPT_SLACK = 2

# Piece shapes by size, as (dx, dy) offsets around the first cell (the pivot)
SHAPES = {
    1: [[(0, 0)]],
    2: [[(0, 0), (1, 0)]],
    3: [[(0, 0), (-1, 0), (1, 0)], [(0, 0), (1, 0), (0, 1)]],
}


def fall_time(level):
    """Seconds a piece takes to fall the whole field: 1.25 s faster every 5 levels."""
    return max(FALL_TIME_MIN, FALL_TIME_START - FALL_TIME_STEP * (level - 1))


def drop_interval(level):
    return fall_time(level) / ROWS


def hint_tier(level):
    """1 = full diagram and recipe, 2 = picture and name, 3 = picture only."""
    if level <= FULL_HINT_LEVELS:
        return 1
    if level <= NAME_HINT_LEVELS:
        return 2
    return 3


class Piece:
    def __init__(self, atoms, x=COLS // 2 - 1, y=0):
        self.atoms = [list(a) for a in atoms]   # [dx, dy, element]
        self.x, self.y = x, y

    def cells(self, x=None, y=None, atoms=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(x + dx, y + dy, el) for dx, dy, el in (atoms or self.atoms)]

    def rotated(self, direction=1):
        if direction > 0:
            return [[-dy, dx, el] for dx, dy, el in self.atoms]
        return [[dy, -dx, el] for dx, dy, el in self.atoms]

    def copy(self):
        return Piece(self.atoms, self.x, self.y)

    @property
    def elements(self):
        return [el for _, _, el in self.atoms]


class Board:
    def __init__(self, cols=COLS, rows=ROWS):
        self.cols, self.rows = cols, rows
        self.grid = [[None] * cols for _ in range(rows)]

    def copy(self):
        b = Board(self.cols, self.rows)
        b.grid = [row[:] for row in self.grid]
        return b

    def get(self, c, r):
        return self.grid[r][c]

    def free(self, c, r):
        return 0 <= c < self.cols and r < self.rows and (r < 0 or self.grid[r][c] is None)

    def fits(self, cells):
        return all(self.free(c, r) for c, r, _ in cells)

    def place(self, cells):
        for c, r, el in cells:
            if 0 <= r < self.rows:
                self.grid[r][c] = el

    def neighbours(self, c, r):
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < self.cols and 0 <= nr < self.rows:
                yield nc, nr

    def is_atom(self, c, r):
        v = self.grid[r][c]
        return v is not None and v != RUBBLE

    def group(self, c, r):
        """All atoms touching (c, r), directly or through other atoms."""
        if not self.is_atom(c, r):
            return set()
        seen = {(c, r)}
        stack = [(c, r)]
        while stack:
            cc, rr = stack.pop()
            for n in self.neighbours(cc, rr):
                if n not in seen and self.is_atom(*n):
                    seen.add(n)
                    stack.append(n)
        return seen

    def groups_touching(self, cells):
        groups, seen = [], set()
        for c, r in cells:
            if (c, r) in seen or not (0 <= r < self.rows) or not self.is_atom(c, r):
                continue
            g = self.group(c, r)
            seen |= g
            groups.append(g)
        return groups

    def all_groups(self):
        return self.groups_touching([(c, r) for r in range(self.rows) for c in range(self.cols)])

    def counts(self, cells):
        return Counter(self.grid[r][c] for c, r in cells)

    def remove(self, cells):
        for c, r in cells:
            self.grid[r][c] = None

    def gravity(self):
        """Every block falls straight down to fill gaps. Returns True if anything moved."""
        moved = False
        for c in range(self.cols):
            column = [self.grid[r][c] for r in range(self.rows) if self.grid[r][c] is not None]
            new = [None] * (self.rows - len(column)) + column
            for r in range(self.rows):
                if self.grid[r][c] != new[r]:
                    moved = True
                self.grid[r][c] = new[r]
        return moved

    def full_rows(self):
        return [r for r in range(self.rows) if all(v is not None for v in self.grid[r])]

    def clear_rows(self, rows):
        keep = [row for r, row in enumerate(self.grid) if r not in rows]
        self.grid = [[None] * self.cols for _ in rows] + keep

    def height(self):
        for r in range(self.rows):
            if any(v is not None for v in self.grid[r]):
                return self.rows - r
        return 0

    def top_out(self):
        return any(v is not None for v in self.grid[0])


def judge(counts, target):
    """'match', 'wrong' or None (still building) for a group of atoms."""
    if not all(el in counts for el in target.counts):
        return None
    total = sum(counts.values())
    if total < target.size or total > target.size + ATTEMPT_SLACK:
        return None     # still building, or a big clump of spare atoms that is not an attempt
    return "match" if counts == target.counts else "wrong"


def decoy_share(level):
    return min(0.4, 0.15 + 0.01 * (level - 1))


class PieceFactory:
    """Deals pieces from a bag that always holds enough atoms to build the target."""

    def __init__(self, rng):
        self.rng = rng
        self.bag = []

    def refill(self, target, level):
        rng = self.rng
        pieces = []
        for _ in range(2):
            atoms = [el for el, n in target.parts for _ in range(n)]
            rng.shuffle(atoms)
            biggest = max(1, min(3, len(atoms) - 1))
            while atoms:
                size = rng.randint(1, min(biggest, len(atoms)))
                pieces.append(atoms[:size])
                atoms = atoms[size:]
        decoys = [e for e in ELEMENTS if e not in target.counts]
        n_decoys = max(1, round(len(pieces) * decoy_share(level) / (1 - decoy_share(level))))
        for _ in range(n_decoys):
            size = rng.choice((1, 1, 2, 2, 3))
            pieces.append([rng.choice(decoys) for _ in range(size)])
        rng.shuffle(pieces)
        self.bag = pieces

    def next(self, target, level):
        if not self.bag:
            self.refill(target, level)
        elements = self.bag.pop()
        shape = self.rng.choice(SHAPES[len(elements)])
        piece = Piece([(dx, dy, el) for (dx, dy), el in zip(shape, elements)])
        for _ in range(self.rng.randint(0, 3)):
            piece.atoms = piece.rotated()
        # Spawn with nothing above the top row
        top = min(dy for _, dy, _ in piece.atoms)
        piece.y = -top
        return piece


class Stats:
    def __init__(self):
        self.molecules = 0
        self.errors = 0
        self.rows = 0
        self.pieces = 0
        self.seconds = 0.0
        self.built = Counter()        # molecule id -> times built
        self.wrong = Counter()        # molecule id -> wrong formulas
        self.best_times = {}          # molecule id -> fastest seconds
        self.error_log = []           # [(level, molecule id, wrong formula)]


class Game:
    def __init__(self, seed=None, start_level=1):
        self.rng = random.Random(seed)
        self.board = Board()
        self.level = start_level
        self.score = 0
        self.stats = Stats()
        self.factory = PieceFactory(self.rng)
        self.recent = []
        self.target = self._pick_target()
        self.target_time = 0.0
        self.current = self.factory.next(self.target, self.level)
        self.next_piece = self.factory.next(self.target, self.level)
        self.fall_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.soft = False
        self.over = False
        self.events = []

    # ----- targets -----
    def _pick_target(self):
        if self.level <= len(INTRO_ORDER):
            mol = BY_ID[INTRO_ORDER[self.level - 1]]
        else:
            choices = [m for m in MOLECULES if m.id not in self.recent[-4:]]
            mol = self.rng.choice(choices)
        self.recent.append(mol.id)
        return mol

    @property
    def tier(self):
        return hint_tier(self.level)

    # ----- player actions -----
    def _try(self, atoms=None, dx=0, dy=0):
        p = self.current
        atoms = atoms or p.atoms
        if self.board.fits(p.cells(p.x + dx, p.y + dy, atoms)):
            p.atoms, p.x, p.y = [list(a) for a in atoms], p.x + dx, p.y + dy
            return True
        return False

    def _grounded(self):
        p = self.current
        return not self.board.fits(p.cells(p.x, p.y + 1))

    def _moved(self):
        if self._grounded() and self.lock_resets < LOCK_RESETS:
            self.lock_timer = 0.0
            self.lock_resets += 1

    def move(self, dx):
        if self.over:
            return False
        if self._try(dx=dx):
            self._moved()
            return True
        return False

    def rotate(self, direction=1):
        if self.over:
            return False
        atoms = self.current.rotated(direction)
        for kick_x, kick_y in ((0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)):
            if self._try(atoms, kick_x, kick_y):
                self._moved()
                return True
        return False

    def hard_drop(self):
        if self.over:
            return
        rows = 0
        while self._try(dy=1):
            rows += 1
        self.score += rows * 2
        self.events.append(("drop", rows))
        self._lock()

    def ghost_y(self):
        p = self.current
        y = p.y
        while self.board.fits(p.cells(p.x, y + 1)):
            y += 1
        return y

    # ----- time -----
    def update(self, dt):
        if self.over:
            return
        self.stats.seconds += dt
        self.target_time += dt
        interval = min(drop_interval(self.level), SOFT_DROP_INTERVAL) if self.soft else drop_interval(self.level)
        if self._grounded():
            self.lock_timer += dt
            if self.lock_timer >= LOCK_DELAY:
                self._lock()
            return
        self.fall_timer += dt
        while self.fall_timer >= interval and not self.over:
            self.fall_timer -= interval
            if self._try(dy=1):
                if self.soft:
                    self.score += 1
            else:
                break

    # ----- locking and the chemistry -----
    def _lock(self):
        p = self.current
        cells = p.cells()
        self.board.place(cells)
        self.stats.pieces += 1
        self.events.append(("lock", [(c, r, el) for c, r, el in cells]))
        self._resolve([(c, r) for c, r, _ in cells])
        if self.board.top_out() or any(r < 0 for _, r, _ in cells):
            self._game_over()
            return
        self.current = self.next_piece
        self.next_piece = self.factory.next(self.target, self.level)
        self.fall_timer = self.lock_timer = 0.0
        self.lock_resets = 0
        if not self.board.fits(self.current.cells()):
            self._game_over()

    def _resolve(self, cells):
        target = self.target
        built = None
        for group in self.board.groups_touching(cells):
            counts = self.board.counts(group)
            verdict = judge(counts, target)
            if verdict == "match" and built is None:
                built = group
            elif verdict is not None:
                self._wrong(group, counts)
        if built:
            self._build(built)
        rows = self.board.full_rows()
        if rows:
            snapshot = {r: self.board.grid[r][:] for r in rows}
            self.board.clear_rows(rows)
            n = len(rows)
            gained = (0, 100, 300, 500, 800)[min(n, 4)] * self.level + max(0, n - 4) * 400 * self.level
            self.score += gained
            self.stats.rows += n
            self.events.append(("rows", rows, snapshot, gained))

    def _wrong(self, group, counts):
        from .molecules import formula_of
        made = formula_of(counts)
        for c, r in group:
            self.board.grid[r][c] = RUBBLE
        self.stats.errors += 1
        self.stats.wrong[self.target.id] += 1
        self.stats.error_log.append((self.level, self.target.id, made))
        self.events.append(("wrong", sorted(group), made))

    def _build(self, group):
        mol = self.target
        atoms = [(c, r, self.board.grid[r][c]) for c, r in sorted(group)]
        # The reaction also blasts away the rubble right next to the new molecule
        blasted = {n for c, r in group for n in self.board.neighbours(c, r)
                   if n not in group and self.board.grid[n[1]][n[0]] is not None}
        self.board.remove(group)
        self.board.remove(blasted)
        self.board.gravity()
        gained = 100 * mol.size * self.level + 25 * len(blasted) * self.level
        self.score += gained
        st = self.stats
        st.molecules += 1
        st.built[mol.id] += 1
        if mol.id not in st.best_times or self.target_time < st.best_times[mol.id]:
            st.best_times[mol.id] = self.target_time
        self.events.append(("built", mol, atoms, sorted(blasted), gained, self.target_time))
        self.level += 1
        self.target = self._pick_target()
        self.target_time = 0.0
        # Keep the piece shown in the preview, but deal the rest for the new target
        self.factory.bag = []
        self.events.append(("level", self.level, self.target))

    def _game_over(self):
        self.over = True
        self.events.append(("gameover",))

    def take_events(self):
        events, self.events = self.events, []
        return events
