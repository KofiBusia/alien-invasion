"""Bullet and projectile classes — standard + 4 advanced chapter weapons."""

import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, IS_ANDROID


class Bullet(pygame.sprite.Sprite):
    piercing = False

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

        if glow:
            gc = (*color, 45)
            pygame.draw.ellipse(surf, gc, (0, 1, w+10, h+8))

        pts = [
            (cx,         cy - h//2),
            (cx + w//2,  cy - h//4),
            (cx + w//2,  cy + h//3),
            (cx,         cy + h//2),
            (cx - w//2,  cy + h//3),
            (cx - w//2,  cy - h//4),
        ]
        pygame.draw.polygon(surf, color, pts)

        bright = tuple(min(255, c + 100) for c in color)
        white_core_h = max(2, h // 3)
        pygame.draw.rect(surf, bright,
                         (cx - max(1,w//4), cy - h//2 + 2, max(1,w//2), white_core_h),
                         border_radius=1)
        pygame.draw.rect(surf, (255,255,255,200), (cx-1, cy-h//2+2, 2, white_core_h//2))

        self.image = surf

    def update(self):
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
        col = self.color or (0, 200, 255)
        n   = len(self._trail)
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(n, 1) * 0.38
            c     = tuple(int(v * ratio) for v in col)
            if any(v > 2 for v in c):
                pygame.draw.circle(surface, c, (int(tx), int(ty)), 1)


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
        RainbowBullet._hue = (RainbowBullet._hue + 3) % 360
        self.color = self._hue_to_rgb(RainbowBullet._hue)
        super().update()


class PlasmaBullet(Bullet):
    _frames: list = []

    @classmethod
    def _ensure_frames(cls):
        if cls._frames:
            return
        for fi in range(16):
            pulse = fi / 16 * math.tau
            r     = int(28 + 4 * math.sin(pulse))
            cr    = r // 2
            s     = pygame.Surface((r, r), pygame.SRCALPHA)
            pygame.draw.circle(s, (100,  0, 180, 45),  (cr, cr), cr)
            pygame.draw.circle(s, (190,  0, 255, 120), (cr, cr), int(cr*0.75))
            pygame.draw.circle(s, (230, 80, 255, 200), (cr, cr), int(cr*0.55))
            pygame.draw.circle(s, (255,200, 255, 240), (cr, cr), int(cr*0.35))
            pygame.draw.circle(s, (255, 255, 255),      (cr, cr), int(cr*0.2))
            cls._frames.append(s)

    def __init__(self, x, y, vx, vy, damage):
        PlasmaBullet._ensure_frames()
        super().__init__(x, y, vx, vy, damage, (200, 0, 255), size=(14, 14), glow=True)
        self._pulse_idx = 0

    def _build_image(self, size, color, glow):
        PlasmaBullet._ensure_frames()
        self.image = PlasmaBullet._frames[0]

    def update(self):
        self._pulse_idx = (self._pulse_idx + 1) % len(PlasmaBullet._frames)
        self.image = PlasmaBullet._frames[self._pulse_idx]
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))
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
            sz    = max(1, int(ratio * 6))
            col   = (int(160 * ratio * 0.5), 0, int(230 * ratio * 0.5))
            if col[2] > 3:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


class MissileBullet(Bullet):
    def __init__(self, x, y, vy, damage, target_group):
        super().__init__(x, y, 0, vy, damage, (255, 140, 0), size=(8, 22))
        self.target_group = target_group
        self.turn_speed   = 3.0
        self._angle       = 0.0
        self._smoke_t     = 0

    def _build_image(self, size, color, glow):
        s = pygame.Surface((16, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 160, 0, 80), (3, 22, 10, 8))
        pygame.draw.rect(s, (200, 100, 0), (5, 8, 6, 16), border_radius=3)
        pygame.draw.rect(s, (230, 140, 30), (6, 9, 4, 14), border_radius=2)
        pygame.draw.polygon(s, (255, 200, 50), [(8, 0), (4, 10), (12, 10)])
        pygame.draw.polygon(s, (255, 240, 120), [(8, 2), (5, 10), (11, 10)])
        pygame.draw.polygon(s, (160, 70, 0), [(4, 20), (0, 30), (5, 24)])
        pygame.draw.polygon(s, (160, 70, 0), [(12, 20), (16, 30), (11, 24)])
        pygame.draw.circle(s, (255, 220, 80), (8, 28), 3)
        self.image = s

    def update(self):
        self._smoke_t += 1
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
            sz    = max(1, int(ratio * 5))
            col   = (int(200 * ratio * 0.7), int(100 * ratio * 0.5), 0)
            if col[0] > 3:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


# ── Chapter 2+ Advanced Bullets ───────────────────────────────────────────────

class IonBullet(Bullet):
    """Piercing ion beam — passes through all enemies it hits."""
    piercing = True

    def __init__(self, x, y, vx, vy, damage, speed_mult=1.0):
        self._spd_mult = speed_mult
        super().__init__(x, y, vx * speed_mult, vy * speed_mult,
                         damage, (80, 220, 255), size=(4, 28), glow=True)
        self._hit_set: set = set()   # tracks enemy ids already hit this bullet's life

    def _build_image(self, size, color, glow):
        w, h = 10, 36
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        # Outer glow
        pygame.draw.rect(s, (40, 160, 255, 40), (0, 0, w, h), border_radius=4)
        # Main bolt — thin intense beam
        pygame.draw.rect(s, (80, 200, 255), (w//2-2, 0, 4, h), border_radius=2)
        # Bright core
        pygame.draw.rect(s, (200, 240, 255), (w//2-1, 0, 2, h), border_radius=1)
        # Tip
        pygame.draw.ellipse(s, (255, 255, 255), (w//2-2, 0, 4, 6))
        self.image = s

    def update(self):
        # Reset hit set each frame so we can re-hit as we move
        self._hit_set.clear()
        self._trail.append((self.x, self.y))
        if len(self._trail) > 4:
            self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -50 or self.x > SCREEN_WIDTH + 50 or
                self.y < -80 or self.y > SCREEN_HEIGHT + 80):
            self.kill()

    def draw_trail(self, surface):
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            sz = max(1, int(ratio * 4))
            col = (int(60 * ratio * 0.6), int(160 * ratio * 0.7), int(255 * ratio * 0.6))
            if col[2] > 5:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


class QuantumBullet(Bullet):
    """Quantum burst bullet — bounces off screen edges."""

    def __init__(self, x, y, vx, vy, damage):
        super().__init__(x, y, vx, vy, damage, (255, 60, 220), size=(5, 5), glow=True)
        self._bounces = 2

    def _build_image(self, size, color, glow):
        s = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(s, (180, 0, 255, 60), (7, 7), 7)
        pygame.draw.circle(s, (255, 60, 220, 160), (7, 7), 5)
        pygame.draw.circle(s, (255, 200, 255, 230), (7, 7), 3)
        pygame.draw.circle(s, (255, 255, 255),       (7, 7), 1)
        self.image = s

    def update(self):
        self._trail.append((self.x, self.y))
        if len(self._trail) > 5:
            self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        # Bounce off side walls
        if self._bounces > 0:
            if self.x < 10 or self.x > SCREEN_WIDTH - 10:
                self.vx *= -1
                self.x = max(10, min(SCREEN_WIDTH-10, self.x))
                self._bounces -= 1
        self.rect.center = (int(self.x), int(self.y))
        if (self.y < -80 or self.y > SCREEN_HEIGHT + 80 or
                (self._bounces <= 0 and (self.x < -50 or self.x > SCREEN_WIDTH + 50))):
            self.kill()

    def draw_trail(self, surface):
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            sz = max(1, int(ratio * 4))
            col = (int(200 * ratio * 0.6), 0, int(220 * ratio * 0.7))
            if col[2] > 5:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


class DarkMatterBullet(Bullet):
    """Dark Matter singularity — pulls nearby enemies toward it on impact."""

    def __init__(self, x, y, vx, vy, damage):
        super().__init__(x, y, vx, vy, damage, (110, 0, 210), size=(18, 18), glow=True)
        self._pulse = 0

    def _build_image(self, size, color, glow):
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(s, (60, 0, 140, 60),  (16, 16), 16)
        pygame.draw.circle(s, (110, 0, 200, 130), (16, 16), 11)
        pygame.draw.circle(s, (180, 0, 255, 200), (16, 16), 7)
        pygame.draw.circle(s, (220, 80, 255, 240),(16, 16), 4)
        pygame.draw.circle(s, (0, 0, 0),           (16, 16), 2)
        self.image = s

    def update(self):
        self._pulse = (self._pulse + 1) % 20
        self._trail.append((self.x, self.y))
        if len(self._trail) > 6:
            self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -80 or self.x > SCREEN_WIDTH + 80 or
                self.y < -80 or self.y > SCREEN_HEIGHT + 80):
            self.kill()

    def draw_trail(self, surface):
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            sz = max(2, int(ratio * 8))
            col = (int(80 * ratio * 0.5), 0, int(180 * ratio * 0.6))
            if col[2] > 5:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


class OmegaBullet(Bullet):
    """Omega Beam — catastrophic fusion bolt, huge and devastating."""
    _frames: list = []

    @classmethod
    def _ensure_frames(cls):
        if cls._frames:
            return
        for fi in range(12):
            pulse = fi / 12 * math.tau
            r = int(22 + 4 * math.sin(pulse))
            h = 46
            s = pygame.Surface((r + 12, h + 12), pygame.SRCALPHA)
            cx_ = (r + 12) // 2
            # Outer corona
            pygame.draw.ellipse(s, (180, 160, 0, 40), (0, 2, r+12, h+8))
            # Main body
            pts = [
                (cx_, 2),
                (cx_ + r//2, h//4),
                (cx_ + r//2, h*3//4),
                (cx_, h+4),
                (cx_ - r//2, h*3//4),
                (cx_ - r//2, h//4),
            ]
            pygame.draw.polygon(s, (255, 220, 0), pts)
            # Inner hot core
            inner = [(cx_, 6), (cx_+r//3, h//4+4), (cx_+r//3, h*3//4-4),
                     (cx_, h), (cx_-r//3, h*3//4-4), (cx_-r//3, h//4+4)]
            pygame.draw.polygon(s, (255, 255, 100), inner)
            # White-hot center
            pygame.draw.rect(s, (255, 255, 255), (cx_-2, 4, 4, h-2), border_radius=2)
            cls._frames.append(s)

    def __init__(self, x, y, vx, vy, damage):
        OmegaBullet._ensure_frames()
        super().__init__(x, y, vx, vy, damage, (255, 235, 0), size=(8, 34), glow=True)
        self._frame_idx = 0

    def _build_image(self, size, color, glow):
        OmegaBullet._ensure_frames()
        self.image = OmegaBullet._frames[0]

    def update(self):
        self._frame_idx = (self._frame_idx + 1) % len(OmegaBullet._frames)
        self.image = OmegaBullet._frames[self._frame_idx]
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._trail.append((self.x, self.y))
        if len(self._trail) > 7:
            self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -80 or self.x > SCREEN_WIDTH + 80 or
                self.y < -80 or self.y > SCREEN_HEIGHT + 80):
            self.kill()

    def draw_trail(self, surface):
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            sz = max(2, int(ratio * 10))
            col = (int(220 * ratio * 0.8), int(200 * ratio * 0.7), 0)
            if col[0] > 5:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


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
        base = (255, 55, 20) if self.explosive else (220, 40, 40)
        for i, (tx, ty) in enumerate(self._trail):
            ratio = (i + 1) / max(len(self._trail), 1)
            sz    = max(1, int(ratio * 3))
            col   = tuple(int(v * ratio * 0.45) for v in base)
            if col[0] > 3:
                pygame.draw.circle(surface, col, (int(tx), int(ty)), sz)


class BossLaser(pygame.sprite.Sprite):
    def __init__(self, x, y, width=20, damage=2):
        super().__init__()
        self.x, self.y  = x, float(y)
        self.beam_width  = width
        self.damage      = damage
        self.life        = 90
        self.max_life    = 90
        self._tick       = 0
        self.color       = None
        # Pre-allocate once at max size — reuse every frame instead of re-creating
        self._fixed_h = SCREEN_HEIGHT - int(y)
        self._surf_w  = width + 40   # generous max width for flicker headroom
        if IS_ANDROID:
            self.image = pygame.Surface((self._surf_w, self._fixed_h))
            self.image.fill((0, 0, 0))
            self.image.set_colorkey((0, 0, 0))
        else:
            self.image = pygame.Surface((self._surf_w, self._fixed_h), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midtop=(int(x), int(y)))

    def update(self):
        self._tick += 1
        self.life  -= 1
        if self.life <= 0:
            self.kill()
            return
        ratio   = self.life / self.max_life
        flicker = 0.8 + 0.2 * math.sin(self._tick * 0.8)
        w       = int(self.beam_width * flicker)
        h       = self._fixed_h
        alpha   = int(200 * ratio)

        if IS_ANDROID:
            self.image.fill((0, 0, 0))   # clear (colorkey = transparent)
            pygame.draw.rect(self.image, (255, 50, 50),  (10, 0, w, h))
            pygame.draw.rect(self.image, (255, 180, 180),(10 + w//3, 0, w//3, h))
        else:
            self.image.fill((0, 0, 0, 0))   # clear SRCALPHA
            pygame.draw.rect(self.image, (255, 30, 30, int(alpha*0.3)), (0, 0, self._surf_w, h))
            pygame.draw.rect(self.image, (255, 50, 50, alpha),          (10, 0, w, h))
            pygame.draw.rect(self.image, (255, 200, 200, min(255, int(alpha*1.3))),
                             (10+w//3, 0, w//3, h))
            if self._tick % 4 < 2:
                for sy in range(0, h, 8):
                    pygame.draw.line(self.image, (255, 255, 255, int(alpha*0.15)),
                                     (10, sy), (10+w, sy))
        self.rect = self.image.get_rect(midtop=(int(self.x), int(self.y)))

    def draw_trail(self, surface):
        pass
