"""Animated space background: 3-layer parallax stars, nebulas, aurora, planets, comets."""

import random
import math
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, PLANET_COUNT, COMET_CHANCE, IS_ANDROID


# ── Star layers (far / mid / near) ───────────────────────────────────────────
class Star:
    # Star colour palettes by stellar type
    _STAR_TYPES = [
        (1.00, 1.00, 1.00),   # white
        (0.85, 0.90, 1.00),   # blue-white (hot)
        (1.00, 0.85, 0.65),   # yellow (sun-like)
        (1.00, 0.65, 0.55),   # orange giant
        (1.00, 0.50, 0.50),   # red giant
        (0.75, 0.85, 1.00),   # blue (very hot)
    ]

    def __init__(self, layer: int = 1):
        """layer 0=far(slow/dim), 1=mid, 2=near(fast/bright)"""
        self.layer = layer
        self.reset(random.randint(0, SCREEN_HEIGHT))
        self._twinkle_offset = random.uniform(0, math.tau)

    def reset(self, y: float = 0.0):
        self.x = random.uniform(0, SCREEN_WIDTH)
        self.y = float(y)
        speeds  = [0.18, 0.75, 2.0]
        bases   = [45,   130,  230]
        sizes   = [1,    1,    2  ]
        self.speed   = speeds[self.layer] + random.uniform(-0.08, 0.08)
        self._base_b = bases[self.layer] + random.randint(-25, 25)
        self.size    = sizes[self.layer]
        # Near stars: some are larger and coloured
        if self.layer == 2:
            if random.random() < 0.18:
                self.size = 3
            elif random.random() < 0.06:
                self.size = 4   # rare bright star
            # Assign stellar type — far stars are always white
            self._tint = random.choice(self._STAR_TYPES)
        elif self.layer == 1 and random.random() < 0.08:
            self._tint = random.choice(self._STAR_TYPES[:3])  # subtle mid tints
        else:
            self._tint = (1.00, 1.00, 1.00)

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT + 2:
            self.reset()

    def draw(self, surface: pygame.Surface, tick: int):
        b = self._base_b
        if self.layer > 0:
            twinkle = math.sin(tick * 0.04 + self._twinkle_offset)
            b = max(0, min(255, int(b + twinkle * 30)))
        tr, tg, tb = self._tint
        col = (min(255, int(b * tr)), min(255, int(b * tg)), min(255, int(b * tb + 30)))
        pygame.draw.circle(surface, col, (int(self.x), int(self.y)), self.size)
        # Bright stars get a 1-px cross-halo
        if self.size >= 3 and b > 200:
            lc = (min(255, col[0]+60), min(255, col[1]+60), min(255, col[2]+60))
            pygame.draw.line(surface, lc,
                             (int(self.x)-self.size-1, int(self.y)),
                             (int(self.x)+self.size+1, int(self.y)), 1)
            pygame.draw.line(surface, lc,
                             (int(self.x), int(self.y)-self.size-1),
                             (int(self.x), int(self.y)+self.size+1), 1)


class Nebula:
    def __init__(self):
        self.surf = self._make()
        self.x    = random.randint(0, SCREEN_WIDTH)
        self.y    = float(random.randint(-100, SCREEN_HEIGHT))
        self.vy   = random.uniform(0.03, 0.10)

    def _make(self) -> pygame.Surface:
        w = random.randint(160, 340)
        h = random.randint(100, 200)
        hue = random.choice([
            (80, 0, 130), (0, 40, 140), (0, 90, 70),
            (130, 20, 0), (0, 60, 100), (90, 0, 80),
        ])
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(220):
            rx    = random.randint(0, w)
            ry    = random.randint(0, h)
            rr    = random.randint(18, 60)
            alpha = random.randint(5, 22)
            c = (
                max(0, min(255, hue[0] + random.randint(-30, 30))),
                max(0, min(255, hue[1] + random.randint(-30, 30))),
                max(0, min(255, hue[2] + random.randint(-30, 30))),
                alpha,
            )
            pygame.draw.ellipse(s, c, (rx - rr, ry - rr//2, rr*2, rr))
        return s

    def update(self):
        self.y += self.vy
        if self.y > SCREEN_HEIGHT + 220:
            self.y = float(-220)
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface: pygame.Surface):
        surface.blit(self.surf,
                     (int(self.x) - self.surf.get_width()//2,
                      int(self.y) - self.surf.get_height()//2))


class Planet:
    def __init__(self, start_offscreen: bool = True):
        self._randomise(start_offscreen)

    def _randomise(self, offscreen: bool = True):
        self.r     = random.randint(28, 90)
        self.x     = float(random.randint(self.r, SCREEN_WIDTH - self.r))
        self.y     = float(-(self.r + 40)) if offscreen else float(random.randint(0, SCREEN_HEIGHT))
        self.speed = random.uniform(0.03, 0.14)
        base       = random.choice([
            (80, 50, 20), (30, 55, 110), (50, 28, 70),
            (20, 80, 50), (90, 30, 10), (10, 60, 90),
        ])
        self.color    = base
        self.ring     = random.random() < 0.45
        self.ring_col = tuple(min(255, v + 50) for v in base)
        self.stripe   = random.random() < 0.4  # gas giant bands

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT + self.r + 60:
            self._randomise(offscreen=True)

    def draw(self, surface: pygame.Surface):
        ix, iy = int(self.x), int(self.y)

        if not IS_ANDROID:
            # Atmosphere halo (SRCALPHA — desktop only)
            for dr in range(self.r + 14, self.r, -2):
                alpha = max(0, int(25 * (self.r - dr + 14) / 14))
                ah = pygame.Surface((dr*2, dr*2), pygame.SRCALPHA)
                pygame.draw.circle(ah, (*self.color, alpha), (dr, dr), dr)
                surface.blit(ah, (ix - dr, iy - dr))

        # Body
        pygame.draw.circle(surface, self.color, (ix, iy), self.r)

        if not IS_ANDROID:
            # Surface bands (gas giant) — desktop only
            if self.stripe:
                band_col = tuple(min(255, v + 30) for v in self.color)
                for band_y in range(-self.r + 8, self.r - 8, 14):
                    bh = 5
                    clip = pygame.Surface((self.r*2, self.r*2), pygame.SRCALPHA)
                    pygame.draw.circle(clip, (255,255,255), (self.r, self.r), self.r)
                    band_surf = pygame.Surface((self.r*2, bh), pygame.SRCALPHA)
                    band_surf.fill((*band_col, 60))
                    clip.blit(band_surf, (0, self.r + band_y - bh//2),
                              special_flags=pygame.BLEND_RGBA_MIN)
                    surface.blit(clip, (ix - self.r, iy - self.r))

        # Highlight
        hl = tuple(min(255, v + 70) for v in self.color)
        pygame.draw.circle(surface, hl,
                           (ix - self.r//3, iy - self.r//3),
                           max(2, self.r//4))

        if not IS_ANDROID and self.ring:
            rw = self.r * 4
            rh = self.r + 8
            rs = pygame.Surface((rw, rh), pygame.SRCALPHA)
            pygame.draw.ellipse(rs, (*self.ring_col, 90),
                                (0, rh//3, rw, rh//3), 3)
            surface.blit(rs, (ix - rw//2, iy - rh//2))


class Comet:
    TAIL_LEN = 24

    def __init__(self):
        side = random.choice(['top','left','right'])
        if side == 'top':
            self.x = random.uniform(0, SCREEN_WIDTH)
            self.y = -10.0
        elif side == 'left':
            self.x = -10.0
            self.y = random.uniform(0, SCREEN_HEIGHT * 0.6)
        else:
            self.x = SCREEN_WIDTH + 10.0
            self.y = random.uniform(0, SCREEN_HEIGHT * 0.6)
        angle     = random.uniform(60, 120)   # mostly downward
        speed     = random.uniform(7, 15)
        rad       = math.radians(angle)
        self.vx   = math.sin(rad) * speed * random.choice([-1,1]) * 0.4
        self.vy   = math.cos(rad) * speed
        self.tail : list[tuple[float,float]] = []

    def update(self):
        self.tail.append((self.x, self.y))
        if len(self.tail) > self.TAIL_LEN:
            self.tail.pop(0)
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface: pygame.Surface):
        n = len(self.tail)
        for i, (tx, ty) in enumerate(self.tail):
            ratio = i / max(n, 1)
            size  = max(1, int(ratio * 4))
            if IS_ANDROID:
                # No per-segment SRCALPHA on Android — scale RGB instead
                fade = ratio * 0.75
                c = (int(210 * fade), int(200 * fade), int(255 * fade))
                if c[2] > 3:
                    pygame.draw.circle(surface, c, (int(tx), int(ty)), size)
            else:
                alpha = int(220 * ratio)
                ts    = pygame.Surface((size*2+2, size*2+2), pygame.SRCALPHA)
                c = (200, 220, 255, alpha) if ratio > 0.6 else (255, 180, 80, alpha)
                pygame.draw.circle(ts, c, (size+1, size+1), size+1)
                surface.blit(ts, (int(tx)-size-1, int(ty)-size-1))
        # Head
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), 3)
        pygame.draw.circle(surface, (200, 240, 255), (int(self.x), int(self.y)), 5, 1)

    @property
    def off_screen(self) -> bool:
        return (self.y > SCREEN_HEIGHT + 60 or
                self.x < -60 or self.x > SCREEN_WIDTH + 60)


# ── Aurora borealis ───────────────────────────────────────────────────────────
class Aurora:
    """Sweeping bands of light at the top of the screen."""
    COLORS = [
        (0, 200, 120),   # teal-green
        (80, 0, 200),    # violet
        (0, 150, 255),   # cyan-blue
        (200, 0, 150),   # magenta
        (0, 220, 180),   # seafoam
    ]

    def __init__(self):
        self._bands: list[dict] = []
        for _ in range(4):
            self._bands.append(self._new_band())
        self._tick = 0

    def _new_band(self) -> dict:
        return {
            'x':     random.uniform(-200, SCREEN_WIDTH + 200),
            'width': random.randint(180, 420),
            'height':random.randint(80, 180),
            'alpha': random.randint(15, 45),
            'color': random.choice(self.COLORS),
            'speed': random.uniform(-0.2, 0.2),
            'phase': random.uniform(0, math.tau),
            'drift': random.uniform(-0.08, 0.08),
        }

    def update(self):
        self._tick += 1
        for b in self._bands:
            b['x']    += b['drift']
            b['phase'] += 0.008

    def draw(self, surface: pygame.Surface):
        if IS_ANDROID:
            return   # aurora creates one SRCALPHA surface per row — too expensive
        t = self._tick
        for b in self._bands:
            pulse  = 0.5 + 0.5 * math.sin(b['phase'])
            alpha  = int(b['alpha'] * pulse)
            if alpha < 4:
                continue
            w      = b['width']
            h      = b['height']
            bx     = int(b['x'])
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            for dy in range(0, h, 2):
                row_a = int(alpha * math.sin(dy / h * math.pi))
                if row_a < 2:
                    continue
                col = (*b['color'], row_a)
                wave = math.sin(t * 0.02 + dy * 0.05 + b['phase']) * 30
                pygame.draw.line(s, col, (max(0,int(wave)), dy), (min(w, w+int(wave)), dy))
            surface.blit(s, (bx - w//2, 0))


class Background:
    _LAYER_COUNTS        = [90, 65, 35]   # far, mid, near — desktop
    _LAYER_COUNTS_MOBILE = [30, 22, 12]   # ~60% fewer on Android
    _grad: pygame.Surface | None = None   # cached full-coverage gradient

    @staticmethod
    def _build_gradient() -> pygame.Surface:
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(5  + t * 3)
            g = int(8  + t * 10)
            b = int(48 + t * 42)
            pygame.draw.line(s, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        return s

    _CHAPTER_THEMES = {
        1: ((5,  8,  48), (8,  18, 90)),    # cobalt deep space
        2: ((22, 5,  55), (50, 8,  105)),   # violet nebula
        3: ((2,  30, 55), (4,  65, 100)),   # teal shockwave
        4: ((55, 4,  12), (110,8,  28)),    # crimson inferno
        5: ((35, 0,  70), (75, 5,  130)),   # deep purple chaos
    }

    def set_theme(self, chapter: int):
        top, bot = self._CHAPTER_THEMES.get(chapter, self._CHAPTER_THEMES[1])
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(top[0] + t * (bot[0] - top[0]))
            g = int(top[1] + t * (bot[1] - top[1]))
            b = int(top[2] + t * (bot[2] - top[2]))
            pygame.draw.line(s, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        Background._grad = s

    def __init__(self):
        if Background._grad is None:
            Background._grad = self._build_gradient()
        counts = self._LAYER_COUNTS_MOBILE if IS_ANDROID else self._LAYER_COUNTS
        self.stars   = [Star(layer=l) for l, n in enumerate(counts) for _ in range(n)]
        self.nebulas = [Nebula() for _ in range(3 if IS_ANDROID else 8)]
        self.planets = [Planet(start_offscreen=False) for _ in range(PLANET_COUNT)]
        self.aurora  = Aurora()
        self.comets  : list[Comet] = []
        self._tick   = 0

    def update(self):
        self._tick += 1
        for s in self.stars:   s.update()
        for n in self.nebulas: n.update()
        for p in self.planets: p.update()
        self.aurora.update()
        for c in self.comets:  c.update()
        self.comets = [c for c in self.comets if not c.off_screen]
        if random.random() < COMET_CHANCE * 1.5:   # slightly more comets
            self.comets.append(Comet())

    def draw(self, surface: pygame.Surface):
        # Blit pre-rendered gradient — fully covers every pixel every frame
        surface.blit(Background._grad, (0, 0))

        # Aurora at top of screen
        self.aurora.draw(surface)

        # Nebulas (furthest back, now richer)
        for n in self.nebulas:
            n.draw(surface)

        # Distant (layer-0) stars
        for s in self.stars:
            if s.layer == 0:
                s.draw(surface, self._tick)

        # Planets (between far and mid stars)
        for p in self.planets:
            p.draw(surface)

        # Mid + near stars in front of planets
        for s in self.stars:
            if s.layer > 0:
                s.draw(surface, self._tick)

        # Comets on top
        for c in self.comets:
            c.draw(surface)
