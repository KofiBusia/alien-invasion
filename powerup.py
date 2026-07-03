"""Power-up drop classes."""

import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, POWERUP_CONFIGS, POWERUP_ORDER


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, ptype: str):
        super().__init__()
        self.ptype    = ptype
        cfg           = POWERUP_CONFIGS[ptype]
        self.color    = cfg['color']
        self.duration = cfg['duration']
        self.name     = cfg['name']
        self.x        = float(x)
        self.y        = float(y)
        self.vy       = 1.5
        self.vx       = random.uniform(-0.6, 0.6)
        self._tick    = 0
        self._magnet  = False
        self._tx      = 0.0
        self._ty      = 0.0
        self.image    = self._make_image()
        self.rect     = self.image.get_rect(center=(x, y))

    # ── Image factory ─────────────────────────────────────────────────────────
    def _make_image(self) -> pygame.Surface:
        s  = pygame.Surface((32, 32), pygame.SRCALPHA)
        c  = self.color
        gc = (*c, 60)
        # Glow
        pygame.draw.circle(s, gc, (16, 16), 16)
        # Body
        pygame.draw.circle(s, c, (16, 16), 11)
        bright = tuple(min(255, v+80) for v in c)
        pygame.draw.circle(s, bright, (13, 13), 5)
        # Icon letter
        font = pygame.font.SysFont('consolas', 12, bold=True)
        letters = {
            'health':        'H', 'shield':     'S',
            'rapid_fire':    'R', 'damage_boost':'D',
            'speed_boost':   'V', 'coin_magnet': 'M',
            'invincibility': 'I', 'bomb':        'B',
            'full_heal':     'F', 'power_surge': 'P',
            'freeze_bomb':   'Z',
        }
        letter = letters.get(self.ptype, '?')
        txt = font.render(letter, True, (0,0,0))
        s.blit(txt, txt.get_rect(center=(16,17)))
        return s

    # ── Magnet pull ───────────────────────────────────────────────────────────
    def attract(self, tx: float, ty: float):
        self._magnet = True
        self._tx, self._ty = tx, ty

    # ── Update / draw ─────────────────────────────────────────────────────────
    def update(self):
        self._tick += 1
        if self._magnet:
            dx = self._tx - self.x
            dy = self._ty - self.y
            d  = math.hypot(dx, dy) or 1
            self.x += dx / d * 8
            self.y += dy / d * 8
        else:
            self.y += self.vy
            self.x += self.vx
            self.vy = min(self.vy + 0.02, 3.0)
        self.rect.center = (int(self.x), int(self.y))
        if self.y > SCREEN_HEIGHT + 40:
            self.kill()

    _label_font = None

    def draw_label(self, surface: pygame.Surface):
        """Draw floating name text above power-up."""
        if PowerUp._label_font is None:
            PowerUp._label_font = pygame.font.SysFont('consolas', 10)
        font = PowerUp._label_font
        txt  = font.render(self.name, True, self.color)
        alpha = max(0, min(255, int(255 * math.sin(self._tick * 0.08))))
        txt.set_alpha(alpha)
        surface.blit(txt, txt.get_rect(midbottom=(int(self.x), int(self.y)-14)))

    # ── Effect application ────────────────────────────────────────────────────
    def apply(self, player, particles) -> str:
        """Apply effect to player.  Returns message string."""
        pt = self.ptype
        if pt == 'health':
            amt = 30
            player.heal(amt)
            return f'+{amt} Health'
        elif pt == 'shield':
            amt = 30
            player.shield = min(player.max_shield, player.shield + amt)
            return f'+{amt} Shield'
        elif pt == 'rapid_fire':
            player.add_effect('rapid_fire', self.duration)
            return 'Rapid Fire!'
        elif pt == 'damage_boost':
            player.add_effect('damage_boost', self.duration)
            return 'Damage x2!'
        elif pt == 'speed_boost':
            player.add_effect('speed_boost', self.duration)
            return 'Speed Boost!'
        elif pt == 'coin_magnet':
            player.add_effect('coin_magnet', self.duration)
            return 'Coin Magnet!'
        elif pt == 'invincibility':
            player.add_effect('invincibility', self.duration)
            return 'Invincible!'
        elif pt == 'bomb':
            return 'BOMB!'   # game handles killing all enemies
        elif pt == 'full_heal':
            player.health = player.max_health
            player.shield = player.max_shield
            return 'FULLY REPAIRED!'
        elif pt == 'power_surge':
            player.add_effect('rapid_fire',   self.duration)
            player.add_effect('damage_boost', self.duration)
            player.add_effect('speed_boost',  self.duration)
            return 'POWER SURGE!'
        elif pt == 'freeze_bomb':
            return 'FREEZE!'  # game handles this
        return ''


# ── Coin drop ─────────────────────────────────────────────────────────────────
class Coin(pygame.sprite.Sprite):
    _img_cache: dict = {}

    def __init__(self, x, y, value: int = 1):
        super().__init__()
        self.value = value
        self.x     = float(x) + random.uniform(-15, 15)
        self.y     = float(y)
        self.vx    = random.uniform(-1.5, 1.5)
        self.vy    = random.uniform(-2.0, 0.5)
        self._tick = 0
        self._magnet = False
        self._tx = self._ty = 0.0
        self.image = self._get_img(value)
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))

    @classmethod
    def _get_img(cls, value):
        if value not in cls._img_cache:
            r = 8 if value == 1 else 10
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            color = (255, 200, 0) if value == 1 else (200, 200, 200)
            pygame.draw.circle(s, (*color, 80), (r+2, r+2), r+2)
            pygame.draw.circle(s, color, (r+2, r+2), r)
            bright = tuple(min(255,v+60) for v in color)
            pygame.draw.circle(s, bright, (r, r), r//3)
            cls._img_cache[value] = s
        return cls._img_cache[value]

    def attract(self, tx, ty):
        self._magnet = True
        self._tx, self._ty = tx, ty

    def update(self):
        self._tick += 1
        if self._magnet:
            dx = self._tx - self.x
            dy = self._ty - self.y
            d  = math.hypot(dx, dy) or 1
            self.x += dx / d * 9
            self.y += dy / d * 9
        else:
            self.vy += 0.1
            self.x  += self.vx
            self.y  += self.vy
            self.vx *= 0.95
        self.rect.center = (int(self.x), int(self.y))
        if self.y > SCREEN_HEIGHT + 30:
            self.kill()


def maybe_drop_powerup(x, y, level: int) -> 'PowerUp | None':
    """Roll for a power-up drop at given coords; returns instance or None."""
    base_chance = 0.18 + level * 0.005
    if random.random() > base_chance:
        return None
    # Weight rarer types lower at early levels
    weights = []
    for pt in POWERUP_ORDER:
        drop = POWERUP_CONFIGS[pt]['drop']
        weights.append(drop)
    total = sum(weights)
    r = random.random() * total
    for pt, w in zip(POWERUP_ORDER, weights):
        r -= w
        if r <= 0:
            return PowerUp(x, y, pt)
    return PowerUp(x, y, 'health')
