"""Asteroid hazard field — drifting rock obstacles that split on destruction."""

import math
import os
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

_IS_ANDROID = bool(os.environ.get('ANDROID_ROOT'))

_SIZES = {
    'large':  {'r': 52, 'hp': 6, 'dmg': 22, 'coins': (5, 10), 'speed': (0.4, 0.85), 'score': 150, 'pts': 12},
    'medium': {'r': 33, 'hp': 4, 'dmg': 14, 'coins': (2,  6), 'speed': (0.7, 1.4),  'score': 75,  'pts': 9},
    'small':  {'r': 17, 'hp': 2, 'dmg':  8, 'coins': (1,  3), 'speed': (1.0, 2.2),  'score': 30,  'pts': 7},
}


class Asteroid(pygame.sprite.Sprite):
    def __init__(self, game, size_key='large', x=None, y=None, vx=None, vy=None):
        super().__init__()
        self.game     = game
        self.size_key = size_key
        cfg = _SIZES[size_key]
        self.r         = cfg['r']
        self.hp        = cfg['hp']
        self.dmg       = cfg['dmg']
        self._coin_lo, self._coin_hi = cfg['coins']
        self.score_val = cfg['score']
        self._n_pts    = cfg['pts']

        if x is None:
            x = float(SCREEN_WIDTH + self.r + 20)
        if y is None:
            y = float(random.randint(70, SCREEN_HEIGHT - 110))
        if vx is None:
            vx = -random.uniform(*cfg['speed'])
        if vy is None:
            vy = random.uniform(-0.4, 0.4)

        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self._rot        = 0.0
        self._rot_spd    = random.uniform(-1.5, 1.5)
        self._shape      = self._gen_shape()
        self._hit_flash  = 0

        self.image = self._build_image(0)
        self._orig = self.image.copy()
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))

    def _gen_shape(self):
        r  = self.r
        n  = self._n_pts
        pts = []
        for i in range(n):
            a    = math.pi * 2 * i / n + random.uniform(-0.25, 0.25)
            dist = r * random.uniform(0.60, 1.0)
            pts.append((dist * math.cos(a), dist * math.sin(a)))
        return pts

    def _build_image(self, rot_deg=0):
        r  = self.r
        d  = r * 2 + 6
        cx = d // 2
        cy = d // 2
        s  = pygame.Surface((d, d), pygame.SRCALPHA)

        a_rad = math.radians(rot_deg)
        cos_a, sin_a = math.cos(a_rad), math.sin(a_rad)

        def rot(px, py):
            return (cx + int(px * cos_a - py * sin_a),
                    cy + int(px * sin_a + py * cos_a))

        pts = [rot(px, py) for px, py in self._shape]

        base  = (88, 76, 65)
        dark  = (55, 46, 38)
        light = (128, 114, 102)
        flash = self._hit_flash > 0

        pygame.draw.polygon(s, (220, 150, 100) if flash else base, pts)
        pygame.draw.polygon(s, dark, pts, 2)

        # Craters
        for px, py in self._shape[::3]:
            rx = cx + int(px * cos_a - py * sin_a) * 2 // 3
            ry = cy + int(px * sin_a + py * cos_a) * 2 // 3
            cr = max(3, r // 6)
            pygame.draw.circle(s, dark, (rx, ry), cr, 1)

        # Highlight scratch
        if len(pts) >= 2:
            pygame.draw.line(s, light, pts[0], pts[len(pts) // 3], 1)

        return s

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        if self._hit_flash > 0:
            self._hit_flash -= 1

        if _IS_ANDROID:
            self.rect.center = (int(self.x), int(self.y))
        else:
            self._rot += self._rot_spd
            img = self._build_image(self._rot % 360)
            self.image = img
            self.rect  = img.get_rect(center=(int(self.x), int(self.y)))

    def take_damage(self, dmg: int) -> bool:
        self.hp -= dmg
        self._hit_flash = 4
        return self.hp <= 0

    def split(self) -> list:
        fragments = []
        next_size = {'large': 'medium', 'medium': 'small'}.get(self.size_key)
        if next_size:
            for _ in range(2):
                spread = random.uniform(0.6, 1.8)
                vx = self.vx * spread
                vy = self.vy + random.uniform(-1.5, 1.5)
                fragments.append(Asteroid(self.game, next_size,
                                          self.x + random.uniform(-10, 10),
                                          self.y + random.uniform(-10, 10),
                                          vx, vy))
        return fragments

    def coin_drop(self) -> int:
        return random.randint(self._coin_lo, self._coin_hi)

    @property
    def offscreen(self) -> bool:
        return self.x < -self.r - 80 or self.y < -self.r - 80 or self.y > SCREEN_HEIGHT + self.r + 80


class AsteroidField:
    _BASE_CD = (240, 540)   # min/max frames between spawns at 30 FPS

    def __init__(self, game):
        self.game = game
        self._cd  = random.randint(*self._BASE_CD)

    def reset(self):
        self._cd = random.randint(*self._BASE_CD)

    def update(self, asteroid_group: pygame.sprite.Group):
        self._cd -= 1
        if self._cd > 0:
            return
        self._cd = random.randint(*self._BASE_CD)

        # Don't overcrowd
        if len(asteroid_group) >= 6:
            return

        r = random.random()
        size = 'large' if r < 0.18 else ('medium' if r < 0.55 else 'small')
        asteroid_group.add(Asteroid(self.game, size))
