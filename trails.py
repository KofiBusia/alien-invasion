"""Purchasable ship trail system — particles that FADE OUT, never stick."""

import math
import random
import pygame


class _Particle:
    __slots__ = ('x','y','vx','vy','r','g','b','a','max_a','size','life','max_life')

    def __init__(self, x, y, vx, vy, r, g, b, a, size, life):
        self.x, self.y       = x, y
        self.vx, self.vy     = vx, vy
        self.r, self.g, self.b = r, g, b
        self.a = self.max_a  = a
        self.size            = size
        self.life = self.max_life = max(1, life)

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.vy  += 0.06          # gravity-like fall (trails drop away)
        self.vx  *= 0.96          # air drag
        self.life -= 1
        self.a    = int(self.max_a * self.life / self.max_life)

    @property
    def alive(self):
        return self.life > 0


def _hsv(h):
    h = h % 360
    c = x = 1.0
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = 0
    if   h < 60:  r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else:         r,g,b = c,0,x
    return int((r+m)*255), int((g+m)*255), int((b+m)*255)


# ── Catalogue of available trail types ───────────────────────────────────────
TRAIL_CATALOGUE = [
    {
        'id':    'fire',
        'name':  'Fire Trail',
        'desc':  'Blazing orange-red engine fire',
        'cost':  350,
        'color': (255, 90, 0),
    },
    {
        'id':    'ice',
        'name':  'Ice Trail',
        'desc':  'Frosty crystal-blue shards',
        'cost':  350,
        'color': (80, 190, 255),
    },
    {
        'id':    'plasma',
        'name':  'Plasma Trail',
        'desc':  'Crackling cyan energy wake',
        'cost':  500,
        'color': (0, 220, 255),
    },
    {
        'id':    'lightning',
        'name':  'Lightning Trail',
        'desc':  'Electric violet sparks',
        'cost':  600,
        'color': (180, 80, 255),
    },
    {
        'id':    'stardust',
        'name':  'Stardust Trail',
        'desc':  'Golden sparkling dust cloud',
        'cost':  550,
        'color': (255, 210, 40),
    },
    {
        'id':    'ghost',
        'name':  'Ghost Trail',
        'desc':  'Ethereal purple wisps',
        'cost':  450,
        'color': (140, 60, 230),
    },
    {
        'id':    'rainbow',
        'name':  'Rainbow Trail',
        'desc':  'Full-spectrum shifting burst',
        'cost':  750,
        'color': None,           # drawn dynamically
    },
    {
        'id':    'shadow',
        'name':  'Shadow Trail',
        'desc':  'Dark void echoes',
        'cost':  800,
        'color': (80, 0, 130),
    },
]

TRAIL_IDS = [t['id'] for t in TRAIL_CATALOGUE]


class TrailSystem:
    """Manages ship trail particles.  Trail type = None means no trail."""

    def __init__(self):
        self.particles: list[_Particle] = []
        self.trail_type: str | None     = None
        self._hue                        = 0

    # ── Public API ────────────────────────────────────────────────────────────
    def set_trail(self, trail_type: str | None):
        if trail_type not in (None, *TRAIL_IDS):
            raise ValueError(f'Unknown trail type: {trail_type}')
        self.trail_type = trail_type
        self.particles.clear()

    def emit(self, engine_positions: list[tuple[float, float]], moving: bool):
        """Call every frame with the ship's engine nozzle world positions."""
        if self.trail_type is None:
            return
        for ex, ey in engine_positions:
            self._emit_at(ex, ey, moving)

    def update(self):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update()

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            if p.a < 4:
                continue
            sz = max(1, p.size)
            s  = pygame.Surface((sz * 2 + 2, sz * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (p.r, p.g, p.b, p.a), (sz + 1, sz + 1), sz + 1)
            surface.blit(s, (int(p.x) - sz - 1, int(p.y) - sz - 1))

    # ── Emitters per trail type ───────────────────────────────────────────────
    def _emit_at(self, x: float, y: float, moving: bool):
        n   = lambda s: random.uniform(-s, s)
        t   = self.trail_type
        cnt = 3 if moving else 1

        if t == 'fire':
            for _ in range(cnt):
                self.particles.append(_Particle(
                    x + n(4), y + n(2),
                    n(0.4), random.uniform(-0.5, 0.3),   # upward-ish
                    255, random.randint(60, 160), 0,
                    random.randint(160, 220),
                    random.randint(3, 6),
                    random.randint(8, 14)
                ))

        elif t == 'ice':
            for _ in range(cnt):
                self.particles.append(_Particle(
                    x + n(3), y + n(2),
                    n(0.5), random.uniform(-0.2, 0.4),
                    random.randint(60, 120), random.randint(170, 230), 255,
                    random.randint(140, 200),
                    random.randint(2, 5),
                    random.randint(7, 13)
                ))

        elif t == 'plasma':
            for _ in range(cnt):
                self.particles.append(_Particle(
                    x + n(3), y + n(2),
                    n(0.3), random.uniform(-0.1, 0.3),
                    0, random.randint(190, 255), random.randint(220, 255),
                    random.randint(160, 210),
                    random.randint(3, 7),
                    random.randint(8, 14)
                ))

        elif t == 'lightning':
            if random.random() < 0.5:
                self.particles.append(_Particle(
                    x + n(8), y + n(5),
                    n(1.2), random.uniform(-0.3, 0.6),
                    random.randint(160, 220), random.randint(80, 150), 255,
                    random.randint(180, 255),
                    random.randint(2, 4),
                    random.randint(5, 10)
                ))

        elif t == 'stardust':
            for _ in range(cnt):
                self.particles.append(_Particle(
                    x + n(10), y + n(6),
                    n(0.9), random.uniform(-0.4, 0.5),
                    255, random.randint(180, 240), random.randint(20, 80),
                    random.randint(180, 240),
                    random.randint(2, 4),
                    random.randint(16, 28)      # longer-lived sparkles
                ))

        elif t == 'ghost':
            if random.random() < 0.55:
                self.particles.append(_Particle(
                    x + n(7), y + n(4),
                    n(0.3), random.uniform(-0.2, 0.15),
                    random.randint(100, 170), random.randint(30, 80), 245,
                    random.randint(80, 140),
                    random.randint(7, 13),
                    random.randint(20, 32)
                ))

        elif t == 'rainbow':
            self._hue = (self._hue + 8) % 360
            r, g, b   = _hsv(self._hue)
            for _ in range(cnt):
                self.particles.append(_Particle(
                    x + n(5), y + n(3),
                    n(0.5), random.uniform(-0.2, 0.4),
                    r, g, b,
                    random.randint(170, 230),
                    random.randint(3, 6),
                    random.randint(9, 15)
                ))

        elif t == 'shadow':
            for _ in range(cnt):
                self.particles.append(_Particle(
                    x + n(6), y + n(4),
                    n(0.5), random.uniform(-0.1, 0.5),
                    random.randint(50, 100), 0, random.randint(90, 160),
                    random.randint(160, 210),
                    random.randint(4, 8),
                    random.randint(10, 18)
                ))
