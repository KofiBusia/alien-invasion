"""Enemy classes: Scout, Fighter (with dodge), Tank."""

import math
import random
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_CONFIGS
)
from bullet import EnemyBullet
from powerup import maybe_drop_powerup, Coin


class Enemy(pygame.sprite.Sprite):
    KIND = 'scout'

    def __init__(self, game, x: float, y: float, level: int = 1):
        super().__init__()
        self.game   = game
        cfg         = ENEMY_CONFIGS[self.KIND]
        lc          = game.level_cfg

        self.name       = cfg['name']
        self.max_health = int(cfg['health'] * lc['health_mult'])
        self.health     = self.max_health
        self.speed      = cfg['speed']  * lc['speed_mult']
        self.damage     = int(cfg['damage']  * lc['damage_mult'])
        self.score_val  = cfg['score']
        self.coin_val   = int(cfg['coins']  * game.player.coin_mult)
        self.can_shoot  = cfg['can_shoot']
        self.shoot_cd   = int(cfg.get('shoot_cd', 0) * lc.get('fire_rate_mult', 1.0))
        self.bullet_dmg = int(cfg.get('bullet_dmg', 0) * lc['damage_mult'])
        self.bullet_spd = cfg.get('bullet_spd', 0)
        self.pattern    = cfg['pattern']
        self.color      = cfg['color']
        self.size       = cfg['size']
        self.level      = level

        self.x     = float(x)
        self.y     = float(y)
        self._tick = 0
        self._shoot_timer = random.randint(0, self.shoot_cd) if self.shoot_cd else 0
        self._zig_dir  = random.choice([-1, 1])
        self._zig_timer= 0
        self._hit_flash= 0

        # Death animation
        self._dying       = False
        self._dying_timer = 0

        self.image = self._build_image()
        self._orig = self.image.copy()
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

    # ── Image factory ─────────────────────────────────────────────────────────
    def _build_image(self) -> pygame.Surface:
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v - 60) for v in c)
        bright = tuple(min(255, v + 60) for v in c)
        pts = [(w//2, h), (0, h//3), (w//4, 0), (w*3//4, 0), (w, h//3)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 2)
        pygame.draw.ellipse(s, bright, (w//2-6, h//3-4, 12, 14))
        pygame.draw.ellipse(s, (200,240,255,180), (w//2-4, h//3-2, 8, 9))
        pygame.draw.rect(s, dim, (w//4, h-6, w//2, 6), border_radius=3)
        return s

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        self._tick += 1

        if self._dying:
            self._dying_timer -= 1
            # Spin and shrink during death
            ang  = self._dying_timer * 15
            frac = self._dying_timer / 8
            sz   = (max(1, int(self.size[0]*frac)), max(1, int(self.size[1]*frac)))
            tmp  = pygame.transform.scale(self._orig, sz)
            self.image = pygame.transform.rotate(tmp, ang)
            self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self._dying_timer <= 0:
                self._finish_die()
            return

        self._move()
        if self.can_shoot:
            self._try_shoot()

        if self._hit_flash > 0:
            self._hit_flash -= 1
            flash = self._orig.copy()
            flash.fill((255,255,255,180), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = flash
        else:
            self.image = self._orig

        self.rect.center = (int(self.x), int(self.y))
        if self.y > SCREEN_HEIGHT + 60:
            self.kill()

    def _move(self):
        self.y += self.speed
        if self.pattern == 'zigzag':
            self._zig_timer += 1
            if self._zig_timer > 45:
                self._zig_dir   *= -1
                self._zig_timer  = 0
            self.x = max(30, min(SCREEN_WIDTH-30, self.x + self._zig_dir * self.speed * 0.8))
        elif self.pattern == 'slow':
            pass

    def _try_shoot(self):
        if self._shoot_timer > 0:
            self._shoot_timer -= 1
            return
        self._shoot_timer = self.shoot_cd
        self._fire()

    def _fire(self):
        px = self.game.player.x
        py = self.game.player.y
        dx = px - self.x
        dy = py - self.y
        d  = math.hypot(dx, dy) or 1
        vx = dx / d * self.bullet_spd
        vy = dy / d * self.bullet_spd
        b  = EnemyBullet(int(self.x), int(self.y) + self.rect.height//2,
                         vx, vy, self.bullet_dmg)
        self.game.enemy_bullets.add(b)
        self.game.all_sprites.add(b)

    # ── Damage ────────────────────────────────────────────────────────────────
    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        self._hit_flash = 4
        self.game.save.increment_stat('damage_dealt', amount)
        if self.health <= 0:
            self._die()
            return True
        return False

    def _die(self):
        if self._dying:
            return
        self._dying       = True
        self._dying_timer = 8
        px, py = int(self.x), int(self.y)
        self._death_effect(px, py)
        self.game.audio.play('explosion')
        self._drop_loot()
        self.game.player.score += self.score_val
        self.game.save.increment_stat('kills')

    def _death_effect(self, px: int, py: int):
        self.game.particles.explosion(px, py, self.color, count=22, speed=5)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=55, speed=4)
        self.game.particles.shake(5)

    def _finish_die(self):
        self.kill()

    def _drop_loot(self):
        px, py = int(self.x), int(self.y)
        n_coins = max(1, int(self.coin_val * random.uniform(0.8, 1.2)))
        for _ in range(min(n_coins, 8)):
            c = Coin(px, py, 1)
            self.game.coins_group.add(c)
            self.game.all_sprites.add(c)
        pu = maybe_drop_powerup(px, py, self.level)
        if pu:
            self.game.powerups.add(pu)
            self.game.all_sprites.add(pu)

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw_health_bar(self, surface: pygame.Surface):
        if self.health >= self.max_health or self._dying:
            return
        bw    = self.rect.width
        bh    = 5
        bx    = self.rect.left
        by    = self.rect.top - 8
        ratio = max(0, self.health / self.max_health)
        pygame.draw.rect(surface, (80,0,0),    (bx, by, bw, bh), border_radius=2)
        pygame.draw.rect(surface, (220,50,50), (bx, by, int(bw*ratio), bh), border_radius=2)


class Scout(Enemy):
    KIND = 'scout'

    def _death_effect(self, px: int, py: int):
        self.game.particles.explosion(px, py, self.color, count=16, speed=4)
        self.game.particles.fire_ring(px, py, self.color, count=14, radius=22)
        self.game.particles.smoke_puff(px, py, count=8)
        self.game.particles.shake(4)


class Fighter(Enemy):
    KIND = 'fighter'

    def __init__(self, game, x: float, y: float, level: int = 1):
        super().__init__(game, x, y, level)
        self._dodge_cd    = random.randint(60, 120)
        self._dodge_dir   = 0
        self._dodge_timer = 0
        # Dive-bomb charge
        self._dive_cd    = random.randint(220, 420)
        self._diving     = False
        self._dive_vx    = 0.0
        self._dive_vy    = 0.0

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-50) for v in c)
        br   = tuple(min(255, v+60) for v in c)
        pts  = [(w//2,h),(2,h//2),(w//4,0),(w*3//4,0),(w-2,h//2)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 2)
        pygame.draw.rect(s, dim, (0, h//2-3, 8, 6), border_radius=2)
        pygame.draw.rect(s, dim, (w-8, h//2-3, 8, 6), border_radius=2)
        pygame.draw.rect(s, br,  (1, h//2-2, 4, 4))
        pygame.draw.rect(s, br,  (w-5, h//2-2, 4, 4))
        pygame.draw.ellipse(s, br, (w//2-5, h//3, 10, 12))
        return s

    def _move(self):
        # Dive-bomb: charge straight at player at high speed
        if self._diving:
            self.x += self._dive_vx
            self.y += self._dive_vy
            self._dive_cd = max(0, self._dive_cd - 1)
            if self._dive_cd == 0:
                self._diving  = False
                self._dive_cd = random.randint(300, 500)
            return

        self.y += self.speed

        # Countdown to next dive
        self._dive_cd = max(0, self._dive_cd - 1)
        if self._dive_cd == 0:
            px, py = self.game.player.x, self.game.player.y
            if self.y < py - 40:   # only dive when above player
                dx = px - self.x
                dy = py - self.y
                d  = math.hypot(dx, dy) or 1
                spd = self.speed * 6.5
                self._dive_vx = dx / d * spd
                self._dive_vy = dy / d * spd
                self._diving  = True
                self._dive_cd = 48
                self.game.particles.hit_sparks(int(self.x), int(self.y),
                                               self.color, count=10)
                self.game.particles.shockwave_ring(int(self.x), int(self.y),
                                                   self.color, max_radius=32, speed=4)
            else:
                self._dive_cd = random.randint(120, 260)
            return

        # Dodge: scan for nearby player bullets
        self._dodge_cd    = max(0, self._dodge_cd - 1)
        self._dodge_timer = max(0, self._dodge_timer - 1)

        if self._dodge_cd == 0:
            for b in self.game.player_bullets:
                dx = b.rect.centerx - self.x
                dy = b.rect.centery - self.y
                if abs(dy) < 120 and abs(dx) < 50:
                    self._dodge_dir   = -1 if dx > 0 else 1
                    self._dodge_timer = 25
                    self._dodge_cd    = 90
                    break

        if self._dodge_timer > 0:
            self.x = max(30, min(SCREEN_WIDTH-30, self.x + self._dodge_dir * self.speed * 1.5))
        elif self.pattern == 'zigzag':
            self._zig_timer += 1
            if self._zig_timer > 45:
                self._zig_dir   *= -1
                self._zig_timer  = 0
            self.x = max(30, min(SCREEN_WIDTH-30, self.x + self._zig_dir * self.speed * 0.8))

    def _death_effect(self, px: int, py: int):
        self.game.particles.explosion(px, py, self.color, count=30, speed=7)
        self.game.particles.fire_ring(px, py, self.color, count=18, radius=32)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=75, speed=5)
        self.game.particles.smoke_puff(px, py, count=12)
        self.game.particles.shake(6)


class Tank(Enemy):
    KIND = 'tank'

    def _death_effect(self, px: int, py: int):
        self.game.particles.explosion(px, py, self.color, count=44, speed=8, size=7)
        self.game.particles.fire_ring(px, py, self.color, count=22, radius=44)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=110, speed=6)
        self.game.particles.debris_burst(px, py, self.color, count=18)
        self.game.particles.smoke_puff(px, py, count=20)
        self.game.particles.shake(14)
        self.game.screen_flash(self.color, 35)

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-40) for v in c)
        br   = tuple(min(255, v+50) for v in c)
        pygame.draw.rect(s, c,   (4, 4, w-8, h-10), border_radius=6)
        pygame.draw.rect(s, dim, (4, 4, w-8, h-10), border_radius=6, width=2)
        pygame.draw.rect(s, dim, (0, h//3, w, h//4), border_radius=3)
        pygame.draw.rect(s, br,  (1, h//3+1, w-2, h//4-2), border_radius=2)
        pygame.draw.rect(s, dim, (w//2-5, h-14, 10, 16), border_radius=4)
        pygame.draw.circle(s, dim, (w//2, h-14), 6)
        pygame.draw.ellipse(s, (180,200,255,200), (w//2-7, 8, 14, 16))
        return s

    def _fire(self):
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d      = math.hypot(dx, dy) or 1
        b = EnemyBullet(int(self.x), int(self.y)+self.rect.height//2,
                        dx/d*self.bullet_spd, dy/d*self.bullet_spd,
                        self.bullet_dmg, explosive=True)
        self.game.enemy_bullets.add(b)
        self.game.all_sprites.add(b)


class Destroyer(Enemy):
    """Massive warship — slow, tanky, twin explosive cannons."""
    KIND = 'destroyer'

    def _build_image(self) -> pygame.Surface:
        w, h = self.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = self.color
        dim   = tuple(max(0,  v - 50) for v in c)
        br    = tuple(min(255, v + 90) for v in c)
        glow  = (min(255, c[0]+40), min(255, c[1]+30), 255)

        # Main hull — wide hexagonal body
        pts = [(w//2, 0), (w-4, h//5), (w, h*2//3),
               (w*2//3, h), (w//3, h), (0, h*2//3), (4, h//5)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)

        # Armour ridge
        ridge = [(w//2, 8), (w//2+14, h//3), (w//2+9, h*2//3-8),
                 (w//2, h-12), (w//2-9, h*2//3-8), (w//2-14, h//3)]
        pygame.draw.polygon(s, dim, ridge)
        pygame.draw.polygon(s, br, ridge, 1)

        # Heavy side turrets
        for tx in (6, w - 18):
            pygame.draw.rect(s, dim, (tx, h//3+2, 12, 30), border_radius=3)
            pygame.draw.rect(s, br,  (tx+1, h//3+3, 10, 28), border_radius=2, width=1)
            # Cannon barrel
            bx = tx + 6
            pygame.draw.rect(s, (200, 80, 255), (bx-3, h//3+28, 6, 14), border_radius=2)
            pygame.draw.circle(s, glow, (bx, h//3+42), 5)

        # Central reactor core
        pygame.draw.ellipse(s, (70, 0, 180, 190),  (w//2-14, 12, 28, 36))
        pygame.draw.ellipse(s, (150, 0, 255, 220),  (w//2-10, 16, 20, 26))
        pygame.draw.ellipse(s, (220, 100, 255, 255),(w//2-6,  20, 12, 16))
        pygame.draw.ellipse(s, (255, 255, 255),      (w//2-3,  24,  6,  8))

        # Engine pods
        for ex in (w//4, w//2, w*3//4):
            pygame.draw.ellipse(s, dim,              (ex-7, h-12, 14, 12))
            pygame.draw.ellipse(s, (120, 0, 255, 150),(ex-5, h-10, 10, 10))

        return s

    def _move(self):
        self.y += self.speed
        # Slowly drift toward player's x
        px  = self.game.player.x
        dx  = px - self.x
        self.x += min(abs(dx), 0.55) * (1 if dx > 0 else -1)
        self.x = max(55, min(SCREEN_WIDTH - 55, self.x))

    def _fire(self):
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy) or 1
        for ox in (-18, 18):
            b = EnemyBullet(
                int(self.x) + ox, int(self.y) + self.rect.height // 2,
                dx / d * self.bullet_spd, dy / d * self.bullet_spd,
                self.bullet_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)
        self.game.particles.hit_sparks(int(self.x), int(self.y) + self.rect.height // 2,
                                       self.color, count=12)

    def _death_effect(self, px: int, py: int):
        self.game.particles.mega_explosion(px, py, self.color)
        self.game.particles.shake(22)
        self.game.screen_flash((100, 0, 255), 70)
        for _ in range(4):
            ox = random.randint(-70, 70)
            oy = random.randint(-60, 60)
            self.game.particles.spawn_lightning(px, py, px + ox, py + oy, (180, 80, 255))
            self.game.particles.explosion(px + ox//2, py + oy//2,
                                          self.color, count=18, speed=5)


def spawn_enemy(game, kind: str, x: float = None, y: float = -40) -> Enemy:
    if x is None:
        x = random.uniform(40, SCREEN_WIDTH - 40)
    classes = {'scout': Scout, 'fighter': Fighter, 'tank': Tank, 'destroyer': Destroyer}
    cls = classes.get(kind, Scout)
    e   = cls(game, x, y, level=game.current_level)
    game.enemies.add(e)
    game.all_sprites.add(e)
    return e
