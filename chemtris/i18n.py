"""English and Japanese text, plus the font that draws both.

`t(key)` returns the string for the current language. The bundled M+ 1p font
covers Latin, kana and kanji, so one font serves every screen.
"""
import os
import sys

import pygame

ENGLISH, JAPANESE = "en", "ja"
_language = ENGLISH

STRINGS = {
    # Title
    "subtitle": ("Build molecules, atom by atom!", "原子を組み合わせて分子を作ろう！"),
    "play": ("Play", "あそぶ"),
    "how_to": ("How to Play", "あそびかた"),
    "parents": ("For Parents", "保護者の方へ"),
    "settings": ("Settings", "設定"),
    "credits": ("Credits", "クレジット"),
    "quit": ("Quit", "おわる"),
    "language": ("Language", "言語"),
    "menu_hint": ("Arrow keys or mouse to choose  ·  L: language", "矢印キーかマウスで選択  ·  L：言語切替"),
    "back": ("Back", "もどる"),
    "back_hint": ("Esc: back", "Esc：もどる"),
    # HUD
    "target": ("BUILD THIS MOLECULE", "この分子を作ろう"),
    "target_name_only": ("WHAT IS THE FORMULA?", "化学式はなに？"),
    "target_picture": ("WHAT MOLECULE IS THIS?", "これはなんの分子？"),
    "recipe": ("Connect {list} so they touch.", "{list}をくっつけよう。"),
    "recipe_join": (" and ", "と"),
    "recipe_item": ("{n} {name}", "{name}{n}つ"),
    "next": ("NEXT", "つぎ"),
    "score": ("SCORE", "スコア"),
    "level": ("LEVEL", "レベル"),
    "fall_time": ("FALL TIME", "落下時間"),
    "seconds": ("{n} s", "{n}秒"),
    "molecules": ("MOLECULES", "分子"),
    "errors": ("ERRORS", "まちがい"),
    "rows": ("ROWS", "ライン"),
    "controls": ("← → move   ↑ / X rotate   Z rotate back\n↓ soft drop   Space drop\nP pause   M music   F11 full screen",
                 "← → 移動   ↑ / X 回転   Z 逆回転\n↓ ゆっくり落下   スペース 一気に落下\nP 一時停止   M 音楽   F11 全画面"),
    "guess_hint": ("Think of the formula, then build it from the falling atoms!",
                   "化学式を思い出して、落ちてくる原子で作ろう！"),
    "built": ("{name} made!", "{name}ができた！"),
    "next_level": ("Level {n}", "レベル {n}"),
    "wrong": ("Not quite: that's {made}", "おしい！それは{made}"),
    "rows_cleared": ("Row clear!", "ラインクリア！"),
    "faster": ("Faster!", "スピードアップ！"),
    "paused": ("PAUSED", "一時停止"),
    "resume": ("Resume", "つづける"),
    "to_title": ("Quit to Title", "タイトルへ"),
    "game_over": ("GAME OVER", "ゲームオーバー"),
    "reached": ("You reached level {n}", "レベル {n} まで到達"),
    "new_best": ("New high score!", "ハイスコア更新！"),
    "play_again": ("Play Again", "もう一度"),
    "final_score": ("Score", "スコア"),
    "made_list": ("Molecules made: {n}", "作った分子：{n}"),
    # How to play
    "how_title": ("How to Play", "あそびかた"),
    "how_1": ("Atoms fall from the top. Move and turn them to stack them.",
              "原子が上から落ちてくるよ。動かしたり回したりして積み上げよう。"),
    "how_2": ("Put the right atoms next to each other to build the molecule on the left card.",
              "左のカードの分子になるように、原子をとなり同士にくっつけよう。"),
    "how_3": ("Exactly right? The molecule bursts, blasts nearby rubble, and the next level starts.",
              "ぴったり正解なら分子がはじけて、まわりのがれきも消え、次のレベルへ！"),
    "how_4": ("Too many or wrong atoms touching? It turns into grey rubble.",
              "原子が多すぎたり、ちがう原子がくっつくと灰色のがれきになるよ。"),
    "how_5": ("Fill a whole row to clear it. If blocks reach the top, the game is over.",
              "横一列をうめると消えるよ。ブロックがいちばん上まで届くとゲームオーバー。"),
    "how_6": ("Later levels show only a picture. You must know the formula yourself!",
              "レベルが進むと絵だけになるよ。化学式は自分で考えよう！"),
    "how_7": ("Every level the atoms fall faster.", "レベルが上がるたびに落ちるのが速くなるよ。"),
    "how_controls": ("Controls", "操作方法"),
    "atoms_title": ("The atoms", "原子のしゅるい"),
    # Settings
    "settings_title": ("Settings", "設定"),
    "music": ("Music", "音楽"),
    "sound": ("Sound effects", "効果音"),
    "fullscreen": ("Full screen", "フルスクリーン"),
    "on": ("On", "オン"),
    "off": ("Off", "オフ"),
    # Credits
    "credits_title": ("Credits", "クレジット"),
    "created_by": ("Created by", "制作"),
    "creators": ("Shawn Rapaz and Claude Code", "Shawn Rapaz と Claude Code"),
    "website": ("Website", "ウェブサイト"),
    "email": ("Email", "メール"),
    "version": ("Version", "バージョン"),
    "date": ("Date", "日付"),
    "music_credit": ("Music", "音楽"),
    "music_list": ("Mozart · Grieg · Rossini · Beethoven · Chopin\n(public domain, synthesised in the game)",
                   "モーツァルト · グリーグ · ロッシーニ · ベートーヴェン · ショパン\n（パブリックドメイン、ゲーム内で合成）"),
    "font_credit": ("Font", "フォント"),
    "license": ("License", "ライセンス"),
    # Parents
    "parents_title": ("For Parents", "保護者の方へ"),
    "tab_overview": ("Overview", "概要"),
    "tab_molecules": ("Molecules", "分子"),
    "tab_history": ("History", "履歴"),
    "tab_errors": ("Errors", "まちがい"),
    "high_score": ("High score", "ハイスコア"),
    "best_level": ("Best level", "最高レベル"),
    "games_played": ("Games played", "プレイ回数"),
    "play_time": ("Total play time", "合計プレイ時間"),
    "total_molecules": ("Molecules built", "作った分子"),
    "total_errors": ("Wrong formulas", "まちがえた化学式"),
    "accuracy": ("Accuracy", "正答率"),
    "total_rows": ("Rows cleared", "消したライン"),
    "score_chart": ("Score in recent games", "最近のゲームのスコア"),
    "col_molecule": ("Molecule", "分子"),
    "col_built": ("Built", "成功"),
    "col_errors": ("Errors", "まちがい"),
    "col_accuracy": ("Accuracy", "正答率"),
    "col_best": ("Fastest", "最速"),
    "col_date": ("Date", "日時"),
    "col_score": ("Score", "スコア"),
    "col_level": ("Level", "レベル"),
    "col_time": ("Time", "時間"),
    "col_target": ("Goal", "目標"),
    "col_made": ("Made instead", "作ったもの"),
    "no_data": ("No games played yet.", "まだプレイ記録がありません。"),
    "no_errors": ("No wrong formulas so far. Great work!", "まちがいはまだありません。すばらしい！"),
    "reset": ("Reset progress", "記録をリセット"),
    "reset_confirm": ("Click again to erase everything", "もう一度クリックで全て消去"),
    "reset_done": ("Progress erased", "記録を消去しました"),
    "parents_note": ("Progress is saved on this computer after every game.",
                     "記録はゲームのたびにこのコンピューターに保存されます。"),
    "tabs_hint": ("← → change tab  ·  Esc back", "← → タブ切替  ·  Esc もどる"),
    "minutes": ("{m} min", "{m}分"),
    "hours": ("{h} h {m} min", "{h}時間{m}分"),
}

LANGUAGE_NAMES = {ENGLISH: "EN", JAPANESE: "日本語"}


def set_language(lang):
    global _language
    _language = lang if lang in (ENGLISH, JAPANESE) else ENGLISH


def language():
    return _language


def t(key, **fmt):
    en, ja = STRINGS[key]
    text = ja if _language == JAPANESE else en
    return text.format(**fmt) if fmt else text


def pick(pair):
    """Choose from an (english, japanese) pair."""
    return pair[1] if _language == JAPANESE else pair[0]


# ----- fonts -----
def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return os.path.join(base, *parts)


FONT_PATH = resource("assets", "fonts", "MPLUS1p-Bold.ttf")
_fonts = {}


def font(size):
    f = _fonts.get(size)
    if f is None:
        try:
            f = pygame.font.Font(FONT_PATH, size)
        except (OSError, FileNotFoundError):
            f = pygame.font.Font(None, int(size * 1.3))
        _fonts[size] = f
    return f
