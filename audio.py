"""Audio manager — generates tones via pygame mixer, gracefully silent if unavailable."""

import math
import struct
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class AudioManager:
    def __init__(self, save_system):
        self.save = save_system
        self.enabled = False
        self.music_vol = self.save.get_setting("music_volume", 0.5)
        self.sfx_vol   = self.save.get_setting("sfx_volume",   0.7)
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._rainbow_hue = 0

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
            self._generate_sounds()
        except Exception as e:
            print(f"[Audio] Mixer unavailable: {e}")

    # ── Public ────────────────────────────────────────────────────────────────
    def play(self, name: str):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(self.sfx_vol)
            snd.play()

    def play_music(self, name: str = "bg"):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(self.music_vol)
            snd.play(-1)

    def stop_music(self):
        if not self.enabled:
            return
        for key in ("bg", "boss_music", "victory"):
            self.sounds.get(key, None) and self.sounds[key].stop()

    def set_music_volume(self, v: float):
        self.music_vol = max(0.0, min(1.0, v))
        self.save.set_setting("music_volume", self.music_vol)

    def set_sfx_volume(self, v: float):
        self.sfx_vol = max(0.0, min(1.0, v))
        self.save.set_setting("sfx_volume", self.sfx_vol)

    # ── Sound generation ─────────────────────────────────────────────────────
    def _generate_sounds(self):
        SR = 44100
        self.sounds["laser"]      = self._tone(SR, 880, 0.08, 0.4, wave="saw",  fade=0.9)
        self.sounds["plasma"]     = self._tone(SR, 330, 0.18, 0.5, wave="saw",  fade=0.85)
        self.sounds["missile"]    = self._tone(SR, 220, 0.22, 0.4, wave="saw",  fade=0.7)
        self.sounds["explosion"]  = self._noise(SR, 0.25, 0.6)
        self.sounds["hit"]        = self._noise(SR, 0.08, 0.5)
        self.sounds["powerup"]    = self._tone(SR, 660, 0.15, 0.8, wave="sine", fade=0.5)
        self.sounds["coin"]       = self._tone(SR, 1320,0.06, 0.8, wave="sine", fade=0.9)
        self.sounds["shield"]     = self._tone(SR, 440, 0.12, 0.6, wave="sine", fade=0.7)
        self.sounds["click"]      = self._tone(SR, 1000,0.04, 0.8, wave="sine", fade=0.9)
        self.sounds["boss_warn"]  = self._tone(SR, 200, 1.50, 0.6, wave="saw",  fade=0.3)
        self.sounds["victory"]    = self._victory(SR)
        self.sounds["gameover"]   = self._tone(SR, 110, 1.20, 0.5, wave="sine", fade=0.2)
        self.sounds["bg"]         = self._ambient(SR)

    def _make_sound(self, samples: list[int]) -> pygame.mixer.Sound:
        buf = bytearray(len(samples) * 4)
        for i, v in enumerate(samples):
            v = max(-32767, min(32767, v))
            struct.pack_into('<hh', buf, i * 4, v, v)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _tone(self, sr, freq, dur, vol, wave="sine", fade=0.8):
        n = int(sr * dur)
        out = []
        for i in range(n):
            t = i / sr
            if wave == "sine":
                s = math.sin(2 * math.pi * freq * t)
            elif wave == "saw":
                s = 2 * ((freq * t) % 1) - 1
            else:
                s = 1 if math.sin(2 * math.pi * freq * t) >= 0 else -1
            env = (1 - i / n) ** (1 - fade)
            out.append(int(vol * 32767 * s * env))
        return self._make_sound(out)

    def _noise(self, sr, dur, vol):
        import random
        n = int(sr * dur)
        out = []
        for i in range(n):
            env = (1 - i / n) ** 0.5
            out.append(int(vol * 32767 * (random.random() * 2 - 1) * env))
        return self._make_sound(out)

    def _victory(self, sr):
        notes = [523, 659, 784, 1047]
        out = []
        for freq in notes:
            n = int(sr * 0.18)
            for i in range(n):
                t = i / sr
                s = math.sin(2 * math.pi * freq * t)
                env = (1 - i / n) ** 0.3
                out.append(int(0.6 * 32767 * s * env))
        return self._make_sound(out)

    def _ambient(self, sr):
        """Simple low drone for background music."""
        dur = 4.0
        n = int(sr * dur)
        out = []
        for i in range(n):
            t = i / sr
            s  = 0.5 * math.sin(2 * math.pi * 60 * t)
            s += 0.3 * math.sin(2 * math.pi * 90 * t)
            s += 0.2 * math.sin(2 * math.pi * 45 * t)
            out.append(int(0.25 * 32767 * s))
        return self._make_sound(out)
