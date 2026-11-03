"""Every molecule in the game, with its formula, names, fun facts and a 2D structure.

`parts` lists the formula in the order chemists write it. `atoms` and `bonds`
draw the ball-and-stick diagram: positions are in bond lengths, bond order 0
means an ionic bond (drawn dashed).
"""
from collections import Counter


class Molecule:
    def __init__(self, mid, parts, name, fact, atoms, bonds):
        self.id = mid
        self.parts = parts
        self.counts = Counter({el: n for el, n in parts})
        self.size = sum(n for _, n in parts)
        self.name = name          # (english, japanese)
        self.fact = fact          # (english, japanese)
        self.atoms = atoms        # [(element, x, y)]
        self.bonds = bonds        # [(i, j, order)]

    @property
    def formula(self):
        return "".join(el + (str(n) if n > 1 else "") for el, n in self.parts)

    def __repr__(self):
        return f"Molecule({self.formula})"


def formula_of(counts):
    """A readable formula for any group of atoms, in Hill order (C, H, then A-Z)."""
    order = sorted(counts, key=lambda e: (e != "C", e != "H", e))
    if "C" not in counts:
        order = sorted(counts, key=lambda e: e)
    return "".join(el + (str(counts[el]) if counts[el] > 1 else "") for el in order if counts[el])


ELEMENT_NAMES = {
    "H": ("Hydrogen", "水素"),
    "O": ("Oxygen", "酸素"),
    "C": ("Carbon", "炭素"),
    "N": ("Nitrogen", "窒素"),
    "Na": ("Sodium", "ナトリウム"),
    "Cl": ("Chlorine", "塩素"),
    "S": ("Sulfur", "硫黄"),
}

MOLECULES = [
    Molecule("H2", [("H", 2)], ("Hydrogen gas", "水素ガス"),
             ("The lightest gas in the universe. Rockets burn it as fuel!",
              "宇宙でいちばん軽い気体。ロケットの燃料にも使われるよ！"),
             [("H", -0.6, 0), ("H", 0.6, 0)], [(0, 1, 1)]),
    Molecule("O2", [("O", 2)], ("Oxygen", "酸素"),
             ("Trees and plants make it. You breathe it in every second!",
              "木や植物が作り出す気体。わたしたちは毎秒これを吸っているよ！"),
             [("O", -0.6, 0), ("O", 0.6, 0)], [(0, 1, 2)]),
    Molecule("H2O", [("H", 2), ("O", 1)], ("Water", "水"),
             ("Two hydrogens hold hands with one oxygen. It covers most of Earth!",
              "水素2つと酸素1つが手をつなぐ。地球の大部分をおおっているよ！"),
             [("O", 0, -0.3), ("H", -0.85, 0.35), ("H", 0.85, 0.35)], [(0, 1, 1), (0, 2, 1)]),
    Molecule("HCl", [("H", 1), ("Cl", 1)], ("Hydrochloric acid", "塩酸（塩化水素）"),
             ("A strong acid. Your stomach uses it to break down food!",
              "強い酸。胃の中で食べ物を消化するのに使われているよ！"),
             [("H", -0.6, 0), ("Cl", 0.65, 0)], [(0, 1, 1)]),
    Molecule("NaCl", [("Na", 1), ("Cl", 1)], ("Table salt", "食塩（塩化ナトリウム）"),
             ("Sodium and chlorine are dangerous alone, but together they make salt!",
              "ナトリウムも塩素も単体では危険。でも合わさると塩になるよ！"),
             [("Na", -0.7, 0), ("Cl", 0.7, 0)], [(0, 1, 0)]),
    Molecule("CO", [("C", 1), ("O", 1)], ("Carbon monoxide", "一酸化炭素"),
             ("An invisible gas in car exhaust. That's why alarms watch for it!",
              "車の排気ガスにふくまれる見えない気体。警報器で見張っているよ！"),
             [("C", -0.6, 0), ("O", 0.6, 0)], [(0, 1, 3)]),
    Molecule("CO2", [("C", 1), ("O", 2)], ("Carbon dioxide", "二酸化炭素"),
             ("The fizzy bubbles in soda. You breathe it out!",
              "炭酸飲料のシュワシュワの泡。わたしたちが吐く息にもふくまれるよ！"),
             [("O", -1.1, 0), ("C", 0, 0), ("O", 1.1, 0)], [(0, 1, 2), (1, 2, 2)]),
    Molecule("N2", [("N", 2)], ("Nitrogen", "窒素"),
             ("Almost 80% of the air is nitrogen. Liquid nitrogen is super cold!",
              "空気の約80%は窒素。液体窒素はとっても冷たいよ！"),
             [("N", -0.6, 0), ("N", 0.6, 0)], [(0, 1, 3)]),
    Molecule("Cl2", [("Cl", 2)], ("Chlorine", "塩素"),
             ("It keeps swimming pools clean and gives them that pool smell.",
              "プールの水をきれいに保つ。プールのにおいのもとだよ。"),
             [("Cl", -0.65, 0), ("Cl", 0.65, 0)], [(0, 1, 1)]),
    Molecule("O3", [("O", 3)], ("Ozone", "オゾン"),
             ("Three oxygens make a shield high in the sky against sunburn rays.",
              "酸素3つでできた分子。空の高いところで紫外線から地球を守っているよ。"),
             [("O", 0, -0.35), ("O", -0.9, 0.3), ("O", 0.9, 0.3)], [(0, 1, 2), (0, 2, 1)]),
    Molecule("NH3", [("N", 1), ("H", 3)], ("Ammonia", "アンモニア"),
             ("A strong-smelling gas used in window cleaners and plant food.",
              "においの強い気体。ガラス用洗剤や肥料に使われているよ。"),
             [("N", 0, -0.25), ("H", -0.9, 0.3), ("H", 0.9, 0.3), ("H", 0, 0.85)],
             [(0, 1, 1), (0, 2, 1), (0, 3, 1)]),
    Molecule("H2S", [("H", 2), ("S", 1)], ("Hydrogen sulfide", "硫化水素"),
             ("The stinky smell of rotten eggs! Phew!",
              "くさった卵のようなにおいのもと！くさ〜い！"),
             [("S", 0, -0.3), ("H", -0.9, 0.4), ("H", 0.9, 0.4)], [(0, 1, 1), (0, 2, 1)]),
    Molecule("N2O", [("N", 2), ("O", 1)], ("Laughing gas", "笑気ガス（亜酸化窒素）"),
             ("Dentists use it to help patients relax. It can make people giggle!",
              "歯医者さんでリラックスするために使われる。笑いたくなることも！"),
             [("N", -1.15, 0), ("N", 0, 0), ("O", 1.15, 0)], [(0, 1, 3), (1, 2, 1)]),
    Molecule("NaOH", [("Na", 1), ("O", 1), ("H", 1)], ("Sodium hydroxide", "水酸化ナトリウム"),
             ("Also called lye. It is used to make bars of soap.",
              "苛性ソーダとも呼ばれる。せっけん作りに使われるよ。"),
             [("Na", -1.2, 0), ("O", 0.1, 0), ("H", 1.1, 0)], [(0, 1, 0), (1, 2, 1)]),
    Molecule("CH4", [("C", 1), ("H", 4)], ("Methane", "メタン"),
             ("Natural gas for stoves. Cows burp out lots of it, too!",
              "コンロで燃やす天然ガス。牛のゲップにもたくさんふくまれるよ！"),
             [("C", 0, 0), ("H", 0, -1), ("H", 1, 0), ("H", 0, 1), ("H", -1, 0)],
             [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1)]),
    Molecule("H2O2", [("H", 2), ("O", 2)], ("Hydrogen peroxide", "過酸化水素"),
             ("Water with one extra oxygen. It cleans cuts and bubbles up!",
              "水に酸素が1つ多い分子。傷の消毒に使うと泡が出るよ！"),
             [("H", -1.45, 0.55), ("O", -0.5, 0), ("O", 0.5, 0), ("H", 1.45, -0.55)],
             [(0, 1, 1), (1, 2, 1), (2, 3, 1)]),
    Molecule("C2H4", [("C", 2), ("H", 4)], ("Ethylene", "エチレン"),
             ("Bananas give off this gas, and it makes fruit ripen faster!",
              "バナナが出す気体。くだものを早く熟させるよ！"),
             [("C", -0.6, 0), ("C", 0.6, 0), ("H", -1.3, -0.75), ("H", -1.3, 0.75),
              ("H", 1.3, -0.75), ("H", 1.3, 0.75)],
             [(0, 1, 2), (0, 2, 1), (0, 3, 1), (1, 4, 1), (1, 5, 1)]),
]

BY_ID = {m.id: m for m in MOLECULES}
# The order levels introduce them: small and familiar first
INTRO_ORDER = ["H2O", "H2", "O2", "NaCl", "HCl", "CO2", "CO", "N2", "Cl2", "O3",
               "NH3", "H2S", "N2O", "NaOH", "CH4", "H2O2", "C2H4"]
assert sorted(INTRO_ORDER) == sorted(BY_ID)
