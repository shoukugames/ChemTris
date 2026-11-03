# Reporting a bug in ChemTris

Thank you for helping make ChemTris better! A good bug report lets us find and
fix the problem quickly.

**Where to send it:** email **info@shoukugames.org** with the subject
`ChemTris bug: <short summary>`, or open an issue on the project's repository.

## Before you report

1. Check you have the latest version (the version number is on the title screen
   and in **Credits**).
2. Try to make the problem happen a second time and note the exact steps.

## Copy this template

```
ChemTris version:      (e.g. v0.1.0, from the Credits screen)
Operating system:      (e.g. Windows 11, Ubuntu 24.04, Debian 12)
How installed:         (.exe / .deb / from source)
Language setting:      (English / 日本語)
Level when it happened:

What happened:

What I expected to happen:

Steps to make it happen again:
1.
2.
3.

How often:             (every time / sometimes / once)
```

## Helpful extras

- **Screenshot or video** of the problem.
- **Crash log:** if the game closes unexpectedly it writes `crash.log` to its
  data folder. Please attach it.
  - Windows: `%APPDATA%\ChemTris\crash.log`
  - Linux: `~/.local/share/chemtris/crash.log`
- **Progress file**, if the bug is about the For Parents screen:
  `progress.json` in the same folder. (It contains only scores, levels and
  molecule names, no personal information.)
- **From source:** run `python3 run_game.py --windowed` in a terminal and copy
  any error text it prints.

## Known limitations

- Speed stops increasing at a fall time of 1 second (around level 61). Levels
  keep going forever after that.
- No sound on a computer without a working audio device; the game still runs.

---

# バグの報告（日本語）

ChemTris の改善にご協力いただきありがとうございます。

**送り先:** **info@shoukugames.org** まで、件名を
`ChemTris bug: <内容の要約>` としてメールしてください。

上の英語のテンプレートをコピーして、バージョン（クレジット画面に表示）、OS、
起きたこと、期待していたこと、再現手順を書いてください。ゲームが突然終了した場合は、
データフォルダーの `crash.log` を添付していただけると助かります。

- Windows: `%APPDATA%\ChemTris\crash.log`
- Linux: `~/.local/share/chemtris/crash.log`
