"""Game-wide constants and configuration — 5 Chapters, 100 Levels."""

import os

IS_ANDROID = bool(os.environ.get('ANDROID_ROOT'))

# ── Screen ────────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1200
SCREEN_HEIGHT = 800
FPS   = 30 if IS_ANDROID else 60
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

UI_BG          = ( 10,  10,  30)
UI_BORDER      = (  0, 150, 255)
UI_TEXT        = (220, 220, 255)
UI_HIGHLIGHT   = (255, 200,   0)
UI_BUTTON      = ( 30,  50, 100)
UI_BUTTON_HOV  = ( 50,  80, 150)
UI_SUCCESS     = ( 50, 200,  50)
UI_DANGER      = (220,  50,  50)

# ── Player ────────────────────────────────────────────────────────────────────
PLAYER_SPEED            = 6.5 if IS_ANDROID else 5.0
PLAYER_HEALTH           = 100
PLAYER_SHIELD           = 50
PLAYER_LIVES            = 3
PLAYER_SHOOT_COOLDOWN   = 250
PLAYER_INVINCIBILITY_MS = 2000
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
    # ── Chapter 2+ Weapons ───────────────────────────────────────────────────
    'ion_cannon': {
        'name': 'Ion Cannon',       'damage': 30,  'speed': 20,
        'cooldown': 300,  'pattern': 'single',  'spread': 0,
        'color': (80, 220, 255),    'size': (4, 28),
        'cost': 3500, 'description': 'Piercing beam hits all in line',
        'piercing': True,
    },
    'quantum_burst': {
        'name': 'Quantum Burst',    'damage': 22,  'speed': 11,
        'cooldown': 260,  'pattern': 'burst8',  'spread': 0,
        'color': (255, 60, 220),    'size': (5, 5),
        'cost': 5000, 'description': '8-direction simultaneous burst',
    },
    'dark_matter': {
        'name': 'Dark Matter',      'damage': 65,  'speed': 6,
        'cooldown': 680,  'pattern': 'single',  'spread': 0,
        'color': (110, 0, 210),     'size': (18, 18),
        'cost': 7500, 'description': 'Singularity orb — pulls enemies in',
    },
    'omega_beam': {
        'name': 'Omega Beam',       'damage': 140, 'speed': 24,
        'cooldown': 1100, 'pattern': 'single',  'spread': 0,
        'color': (255, 235, 0),     'size': (8, 34),
        'cost': 12000,'description': 'Catastrophic fusion annihilator',
    },
}
WEAPON_ORDER = [
    'laser','double_laser','triple_laser','plasma','missile','spread','rainbow',
    'ion_cannon','quantum_burst','dark_matter','omega_beam',
]

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
    'full_heal':   {'name': 'Full Repair',    'color': (255, 120, 180), 'duration': 0,    'drop': 0.04},
    'power_surge': {'name': 'POWER SURGE!',   'color': (255, 160,   0), 'duration': 8000, 'drop': 0.05},
    'freeze_bomb': {'name': 'Freeze Bomb',    'color': (  0, 200, 255), 'duration': 0,    'drop': 0.05},
}
POWERUP_ORDER = list(POWERUP_CONFIGS.keys())

# ── Shop upgrades ─────────────────────────────────────────────────────────────
SHOP_UPGRADES = [
    {'id': 'max_health',    'name': 'Max Health',    'desc': '+25 HP cap',            'base_cost': 200,  'mult': 1.40, 'max_lvl': 10, 'color': (255,  60,  60)},
    {'id': 'shield_power',  'name': 'Shield Power',  'desc': '+20 shield cap',         'base_cost': 250,  'mult': 1.40, 'max_lvl': 10, 'color': ( 60, 100, 255)},
    {'id': 'move_speed',    'name': 'Engine Boost',  'desc': '+0.5 move speed',        'base_cost': 150,  'mult': 1.50, 'max_lvl':  8, 'color': (  0, 255, 200)},
    {'id': 'weapon_damage', 'name': 'Weapon Power',  'desc': '+15% weapon damage',     'base_cost': 300,  'mult': 1.50, 'max_lvl': 10, 'color': (255, 100,   0)},
    {'id': 'fire_rate',     'name': 'Fire Rate',     'desc': '-8% shoot cooldown',     'base_cost': 250,  'mult': 1.40, 'max_lvl': 10, 'color': (255, 200,   0)},
    {'id': 'crit_chance',   'name': 'Critical Hit',  'desc': '+5% crit chance',        'base_cost': 350,  'mult': 1.60, 'max_lvl':  8, 'color': (255,  50, 150)},
    {'id': 'coin_bonus',    'name': 'Coin Magnet',   'desc': '+12% coin drops',        'base_cost': 200,  'mult': 1.40, 'max_lvl':  8, 'color': (255, 215,   0)},
    # New upgrades
    {'id': 'hull_armor',    'name': 'Hull Armor',    'desc': '-8% damage taken',       'base_cost': 320,  'mult': 1.55, 'max_lvl':  8, 'color': (160, 160, 160)},
    {'id': 'energy_core',   'name': 'Energy Core',   'desc': '+2 shield/s regen',      'base_cost': 280,  'mult': 1.45, 'max_lvl':  8, 'color': (  0, 255, 180)},
    {'id': 'targeting_ai',  'name': 'Targeting AI',  'desc': '+8% bullet speed',       'base_cost': 260,  'mult': 1.40, 'max_lvl':  6, 'color': (180, 220, 100)},
    {'id': 'overdrive',     'name': 'Overdrive',     'desc': '+10% all dmg dealt',     'base_cost': 450,  'mult': 1.65, 'max_lvl':  5, 'color': (255,  30,  30)},
]

# ── Chapter system ────────────────────────────────────────────────────────────
TOTAL_CHAPTERS    = 5
LEVELS_PER_CHAPTER= 20
TOTAL_LEVELS      = TOTAL_CHAPTERS * LEVELS_PER_CHAPTER   # 100

_CHAPTER_NAMES = {
    1: 'FIRST CONTACT',
    2: 'DEEP SPACE ASSAULT',
    3: 'NEBULA WARS',
    4: 'DARK MATTER',
    5: 'APOCALYPSE',
}
_CHAPTER_COLORS = {
    1: ( 80, 200, 255),
    2: (255, 140,   0),
    3: ( 60, 255, 110),
    4: (180,   0, 255),
    5: (255,  30,  30),
}
_CHAPTER_SUBTITLES = {
    1: 'The alien vanguard has arrived. Defend Earth!',
    2: 'A second wave — faster and more ruthless.',
    3: 'Spectral entities emerge from the nebula.',
    4: 'Iron Legion: armored war-machines of doom.',
    5: 'The Omega Fleet. This ends now.',
}

def get_chapter(level: int) -> int:
    return min(TOTAL_CHAPTERS, (level - 1) // LEVELS_PER_CHAPTER + 1)

def get_chapter_level(level: int) -> int:
    """1-based level index within the current chapter (1–20)."""
    return (level - 1) % LEVELS_PER_CHAPTER + 1

def get_chapter_name(chapter: int) -> str:
    return _CHAPTER_NAMES.get(chapter, 'UNKNOWN')

def get_chapter_color(chapter: int) -> tuple:
    return _CHAPTER_COLORS.get(chapter, (255, 255, 255))

def get_chapter_subtitle(chapter: int) -> str:
    return _CHAPTER_SUBTITLES.get(chapter, '')

# ── Enemy roster per chapter ──────────────────────────────────────────────────
# Each list: [scout_tier, fighter_tier, tank_tier, destroyer_tier]
CHAPTER_ENEMIES = {
    1: ['scout',    'fighter',     'tank',      'destroyer'],
    2: ['phantom',  'interceptor', 'goliath',   'annihilator'],
    3: ['specter',  'raptor',      'leviathan', 'devastator'],
    4: ['shade',    'marauder',    'colossus',  'obliterator'],
    5: ['reaper',   'predator',    'titan',     'nemesis'],
}

# ── Enemy configs ─────────────────────────────────────────────────────────────
ENEMY_CONFIGS = {
    # ── Chapter 1: First Contact ─────────────────────────────────────────────
    'scout': {
        'name': 'Scout',     'health': 20,   'speed': 1.8,  'damage': 8,
        'score': 50,  'coins': 5,   'can_shoot': False,
        'shoot_cd': 0, 'bullet_dmg': 0, 'bullet_spd': 0,
        'color': (0, 220, 100),   'size': (32, 34), 'pattern': 'straight',
    },
    'fighter': {
        'name': 'Fighter',   'health': 60,   'speed': 1.4,  'damage': 12,
        'score': 100, 'coins': 12,  'can_shoot': True,
        'shoot_cd': 2200, 'bullet_dmg': 12, 'bullet_spd': 7,
        'color': (220, 100, 0),   'size': (40, 44), 'pattern': 'zigzag',
    },
    'tank': {
        'name': 'Tank',      'health': 180,  'speed': 0.7,  'damage': 20,
        'score': 200, 'coins': 28,  'can_shoot': True,
        'shoot_cd': 3200, 'bullet_dmg': 20, 'bullet_spd': 5,
        'color': (180, 0, 60),    'size': (58, 62), 'pattern': 'slow',
    },
    'destroyer': {
        'name': 'Destroyer', 'health': 420,  'speed': 0.45, 'damage': 38,
        'score': 480, 'coins': 65,  'can_shoot': True,
        'shoot_cd': 2200, 'bullet_dmg': 30, 'bullet_spd': 6,
        'color': (70, 0, 210),    'size': (74, 82), 'pattern': 'slow',
    },

    # ── Chapter 2: Deep Space Assault ────────────────────────────────────────
    'phantom': {
        'name': 'Phantom',   'health': 35,   'speed': 2.8,  'damage': 12,
        'score': 90,  'coins': 10,  'can_shoot': False,
        'shoot_cd': 0, 'bullet_dmg': 0, 'bullet_spd': 0,
        'color': (0, 200, 255),   'size': (32, 34), 'pattern': 'weave',
    },
    'interceptor': {
        'name': 'Interceptor','health': 90,  'speed': 2.0,  'damage': 16,
        'score': 160, 'coins': 22,  'can_shoot': True,
        'shoot_cd': 1800, 'bullet_dmg': 15, 'bullet_spd': 9,
        'color': (255, 160, 0),   'size': (40, 44), 'pattern': 'zigzag',
    },
    'goliath': {
        'name': 'Goliath',   'health': 260,  'speed': 0.9,  'damage': 26,
        'score': 320, 'coins': 45,  'can_shoot': True,
        'shoot_cd': 2600, 'bullet_dmg': 24, 'bullet_spd': 6,
        'color': (210, 60, 0),    'size': (60, 64), 'pattern': 'slow',
    },
    'annihilator': {
        'name': 'Annihilator','health': 560, 'speed': 0.5,  'damage': 44,
        'score': 620, 'coins': 88,  'can_shoot': True,
        'shoot_cd': 2000, 'bullet_dmg': 34, 'bullet_spd': 8,
        'color': (255, 40, 90),   'size': (76, 84), 'pattern': 'slow',
    },

    # ── Chapter 3: Nebula Wars ────────────────────────────────────────────────
    'specter': {
        'name': 'Specter',   'health': 50,   'speed': 2.2,  'damage': 14,
        'score': 130, 'coins': 14,  'can_shoot': False,
        'shoot_cd': 0, 'bullet_dmg': 0, 'bullet_spd': 0,
        'color': (80, 255, 180),  'size': (32, 34), 'pattern': 'straight',
    },
    'raptor': {
        'name': 'Raptor',    'health': 110,  'speed': 1.8,  'damage': 20,
        'score': 220, 'coins': 30,  'can_shoot': True,
        'shoot_cd': 2000, 'bullet_dmg': 18, 'bullet_spd': 10,
        'color': (40, 200, 80),   'size': (42, 46), 'pattern': 'zigzag',
    },
    'leviathan': {
        'name': 'Leviathan', 'health': 360,  'speed': 0.6,  'damage': 30,
        'score': 440, 'coins': 60,  'can_shoot': True,
        'shoot_cd': 2800, 'bullet_dmg': 28, 'bullet_spd': 5,
        'color': (20, 150, 90),   'size': (62, 66), 'pattern': 'slow',
    },
    'devastator': {
        'name': 'Devastator','health': 680,  'speed': 0.4,  'damage': 50,
        'score': 780, 'coins': 110, 'can_shoot': True,
        'shoot_cd': 1800, 'bullet_dmg': 38, 'bullet_spd': 7,
        'color': (0, 200, 120),   'size': (78, 86), 'pattern': 'slow',
    },

    # ── Chapter 4: Dark Matter ────────────────────────────────────────────────
    'shade': {
        'name': 'Shade',     'health': 65,   'speed': 2.5,  'damage': 16,
        'score': 180, 'coins': 18,  'can_shoot': False,
        'shoot_cd': 0, 'bullet_dmg': 0, 'bullet_spd': 0,
        'color': (120, 0, 180),   'size': (32, 34), 'pattern': 'straight',
    },
    'marauder': {
        'name': 'Marauder',  'health': 140,  'speed': 1.6,  'damage': 24,
        'score': 290, 'coins': 40,  'can_shoot': True,
        'shoot_cd': 1800, 'bullet_dmg': 22, 'bullet_spd': 8,
        'color': (180, 0, 140),   'size': (42, 46), 'pattern': 'zigzag',
    },
    'colossus': {
        'name': 'Colossus',  'health': 500,  'speed': 0.55, 'damage': 36,
        'score': 560, 'coins': 78,  'can_shoot': True,
        'shoot_cd': 2400, 'bullet_dmg': 32, 'bullet_spd': 5,
        'color': (80, 0, 160),    'size': (64, 68), 'pattern': 'slow',
    },
    'obliterator': {
        'name': 'Obliterator','health': 850, 'speed': 0.38, 'damage': 58,
        'score': 960, 'coins': 140, 'can_shoot': True,
        'shoot_cd': 1600, 'bullet_dmg': 44, 'bullet_spd': 7,
        'color': (140, 0, 220),   'size': (80, 88), 'pattern': 'slow',
    },

    # ── Chapter 5: Apocalypse ─────────────────────────────────────────────────
    'reaper': {
        'name': 'Reaper',    'health': 80,   'speed': 3.5,  'damage': 20,
        'score': 240, 'coins': 24,  'can_shoot': False,
        'shoot_cd': 0, 'bullet_dmg': 0, 'bullet_spd': 0,
        'color': (255, 0, 80),    'size': (32, 34), 'pattern': 'straight',
    },
    'predator': {
        'name': 'Predator',  'health': 180,  'speed': 2.0,  'damage': 30,
        'score': 380, 'coins': 55,  'can_shoot': True,
        'shoot_cd': 1500, 'bullet_dmg': 28, 'bullet_spd': 11,
        'color': (200, 0, 60),    'size': (44, 48), 'pattern': 'zigzag',
    },
    'titan': {
        'name': 'Titan',     'health': 700,  'speed': 0.5,  'damage': 44,
        'score': 740, 'coins': 105, 'can_shoot': True,
        'shoot_cd': 2200, 'bullet_dmg': 38, 'bullet_spd': 6,
        'color': (220, 0, 0),     'size': (66, 70), 'pattern': 'slow',
    },
    'nemesis': {
        'name': 'Nemesis',   'health': 1100, 'speed': 0.35, 'damage': 70,
        'score': 1400,'coins': 200, 'can_shoot': True,
        'shoot_cd': 1400, 'bullet_dmg': 55, 'bullet_spd': 9,
        'color': (255, 0, 0),     'size': (82, 90), 'pattern': 'slow',
    },
}

# ── Level generator ───────────────────────────────────────────────────────────
def get_level_config(level: int) -> dict:
    # Endless survival: levels beyond 100 use Chapter 5 enemies with escalating difficulty
    if level > TOTAL_LEVELS:
        wave    = level - TOTAL_LEVELS
        base_m  = 1.0 + (TOTAL_CHAPTERS - 1) * 0.35   # Chapter 5 base
        esc_m   = 1.0 + wave * 0.06
        m       = base_m * esc_m
        enemies = CHAPTER_ENEMIES[5]
        scout, fighter, tank, destr = enemies
        counts = {
            scout:   min(int(5 + wave * 1.8), 30),
            fighter: min(int(max(0, wave - 1) * 1.5), 18),
            tank:    min(int(max(0, wave - 2) * 1.0), 12),
            destr:   min(int(max(0, wave - 4) * 0.7),  8),
        }
        is_boss = (wave % 10 == 0)
        return {
            'level':          level,
            'chapter':        5,
            'chapter_level':  wave,
            'is_boss':        is_boss,
            'enemy_kinds':    enemies,
            'enemy_counts':   counts,
            'scout_count':    counts[scout],
            'fighter_count':  counts[fighter],
            'tank_count':     counts[tank],
            'destroyer_count':counts[destr],
            'spawn_rate':     max(0.15, 2.0 - wave * 0.07),
            'speed_mult':     m,
            'health_mult':    m,
            'damage_mult':    m * 0.9,
            'fire_rate_mult': max(0.20, 1.0 - wave * 0.02),
            'boss_health':    int(1500 * esc_m),
            'boss_damage':    int(45 * esc_m),
        }

    chapter  = get_chapter(level)
    ch_level = get_chapter_level(level)   # 1-20 within the chapter

    # Scale difficulty within a chapter (gentler than before)
    m        = 1.0 + (ch_level - 1) * 0.10
    # Each chapter also adds a base multiplier
    chap_m   = 1.0 + (chapter - 1) * 0.35

    is_boss  = (ch_level % 5 == 0)

    enemies      = CHAPTER_ENEMIES[chapter]
    scout_kind   = enemies[0]
    fighter_kind = enemies[1]
    tank_kind    = enemies[2]
    destr_kind   = enemies[3]

    if IS_ANDROID:
        # Android: cap total enemies at ~14 to stay within draw budget
        enemy_counts = {
            scout_kind:   min(int(3 + ch_level * 1.0),          8),
            fighter_kind: min(int(max(0, ch_level - 1) * 0.7),  4),
            tank_kind:    min(int(max(0, ch_level - 3)),         2),
            destr_kind:   min(int(max(0, ch_level - 7) * 0.5),  2),
        }
    else:
        enemy_counts = {
            scout_kind:   min(int(5 + ch_level * 2.0),           28),
            fighter_kind: min(int(max(0, ch_level - 1) * 1.5),   16),
            tank_kind:    min(int(max(0, ch_level - 3)),          10),
            destr_kind:   min(int(max(0, ch_level - 7) * 0.7),    7),
        }

    return {
        'level':          level,
        'chapter':        chapter,
        'chapter_level':  ch_level,
        'is_boss':        is_boss,
        'enemy_kinds':    enemies,
        'enemy_counts':   enemy_counts,
        # legacy keys kept for compatibility
        'scout_count':    enemy_counts[scout_kind],
        'fighter_count':  enemy_counts[fighter_kind],
        'tank_count':     enemy_counts[tank_kind],
        'destroyer_count':enemy_counts[destr_kind],
        'spawn_rate':     max(0.22, 1.9 - ch_level * 0.07),
        'speed_mult':     m * chap_m,
        'health_mult':    m * chap_m,
        'damage_mult':    (1.0 + (ch_level - 1) * 0.06) * chap_m,
        'fire_rate_mult': max(0.30, 1.0 - (ch_level - 1) * 0.025),
        'boss_health':    int(800 * chap_m * (ch_level / 5)),
        'boss_damage':    int(20 * chap_m * (ch_level / 5)),
    }

# ── Achievements ──────────────────────────────────────────────────────────────
ACHIEVEMENTS = {
    'first_kill':     ('First Blood',        'Defeat your first alien'),
    'kills_100':      ('Alien Exterminator', 'Destroy 100 aliens'),
    'boss_slayer':    ('Boss Slayer',        'Defeat a boss'),
    'untouchable':    ('Untouchable',        'Complete a level without damage'),
    'coin_collector': ('Coin Hoarder',       'Collect 10 000 total coins'),
    'weapon_master':  ('Arsenal',            'Unlock all 11 weapons'),
    'ch2_clear':      ('Deep Space Veteran', 'Clear Chapter 2'),
    'ch3_clear':      ('Nebula Walker',      'Clear Chapter 3'),
    'ch4_clear':      ('Dark Matter Lord',   'Clear Chapter 4'),
    'earth_defender':  ('Saviour of Earth',    'Complete all 5 chapters'),
    'ultimate_slayer': ('Omega Nemesis',       'Defeat the ultimate final boss'),
    'elite_slayer':    ('Elite Hunter',        'Kill 50 elite enemies'),
    'combo_god':       ('Combo God',           'Reach a 50x combo'),
    'endless_veteran': ('Endless Veteran',     'Survive 20 endless waves'),
}

# ── Ship skins ────────────────────────────────────────────────────────────────
SHIP_SKINS = {
    'cyan':    {'name': 'CYAN',    'dark': (18, 50,145),  'mid': (35, 90,215),  'bright': (65,130,255), 'neon': (0,210,255),  'eng': (0,135,255),  'cock': (0,155,235)},
    'crimson': {'name': 'CRIMSON', 'dark': (120,15, 25),  'mid': (185,35, 50),  'bright': (240,70, 80), 'neon': (255,80,  0), 'eng': (220,60,  0), 'cock': (200,20, 30)},
    'forest':  {'name': 'FOREST',  'dark': (10, 80, 25),  'mid': (25,155, 55),  'bright': (55,220, 90), 'neon': (0,255,100),  'eng': (0,180, 70),  'cock': (0,160, 60)},
    'plasma':  {'name': 'PLASMA',  'dark': (70, 10,110),  'mid': (140,30,200),  'bright': (190,70,255), 'neon': (220,0, 255), 'eng': (180,20,255), 'cock': (150,10,220)},
    'gold':    {'name': 'GOLD',    'dark': (100,75, 10),  'mid': (185,145, 20), 'bright': (255,215, 55),'neon': (255,230,  0),'eng': (220,180,  0),'cock': (200,150,  0)},
}
SKIN_ORDER = ['cyan', 'crimson', 'forest', 'plasma', 'gold']

# ── Visual FX ─────────────────────────────────────────────────────────────────
MAX_PARTICLES       = 9 if IS_ANDROID else 1000
EXPLOSION_PARTICLES = 38
HIT_PARTICLES       = 8
STAR_COUNT          = 160
PLANET_COUNT        = 2
COMET_CHANCE        = 0.0015
SCREEN_SHAKE_DECAY  = 0.82
MAX_SHAKE           = 22
