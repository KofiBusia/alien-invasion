"""Game-wide constants and configuration."""

import os

# True when running inside a python-for-android / Buildozer APK
IS_ANDROID = bool(os.environ.get('ANDROID_ROOT'))

# ── Screen ────────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1200
SCREEN_HEIGHT = 800
FPS   = 60
TITLE = "Alien Invasion — Earth's Last Defense"

# ── Colours ───────────────────────────────────────────────────────────────────
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
RED        = (220,  50,  50)
DARK_RED   = (120,   0,   0)
GREEN      = ( 50, 220,  50)
DARK_GREEN = (  0, 120,   0)
BLUE       = ( 50, 100, 255)
DARK_BLUE  = ( 10,  10,  50)
YELLOW     = (255, 240,   0)
CYAN       = (  0, 220, 255)
ORANGE     = (255, 160,   0)
PURPLE     = (160,   0, 255)
GOLD       = (255, 210,   0)
PINK       = (255, 100, 180)
SILVER     = (192, 192, 192)
NEON_GREEN = ( 57, 255,  20)
NEON_BLUE  = ( 30, 144, 255)
NEON_CYAN  = (  0, 255, 255)
DARK_PURPLE= ( 20,   0,  40)

# UI palette
UI_BG          = ( 10,  10,  30)
UI_BORDER      = (  0, 150, 255)
UI_TEXT        = (220, 220, 255)
UI_HIGHLIGHT   = (255, 200,   0)
UI_BUTTON      = ( 30,  50, 100)
UI_BUTTON_HOV  = ( 50,  80, 150)
UI_SUCCESS     = ( 50, 200,  50)
UI_DANGER      = (220,  50,  50)

# ── Player ────────────────────────────────────────────────────────────────────
PLAYER_SPEED            = 5.0
PLAYER_HEALTH           = 100
PLAYER_SHIELD           = 50
PLAYER_LIVES            = 3
PLAYER_SHOOT_COOLDOWN   = 250   # ms
PLAYER_INVINCIBILITY_MS = 2000  # ms of iframe after hit
PLAYER_SIZE             = (50, 60)

# ── Weapons ───────────────────────────────────────────────────────────────────
WEAPONS = {
    'laser': {
        'name': 'Basic Laser',      'damage': 10,  'speed': 14,
        'cooldown': 250,  'pattern': 'single',  'spread': 0,
        'color': (0, 255, 255),     'size': (4, 18),
        'cost': 0,    'description': 'Standard rapid-fire laser',
    },
    'double_laser': {
        'name': 'Double Laser',     'damage': 10,  'speed': 14,
        'cooldown': 250,  'pattern': 'double',  'spread': 22,
        'color': (0, 180, 255),     'size': (4, 18),
        'cost': 500,  'description': 'Two parallel laser beams',
    },
    'triple_laser': {
        'name': 'Triple Laser',     'damage': 12,  'speed': 13,
        'cooldown': 280,  'pattern': 'triple',  'spread': 20,
        'color': (100, 255, 100),   'size': (4, 18),
        'cost': 1000, 'description': 'Three-direction spread',
    },
    'plasma': {
        'name': 'Plasma Cannon',    'damage': 38,  'speed': 9,
        'cooldown': 500,  'pattern': 'single',  'spread': 0,
        'color': (200, 0, 255),     'size': (14, 14),
        'cost': 1500, 'description': 'High-damage plasma orb',
    },
    'missile': {
        'name': 'Missile Launcher', 'damage': 65,  'speed': 7,
        'cooldown': 900,  'pattern': 'missile', 'spread': 0,
        'color': (255, 140, 0),     'size': (8, 22),
        'cost': 2000, 'description': 'Homing explosive missile',
    },
    'spread': {
        'name': 'Spread Shot',      'damage': 8,   'speed': 11,
        'cooldown': 350,  'pattern': 'spread5', 'spread': 40,
        'color': (255, 255, 0),     'size': (5, 12),
        'cost': 2500, 'description': 'Wide 5-bullet fan',
    },
    'rainbow': {
        'name': 'Rainbow Beam',     'damage': 18,  'speed': 16,
        'cooldown': 110,  'pattern': 'single',  'spread': 0,
        'color': None,              'size': (6, 20),
        'cost': 5000, 'description': 'Ultra-rapid shifting beam',
    },
}
WEAPON_ORDER = ['laser', 'double_laser', 'triple_laser', 'plasma', 'missile', 'spread', 'rainbow']

# ── Enemies ───────────────────────────────────────────────────────────────────
ENEMY_CONFIGS = {
    'scout': {
        'name': 'Scout',   'health': 20,  'speed': 1.8, 'damage': 8,
        'score': 50,  'coins': 5,   'can_shoot': False,
        'shoot_cd': 0, 'bullet_dmg': 0, 'bullet_spd': 0,
        'color': (0, 220, 100),  'size': (32, 34), 'pattern': 'straight',
    },
    'fighter': {
        'name': 'Fighter', 'health': 60,  'speed': 1.4, 'damage': 12,
        'score': 100, 'coins': 12,  'can_shoot': True,
        'shoot_cd': 2200, 'bullet_dmg': 12, 'bullet_spd': 7,
        'color': (220, 100, 0),  'size': (40, 44), 'pattern': 'zigzag',
    },
    'tank': {
        'name': 'Tank',    'health': 180, 'speed': 0.7, 'damage': 20,
        'score': 200, 'coins': 28,  'can_shoot': True,
        'shoot_cd': 3200, 'bullet_dmg': 20, 'bullet_spd': 5,
        'color': (180, 0, 60),   'size': (58, 62), 'pattern': 'slow',
    },
}

# ── Power-ups ─────────────────────────────────────────────────────────────────
POWERUP_CONFIGS = {
    'health':       {'name': 'Health Pack',     'color': (255, 60,  60),  'duration': 0,    'drop': 0.15},
    'shield':       {'name': 'Shield Restore',  'color': (60,  100, 255), 'duration': 0,    'drop': 0.12},
    'rapid_fire':   {'name': 'Rapid Fire',      'color': (255, 200,  0),  'duration': 5000, 'drop': 0.10},
    'damage_boost': {'name': 'Damage Boost',    'color': (255, 100,  0),  'duration': 7000, 'drop': 0.08},
    'speed_boost':  {'name': 'Speed Boost',     'color': (0,   255, 200), 'duration': 6000, 'drop': 0.10},
    'coin_magnet':  {'name': 'Coin Magnet',     'color': (255, 215,  0),  'duration': 8000, 'drop': 0.08},
    'invincibility':{'name': 'Invincibility',   'color': (200,   0, 255), 'duration': 4000, 'drop': 0.05},
    'bomb':         {'name': 'Screen Bomb',     'color': (255,  50, 150), 'duration': 0,    'drop': 0.05},
}
POWERUP_ORDER = list(POWERUP_CONFIGS.keys())

# ── Shop upgrades ─────────────────────────────────────────────────────────────
SHOP_UPGRADES = [
    {'id': 'max_health',     'name': 'Max Health',      'desc': '+25 HP cap',          'base_cost': 200, 'mult': 1.40, 'max_lvl': 10, 'color': (255,  60,  60)},
    {'id': 'shield_power',   'name': 'Shield Power',    'desc': '+20 shield cap',       'base_cost': 250, 'mult': 1.40, 'max_lvl': 10, 'color': ( 60, 100, 255)},
    {'id': 'move_speed',     'name': 'Engine Boost',    'desc': '+0.5 move speed',      'base_cost': 150, 'mult': 1.50, 'max_lvl':  8, 'color': (  0, 255, 200)},
    {'id': 'weapon_damage',  'name': 'Weapon Power',    'desc': '+15% weapon damage',   'base_cost': 300, 'mult': 1.50, 'max_lvl': 10, 'color': (255, 100,   0)},
    {'id': 'fire_rate',      'name': 'Fire Rate',       'desc': '-8% shoot cooldown',   'base_cost': 250, 'mult': 1.40, 'max_lvl': 10, 'color': (255, 200,   0)},
    {'id': 'crit_chance',    'name': 'Critical Hit',    'desc': '+5% crit chance',      'base_cost': 350, 'mult': 1.60, 'max_lvl':  8, 'color': (255,  50, 150)},
    {'id': 'coin_bonus',     'name': 'Coin Magnet',     'desc': '+12% coin drops',      'base_cost': 200, 'mult': 1.40, 'max_lvl':  8, 'color': (255, 215,   0)},
]

# ── Level generator ───────────────────────────────────────────────────────────
def get_level_config(level: int) -> dict:
    m = 1.0 + (level - 1) * 0.15
    is_boss = (level % 5 == 0)
    return {
        'level':              level,
        'is_boss':            is_boss,
        'scout_count':        min(int(3 + level * 1.5), 20),
        'fighter_count':      min(int(max(0, level - 2) * 1.0), 12),
        'tank_count':         min(int(max(0, level - 4) * 0.5), 8),
        'spawn_rate':         max(0.4, 2.5 - level * 0.09),
        'speed_mult':         m,
        'health_mult':        m,
        'damage_mult':        1.0 + (level - 1) * 0.08,
        'fire_rate_mult':     max(0.35, 1.0 - (level - 1) * 0.03),
        'boss_health':        int(600 * (level / 5) * 1.4),
        'boss_damage':        int(18 * (level / 5) * 1.2),
    }

TOTAL_LEVELS = 20

# ── Visual FX ─────────────────────────────────────────────────────────────────
MAX_PARTICLES       = 800
EXPLOSION_PARTICLES = 38
HIT_PARTICLES       = 8
STAR_COUNT          = 160
PLANET_COUNT        = 2
COMET_CHANCE        = 0.0015
SCREEN_SHAKE_DECAY  = 0.82
MAX_SHAKE           = 22

# ── Achievements ──────────────────────────────────────────────────────────────
ACHIEVEMENTS = {
    'first_kill':    ('First Blood',          'Defeat your first alien'),
    'kills_100':     ('Alien Exterminator',   'Destroy 100 aliens'),
    'boss_slayer':   ('Boss Slayer',          'Defeat a boss'),
    'untouchable':   ('Untouchable',          'Complete a level without damage'),
    'coin_collector':('Coin Hoarder',         'Collect 10 000 total coins'),
    'weapon_master': ('Arsenal',              'Unlock all weapons'),
    'earth_defender':('Earth Defender',       'Complete all 20 levels'),
}
