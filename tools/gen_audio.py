"""Procedural audio: every sound effect and music loop is synthesised here.

    python3 tools/gen_audio.py        (needs numpy: pip install numpy)

Writes assets/sfx/*.wav and assets/music/*.wav. All 22050 Hz mono 16-bit.
"""

import math
import os
import struct
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets"))
SR = 22050


# --------------------------------------------------------------------------- #
# primitives
# --------------------------------------------------------------------------- #
def _t(dur):
    return np.linspace(0, dur, int(SR * dur), endpoint=False)


def sine(freq, dur, vol=0.3):
    return vol * np.sin(2 * np.pi * freq * _t(dur))


def tri(freq, dur, vol=0.3):
    return vol * (2.0 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * _t(dur)))


def square(freq, dur, vol=0.2):
    return vol * np.sign(np.sin(2 * np.pi * freq * _t(dur)))


def saw(freq, dur, vol=0.2):
    x = _t(dur) * freq
    return vol * 2.0 * (x - np.floor(x + 0.5))


def noise(dur, vol=0.3, rng=None):
    rng = rng or np.random.default_rng(7)
    return vol * rng.uniform(-1, 1, int(SR * dur))


def env_ad(n, attack=0.01, decay=None, curve=3.0):
    """attack/decay envelope over n samples."""
    a = max(1, int(SR * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    if decay is not None:
        d = max(1, int(SR * decay))
        e = np.minimum(e, np.linspace(1, 0, n) ** curve)
    return e


def env_decay(n, curve=4.0):
    return np.linspace(1, 0, n) ** curve


def lowpass(x, cutoff):
    """one-pole low pass, cutoff in Hz"""
    rc = 1.0 / (2 * math.pi * cutoff)
    dt = 1.0 / SR
    a = dt / (rc + dt)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def lowpass_fast(x, cutoff):
    from scipy.signal import lfilter  # type: ignore
    rc = 1.0 / (2 * math.pi * cutoff)
    dt = 1.0 / SR
    a = dt / (rc + dt)
    return lfilter([a], [1, -(1 - a)], x)


def lp(x, cutoff):
    try:
        return lowpass_fast(x, cutoff)
    except Exception:
        return lowpass(x, cutoff)


def delay(x, times=(0.11, 0.19, 0.29), gains=(0.35, 0.24, 0.16)):
    out = x.copy()
    for tm, g in zip(times, gains):
        d = int(SR * tm)
        out[d:] += x[:-d] * g
    return out


def place(buf, sig, at):
    i = int(SR * at)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def norm(x, peak=0.85):
    m = np.max(np.abs(x))
    return x / m * peak if m > 1e-9 else x


def save(name, x, subdir="sfx", peak=0.85):
    path = os.path.join(OUT, subdir, name + ".wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = norm(np.clip(x, -1.0, 1.0), peak)
    data = (x * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("  %-22s %5.2f s  %6.1f KB" % (subdir + "/" + name + ".wav", len(x) / SR, os.path.getsize(path) / 1024))


# --------------------------------------------------------------------------- #
# sound effects
# --------------------------------------------------------------------------- #
def sfx_cast():
    rng = np.random.default_rng(11)
    n = int(SR * 0.42)
    x = rng.uniform(-1, 1, n) * 0.7
    # sweeping band by mixing filtered copies
    lo = lp(x, 900)
    hi = x - lp(x, 1400)
    t = np.linspace(0, 1, n)
    sweep = lo * (1 - t) + hi * t
    return sweep * env_decay(n, 2.2) * 0.9


def sfx_splash():
    rng = np.random.default_rng(3)
    n = int(SR * 0.65)
    x = rng.uniform(-1, 1, n)
    body = lp(x, 1800) * env_decay(n, 3.0)
    dlen = int(SR * 0.30)
    drop = sine(320, 0.30) * env_decay(dlen, 6.0) + sine(180, 0.30, 0.5) * env_decay(dlen, 5.0)
    out = body * 0.8
    out[: len(drop)] += drop * 0.6
    # droplets
    for i, at in enumerate((0.24, 0.33, 0.44)):
        d = int(SR * 0.05)
        place(out, sine(900 - i * 120, 0.05, 0.35) * env_decay(d, 4.0), at)
    return out


def sfx_reel():
    out = np.zeros(int(SR * 0.3))
    for i in range(7):
        d = int(SR * 0.02)
        tick = square(1500 + (i % 3) * 180, 0.02, 0.35) * env_decay(d, 3.0)
        place(out, tick, i * 0.038)
    return out


def sfx_bite():
    out = np.zeros(int(SR * 0.34))
    for i, (f, at) in enumerate(((880, 0.0), (1320, 0.12))):
        d = int(SR * 0.12)
        place(out, (sine(f, 0.12, 0.5) + sine(f * 2, 0.12, 0.18)) * env_decay(d, 4.0), at)
    return out


def sfx_catch():
    out = np.zeros(int(SR * 1.25))
    notes = (523.25, 659.25, 783.99, 1046.5, 1318.5)
    for i, f in enumerate(notes):
        d = int(SR * 0.3)
        sig = (tri(f, 0.3, 0.5) + sine(f * 2, 0.3, 0.12)) * env_ad(d, 0.006) * env_decay(d, 2.0)
        place(out, sig, i * 0.11)
    d = int(SR * 0.7)
    place(out, tri(notes[-1] * 1.5, 0.7, 0.3) * env_decay(d, 2.5), 0.55)
    return delay(out, (0.09, 0.18), (0.25, 0.14))


def sfx_coin():
    out = np.zeros(int(SR * 0.26))
    for i, f in enumerate((1180, 1560)):
        d = int(SR * 0.13)
        place(out, square(f, 0.13, 0.3) * env_decay(d, 3.0), i * 0.07)
    return out


def sfx_ui():
    d = int(SR * 0.07)
    return square(760, 0.07, 0.25) * env_decay(d, 4.0)


def sfx_error():
    d = int(SR * 0.24)
    return (square(180, 0.24, 0.3) + square(121, 0.24, 0.2)) * env_ad(d, 0.01) * env_decay(d, 2.0)


def sfx_sleep():
    out = np.zeros(int(SR * 1.4))
    for i, f in enumerate((523.25, 392.0, 329.63, 261.63)):
        d = int(SR * 0.4)
        place(out, tri(f, 0.4, 0.4) * env_ad(d, 0.02) * env_decay(d, 2.0), i * 0.24)
    return delay(out, (0.13, 0.26), (0.3, 0.18))


def sfx_upgrade():
    out = np.zeros(int(SR * 1.0))
    for i, f in enumerate((392, 523.25, 659.25, 880, 1174.66)):
        d = int(SR * 0.34)
        place(out, (saw(f, 0.34, 0.16) + sine(f * 2, 0.34, 0.1)) * env_ad(d, 0.008) * env_decay(d, 2.0), i * 0.1)
    return delay(out, (0.1, 0.21), (0.26, 0.14))


def sfx_step():
    rng = np.random.default_rng(21)
    d = int(SR * 0.07)
    return lp(rng.uniform(-1, 1, d), 700) * env_decay(d, 5.0) * 0.8


def sfx_thunder():
    rng = np.random.default_rng(5)
    n = int(SR * 1.8)
    x = rng.uniform(-1, 1, n)
    rumble = lp(x, 220) * env_ad(n, 0.05) * env_decay(n, 1.6)
    crack = lp(x, 3000) * env_decay(int(n), 9.0) * 0.5
    return rumble * 0.9 + crack * 0.3


def sfx_page():
    rng = np.random.default_rng(31)
    d = int(SR * 0.18)
    return lp(rng.uniform(-1, 1, d), 2600) * env_decay(d, 3.0) * 0.7


# --------------------------------------------------------------------------- #
# music
# --------------------------------------------------------------------------- #
BPM = 74.0
BEAT = 60.0 / BPM
BAR = BEAT * 4

# Am - F - C - G  (i  -  VI - III - VII)
PROG = [
    ("A2", ["A3", "C4", "E4"]),
    ("F2", ["F3", "A3", "C4"]),
    ("C3", ["C3", "E3", "G3"]),
    ("G2", ["G3", "B3", "D4"]),
]

NOTE_FREQ = {}
for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]):
    for octv in range(0, 8):
        midi = (octv + 1) * 12 + i
        NOTE_FREQ["%s%d" % (n, octv)] = 440.0 * (2 ** ((midi - 69) / 12.0))


def f(n):
    return NOTE_FREQ[n]


def pad_chord(notes, dur, vol=0.16):
    out = np.zeros(int(SR * dur))
    for n in notes:
        for det in (-3, 0, 4):
            freq = f(n) * (2 ** (det / 1200.0))
            out += tri(freq, dur, vol / 3.0)
    e = env_ad(len(out), 0.35) * env_decay(len(out), 1.2)
    return out * e


def pluck(note, dur, vol=0.22):
    n = int(SR * dur)
    x = (sine(f(note), dur, vol) + tri(f(note) * 2, dur, vol * 0.3) + saw(f(note) * 3, dur, vol * 0.1))
    return x * env_ad(n, 0.004) * env_decay(n, 3.5)


def bass_note(note, dur, vol=0.3):
    n = int(SR * dur)
    x = sine(f(note), dur, vol) + sine(f(note) / 2, dur, vol * 0.4) + tri(f(note), dur, vol * 0.15)
    return x * env_ad(n, 0.008) * env_decay(n, 1.8)


def tick(vol=0.14, hp=4000):
    rng = np.random.default_rng(99)
    d = int(SR * 0.05)
    x = rng.uniform(-1, 1, d)
    return (x - lp(x, hp)) * env_decay(d, 6.0) * vol


PENTA = ["A3", "C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5"]


def _loopify(x, xf=0.06):
    """crossfade the tail into the head so the loop is seamless"""
    n = int(SR * xf)
    if len(x) < 2 * n:
        return x
    head = x[:n].copy()
    x[:n] = head * np.linspace(1, 0, n) + x[-n:] * np.linspace(0, 1, n)
    return x[:-n]


def music_day(bars=8):
    rng = np.random.default_rng(2024)
    total = BAR * bars
    out = np.zeros(int(SR * (total + 1.5)))
    for b in range(bars):
        root, chord = PROG[b % 4]
        t0 = b * BAR
        place(out, pad_chord(chord, BAR * 1.05, 0.15), t0)
        place(out, bass_note(root, BEAT * 1.7, 0.34), t0)
        place(out, bass_note(root, BEAT * 1.2, 0.22), t0 + BEAT * 2)
        # arpeggio
        for step in range(8):
            if rng.random() < 0.78:
                note = PENTA[(b * 3 + step * 2) % len(PENTA)]
                place(out, pluck(note, 0.42, 0.20), t0 + step * BEAT * 0.5)
        if b % 2 == 1:
            place(out, tick(0.10), t0 + BEAT * 3.5)
        place(out, tick(0.07), t0 + BEAT * 1.5)
    # gentle melody every other bar
    for b in range(0, bars, 2):
        for k, note in enumerate(["E5", "C5", "D5", "A4"]):
            place(out, pluck(note, 0.6, 0.16), b * BAR + k * BEAT)
    return _loopify(delay(out, (0.13, 0.27), (0.2, 0.1)))


def music_night(bars=8):
    rng = np.random.default_rng(777)
    total = BAR * bars
    out = np.zeros(int(SR * (total + 2.0)))
    slow_prog = [PROG[0], PROG[2], PROG[1], PROG[3]]
    for b in range(bars):
        root, chord = slow_prog[(b // 2) % 4]
        t0 = b * BAR
        low = [c[:-1] + str(int(c[-1]) - 1) for c in chord]
        place(out, pad_chord(low, BAR * 1.4, 0.13), t0)
        place(out, bass_note(root[:-1] + str(int(root[-1]) - 1), BEAT * 2.4, 0.3), t0)
        for step in range(4):
            if rng.random() < 0.6:
                note = PENTA[(b * 5 + step * 3) % len(PENTA)]
                place(out, pluck(note[:-1] + str(int(note[-1]) - 1), 0.9, 0.15), t0 + step * BEAT)
    return _loopify(delay(out, (0.17, 0.34, 0.51), (0.3, 0.2, 0.13)))


def _rain_bed(dur, vol=0.12, rng=None):
    rng = rng or np.random.default_rng(4242)
    n = int(SR * dur)
    x = rng.uniform(-1, 1, n)
    x = lp(x, 5200)
    # slow swell
    swell = 1.0 + 0.35 * np.sin(np.linspace(0, math.tau * 3, n))
    return x * swell * vol


def music_rain(bars=8):
    rng = np.random.default_rng(101)
    total = BAR * bars
    out = np.zeros(int(SR * (total + 1.5)))
    for b in range(bars):
        root, chord = PROG[b % 4]
        t0 = b * BAR
        place(out, pad_chord(chord, BAR * 1.1, 0.12), t0)
        place(out, bass_note(root, BEAT * 2.2, 0.26), t0)
        for step in range(4):
            if rng.random() < 0.55:
                note = PENTA[(b * 2 + step * 3) % len(PENTA)]
                place(out, pluck(note, 0.7, 0.14), t0 + step * BEAT)
    out += _rain_bed(total + 1.5, 0.10, rng)
    return _loopify(delay(out, (0.12, 0.25), (0.22, 0.12)))


def main():
    os.makedirs(os.path.join(OUT, "sfx"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "music"), exist_ok=True)
    print("sound effects:")
    save("cast", sfx_cast())
    save("splash", sfx_splash())
    save("reel", sfx_reel())
    save("bite", sfx_bite())
    save("catch", sfx_catch())
    save("coin", sfx_coin())
    save("ui", sfx_ui())
    save("error", sfx_error())
    save("sleep", sfx_sleep())
    save("upgrade", sfx_upgrade())
    save("step", sfx_step())
    save("thunder", sfx_thunder())
    save("page", sfx_page())
    print("music:")
    save("day", music_day(8), subdir="music", peak=0.6)
    save("night", music_night(8), subdir="music", peak=0.5)
    save("rain", music_rain(8), subdir="music", peak=0.55)


if __name__ == "__main__":
    main()
