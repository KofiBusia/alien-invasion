"""Particle system, damage numbers, shockwaves, lightning, screen shake."""

import random
import math
import pygame
from settings import MAX_PARTICLES, SCREEN_SHAKE_DECAY, MAX_SHAKE


# ── Base particle ─────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','vx','vy','life','max_life','color','size','gravity','fade')

    def __init__(self, x, y, vx, vy, life, color, size=3, gravity=0.0, fade=True):
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.life        = life
        self.max_life    = life
        self.color       = color
        self.size        = size
        self.gravity     = gravity
        self.fade        = fade

    def update(self) -> bool:
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1
        return self.life > 0

    def draw(self, surface: pygame.Surface):
        if self.life <= 0:
            return
        ratio = self.life / self.max_life
        alpha = max(0, min(255, int(255 * ratio))) if self.fade else 255
        r = max(0, min(255, self.color[0]))
        g = max(0, min(255, self.color[1]))
        b = max(0, min(255, self.color[2]))
        sz = max(1, int(self.size * ratio))
        s  = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (sz, sz), sz)
        surface.blit(s, (int(self.x) - sz, int(self.y) - sz))


# ── Damage number ─────────────────────────────────────────────────────────────
class DamageNumber:
    _fonts: dict = {}

    def __init__(self, x, y, amount: int, kind: str = 'normal'):
        """kind: 'normal' | 'crit' | 'shield' | 'player' | 'heal'"""
        self.x     = float(x) + random.uniform(-18, 18)
        self.y     = float(y)
        self.text  = str(amount)
        self.kind  = kind
        self.vy    = -2.2 if kind == 'crit' else -1.6
        self.vx    = random.uniform(-0.4, 0.4)
        self.life  = 70 if kind == 'crit' else 55
        self.max_life = self.life
        self._size = 22 if kind == 'crit' else 16

        COLS = {
            'normal': (255, 255, 255),
            'crit':   (255, 220,   0),
            'shield': ( 80, 160, 255),
            'player': (255,  60,  60),
            'heal':   ( 60, 220,  80),
        }
        self.color = COLS.get(kind, (255, 255, 255))
        if kind == 'crit':
            self.text = '★ ' + self.text

    def update(self) -> bool:
        self.x    += self.vx
        self.y    += self.vy
        self.vy   *= 0.92
        self.life -= 1
        return self.life > 0

    def draw(self, surface: pygame.Surface):
        size = self._size
        if size not in DamageNumber._fonts:
            DamageNumber._fonts[size] = pygame.font.SysFont('consolas', size, bold=True)
        font  = DamageNumber._fonts[size]
        alpha = min(255, int(self.life / self.max_life * 320))
        txt   = font.render(self.text, True, self.color)
        txt.set_alpha(alpha)
        # Drop shadow
        sh = font.render(self.text, True, (0, 0, 0))
        sh.set_alpha(alpha // 2)
        surface.blit(sh, (int(self.x)+1, int(self.y)+1))
        surface.blit(txt, (int(self.x), int(self.y)))


# ── Shockwave ring ────────────────────────────────────────────────────────────
class Shockwave:
    def __init__(self, x, y, color=(255, 200, 80), max_radius=120, speed=5):
        self.x, self.y   = x, y
        self.radius      = 5.0
        self.max_radius  = max_radius
        self.speed       = speed
        self.color       = color
        self.life        = max_radius // speed + 5
        self.max_life    = self.life

    def update(self) -> bool:
        self.radius += self.speed
        self.life   -= 1
        return self.life > 0 and self.radius < self.max_radius

    def draw(self, surface: pygame.Surface):
        ratio = 1 - self.radius / self.max_radius
        alpha = int(255 * ratio ** 0.5)
        width = max(1, int(4 * ratio))
        r = int(self.radius)
        s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        c = (*self.color, alpha)
        pygame.draw.circle(s, c, (r+2, r+2), r, width)
        surface.blit(s, (self.x - r - 2, self.y - r - 2))


# ── Lightning bolt ────────────────────────────────────────────────────────────
class Lightning:
    def __init__(self, x1, y1, x2, y2, color=(180, 100, 255), life=12):
        self.life  = life
        self.max_life = life
        self.color = color
        self._segs = self._generate(x1, y1, x2, y2)

    def _generate(self, x1, y1, x2, y2, depth=4):
        if depth == 0:
            return [(x1, y1, x2, y2)]
        mx  = (x1 + x2) / 2 + random.uniform(-30, 30)
        my  = (y1 + y2) / 2 + random.uniform(-30, 30)
        return self._generate(x1,y1,mx,my,depth-1) + self._generate(mx,my,x2,y2,depth-1)

    def update(self) -> bool:
        self.life -= 1
        return self.life > 0

    def draw(self, surface: pygame.Surface):
        alpha = int(255 * self.life / self.max_life)
        col   = (*self.color, alpha)
        for x1,y1,x2,y2 in self._segs:
            s = pygame.Surface((abs(int(x2-x1))+4, abs(int(y2-y1))+4), pygame.SRCALPHA)
            # blit directly for simplicity
        # Draw on surface directly (simpler)
        for x1,y1,x2,y2 in self._segs:
            c = tuple(min(255, int(v * alpha/255)) for v in self.color)
            pygame.draw.line(surface, c, (int(x1),int(y1)), (int(x2),int(y2)), 2)


# ── Main particle system ──────────────────────────────────────────────────────
class ParticleSystem:
    def __init__(self):
        self.particles  : list[Particle]     = []
        self.dmg_numbers: list[DamageNumber] = []
        self.shockwaves : list[Shockwave]    = []
        self.lightning  : list[Lightning]    = []
        # Screen shake
        self._shake_x   = 0.0
        self._shake_y   = 0.0
        self._intensity = 0.0

    # ── Emitters ──────────────────────────────────────────────────────────────
    def explosion(self, x, y, color=(255,160,40), count=28, speed=6, size=5):
        budget = MAX_PARTICLES - len(self.particles)
        for _ in range(min(count, budget)):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(1, speed)
            c   = (max(0,min(255,color[0]+random.randint(-30,30))),
                   max(0,min(255,color[1]+random.randint(-30,30))),
                   max(0,min(255,color[2]+random.randint(-30,30))))
            life= random.randint(22, 52)
            self.particles.append(
                Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
                         life, c, size, gravity=0.08))

    def fire_ring(self, x, y, color=(255, 90, 0), count=28, radius=45):
        """Expanding ring of fire particles — spectacular kill effect."""
        budget = MAX_PARTICLES - len(self.particles)
        for i in range(min(count, budget)):
            ang = i / count * math.tau
            r   = radius * random.uniform(0.75, 1.15)
            px  = x + math.cos(ang) * r
            py  = y + math.sin(ang) * r
            vx  = math.cos(ang) * random.uniform(1.0, 3.5)
            vy  = math.sin(ang) * random.uniform(1.0, 3.5)
            c   = (min(255, color[0] + random.randint(-10, 10)),
                   min(255, max(0, color[1] + random.randint(-20, 70))),
                   color[2])
            self.particles.append(
                Particle(px, py, vx, vy, random.randint(16, 32), c,
                         random.randint(3, 6), gravity=0.06))

    def smoke_puff(self, x, y, count=18):
        """Rising grey smoke after explosion."""
        budget = MAX_PARTICLES - len(self.particles)
        for _ in range(min(count, budget)):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(0.4, 2.0)
            g   = random.randint(50, 110)
            self.particles.append(
                Particle(x + random.uniform(-12, 12), y + random.uniform(-6, 6),
                         math.cos(ang)*spd, math.sin(ang)*spd - 0.5,
                         random.randint(35, 70), (g, g, g),
                         random.randint(5, 11), gravity=-0.04))

    def debris_burst(self, x, y, color=(160, 110, 50), count=14):
        """Hot debris chunks flying outward."""
        budget = MAX_PARTICLES - len(self.particles)
        for _ in range(min(count, budget)):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(2.0, 9.0)
            c   = (max(0,min(255,color[0]+random.randint(-20,40))),
                   max(0,min(255,color[1]+random.randint(-20,20))),
                   max(0,min(255,color[2]+random.randint(-10,20))))
            self.particles.append(
                Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
                         random.randint(28, 50), c, random.randint(4, 8),
                         gravity=0.18))

    def mega_explosion(self, x, y, color=(255, 120, 20)):
        """Boss-death level explosion — fire rings + smoke + debris."""
        self.explosion(x, y, color, count=70, speed=12, size=8)
        self.fire_ring(x, y, color, count=36, radius=60)
        self.fire_ring(x, y, (255, 230, 40), count=22, radius=28)
        self.smoke_puff(x, y, count=24)
        self.debris_burst(x, y, count=18)
        self.shockwave_ring(x, y, color, max_radius=260, speed=9)
        self.shockwave_ring(x, y, (255, 255, 255), max_radius=130, speed=14)
        for _ in range(6):
            dx = random.randint(-100, 100)
            dy = random.randint(-70, 70)
            self.explosion(x+dx, y+dy, color, count=24, speed=6, size=5)
            self.fire_ring(x+dx, y+dy, color, count=14, radius=22)

    def hit_sparks(self, x, y, color=(255,255,100), count=8):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(2, 5)
            self.particles.append(
                Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
                         random.randint(8,20), color, 2))

    def trail(self, x, y, color, count=2, size=3):
        for _ in range(count):
            self.particles.append(
                Particle(x+random.uniform(-3,3), y+random.uniform(-3,3),
                         random.uniform(-0.4,0.4), random.uniform(0.5,1.5),
                         random.randint(6,14), color, size))

    def stars_burst(self, x, y, count=40):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(2, 10)
            col = random.choice([(255,200,50),(255,100,0),(255,50,50),(200,100,255)])
            self.particles.append(
                Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
                         random.randint(30,60), col, random.randint(3,8), 0.05))

    def shield_ripple(self, cx, cy, radius, color=(50,150,255)):
        for _ in range(14):
            ang = random.uniform(0, math.tau)
            px  = cx + math.cos(ang)*radius
            py  = cy + math.sin(ang)*radius
            self.particles.append(
                Particle(px, py, math.cos(ang)*0.6, math.sin(ang)*0.6, 16, color, 4))

    def shockwave_ring(self, x, y, color=(255,200,80), max_radius=120, speed=5):
        self.shockwaves.append(Shockwave(x, y, color, max_radius, speed))

    def spawn_lightning(self, x1, y1, x2, y2, color=(180,100,255)):
        self.lightning.append(Lightning(x1,y1,x2,y2,color))

    def damage_number(self, x, y, amount: int, kind: str = 'normal'):
        self.dmg_numbers.append(DamageNumber(x, y, amount, kind))

    # ── Screen shake ──────────────────────────────────────────────────────────
    def shake(self, intensity: float):
        self._intensity = min(max(self._intensity, intensity), MAX_SHAKE)

    @property
    def offset(self) -> tuple[int,int]:
        return (int(self._shake_x), int(self._shake_y))

    # ── Update / Draw ─────────────────────────────────────────────────────────
    def update(self):
        self.particles   = [p for p in self.particles   if p.update()]
        self.dmg_numbers = [d for d in self.dmg_numbers if d.update()]
        self.shockwaves  = [s for s in self.shockwaves  if s.update()]
        self.lightning   = [l for l in self.lightning   if l.update()]
        # Shake decay
        if self._intensity > 0.5:
            self._shake_x  = random.uniform(-self._intensity, self._intensity)
            self._shake_y  = random.uniform(-self._intensity, self._intensity)
            self._intensity *= SCREEN_SHAKE_DECAY
        else:
            self._shake_x = self._shake_y = self._intensity = 0.0

    def draw(self, surface: pygame.Surface):
        for sw in self.shockwaves: sw.draw(surface)
        for lt in self.lightning:  lt.draw(surface)
        for p  in self.particles:  p.draw(surface)
        for d  in self.dmg_numbers: d.draw(surface)
