"""Persistent save/load system using JSON."""

import json
import os
import sys
from settings import WEAPON_ORDER, TOTAL_LEVELS

# Pick the right writable directory on each platform.
if os.environ.get('ANDROID_ROOT'):
    # python-for-android sets ANDROID_PRIVATE to the app's private data dir
    _BASE = os.environ.get('ANDROID_PRIVATE', '.')
elif getattr(sys, 'frozen', False):
    # PyInstaller: keep save next to the .exe, not in the temp extract dir
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(_BASE, "savegame.json")

DEFAULT_SAVE = {
    "high_score":        0,
    "total_coins":       0,
    "current_coins":     0,
    "best_level":        0,
    "unlocked_weapons":  ["laser"],
    "upgrades": {
        "max_health":    0,
        "shield_power":  0,
        "move_speed":    0,
        "weapon_damage": 0,
        "fire_rate":     0,
        "crit_chance":   0,
        "coin_bonus":    0,
        "hull_armor":    0,
        "energy_core":   0,
        "targeting_ai":  0,
        "overdrive":     0,
    },
    "achievements":      [],
    "unlocked_allies":   [],
    "unlocked_trails":   [],
    "active_trail":      None,
    "stats": {
        "kills":         0,
        "bosses_killed": 0,
        "perfect_levels":0,
        "shots_fired":   0,
        "damage_dealt":  0,
        "damage_taken":  0,
    },
    "settings": {
        "music_volume":  0.5,
        "sfx_volume":    0.7,
        "fullscreen":    False,
        "show_fps":      False,
    },
}


class SaveSystem:
    def __init__(self):
        self.data = {}
        self.load()

    # ── Public API ────────────────────────────────────────────────────────────
    def load(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    loaded = json.load(f)
                # Deep-merge so new keys from DEFAULT_SAVE are added
                self.data = self._merge(DEFAULT_SAVE, loaded)
                return
            except Exception:
                pass
        self.data = json.loads(json.dumps(DEFAULT_SAVE))  # deep copy

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[SaveSystem] Could not save: {e}")

    def reset(self):
        self.data = json.loads(json.dumps(DEFAULT_SAVE))
        self.save()

    def reset_run(self):
        """True New Game: wipe run data but keep high score, achievements, settings."""
        keep = {
            'high_score':  self.data.get('high_score', 0),
            'achievements': list(self.data.get('achievements', [])),
            'settings':    dict(self.data.get('settings', DEFAULT_SAVE['settings'])),
            'stats':       dict(self.data.get('stats',    DEFAULT_SAVE['stats'])),
        }
        self.data = json.loads(json.dumps(DEFAULT_SAVE))
        self.data.update(keep)
        self.save()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def update_high_score(self, score: int):
        if score > self.data["high_score"]:
            self.data["high_score"] = score

    def add_coins(self, amount: int):
        self.data["total_coins"]   += amount
        self.data["current_coins"] += amount

    def spend_coins(self, amount: int) -> bool:
        if self.data["current_coins"] >= amount:
            self.data["current_coins"] -= amount
            return True
        return False

    def unlock_weapon(self, weapon_id: str):
        if weapon_id not in self.data["unlocked_weapons"]:
            self.data["unlocked_weapons"].append(weapon_id)

    def get_upgrade_level(self, upgrade_id: str) -> int:
        return self.data["upgrades"].get(upgrade_id, 0)

    def set_upgrade_level(self, upgrade_id: str, level: int):
        self.data["upgrades"][upgrade_id] = level

    def unlock_trail(self, trail_id: str):
        lst = self.data.setdefault("unlocked_trails", [])
        if trail_id not in lst:
            lst.append(trail_id)

    def has_trail(self, trail_id: str) -> bool:
        return trail_id in self.data.get("unlocked_trails", [])

    def unlock_achievement(self, ach_id: str) -> bool:
        """Returns True if newly unlocked."""
        if ach_id not in self.data["achievements"]:
            self.data["achievements"].append(ach_id)
            return True
        return False

    def increment_stat(self, stat: str, amount: int = 1):
        self.data["stats"][stat] = self.data["stats"].get(stat, 0) + amount

    def get_setting(self, key, default=None):
        return self.data["settings"].get(key, default)

    def set_setting(self, key, value):
        self.data["settings"][key] = value

    # ── Private ───────────────────────────────────────────────────────────────
    @staticmethod
    def _merge(base: dict, override: dict) -> dict:
        result = json.loads(json.dumps(base))
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = SaveSystem._merge(result[k], v)
            else:
                result[k] = v
        return result
