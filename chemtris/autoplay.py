"""A robot player used by the tests, the screenshot tool and the build smoke test.

It tries every rotation and column for the current piece, scores the result and
plays the best one. It is not brilliant, but it builds molecules.
"""
from .game import RUBBLE, judge


def _score_board(board, cells, target):
    score = 0.0
    for group in board.groups_touching([(c, r) for c, r, _ in cells]):
        counts = board.counts(group)
        verdict = judge(counts, target)
        if verdict == "match":
            score += 10000
        elif verdict == "wrong":
            score -= 3000
        else:
            if not any(el in target.counts for el in counts):
                continue        # a clump of spare atoms is harmless
            useful = all(el in target.counts and counts[el] <= target.counts[el] for el in counts)
            score += 80 * len(group) if useful else -300
    heights = []
    holes = 0
    for c in range(board.cols):
        top = None
        for r in range(board.rows):
            if board.grid[r][c] is not None:
                if top is None:
                    top = r
            elif top is not None:
                holes += 1
        heights.append(0 if top is None else board.rows - top)
    score -= 6 * max(heights) + 1.5 * sum(heights) + 25 * holes
    score -= 4 * sum(abs(a - b) for a, b in zip(heights, heights[1:]))
    score += 200 * len(board.full_rows())
    score -= 10 * sum(1 for row in board.grid for v in row if v == RUBBLE)
    return score


def best_move(game):
    """(rotations, column) for the best landing spot of the current piece."""
    best, best_score = None, None
    piece = game.current
    atoms = piece.atoms
    for rotations in range(4):
        for x in range(-2, game.board.cols + 2):
            if not game.board.fits(piece.cells(x, piece.y, atoms)):
                continue
            y = piece.y
            while game.board.fits(piece.cells(x, y + 1, atoms)):
                y += 1
            cells = piece.cells(x, y, atoms)
            board = game.board.copy()
            board.place(cells)
            s = _score_board(board, cells, game.target)
            if best_score is None or s > best_score:
                best, best_score = (rotations, x), s
        atoms = [[-dy, dx, el] for dx, dy, el in atoms]
    return best


class Autoplayer:
    """Plays one move every `delay` seconds through the normal player actions."""

    def __init__(self, delay=0.15):
        self.delay = delay
        self.timer = 0.0

    def update(self, dt, game):
        if game.over:
            return
        self.timer += dt
        if self.timer < self.delay:
            return
        self.timer = 0.0
        play_one(game)


def play_one(game):
    move = best_move(game)
    if move is None:
        game.hard_drop()
        return
    rotations, x = move
    for _ in range(rotations):
        game.rotate(1)
    step = 1 if x > game.current.x else -1
    for _ in range(abs(x - game.current.x)):
        if not game.move(step):
            break
    game.hard_drop()
