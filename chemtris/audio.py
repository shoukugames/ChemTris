"""All sound is synthesised in code: instruments, effects and a little music sequencer.

The background music is public-domain classical pieces arranged as note lists:
Mozart, Grieg, Rossini, Beethoven and Chopin. Notes are rendered once, in a
background thread, and then triggered on reserved mixer channels in time with
the game loop. If there is no audio device the game simply stays silent.
"""
import array
import math
import os
import random
import threading

import pygame

from . import WEB

RATE = 22050
TWO_PI = 2 * math.pi
TABLE = 2048
MUSIC_CHANNELS = 5

_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    """'C#4' -> 61"""
    pitch = _NOTE[name[0]]
    i = 1
    while i < len(name) and name[i] in "#b":
        pitch += 1 if name[i] == "#" else -1
        i += 1
    return pitch + 12 * (int(name[i:]) + 1)


def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _table(fn):
    return [fn(i / TABLE) for i in range(TABLE)]


TABLES = {
    "sine": _table(lambda p: math.sin(TWO_PI * p)),
    "tri": _table(lambda p: 4 * abs(p - 0.5) - 1),
    "pulse": _table(lambda p: 0.8 if p < 0.25 else -0.27),
    "saw": _table(lambda p: 2 * p - 1),
    "organ": _table(lambda p: 0.6 * math.sin(TWO_PI * p) + 0.3 * math.sin(2 * TWO_PI * p)
                    + 0.15 * math.sin(3 * TWO_PI * p)),
    "piano": _table(lambda p: 0.7 * math.sin(TWO_PI * p) + 0.25 * math.sin(2 * TWO_PI * p)
                    + 0.1 * math.sin(4 * TWO_PI * p)),
}

# wave, attack, decay rate, sustain level, release fraction, lowpass (0..1), volume
INSTRUMENTS = {
    "lead": ("pulse", 0.006, 5.0, 0.55, 0.15, 0.35, 0.42),
    "flute": ("organ", 0.02, 2.0, 0.75, 0.2, 0.6, 0.5),
    "strings": ("saw", 0.08, 1.0, 0.8, 0.25, 0.12, 0.22),
    "bass": ("tri", 0.004, 6.0, 0.35, 0.2, 0.8, 0.6),
    "pluck": ("tri", 0.002, 12.0, 0.0, 0.1, 0.7, 0.55),
    "piano": ("piano", 0.003, 3.5, 0.25, 0.25, 0.7, 0.55),
    "bell": ("sine", 0.002, 5.0, 0.15, 0.3, 1.0, 0.55),
}


def render_note(inst, m, seconds):
    wave, attack, decay, sustain, release, lp, vol = INSTRUMENTS[inst]
    tab = TABLES[wave]
    n = max(1, int(seconds * RATE))
    step = freq(m) * TABLE / RATE
    out = [0.0] * n
    phase = 0.0
    att_n = max(1, int(attack * RATE))
    rel_start = int(n * (1 - release))
    last = 0.0
    exp = math.exp
    for i in range(n):
        if i < att_n:
            env = i / att_n
        else:
            t = (i - att_n) / RATE
            env = sustain + (1 - sustain) * exp(-decay * t)
        if i > rel_start:
            env *= (n - i) / (n - rel_start)
        v = tab[int(phase) & (TABLE - 1)]
        phase += step
        last += lp * (v - last)
        out[i] = last * env * vol
    return out


def noise(seconds, vol=0.5, cutoff=0.5, decay=8.0, seed=1):
    rng = random.Random(seed)
    n = int(seconds * RATE)
    out = [0.0] * n
    last = 0.0
    for i in range(n):
        last += cutoff * (rng.uniform(-1, 1) - last)
        out[i] = last * math.exp(-decay * i / RATE) * vol
    return out


def sweep(seconds, f0, f1, wave="sine", vol=0.5, decay=4.0):
    tab = TABLES[wave]
    n = int(seconds * RATE)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / n
        f = f0 * (f1 / f0) ** t
        phase += f * TABLE / RATE
        out[i] = tab[int(phase) & (TABLE - 1)] * math.exp(-decay * t) * vol * (1 - t ** 4)
    return out


def mix_into(base, part, offset=0):
    end = offset + len(part)
    if end > len(base):
        base.extend([0.0] * (end - len(base)))
    for i, v in enumerate(part):
        base[offset + i] += v
    return base


def to_sound(samples, gain=1.0):
    data = array.array("h", (max(-32767, min(32767, int(v * gain * 32767))) for v in samples))
    return pygame.mixer.Sound(buffer=data.tobytes())


# ----- songs -----
class Song:
    def __init__(self, name, bpm, spb, tracks, tempo_scales=True):
        self.name, self.bpm, self.spb = name, bpm, spb
        self.tempo_scales = tempo_scales
        self.tracks = []          # [(instrument, volume, [(start_step, midi or 'X', steps)])]
        self.length = 0
        for inst, vol, notes in tracks:
            events, pos = [], 0
            for tok in notes.replace("|", " ").split():
                name, _, steps = tok.partition(":")
                steps = float(steps) if steps else 1.0
                if name != "R":
                    events.append((pos, "X" if name == "X" else midi(name), steps))
                pos += steps
            self.tracks.append((inst, vol, events))
            self.length = max(self.length, pos)
        self.sounds = {}
        self.ready = False

    def step_seconds(self):
        return 60.0 / self.bpm / self.spb

    def render(self, drum_sounds):
        sec = self.step_seconds()
        for inst, _, events in self.tracks:
            for _, m, steps in events:
                key = (inst, m, steps)
                if key in self.sounds:
                    continue
                if m == "X":
                    self.sounds[key] = drum_sounds[inst]
                else:
                    self.sounds[key] = to_sound(render_note(inst, m, min(1.6, max(0.08, steps * sec * 0.95))))
        self.ready = True


def _repeat(s, n):
    return " ".join([s] * n)


NACHTMUSIK = Song("nachtmusik", 124, 2, [
    ("flute", 0.9, "G4:2 R D4 G4:2 R D4 | G4 D4 G4 B4 D5:4 | C5:2 R A4 C5:2 R A4 | C5 A4 F#4 A4 D4:4 |"
                   "G4:2 G4:2 B4 A4 G4 G4 | F#4:2 F#4:2 A4 G4 F#4 F#4 | E4:2 E4:2 G4 F#4 E4 E4 |"
                   "D4 F#4 A4 C5 B4:2 G4:2"),
    ("bass", 0.8, "G2:2 D3:2 G2:2 D3:2 | G2:2 D3:2 G2:2 D3:2 | D3:2 A2:2 D3:2 A2:2 | D3:2 A2:2 D3:2 A2:2 |"
                  "G2:2 D3:2 G2:2 D3:2 | D3:2 A2:2 D3:2 A2:2 | C3:2 G2:2 C3:2 G2:2 | D3:2 A2:2 G2:4"),
    ("strings", 0.7, "B3:8 B3:8 A3:8 F#3:8 B3:8 A3:8 G3:8 F#3:4 G3:4"),
])

_HALL_A = ("B3 C#4 D4 E4 F#4 D4 F#4:2 | F4 C#4 F4:2 E4 C4 E4:2 | B3 C#4 D4 E4 F#4 D4 F#4 B4 |"
           "A4 F#4 D4 F#4 A4:4")
_HALL_B = ("F#4 G#4 A#4 B4 C#5 A#4 C#5:2 | D5 A#4 D5:2 C#5 A#4 C#5:2 | F#4 G#4 A#4 B4 C#5 A#4 C#5 F#5 |"
           "E5 C#5 A#4 C#5 E5:4")
_HALL_BASS_A = "B2:2 F#2:2 B2:2 F#2:2 C#3:2 G#2:2 C3:2 G2:2 B2:2 F#2:2 B2:2 F#2:2 F#2:2 C#3:2 F#2:2 F#2:2"
_HALL_BASS_B = "F#2:2 C#3:2 F#2:2 C#3:2 D3:2 A#2:2 C#3:2 G#2:2 F#2:2 C#3:2 F#2:2 C#3:2 C#3:2 G#2:2 F#2:2 F#2:2"
MOUNTAIN_KING = Song("mountain_king", 104, 2, [
    ("lead", 0.8, " ".join([_HALL_A, _HALL_A, _HALL_B, _HALL_B])),
    ("pluck", 1.0, " ".join([_HALL_BASS_A, _HALL_BASS_A, _HALL_BASS_B, _HALL_BASS_B])),
    ("kick", 0.6, _repeat("X:2 R:2", 32)),
    ("hat", 0.4, _repeat("R:2 X:2", 32)),
])

_TELL_1 = "E4 E4 E4:2 E4 E4 E4:2 E4 E4 A4:2 B4:2 C#5:2"
_TELL_2 = "E4 E4 E4:2 E4 E4 A4:2 C#5 C#5 B4:2 G#4:2 E4:2"
_TELL_4 = "E4 E4 A4:2 E4 E4 C#5:2 B4:2 G#4:2 A4:4"
_TELL_B1 = "A2:2 E3:2 A2:2 E3:2 A2:2 E3:2 A2:2 E3:2"
_TELL_B2 = "A2:2 E3:2 A2:2 E3:2 E2:2 B2:2 E2:2 B2:2"
_TELL_B4 = "A2:2 E3:2 A2:2 E3:2 E2:2 B2:2 A2:4"
WILLIAM_TELL = Song("william_tell", 150, 4, [
    ("lead", 0.8, " ".join([_TELL_1, _TELL_2, _TELL_1, _TELL_4])),
    ("bass", 0.9, " ".join([_TELL_B1, _TELL_B2, _TELL_B1, _TELL_B4])),
    ("kick", 0.6, _repeat("X:4", 16)),
    ("hat", 0.35, _repeat("R:2 X:2", 16)),
])

TURKISH_MARCH = Song("turkish_march", 128, 4, [
    ("piano", 0.9, "B4 A4 G#4 A4 C5:4 | D5 C5 B4 C5 E5:4 | F5 E5 D#5 E5 B5 A5 G#5 A5 | B5 A5 G#5 A5 C6:4 |"
                   "A5:2 B5:2 C6:2 B5:2 | A5:2 G#5:2 A5:2 E5:2 | F5:2 D5:2 C5:2 B4:2 | A4:6 R:2"),
    ("bass", 0.8, "A2:2 C3:2 E3:2 C3:2 | A2:2 C3:2 E3:2 C3:2 | A2:2 C3:2 E3:2 C3:2 | A2:2 C3:2 E3:2 C3:2 |"
                  "A2:2 E3:2 A2:2 E3:2 | E2:2 B2:2 A2:2 E3:2 | D3:2 A2:2 E2:2 G#2:2 | A2:4 R:4"),
    ("kick", 0.55, _repeat("X:4", 16)),
    ("hat", 0.3, _repeat("R:2 X:2", 16)),
])

FUR_ELISE = Song("fur_elise", 72, 4, [
    ("piano", 1.0, "E5 D#5 E5 B4 D5 C5 | A4:2 R C4 E4 A4 | B4:2 R E4 G#4 B4 | C5:2 R E4 E5 D#5 |"
                   "E5 D#5 E5 B4 D5 C5 | A4:2 R C4 E4 A4 | B4:2 R E4 C5 B4 | A4:4 E5 D#5"),
    ("piano", 0.6, "R:6 | A2 E3 A3 R:3 | E2 E3 G#3 R:3 | A2 E3 A3 R:3 | R:6 | A2 E3 A3 R:3 |"
                   "E2 E3 G#3 R:3 | A2 E3 A3 R:3"),
], tempo_scales=False)

GAME_SONGS = [MOUNTAIN_KING, WILLIAM_TELL, TURKISH_MARCH]
ALL_SONGS = [NACHTMUSIK, MOUNTAIN_KING, FUR_ELISE, WILLIAM_TELL, TURKISH_MARCH]


def game_song(level):
    """A new piece every 5 levels."""
    return GAME_SONGS[((level - 1) // 5) % len(GAME_SONGS)]


# ----- browser build -----
# A browser runs the game loop far less evenly than a PC, so notes triggered from the game loop
# stumble, and making the sounds in Python there takes many seconds. The browser build therefore
# gets every effect and every song (as one seamless loop) pre-made as .ogg files in web_sounds/,
# written by tools/build_web.py with the functions below.
WEB_SOUNDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_sounds")


def drum_samples():
    return {"kick": sweep(0.14, 150, 45, "sine", 0.9, 5), "hat": noise(0.05, 0.35, 0.9, 60, seed=4)}


def web_tempo(song, tempo):
    """The browser plays pre-made loops at tenth steps of tempo (1.0, 1.1 ... 1.6)."""
    return math.floor(tempo * 10 + 1e-6) / 10 if song.tempo_scales else 1.0


def web_song_file(song, tempo):
    return f"song_{song.name}_{round(web_tempo(song, tempo) * 10)}"


def web_songs():
    """Every (song, tempo) the game can ask for, as (file name, song, tempo)."""
    combos = {(NACHTMUSIK, 1.0), (FUR_ELISE, 1.0)}
    for level in range(1, 200):
        song = game_song(level)
        combos.add((song, web_tempo(song, 1.0 + min(0.6, (level - 1) * 0.02))))
    return sorted((web_song_file(s, t), s, t) for s, t in combos)


def render_loop(song, tempo=1.0):
    """The whole song as one seamless loop, exactly as Audio.update() would sequence it: each track
    on its own channel, a new note cutting off the one before, notes ringing over the loop's end
    into its start."""
    sec = song.step_seconds() / tempo
    n = int(round(song.length * sec * RATE))
    out = [0.0] * n
    drums = drum_samples()
    for inst, vol, events in song.tracks:
        gain = vol * 0.55
        for j, (start, m, steps) in enumerate(events):
            if m == "X":
                part = drums[inst]
            else:
                part = render_note(inst, m, min(1.6, max(0.08, steps * song.step_seconds() * 0.95)))
            nxt = events[j + 1][0] if j + 1 < len(events) else events[0][0] + song.length
            begin = int(round(start * sec * RATE))
            stop = int(round(nxt * sec * RATE))
            for k, v in enumerate(part[:max(0, stop - begin)]):
                out[(begin + k) % n] += max(-1.0, min(1.0, v)) * gain
    return out


def jingle(notes, step, inst="bell", bass=None):
    out = []
    pos = 0
    for tok in notes.split():
        name, _, steps = tok.partition(":")
        steps = float(steps or 1)
        if name != "R":
            mix_into(out, render_note(inst, midi(name), steps * step * 1.4), int(pos * step * RATE))
        pos += steps
    if bass:
        pos = 0
        for tok in bass.split():
            name, _, steps = tok.partition(":")
            steps = float(steps or 1)
            if name != "R":
                mix_into(out, render_note("strings", midi(name), steps * step), int(pos * step * RATE))
            pos += steps
    return out


def _fx(samples, gain=1.0):
    return samples, gain


def effect_samples():
    """Every sound effect as name -> (samples, gain)."""
    s = {}
    s["move"] = _fx(sweep(0.035, 900, 820, "pulse", 0.18, 6))
    s["rotate"] = _fx(sweep(0.07, 520, 880, "tri", 0.35, 3))
    s["lock"] = _fx(mix_into(sweep(0.12, 170, 80, "sine", 0.6, 5), noise(0.08, 0.25, 0.3, 30)))
    s["drop"] = _fx(mix_into(sweep(0.18, 220, 60, "sine", 0.8, 4), noise(0.12, 0.4, 0.4, 20, 2)))
    built = []
    for i, n in enumerate(("C5", "E5", "G5", "C6", "E6")):
        mix_into(built, render_note("bell", midi(n), 0.5), int(i * 0.06 * RATE))
    s["built"] = _fx(built, 0.9)
    s["wrong"] = _fx(mix_into(sweep(0.4, 240, 120, "saw", 0.35, 2), sweep(0.4, 254, 127, "saw", 0.3, 2)))
    rows = sweep(0.45, 300, 1400, "tri", 0.35, 1.5)
    s["rows"] = _fx(mix_into(rows, noise(0.45, 0.25, 0.8, 5, 3)))
    s["menu"] = _fx(sweep(0.05, 700, 760, "tri", 0.35, 4))
    s["select"] = _fx(mix_into(render_note("bell", midi("E5"), 0.12),
                      render_note("bell", midi("A5"), 0.2), int(0.07 * RATE)))
    # Beethoven, Ode to Joy, for every new level
    s["level"] = _fx(jingle("E5 E5 F5 G5 G5 F5 E5 D5 C5 C5 D5 E5 E5:1.5 D5:0.5 D5:2", 0.13,
                     bass="C4:4 G3:4 A3:4 G3:2 G3:2"), 0.85)
    # Chopin, Funeral March, for game over
    s["gameover"] = _fx(jingle("A#3:3 A#3:2 A#3:1 A#3:3 C#4:2 C4:1 C4:2 A#3:1 A#3:2 A3:1 A#3:5",
                       0.17, "piano", bass="A#2:9 F2:6 A#2:8"), 0.9)
    return s


WEB_EFFECTS = ("move", "rotate", "lock", "drop", "built", "wrong", "rows", "menu", "select", "level", "gameover")


class Audio:
    def __init__(self, settings):
        global RATE  # the browser may change it (see below)
        self.settings = settings
        self.enabled = False
        self.sfx = {}
        self.song = None
        self.pos = 0.0
        self.tempo = 1.0
        self.next_event = []
        self.duck = 0.0
        self._web_key = None      # browser: the loop now playing, its channel and file cache
        self._web_channel = None
        self._web_flip = 0
        self._web_loops = {}
        try:
            pygame.mixer.init(RATE, -16, 1, 512)
            if WEB:
                # Browsers mix at their own rate (48000 Hz): make the sounds at that rate so they keep
                # their pitch and speed (the synth reads RATE as it runs).
                RATE = pygame.mixer.get_init()[0]
            pygame.mixer.set_num_channels(20)
            pygame.mixer.set_reserved(MUSIC_CHANNELS)
            self.channels = [pygame.mixer.Channel(i) for i in range(MUSIC_CHANNELS)]
            self.enabled = True
        except pygame.error:
            return
        self._make_effects()
        self.pending = []
        if not WEB:  # the browser plays pre-made loops instead (see _web_update)
            self.thread = threading.Thread(target=self._render_songs, daemon=True)
            self.thread.start()

    def _drums(self):
        if not hasattr(self, "_drum_sounds"):
            self._drum_sounds = {name: to_sound(samples) for name, samples in drum_samples().items()}
        return self._drum_sounds

    def _render_songs(self):
        for song in ALL_SONGS:
            try:
                song.render(self._drums())
            except pygame.error:
                return

    def _render_next(self):
        if self.song in self.pending:  # the song that should be playing now goes first
            self.pending.remove(self.song)
            song = self.song
        else:
            song = self.pending.pop(0)
        try:
            song.render(self._drums())
        except pygame.error:
            self.pending = []

    def _make_effects(self):
        if WEB:
            self._load_web_effects()
            return
        for name, (samples, gain) in effect_samples().items():
            self.sfx[name] = to_sound(samples, gain)

    def _load_web_effects(self):
        for name in WEB_EFFECTS:
            try:
                self.sfx[name] = pygame.mixer.Sound(os.path.join(WEB_SOUNDS, f"fx_{name}.ogg"))
            except (pygame.error, FileNotFoundError):
                pass

    # ----- effects -----
    def play(self, name):
        if self.enabled and self.settings.get("sound", True) and name in self.sfx:
            self.sfx[name].play()
            if name in ("level", "gameover"):
                self.duck = self.sfx[name].get_length()
                if WEB:
                    if self._web_channel:
                        self._web_channel.pause()
                    return
                for ch in self.channels:
                    ch.fadeout(150)

    # ----- music -----
    def music(self, song, tempo=1.0):
        if song is not self.song:
            self.song = song
            self.pos = 0.0
            self.next_event = [0] * len(song.tracks) if song else []
            if self.enabled:
                for ch in self.channels:
                    ch.fadeout(200)
        self.tempo = tempo if (song and song.tempo_scales) else 1.0

    def stop_music(self):
        self.music(None)

    def update(self, dt):
        if WEB:
            self._web_update(dt)
            return
        if self.pending:
            self._render_next()
        if not self.enabled or self.song is None or not self.song.ready:
            return
        if self.duck > 0:
            self.duck -= dt
            return
        if not self.settings.get("music", True):
            return
        song = self.song
        self.pos += dt / song.step_seconds() * self.tempo
        if self.pos >= song.length:
            self.pos -= song.length
            self.next_event = [0] * len(song.tracks)
        for i, (inst, vol, events) in enumerate(song.tracks):
            idx = self.next_event[i]
            while idx < len(events) and events[idx][0] <= self.pos:
                start, m, steps = events[idx]
                if self.pos - start < 2:  # skip notes we are far too late for
                    ch = self.channels[i % MUSIC_CHANNELS]
                    ch.set_volume(vol * 0.55)
                    ch.play(song.sounds[(inst, m, steps)])
                idx += 1
            self.next_event[i] = idx

    def _web_update(self, dt):
        """Browser: loop the current song's pre-made file, crossfading when the song or tempo changes."""
        if not self.enabled:
            return
        if self.duck > 0:
            self.duck -= dt
            if self.duck <= 0 and self._web_channel:
                self._web_channel.unpause()
            return
        song = self.song if self.settings.get("music", True) else None
        key = web_song_file(song, self.tempo) if song else None
        if key == self._web_key:
            return
        if self._web_channel:
            self._web_channel.fadeout(300)
        self._web_key, self._web_channel = key, None
        if key is None:
            return
        if key not in self._web_loops:
            try:
                self._web_loops[key] = pygame.mixer.Sound(os.path.join(WEB_SOUNDS, key + ".ogg"))
            except (pygame.error, FileNotFoundError):
                self._web_loops[key] = None
        loop = self._web_loops[key]
        if loop:
            self._web_channel = self.channels[self._web_flip]
            self._web_flip ^= 1
            self._web_channel.set_volume(1.0)
            self._web_channel.play(loop, loops=-1, fade_ms=300)

    def set_music_enabled(self, on):
        self.settings["music"] = on
        if not on and self.enabled:
            for ch in self.channels:
                ch.stop()
