"""Friendly companion ships — auto-attack enemies and orbit the player."""

import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


ALLY_CONFIGS = {
    'scout_wing': {
        'name':       'Scout Wing',
        'desc':       'Rapid laser fire — fast & nimble',
        'cost':       2000,
        'max_health': 80,
        'damage':     20,
        'speed':      9,
        'fire_rate':  40,
        'color':      (80, 200, 255),
        'size':       (30, 38),
    },
    'assault_wing': {
        'name':       'Assault Wing',
        'desc':       'Plasma cannon — heavy hitter',
        'cost':       6000,
        'max_health': 200,
        'damage':     50,
        'speed':      7,
        'fire_rate':  60,
        'color':      (200, 80, 255),
        'size':       (40, 50),
    },
    'heavy_gunship': {
        'name':       'Heavy Gunship',
        'desc':       'Missile barrage — unstoppable',
        'cost':       14000,
        'max_health': 400,
        'damage':     100,
        'speed':      5,
        'fire_rate':  80,
        'color':      (255, 160, 40),
        'size':       (54, 64),
    },
}

ALLY_ORDER = ['scout_wing', 'assault_wing', 'heavy_gunship']

# Formation offsets (dx, dy) relative to player
_ALLY_OFFSETS = [
    (-120, 15),
    ( 120, 15),
    (   0, 70),
]


class AllyBullet(pygame.sprite.Sprite):
    """Bullet fired by an ally ship."""

    def __init__(self, x: int, y: int, vx: float, vy: float,
                 damage: int, color=(80, 200, 255)):
        super().__init__()
        self.vx       = vx
        self.vy       = vy
        self.damage   = damage
        self.color    = color
        self.piercing = False

        w, h = 8, 22
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color,           (1, 0, 6, h),     border_radius=3)
        pygame.draw.rect(self.image, (255, 255, 255), (2, 3, 4, h - 8), border_radius=2)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        if (self.rect.bottom < -30 or self.rect.top  > SCREEN_HEIGHT + 30
                or self.rect.right < -30 or self.rect.left > SCREEN_WIDTH + 30):
            self.kill()


class Ally(pygame.sprite.Sprite):
    """AI companion — orbits the player and auto-attacks the nearest enemy."""

    def __init__(self, game, ally_type: str, slot: int):
        super().__init__()
        self.game      = game
        self.ally_type = ally_type
        self.slot      = slot

        cfg             = ALLY_CONFIGS[ally_type]
        self.max_health = cfg['max_health']
        self.health     = self.max_health
        self.damage     = cfg['damage']
        self._speed     = cfg['speed']
        self.fire_rate  = cfg['fire_rate']
        self.color      = cfg['color']
        self._sz        = cfg['size']
        self._offset    = _ALLY_OFFSETS[slot % len(_ALLY_OFFSETS)]

        self.x = float(SCREEN_WIDTH  // 2 + self._offset[0])
        self.y = float(SCREEN_HEIGHT * 0.7)

        self._fire_cd = slot * 14   # stagger shots between allies
        self._tick    = 0

        self.image = self._build_image()
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))

    # ── Appearance ────────────────────────────────────────────────────────────
    def _build_image(self) -> pygame.Surface:
        w, h   = self._sz
        s      = pygame.Surface((w, h), pygame.SRCALPHA)
        col    = self.color
        dim    = tuple(max(0, v - 70) for v in col)
        bright = tuple(min(255, v + 70) for v in col)

        # Hull polygon (pointing upward)
        pts = [(w//2, 0), (w-2, h*2//3), (w*3//4, h-2), (w//4, h-2), (2, h*2//3)]
        pygame.draw.polygon(s, dim, pts)
        pygame.draw.polygon(s, col, pts, 2)

        # Cockpit
        cr = max(4, w // 7)
        pygame.draw.circle(s, bright, (w//2, h//4), cr)
        pygame.draw.circle(s, (255, 255, 255), (w//2, h//4), max(1, cr//2))

        # Centre cannon
        cw = max(3, w // 8)
        pygame.draw.rect(s, dim, (w//2 - cw//2, h//2, cw, h//2 - 4), border_radius=2)
        pygame.draw.circle(s, bright, (w//2, h - 3), cw + 2)

        # Engine glow
        pygame.draw.ellipse(s, (120, 200, 255), (w//2 - 6, h - 12, 12, 10))

        # Friendly indicator: green chevron at very top
        pygame.draw.polygon(s, (0, 255, 100), [(w//2-5, 4), (w//2+5, 4), (w//2, 0)])

        return s

    # ── Logic ─────────────────────────────────────────────────────────────────
    def update(self):
        self._tick += 1
        player = self.game.player
        if player is None:
            return

        # Drift toward orbit position
        tx  = max(20, min(SCREEN_WIDTH  - 20, player.x + self._offset[0]))
        ty  = max(20, min(SCREEN_HEIGHT - 20, player.y + self._offset[1]))
        dx  = tx - self.x
        dy  = ty - self.y
        d   = math.hypot(dx, dy)
        if d > 3:
            step = min(self._speed, d)
            self.x += dx / d * step
            self.y += dy / d * step

        # Auto-fire at nearest target
        self._fire_cd = max(0, self._fire_cd - 1)
        if self._fire_cd == 0:
            self._auto_fire()
            self._fire_cd = self.fire_rate

        self.rect.center = (int(self.x), int(self.y))

    def _auto_fire(self):
        targets = list(self.game.enemies) + list(self.game.boss_group)
        if not targets:
            return
        nearest = min(targets,
                      key=lambda e: math.hypot(
                          getattr(e, 'x', e.rect.centerx) - self.x,
                          getattr(e, 'y', e.rect.centery) - self.y))
        ex = getattr(nearest, 'x', nearest.rect.centerx)
        ey = getattr(nearest, 'y', nearest.rect.centery)
        dx  = ex - self.x
        dy  = ey - self.y
        d   = math.hypot(dx, dy) or 1
        spd = 13.0
        b   = AllyBullet(int(self.x), int(self.y),
                         dx / d * spd, dy / d * spd,
                         self.damage, self.color)
        self.game.ally_bullets.add(b)
        self.game.all_sprites.add(b)

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        if self.health <= 0:
            self._die()
            return True
        return False

    def _die(self):
        self.game.particles.explosion(int(self.x), int(self.y), self.color, 20, 5)
        self.game.particles.shake(8)
        self.game.ui.show_message('ALLY LOST!', int(self.x), int(self.y) - 50,
                                  (255, 80, 80), 'md')
        self.kill()

    def draw_health_bar(self, surface: pygame.Surface):
        if self.health >= self.max_health:
            return
        w   = self._sz[0]
        bx  = int(self.x) - w // 2
        by  = int(self.y) + self._sz[1] // 2 + 5
        rat = max(0.0, self.health / self.max_health)
        pygame.draw.rect(surface, (40, 0, 0),    (bx, by, w, 5))
        pygame.draw.rect(surface, (0, 200, 100), (bx, by, int(w * rat), 5))
        pygame.draw.rect(surface, (80, 255, 140), (bx, by, int(w * rat), 2))
