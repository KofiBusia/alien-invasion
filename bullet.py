"""Bullet and projectile classes with energy-bolt visuals and trails."""

import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage, color, size=(4, 14),
                 is_player=True, glow=True):
        super().__init__()
        self.damage    = damage
        self.color     = color
        self.is_player = is_player
        self.vx, self.vy = vx, vy
        self._trail: list[tuple[float,float]] = []
        self._build_image(size, color, glow)
        self.rect  = self.image.get_rect(center=(x, y))
        self.x     = float(x)
        self.y     = float(y)

    def _build_image(self, size, color, glow):
        w, h  = size
        surf  = pygame.Surface((w + 10, h + 10), pygame.SRCALPHA)
        cx, cy= (w + 10) // 2, (h + 10) // 2

        # Outer glow halo
        if glow:
            gc = (*color, 45)
            pygame.draw.ellipse(surf, gc, (0, 1, w+10, h+8))

        # Main bolt body — tapered energy bolt shape
        pts = [
            (cx,         cy - h//2),      # tip
            (cx + w//2,  cy - h//4),      # shoulder right
            (cx + w//2,  cy + h//3),      # waist right
            (cx,         cy + h//2),      # base center
            (cx - w//2,  cy + h//3),      # waist left
            (cx - w//2,  cy - h//4),      # shoulder left
        ]
        pygame.draw.polygon(surf, color, pts)

        # Bright core streak
        bright = tuple(min(255, c + 100) for c in color)
        white_core_h = max(2, h // 3)
        pygame.draw.rect(surf, bright,
                         (cx - max(1,w//4), cy - h//2 + 2, max(1,w//2), white_core_h),
                         border_radius=1)
        # Hottest center pixel
        pygame.draw.rect(surf, (255,255,255,200), (cx-1, cy-h//2+2, 2, white_core_h//2))

        self.image = surf

    def update(self):
        # Record short energy streak (3 frames max — vanishes almost immediately)
        self._trail.append((self.x, self.y))
        if len(self._trail) > 3:
            self._trail.pop(0)

        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -50 or self.x > SCREEN_WIDTH + 50 or
                self.y < -80 or self.y > SCREEN_HEIGHT + 80):
            self.kill()

    def draw_trail(self, surface: pygame.Surface):
        """Draw a very short fading energy streak. Vanishes within 3 frames."""
        col = self.color or (0, 200, 255)
        n   = len(self._trail)
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(n, 1)
            alpha = int(90 * ratio)          # much more transparent than before
            sz    = 1
            ts    = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ts, (*col, alpha), (sz+1, sz+1), sz+1)
            surface.blit(ts, (int(tx) - sz - 1, int(ty) - sz - 1))


class RainbowBullet(Bullet):
    _hue = 0

    def __init__(self, x, y, vx, vy, damage):
        RainbowBullet._hue = (RainbowBullet._hue + 15) % 360
        color = self._hue_to_rgb(RainbowBullet._hue)
        super().__init__(x, y, vx, vy, damage, color, size=(6, 22))

    @staticmethod
    def _hue_to_rgb(h):
        h = h / 60
        i = int(h)
        f = h - i
        t = int(f * 255)
        q = 255 - t
        combos = [(255,t,0),(q,255,0),(0,255,t),(0,q,255),(t,0,255),(255,0,q)]
        return combos[i % 6]

    def update(self):
        # Cycle color on the fly for shifting rainbow
        RainbowBullet._hue = (RainbowBullet._hue + 3) % 360
        self.color = self._hue_to_rgb(RainbowBullet._hue)
        super().update()


class PlasmaBullet(Bullet):
    def __init__(self, x, y, vx, vy, damage):
        super().__init__(x, y, vx, vy, damage, (200, 0, 255), size=(14, 14), glow=True)
        self._pulse = 0

    def _build_image(self, size, color, glow):
        s = pygame.Surface((28, 28), pygame.SRCALPHA)
        # Multi-layer plasma orb
        pygame.draw.circle(s, (100,  0, 180, 50),  (14, 14), 14)
        pygame.draw.circle(s, (180,  0, 220, 100), (14, 14), 10)
        pygame.draw.circle(s, (220, 60, 255, 180), (14, 14), 7)
        pygame.draw.circle(s, (255,200, 255, 240), (14, 14), 4)
        pygame.draw.circle(s, (255,255, 255),       (14, 14), 2)
        self.image = s

    def update(self):
        self._pulse += 0.3
        # Pulse size
        r  = int(28 + 4 * math.sin(self._pulse))
        s  = pygame.Surface((r, r), pygame.SRCALPHA)
        cr = r // 2
        pygame.draw.circle(s, (100,  0, 180, 40),  (cr, cr), cr)
        pygame.draw.circle(s, (200,  0, 255, 110), (cr, cr), int(cr*0.75))
        pygame.draw.circle(s, (230, 80, 255, 200), (cr, cr), int(cr*0.55))
        pygame.draw.circle(s, (255,200, 255, 240), (cr, cr), int(cr*0.35))
        pygame.draw.circle(s, (255,255, 255),       (cr, cr), int(cr*0.2))
        self.image = s
        self.rect  = s.get_rect(center=(int(self.x), int(self.y)))
        # Parent update (position only)
        self._trail.append((self.x, self.y))
        if len(self._trail) > 5:
            self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -50 or self.x > SCREEN_WIDTH + 50 or
                self.y < -80 or self.y > SCREEN_HEIGHT + 80):
            self.kill()

    def draw_trail(self, surface: pygame.Surface):
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            alpha = int(120 * ratio)
            sz    = max(2, int(ratio * 7))
            ts    = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            pygame.draw.circle(ts, (180, 0, 255, alpha), (sz, sz), sz)
            surface.blit(ts, (int(tx)-sz, int(ty)-sz))


class MissileBullet(Bullet):
    def __init__(self, x, y, vy, damage, target_group):
        super().__init__(x, y, 0, vy, damage, (255, 140, 0), size=(8, 22))
        self.target_group = target_group
        self.turn_speed   = 3.0
        self._angle       = 0.0
        self._smoke_t     = 0

    def _build_image(self, size, color, glow):
        s = pygame.Surface((16, 30), pygame.SRCALPHA)
        # Exhaust glow
        pygame.draw.ellipse(s, (255, 160, 0, 80), (3, 22, 10, 8))
        # Body
        pygame.draw.rect(s, (200, 100, 0), (5, 8, 6, 16), border_radius=3)
        pygame.draw.rect(s, (230, 140, 30), (6, 9, 4, 14), border_radius=2)
        # Nose cone
        pygame.draw.polygon(s, (255, 200, 50), [(8, 0), (4, 10), (12, 10)])
        pygame.draw.polygon(s, (255, 240, 120), [(8, 2), (5, 10), (11, 10)])
        # Fins
        pygame.draw.polygon(s, (160, 70, 0), [(4, 20), (0, 30), (5, 24)])
        pygame.draw.polygon(s, (160, 70, 0), [(12, 20), (16, 30), (11, 24)])
        # Hot exhaust core
        pygame.draw.circle(s, (255, 220, 80), (8, 28), 3)
        self.image = s

    def update(self):
        self._smoke_t += 1
        # Homing
        if self.target_group:
            nearest   = None
            best_dist = float('inf')
            for t in self.target_group:
                d = math.hypot(t.rect.centerx - self.x, t.rect.centery - self.y)
                if d < best_dist:
                    best_dist, nearest = d, t
            if nearest:
                desired_vx = nearest.rect.centerx - self.x
                desired_vy = nearest.rect.centery - self.y
                mag = math.hypot(desired_vx, desired_vy) or 1
                desired_vx /= mag
                desired_vy /= mag
                self.vx += desired_vx * 0.28
                self.vy += desired_vy * 0.28
                spd = math.hypot(self.vx, self.vy) or 1
                self.vx = self.vx / spd * 8
                self.vy = self.vy / spd * 8

        self._trail.append((self.x, self.y))
        if len(self._trail) > 8:
            self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -50 or self.x > SCREEN_WIDTH + 50 or
                self.y < -80 or self.y > SCREEN_HEIGHT + 80):
            self.kill()

    def draw_trail(self, surface: pygame.Surface):
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            alpha = int(160 * ratio)
            sz    = max(1, int(ratio * 5))
            col   = (255, int(120*ratio), 0)
            ts    = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ts, (*col, alpha), (sz+1, sz+1), sz+1)
            surface.blit(ts, (int(tx)-sz-1, int(ty)-sz-1))


class EnemyBullet(Bullet):
    def __init__(self, x, y, vx, vy, damage, explosive=False):
        color = (255, 80, 0) if explosive else (255, 50, 50)
        size  = (10, 10)    if explosive else (6, 14)
        self.explosive = explosive
        super().__init__(x, y, vx, vy, damage, color, size, is_player=False)

    def _build_image(self, size, color, glow):
        if self.explosive:
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 100, 0, 70), (10, 10), 10)
            pygame.draw.circle(s, (255, 150, 0, 150),(10, 10), 7)
            pygame.draw.circle(s, (255, 220, 80, 230),(10, 10), 4)
            pygame.draw.circle(s, (255, 255, 200),    (10, 10), 2)
            self.image = s
        else:
            # Red plasma-like enemy bolt
            w, h  = size
            surf  = pygame.Surface((w+10, h+10), pygame.SRCALPHA)
            cx, cy= (w+10)//2, (h+10)//2
            pygame.draw.ellipse(surf, (255, 30, 30, 40), (0, 1, w+10, h+8))
            pts = [
                (cx,       cy - h//2),
                (cx+w//2,  cy - h//4),
                (cx+w//2,  cy + h//3),
                (cx,       cy + h//2),
                (cx-w//2,  cy + h//3),
                (cx-w//2,  cy - h//4),
            ]
            pygame.draw.polygon(surf, color, pts)
            bright = (255, 180, 180)
            pygame.draw.rect(surf, bright, (cx-1, cy-h//2+2, 2, h//4), border_radius=1)
            self.image = surf

    def draw_trail(self, surface: pygame.Surface):
        col = (255, 60, 20) if self.explosive else (255, 50, 50)
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i+1) / max(len(self._trail), 1)
            alpha = int(120 * ratio)
            sz    = max(1, int(ratio * 3))
            ts    = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ts, (*col, alpha), (sz+1, sz+1), sz+1)
            surface.blit(ts, (int(tx)-sz-1, int(ty)-sz-1))


class BossLaser(pygame.sprite.Sprite):
    """A wide sustained laser beam from the boss."""
    def __init__(self, x, y, width=20, damage=2):
        super().__init__()
        self.x, self.y  = x, float(y)
        self.beam_width  = width
        self.damage      = damage
        self.life        = 90
        self.max_life    = 90
        self.image       = pygame.Surface((width+20, SCREEN_HEIGHT - y), pygame.SRCALPHA)
        self.rect        = self.image.get_rect(midtop=(x, y))
        self._tick       = 0
        self.color       = None   # added for glow pass compatibility

    def update(self):
        self._tick += 1
        self.life  -= 1
        if self.life <= 0:
            self.kill()
            return
        ratio = self.life / self.max_life
        flicker = 0.8 + 0.2 * math.sin(self._tick * 0.8)
        w = int(self.beam_width * flicker)
        h = SCREEN_HEIGHT - int(self.y)
        self.image = pygame.Surface((w + 20, h), pygame.SRCALPHA)

        alpha = int(200 * ratio)
        # Outer glow
        pygame.draw.rect(self.image, (255, 30, 30, int(alpha*0.3)),
                         (0, 0, w+20, h))
        # Main beam
        pygame.draw.rect(self.image, (255, 50, 50, alpha),
                         (10, 0, w, h))
        # Inner bright core
        pygame.draw.rect(self.image, (255, 200, 200, min(255, int(alpha*1.3))),
                         (10+w//3, 0, w//3, h))
        # Scanlines for texture
        if self._tick % 4 < 2:
            for sy in range(0, h, 8):
                pygame.draw.line(self.image, (255,255,255,int(alpha*0.15)),
                                 (10, sy), (10+w, sy))
        self.rect = self.image.get_rect(midtop=(int(self.x), int(self.y)))

    def draw_trail(self, surface):
        pass  # lasers have no trail
