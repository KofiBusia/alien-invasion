"""Enemy classes: 5 chapters × 4 tiers = 20 enemy types."""

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

        self.is_elite = False

        self.x     = float(x)
        self.y     = float(y)
        self._tick = 0
        self._shoot_timer = random.randint(0, self.shoot_cd) if self.shoot_cd else 0
        self._zig_dir  = random.choice([-1, 1])
        self._zig_timer= 0
        self._hit_flash= 0

        self._dying       = False
        self._dying_timer = 0

        self.image = self._build_image()
        self._orig = self.image.copy()
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

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

    def make_elite(self):
        """Upgrade to elite: boosted stats + gold visual baked onto self._orig."""
        self.is_elite    = True
        self.max_health  = int(self.max_health * 1.8)
        self.health      = self.max_health
        self.damage      = int(self.damage * 1.6)
        self.score_val   = int(self.score_val * 3)
        self.coin_val    = int(self.coin_val * 3)
        if self.shoot_cd:
            self.shoot_cd = max(400, int(self.shoot_cd * 0.70))

        # Bake gold border + ELITE badge onto _orig so it survives every-frame reset
        w, h = self._orig.get_size()
        for t in range(3):
            alpha = 220 - t * 50
            pygame.draw.rect(self._orig, (255, 200, 0, alpha),
                             (t, t, w - t * 2, h - t * 2), 1)
        font = pygame.font.SysFont('consolas', 9, bold=True)
        badge = font.render('ELITE', True, (255, 220, 0))
        self._orig.blit(badge, (2, 2))
        self.image = self._orig.copy()

    def update(self):
        self._tick += 1

        if self._dying:
            self._dying_timer -= 1
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
        elif self.pattern == 'weave':
            self.x = max(30, min(SCREEN_WIDTH-30,
                                 self.x + math.sin(self._tick * 0.09) * self.speed * 1.8))
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


# ── Chapter 1: First Contact ──────────────────────────────────────────────────

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
        if self._diving:
            self.x += self._dive_vx
            self.y += self._dive_vy
            self._dive_cd = max(0, self._dive_cd - 1)
            if self._dive_cd == 0:
                self._diving  = False
                self._dive_cd = random.randint(300, 500)
            return
        self.y += self.speed
        self._dive_cd = max(0, self._dive_cd - 1)
        if self._dive_cd == 0:
            px, py = self.game.player.x, self.game.player.y
            if self.y < py - 40:
                dx = px - self.x
                dy = py - self.y
                d  = math.hypot(dx, dy) or 1
                spd = self.speed * 6.5
                self._dive_vx = dx / d * spd
                self._dive_vy = dy / d * spd
                self._diving  = True
                self._dive_cd = 48
                self.game.particles.hit_sparks(int(self.x), int(self.y), self.color, count=10)
            else:
                self._dive_cd = random.randint(120, 260)
            return
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
    KIND = 'destroyer'

    def _build_image(self) -> pygame.Surface:
        w, h = self.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = self.color
        dim   = tuple(max(0,  v - 50) for v in c)
        br    = tuple(min(255, v + 90) for v in c)
        glow  = (min(255, c[0]+40), min(255, c[1]+30), 255)
        pts = [(w//2, 0), (w-4, h//5), (w, h*2//3),
               (w*2//3, h), (w//3, h), (0, h*2//3), (4, h//5)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)
        ridge = [(w//2, 8), (w//2+14, h//3), (w//2+9, h*2//3-8),
                 (w//2, h-12), (w//2-9, h*2//3-8), (w//2-14, h//3)]
        pygame.draw.polygon(s, dim, ridge)
        pygame.draw.polygon(s, br, ridge, 1)
        for tx in (6, w - 18):
            pygame.draw.rect(s, dim, (tx, h//3+2, 12, 30), border_radius=3)
            pygame.draw.rect(s, br,  (tx+1, h//3+3, 10, 28), border_radius=2, width=1)
            bx = tx + 6
            pygame.draw.rect(s, (200, 80, 255), (bx-3, h//3+28, 6, 14), border_radius=2)
            pygame.draw.circle(s, glow, (bx, h//3+42), 5)
        pygame.draw.ellipse(s, (70, 0, 180, 190),  (w//2-14, 12, 28, 36))
        pygame.draw.ellipse(s, (150, 0, 255, 220),  (w//2-10, 16, 20, 26))
        pygame.draw.ellipse(s, (220, 100, 255, 255),(w//2-6,  20, 12, 16))
        pygame.draw.ellipse(s, (255, 255, 255),      (w//2-3,  24,  6,  8))
        for ex in (w//4, w//2, w*3//4):
            pygame.draw.ellipse(s, dim,              (ex-7, h-12, 14, 12))
            pygame.draw.ellipse(s, (120, 0, 255, 150),(ex-5, h-10, 10, 10))
        return s

    def _move(self):
        self.y += self.speed
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


# ── Chapter 2: Deep Space Assault ────────────────────────────────────────────

class Phantom(Enemy):
    """Cloaking scout — invisible for 2 s every 3 s, immune while cloaked."""
    KIND = 'phantom'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._cloak_cd    = random.randint(90, 160)
        self._cloaked     = False
        self._cloak_timer = 0

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color  # cyan-blue
        dim  = tuple(max(0, v-60) for v in c)
        br   = tuple(min(255, v+80) for v in c)
        # Thin swept-wing shape
        pts  = [(w//2, 0), (w, h*2//3), (w*3//4, h), (w//4, h), (0, h*2//3)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)
        # Cockpit
        pygame.draw.ellipse(s, br, (w//2-5, h//4, 10, 14))
        # Wing lines
        pygame.draw.line(s, dim, (w//4, h//2), (0, h*2//3), 2)
        pygame.draw.line(s, dim, (w*3//4, h//2), (w, h*2//3), 2)
        return s

    def update(self):
        self._tick += 1
        if self._cloaked:
            self._cloak_timer -= 1
            if self._cloak_timer <= 0:
                self._cloaked = False
                self._cloak_cd = random.randint(120, 200)
                self._orig.set_alpha(255)
        else:
            self._cloak_cd -= 1
            if self._cloak_cd <= 0:
                self._cloaked     = True
                self._cloak_timer = 80
                self._orig.set_alpha(35)

        if self._dying:
            self._dying_timer -= 1
            frac = self._dying_timer / 8
            sz   = (max(1, int(self.size[0]*frac)), max(1, int(self.size[1]*frac)))
            self.image = pygame.transform.scale(self._orig, sz)
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
            flash.fill((255,255,255,100), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = flash
        else:
            self.image = self._orig

        self.rect.center = (int(self.x), int(self.y))
        if self.y > SCREEN_HEIGHT + 60:
            self.kill()

    def take_damage(self, amount: int) -> bool:
        if self._cloaked:
            return False
        return super().take_damage(amount)

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=20, speed=5)
        self.game.particles.smoke_puff(px, py, count=10)
        self.game.particles.shake(5)


class Interceptor(Fighter):
    """Upgraded Fighter — dives faster, dodges more aggressively."""
    KIND = 'interceptor'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._dive_cd = random.randint(120, 240)  # dives more often

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color  # orange
        dim  = tuple(max(0, v-55) for v in c)
        br   = tuple(min(255, v+70) for v in c)
        # Arrow-head shape
        pts  = [(w//2, 0), (w, h//3), (w-6, h), (w//4+2, h-8), (w*3//4-2, h-8), (6, h), (0, h//3)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 2)
        pygame.draw.ellipse(s, br, (w//2-6, 6, 12, 16))
        pygame.draw.rect(s, dim, (0, h//2, 6, 12), border_radius=3)
        pygame.draw.rect(s, dim, (w-6, h//2, 6, 12), border_radius=3)
        pygame.draw.rect(s, br,  (w//2-4, h-10, 8, 10), border_radius=2)
        return s

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=34, speed=8)
        self.game.particles.fire_ring(px, py, self.color, count=20, radius=36)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=80, speed=6)
        self.game.particles.shake(8)


class Goliath(Tank):
    """Heavy upgraded Tank — fires explosive spread."""
    KIND = 'goliath'

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-45) for v in c)
        br   = tuple(min(255, v+55) for v in c)
        # Wide hexagonal hull
        pts = [(w//2, 0), (w-6, h//4), (w, h-16), (w*3//4, h), (w//4, h), (0, h-16), (6, h//4)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 2)
        # Armour bands
        pygame.draw.rect(s, dim, (0, h//3, w, 5))
        pygame.draw.rect(s, dim, (0, h*2//3, w, 5))
        pygame.draw.rect(s, br,  (1, h//3+1, w-2, 3))
        # Twin cannons
        for cx_ in (w//4, w*3//4):
            pygame.draw.rect(s, dim, (cx_-4, h-20, 8, 20), border_radius=2)
            pygame.draw.circle(s, br,  (cx_, h-20), 5)
        # Reactor
        pygame.draw.ellipse(s, (220, 110, 0, 200), (w//2-8, h//4, 16, 22))
        pygame.draw.ellipse(s, (255, 200, 50, 255), (w//2-5, h//4+3, 10, 14))
        return s

    def _fire(self):
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d      = math.hypot(dx, dy) or 1
        # 3-way spread
        for spread_ang in (-15, 0, 15):
            ra = math.radians(spread_ang)
            ndx = dx/d * math.cos(ra) - dy/d * math.sin(ra)
            ndy = dx/d * math.sin(ra) + dy/d * math.cos(ra)
            b = EnemyBullet(int(self.x), int(self.y)+self.rect.height//2,
                            ndx * self.bullet_spd, ndy * self.bullet_spd,
                            self.bullet_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=50, speed=9, size=7)
        self.game.particles.fire_ring(px, py, self.color, count=25, radius=50)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=120, speed=7)
        self.game.particles.debris_burst(px, py, self.color, count=22)
        self.game.particles.shake(16)
        self.game.screen_flash(self.color, 45)


class Annihilator(Destroyer):
    """Upgraded Destroyer — triple explosive cannon, higher HP."""
    KIND = 'annihilator'

    def _build_image(self):
        w, h = self.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = self.color
        dim = tuple(max(0, v-50) for v in c)
        br  = tuple(min(255, v+80) for v in c)
        # Aggressive wedge hull
        pts = [(w//2, 0), (w, h//4), (w-4, h*3//4), (w*3//4+4, h), (w//4-4, h), (4, h*3//4), (0, h//4)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)
        # Triple cannon bays
        for cx_ in (w//5, w//2, w*4//5):
            pygame.draw.rect(s, dim, (cx_-5, h-24, 10, 24), border_radius=3)
            pygame.draw.circle(s, br, (cx_, h-24), 6)
            pygame.draw.circle(s, (255, 200, 50), (cx_, h-5), 4)
        # Central shield sphere
        pygame.draw.ellipse(s, (200, 80, 0, 200), (w//2-12, 8, 24, 34))
        pygame.draw.ellipse(s, (255, 160, 30, 255), (w//2-8, 13, 16, 22))
        return s

    def _fire(self):
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy) or 1
        for spread in (-22, 0, 22):
            ra = math.radians(spread)
            ndx = dx/d * math.cos(ra) - dy/d * math.sin(ra)
            ndy = dx/d * math.sin(ra) + dy/d * math.cos(ra)
            b = EnemyBullet(
                int(self.x), int(self.y) + self.rect.height // 2,
                ndx * self.bullet_spd, ndy * self.bullet_spd,
                self.bullet_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _death_effect(self, px, py):
        self.game.particles.mega_explosion(px, py, self.color)
        self.game.particles.shake(26)
        self.game.screen_flash(self.color, 80)
        for _ in range(5):
            ox = random.randint(-90, 90)
            oy = random.randint(-70, 70)
            self.game.particles.explosion(px+ox//2, py+oy//2, self.color, count=20, speed=6)


# ── Chapter 3: Nebula Wars ─────────────────────────────────────────────────────

class Specter(Enemy):
    """Phase-shifting scout — periodically immune and semi-transparent."""
    KIND = 'specter'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._phase_cd    = random.randint(100, 180)
        self._phased      = False
        self._phase_timer = 0

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color  # bright green
        dim  = tuple(max(0, v-70) for v in c)
        br   = tuple(min(255, v+60) for v in c)
        # Curved organic shape
        pts  = [(w//2, 0), (w-4, h//3), (w, h*3//4), (w*3//4, h), (w//4, h), (0, h*3//4), (4, h//3)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)
        # Inner core
        pygame.draw.ellipse(s, br, (w//2-7, h//4, 14, 18))
        pygame.draw.ellipse(s, (255,255,255,200), (w//2-4, h//4+2, 8, 10))
        return s

    def update(self):
        self._tick += 1
        if self._phased:
            self._phase_timer -= 1
            if self._phase_timer <= 0:
                self._phased = False
                self._phase_cd = random.randint(130, 220)
                self._orig.set_alpha(255)
        else:
            self._phase_cd -= 1
            if self._phase_cd <= 0:
                self._phased      = True
                self._phase_timer = 60
                self._orig.set_alpha(50)

        if self._dying:
            self._dying_timer -= 1
            frac = self._dying_timer / 8
            sz = (max(1, int(self.size[0]*frac)), max(1, int(self.size[1]*frac)))
            self.image = pygame.transform.scale(self._orig, sz)
            self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self._dying_timer <= 0:
                self._finish_die()
            return

        self._move()
        if self.can_shoot:
            self._try_shoot()

        if self._hit_flash > 0 and not self._phased:
            self._hit_flash -= 1
            flash = self._orig.copy()
            flash.fill((255,255,255,150), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = flash
        else:
            self.image = self._orig

        self.rect.center = (int(self.x), int(self.y))
        if self.y > SCREEN_HEIGHT + 60:
            self.kill()

    def take_damage(self, amount):
        if self._phased:
            return False
        return super().take_damage(amount)

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=18, speed=5)
        self.game.particles.fire_ring(px, py, self.color, count=12, radius=24)
        self.game.particles.shake(5)


class Raptor(Fighter):
    """Nebula Fighter — faster dive speed, fires homing shots."""
    KIND = 'raptor'

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-55) for v in c)
        br   = tuple(min(255, v+70) for v in c)
        pts  = [(w//2, 0), (w, h//4), (w-8, h), (w//2+4, h-10), (w//2-4, h-10), (8, h), (0, h//4)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)
        # Wing claws
        pygame.draw.line(s, br, (0, h//4), (w//4, h//2+4), 3)
        pygame.draw.line(s, br, (w, h//4), (w*3//4, h//2+4), 3)
        pygame.draw.ellipse(s, br, (w//2-5, h//5, 10, 14))
        return s

    def _fire(self):
        # Fires a homing-ish shot (aimed ahead of player)
        px, py = self.game.player.x, self.game.player.y
        pvx = getattr(self.game.player, 'vx', 0)
        pvy = getattr(self.game.player, 'vy', 0)
        # Lead target slightly
        target_x = px + pvx * 12
        target_y = py + pvy * 12
        dx = target_x - self.x
        dy = target_y - self.y
        d  = math.hypot(dx, dy) or 1
        b  = EnemyBullet(int(self.x), int(self.y)+self.rect.height//2,
                         dx/d*self.bullet_spd, dy/d*self.bullet_spd, self.bullet_dmg)
        self.game.enemy_bullets.add(b)
        self.game.all_sprites.add(b)

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=36, speed=8)
        self.game.particles.fire_ring(px, py, self.color, count=22, radius=40)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=85, speed=6)
        self.game.particles.shake(9)


class Leviathan(Tank):
    """Nebula Tank — regenerating shield pool."""
    KIND = 'leviathan'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._extra_shield     = int(80 * game.level_cfg['health_mult'])
        self._max_extra_shield = self._extra_shield
        self._shield_regen_cd  = 0

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-50) for v in c)
        br   = tuple(min(255, v+60) for v in c)
        # Bulky rounded hull
        pygame.draw.rect(s, c,   (2, 6, w-4, h-12), border_radius=8)
        pygame.draw.rect(s, dim, (2, 6, w-4, h-12), border_radius=8, width=3)
        # Shield emitters on sides
        for sx in (0, w-12):
            pygame.draw.rect(s, br, (sx, h//3, 12, h//3), border_radius=4)
            pygame.draw.circle(s, (0, 255, 200), (sx+6, h//2), 5)
        # Main gun
        pygame.draw.rect(s, dim, (w//2-6, h-18, 12, 18), border_radius=3)
        pygame.draw.circle(s, br, (w//2, h-18), 7)
        # Core
        pygame.draw.ellipse(s, (0, 200, 120, 220), (w//2-8, 12, 16, 22))
        pygame.draw.ellipse(s, (100, 255, 200, 255),(w//2-5, 16, 10, 14))
        return s

    def take_damage(self, amount):
        if self._extra_shield > 0:
            absorbed = min(self._extra_shield, amount)
            self._extra_shield -= absorbed
            amount -= absorbed
            self._hit_flash = 4
            self.game.particles.shield_ripple(self.x, self.y, 40)
            self.game.save.increment_stat('damage_dealt', absorbed)
            if amount <= 0:
                return False
        return super().take_damage(amount)

    def update(self):
        super().update()
        if not self._dying:
            self._shield_regen_cd = max(0, self._shield_regen_cd - 1)
            if self._shield_regen_cd == 0 and self._extra_shield < self._max_extra_shield:
                self._extra_shield = min(self._max_extra_shield, self._extra_shield + 1)
                if self._extra_shield >= self._max_extra_shield:
                    self._shield_regen_cd = 180  # wait before next regen cycle

    def draw_health_bar(self, surface):
        super().draw_health_bar(surface)
        if self._dying or self._extra_shield <= 0:
            return
        bw    = self.rect.width
        bh    = 4
        bx    = self.rect.left
        by    = self.rect.top - 15
        ratio = self._extra_shield / max(1, self._max_extra_shield)
        pygame.draw.rect(surface, (0, 60, 40), (bx, by, bw, bh), border_radius=2)
        pygame.draw.rect(surface, (0, 220, 160), (bx, by, int(bw*ratio), bh), border_radius=2)

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=48, speed=9, size=7)
        self.game.particles.fire_ring(px, py, self.color, count=24, radius=50)
        self.game.particles.shockwave_ring(px, py, (0, 255, 180), max_radius=130, speed=7)
        self.game.particles.shake(16)
        self.game.screen_flash(self.color, 40)


class Devastator(Destroyer):
    """Nebula Destroyer — two-phase burst cannon."""
    KIND = 'devastator'

    def _build_image(self):
        w, h = self.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = self.color  # dark green
        dim = tuple(max(0, v-50) for v in c)
        br  = tuple(min(255, v+80) for v in c)
        pts = [(w//2, 0), (w-2, h//5), (w+2, h*2//3),
               (w*2//3+2, h+2), (w//3-2, h+2), (-2, h*2//3), (2, h//5)]
        pts = [(max(0,min(w,x)), max(0,min(h,y))) for x,y in pts]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, br, pts, 2)
        # Organic ribs
        for rib_y in range(h//4, h-10, h//5):
            pygame.draw.line(s, br, (w//4, rib_y), (w*3//4, rib_y), 2)
        # Quad cannons
        for cx_ in (w//6, w*2//5, w*3//5, w*5//6):
            pygame.draw.rect(s, dim, (cx_-4, h-20, 8, 20), border_radius=2)
            pygame.draw.circle(s, br, (cx_, h-3), 4)
        # Bio-core
        pygame.draw.ellipse(s, (0, 180, 80, 200), (w//2-12, 10, 24, 32))
        pygame.draw.ellipse(s, (50, 255, 150, 255),(w//2-7, 16, 14, 18))
        return s

    def _fire(self):
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy) or 1
        for spread in (-28, -10, 10, 28):
            ra = math.radians(spread)
            ndx = dx/d * math.cos(ra) - dy/d * math.sin(ra)
            ndy = dx/d * math.sin(ra) + dy/d * math.cos(ra)
            b = EnemyBullet(
                int(self.x), int(self.y) + self.rect.height // 2,
                ndx * self.bullet_spd, ndy * self.bullet_spd,
                self.bullet_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)


# ── Chapter 4: Dark Matter ─────────────────────────────────────────────────────

class Shade(Enemy):
    """Dark Matter scout — fast, blinks in and out of visibility."""
    KIND = 'shade'

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-60) for v in c)
        br   = tuple(min(255, v+80) for v in c)
        # Dark angular shape
        pts  = [(w//2, 2), (w-2, h//2), (w*2//3, h), (w//3, h), (2, h//2)]
        pygame.draw.polygon(s, dim, pts)
        pygame.draw.polygon(s, c, pts, 2)
        pygame.draw.ellipse(s, br, (w//2-5, h//3, 10, 14))
        # Void tendrils
        for ang in (30, 90, 150):
            a = math.radians(ang)
            ex, ey = w//2 + int(10*math.cos(a)), h//2 + int(10*math.sin(a))
            pygame.draw.line(s, c, (w//2, h//2), (ex, ey), 2)
        return s

    def update(self):
        self._tick += 1
        # Flicker every 20 frames
        if self._tick % 20 < 4:
            self._orig.set_alpha(60)
        else:
            self._orig.set_alpha(220)
        # Call parent update but skip the alpha reset
        if self._dying:
            self._dying_timer -= 1
            frac = self._dying_timer / 8
            sz = (max(1, int(self.size[0]*frac)), max(1, int(self.size[1]*frac)))
            self.image = pygame.transform.scale(self._orig, sz)
            self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self._dying_timer <= 0:
                self._finish_die()
            return
        self._move()
        if self.can_shoot:
            self._try_shoot()
        self.image = self._orig
        self.rect.center = (int(self.x), int(self.y))
        if self.y > SCREEN_HEIGHT + 60:
            self.kill()

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=20, speed=6)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=50, speed=4)
        self.game.particles.shake(6)


class Marauder(Fighter):
    """Dark Matter Fighter — fires burst of 3 shots in quick succession."""
    KIND = 'marauder'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._burst_count   = 0
        self._burst_cd      = 0

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-55) for v in c)
        br   = tuple(min(255, v+70) for v in c)
        # Dark jagged hull
        pts  = [(w//2, 0), (w, h//3), (w-4, h), (w//2+6, h-8), (w//2-6, h-8), (4, h), (0, h//3)]
        pygame.draw.polygon(s, dim, pts)
        pygame.draw.polygon(s, c, pts, 2)
        # Side guns
        for sx in (0, w-8):
            pygame.draw.rect(s, c, (sx, h//2-3, 8, 6), border_radius=2)
            pygame.draw.circle(s, br, (sx+4, h//2), 3)
        pygame.draw.ellipse(s, br, (w//2-5, h//4, 10, 14))
        return s

    def _try_shoot(self):
        if self._burst_cd > 0:
            self._burst_cd -= 1
            if self._burst_count > 0:
                self._burst_count -= 1
                self._fire()
                self._burst_cd = 8
            return
        if self._shoot_timer > 0:
            self._shoot_timer -= 1
            return
        self._shoot_timer  = self.shoot_cd
        self._burst_count  = 2   # fire 3 total (1 now + 2 more)
        self._burst_cd     = 8
        self._fire()

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=38, speed=8)
        self.game.particles.fire_ring(px, py, self.color, count=20, radius=40)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=90, speed=6)
        self.game.particles.shake(10)


class Colossus(Tank):
    """Dark Matter Tank — armored, first 40% of damage absorbed."""
    KIND = 'colossus'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._armor_hp     = int(self.max_health * 0.4)
        self._max_armor    = self._armor_hp
        self._armor_broken = False

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-50) for v in c)
        br   = tuple(min(255, v+60) for v in c)
        # Boxy armored hull
        pygame.draw.rect(s, dim, (0, 0, w, h), border_radius=6)
        pygame.draw.rect(s, c,   (4, 4, w-8, h-8), border_radius=5)
        pygame.draw.rect(s, dim, (4, 4, w-8, h-8), border_radius=5, width=2)
        # Armor plates
        for ry in range(h//5, h-8, h//4):
            pygame.draw.rect(s, br, (6, ry, w-12, 5), border_radius=2)
        # Heavy cannon
        pygame.draw.rect(s, dim, (w//2-8, h-22, 16, 22), border_radius=4)
        pygame.draw.circle(s, br, (w//2, h-22), 9)
        pygame.draw.circle(s, (80, 0, 160, 220), (w//2, h-22), 5)
        # Eye
        pygame.draw.ellipse(s, (100, 0, 200, 220), (w//2-9, 10, 18, 24))
        pygame.draw.ellipse(s, (200, 0, 255, 255), (w//2-5, 14, 10, 15))
        return s

    def take_damage(self, amount):
        if self._armor_hp > 0 and not self._armor_broken:
            absorbed = min(self._armor_hp, amount // 2 + 1)
            self._armor_hp -= absorbed
            amount = max(1, amount - absorbed)
            self.game.save.increment_stat('damage_dealt', absorbed)
            self._hit_flash = 4
            if self._armor_hp <= 0:
                self._armor_broken = True
                self.game.particles.explosion(int(self.x), int(self.y), (150, 150, 150), count=20)
                self.game.ui.show_message('ARMOR BROKEN!', int(self.x), int(self.y)-30, (255,180,0), 'sm')
        return super().take_damage(amount)

    def draw_health_bar(self, surface):
        super().draw_health_bar(surface)
        if self._armor_broken or self._dying or self._armor_hp <= 0:
            return
        bw    = self.rect.width
        bx    = self.rect.left
        by    = self.rect.top - 15
        ratio = self._armor_hp / max(1, self._max_armor)
        pygame.draw.rect(surface, (40, 40, 40),   (bx, by, bw, 4), border_radius=2)
        pygame.draw.rect(surface, (180, 180, 220), (bx, by, int(bw*ratio), 4), border_radius=2)


class Obliterator(Destroyer):
    """Dark Matter Destroyer — omni-directional death cannon."""
    KIND = 'obliterator'

    def _build_image(self):
        w, h = self.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = self.color
        dim = tuple(max(0, v-55) for v in c)
        br  = tuple(min(255, v+80) for v in c)
        # Dark star shape
        pts = [(w//2, 0), (w-6, h//6), (w+4, h//2),
               (w*3//4, h), (w//4, h), (-4, h//2), (6, h//6)]
        pts = [(max(0,min(w,x)), max(0,min(h,y))) for x,y in pts]
        pygame.draw.polygon(s, dim, pts)
        pygame.draw.polygon(s, c, pts, 2)
        # Ring of guns
        cx_, cy_ = w//2, h//2
        for ang in range(0, 360, 60):
            a = math.radians(ang)
            gx = cx_ + int(22*math.cos(a))
            gy = cy_ + int(22*math.sin(a))
            pygame.draw.circle(s, c, (gx, gy), 5)
            pygame.draw.circle(s, br, (gx, gy), 3)
        # Core
        pygame.draw.circle(s, dim, (cx_, cy_), 14)
        pygame.draw.circle(s, (140, 0, 220), (cx_, cy_), 10)
        pygame.draw.circle(s, (220, 80, 255), (cx_, cy_), 5)
        return s

    def _fire(self):
        # Fire 6-way spread
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy) or 1
        base_ang = math.atan2(dy, dx)
        for i in range(6):
            a = base_ang + math.radians(i * 60 - 90)
            b = EnemyBullet(
                int(self.x), int(self.y) + self.rect.height // 2,
                math.cos(a) * self.bullet_spd,
                math.sin(a) * self.bullet_spd,
                self.bullet_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _death_effect(self, px, py):
        self.game.particles.mega_explosion(px, py, self.color)
        self.game.particles.shake(28)
        self.game.screen_flash(self.color, 85)
        for i in range(8):
            ang = math.radians(i * 45)
            ox  = int(80 * math.cos(ang))
            oy  = int(80 * math.sin(ang))
            self.game.particles.explosion(px+ox, py+oy, self.color, count=16, speed=5)


# ── Chapter 5: Apocalypse ─────────────────────────────────────────────────────

class Reaper(Enemy):
    """Apocalypse scout — fastest enemy, erratic darting movement."""
    KIND = 'reaper'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._dart_cd  = random.randint(40, 90)
        self._dart_vx  = 0.0
        self._darting  = False
        self._dart_t   = 0

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-60) for v in c)
        br   = tuple(min(255, v+60) for v in c)
        # Blade shape
        pts  = [(w//2, 0), (w, h*2//3), (w*3//4, h), (w//4, h), (0, h*2//3)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 3)
        # Scythe detail
        pygame.draw.line(s, br, (w//4, h//2), (w//2, h//6), 2)
        pygame.draw.line(s, br, (w*3//4, h//2), (w//2, h//6), 2)
        pygame.draw.circle(s, br, (w//2, h//2), 6)
        pygame.draw.circle(s, dim, (w//2, h//2), 3)
        return s

    def _move(self):
        self.y += self.speed * 0.7  # slower vertical, faster darts
        self._dart_cd = max(0, self._dart_cd - 1)
        if self._dart_cd == 0 and not self._darting:
            self._darting = True
            self._dart_t  = 20
            self._dart_cd = random.randint(50, 100)
            px = self.game.player.x
            self._dart_vx = (px - self.x) / 20.0 * 1.8
        if self._darting:
            self.x += self._dart_vx
            self._dart_t -= 1
            if self._dart_t <= 0:
                self._darting = False
        self.x = max(20, min(SCREEN_WIDTH-20, self.x))

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=24, speed=7)
        self.game.particles.fire_ring(px, py, self.color, count=16, radius=28)
        self.game.particles.shake(7)


class Predator(Fighter):
    """Apocalypse Fighter — cloaks between attacks, dive-bombs."""
    KIND = 'predator'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._cloak_cd    = random.randint(80, 130)
        self._cloaked     = False
        self._cloak_timer = 0
        self._dive_cd     = random.randint(100, 200)  # dives very often

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color
        dim  = tuple(max(0, v-55) for v in c)
        br   = tuple(min(255, v+70) for v in c)
        # Sharp predator shape
        pts  = [(w//2, 0), (w, h//4), (w-2, h*3//4), (w*3//4, h), (w//4, h), (2, h*3//4), (0, h//4)]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 3)
        # Predator eye stripes
        pygame.draw.line(s, br, (w//4, h//3), (w*3//4, h//3), 2)
        pygame.draw.line(s, br, (w//3, h//2), (w*2//3, h//2), 2)
        pygame.draw.ellipse(s, br, (w//2-6, h//4, 12, 16))
        pygame.draw.ellipse(s, dim, (w//2-3, h//4+3, 6, 8))
        return s

    def update(self):
        self._tick += 1
        if self._cloaked:
            self._cloak_timer -= 1
            if self._cloak_timer <= 0:
                self._cloaked = False
                self._cloak_cd = random.randint(80, 140)
                self._orig.set_alpha(255)
        else:
            self._cloak_cd -= 1
            if self._cloak_cd <= 0:
                self._cloaked     = True
                self._cloak_timer = 50
                self._orig.set_alpha(40)
        super().update()

    def take_damage(self, amount):
        if self._cloaked:
            return False
        return super().take_damage(amount)

    def _death_effect(self, px, py):
        self.game.particles.explosion(px, py, self.color, count=40, speed=9)
        self.game.particles.fire_ring(px, py, self.color, count=24, radius=44)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=95, speed=7)
        self.game.particles.shake(12)
        self.game.screen_flash(self.color, 50)


class Titan(Tank):
    """Apocalypse Tank — two phases: armored (slow) then ENRAGED (fast)."""
    KIND = 'titan'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._phase2       = False
        self._base_speed   = self.speed

    def _build_image(self):
        w, h = self.size
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        c    = self.color if not self._phase2 else (255, 80, 0)
        dim  = tuple(max(0, v-50) for v in c)
        br   = tuple(min(255, v+60) for v in c)
        # Titan hull — massive and angular
        pts = [(w//2, 0), (w-4, h//5), (w+2, h*2//3), (w*3//4, h), (w//4, h), (-2, h*2//3), (4, h//5)]
        pts = [(max(0,min(w,x)), max(0,min(h,y))) for x,y in pts]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 3)
        # Heavy armor ribbing
        for ry in range(h//4, h-10, h//5):
            pygame.draw.rect(s, dim, (6, ry, w-12, 4))
            pygame.draw.line(s, br, (8, ry+1), (w-8, ry+1), 1)
        # Quad heavy cannons
        for cx_ in (w//5, w*2//5, w*3//5, w*4//5):
            pygame.draw.rect(s, dim, (cx_-5, h-20, 10, 20), border_radius=3)
            col2 = (255, 100, 0) if self._phase2 else br
            pygame.draw.circle(s, col2, (cx_, h-3), 5)
        # Core reactor
        core_c = (255, 60, 0) if self._phase2 else (200, 0, 0, 200)
        pygame.draw.ellipse(s, core_c, (w//2-12, 8, 24, 32))
        pygame.draw.ellipse(s, (255, 150, 50, 255), (w//2-7, 14, 14, 18))
        return s

    def take_damage(self, amount):
        result = super().take_damage(amount)
        if not self._phase2 and self.health <= self.max_health * 0.5 and self.health > 0:
            self._phase2 = True
            self.speed   = self._base_speed * 2.4
            self.bullet_spd *= 1.5
            self._orig   = self._build_image()
            self.game.particles.mega_explosion(int(self.x), int(self.y), self.color)
            self.game.screen_flash((255, 60, 0), 80)
            from settings import SCREEN_WIDTH, SCREEN_HEIGHT
            self.game.ui.show_message('TITAN ENRAGED!',
                                      SCREEN_WIDTH//2, SCREEN_HEIGHT//3,
                                      (255, 80, 0), 'lg')
        return result

    def _death_effect(self, px, py):
        self.game.particles.mega_explosion(px, py, self.color)
        self.game.particles.explosion(px, py, (255, 100, 0), count=60, speed=10, size=8)
        self.game.particles.shockwave_ring(px, py, (255, 80, 0), max_radius=160, speed=8)
        self.game.particles.shake(22)
        self.game.screen_flash((255, 50, 0), 80)


class Nemesis(Destroyer):
    """Apocalypse Destroyer — ultimate enemy, multi-phase attack patterns."""
    KIND = 'nemesis'

    def __init__(self, game, x, y, level=1):
        super().__init__(game, x, y, level)
        self._attack_phase = 0
        self._attack_cd    = 0

    def _build_image(self):
        w, h = self.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = self.color  # pure red
        dim = tuple(max(0, v-55) for v in c)
        br  = tuple(min(255, v+60) for v in c)
        # Supreme warship hull
        pts = [(w//2, 0), (w-2, h//6), (w+4, h//2), (w*3//4+2, h), (w//4-2, h), (-4, h//2), (2, h//6)]
        pts = [(max(0,min(w,x)), max(0,min(h,y))) for x,y in pts]
        pygame.draw.polygon(s, c, pts)
        pygame.draw.polygon(s, dim, pts, 3)
        # Multiple weapon banks
        for row in range(2):
            for col in range(5):
                gx = int(w * (col+1) / 6)
                gy = h//2 + row * h//4
                pygame.draw.circle(s, dim, (gx, gy), 5)
                pygame.draw.circle(s, br,  (gx, gy), 3)
        # Twin heavy cannons
        for cx_ in (w//4, w*3//4):
            pygame.draw.rect(s, dim, (cx_-7, h-26, 14, 26), border_radius=4)
            pygame.draw.circle(s, br,  (cx_, h-26), 8)
            pygame.draw.circle(s, (255, 0, 0), (cx_, h-4), 5)
        # Command core
        pygame.draw.circle(s, (180, 0, 0, 220), (w//2, h//3), 16)
        pygame.draw.circle(s, (255, 80, 0, 255), (w//2, h//3), 10)
        pygame.draw.circle(s, (255, 220, 0),      (w//2, h//3),  5)
        return s

    def _fire(self):
        self._attack_phase = (self._attack_phase + 1) % 3
        px, py = self.game.player.x, self.game.player.y
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy) or 1

        if self._attack_phase == 0:
            # Twin heavy shots
            for ox in (-22, 22):
                b = EnemyBullet(
                    int(self.x) + ox, int(self.y) + self.rect.height // 2,
                    dx / d * self.bullet_spd, dy / d * self.bullet_spd,
                    self.bullet_dmg, explosive=True)
                self.game.enemy_bullets.add(b)
                self.game.all_sprites.add(b)

        elif self._attack_phase == 1:
            # 5-way spread
            for spread in (-35, -17, 0, 17, 35):
                ra = math.radians(spread)
                ndx = dx/d * math.cos(ra) - dy/d * math.sin(ra)
                ndy = dx/d * math.sin(ra) + dy/d * math.cos(ra)
                b = EnemyBullet(
                    int(self.x), int(self.y) + self.rect.height // 2,
                    ndx * self.bullet_spd, ndy * self.bullet_spd,
                    int(self.bullet_dmg * 0.7))
                self.game.enemy_bullets.add(b)
                self.game.all_sprites.add(b)

        else:
            # Aimed double shot
            for offset_t in (0, 12):
                b = EnemyBullet(
                    int(self.x), int(self.y) + self.rect.height // 2 + offset_t,
                    dx / d * self.bullet_spd * 1.3,
                    dy / d * self.bullet_spd * 1.3,
                    int(self.bullet_dmg * 1.4), explosive=True)
                self.game.enemy_bullets.add(b)
                self.game.all_sprites.add(b)

    def _death_effect(self, px, py):
        self.game.particles.mega_explosion(px, py, self.color)
        self.game.particles.shake(32)
        self.game.screen_flash((255, 0, 0), 100)
        for i in range(8):
            ang = math.radians(i * 45)
            ox = int(100 * math.cos(ang)); oy = int(100 * math.sin(ang))
            self.game.particles.spawn_lightning(px, py, px+ox, py+oy, (255, 50, 0))
            self.game.particles.explosion(px+ox//2, py+oy//2, self.color, count=22, speed=7)


# ── Factory ───────────────────────────────────────────────────────────────────

_ENEMY_CLASSES = {
    # Ch1
    'scout':       Scout,
    'fighter':     Fighter,
    'tank':        Tank,
    'destroyer':   Destroyer,
    # Ch2
    'phantom':     Phantom,
    'interceptor': Interceptor,
    'goliath':     Goliath,
    'annihilator': Annihilator,
    # Ch3
    'specter':     Specter,
    'raptor':      Raptor,
    'leviathan':   Leviathan,
    'devastator':  Devastator,
    # Ch4
    'shade':       Shade,
    'marauder':    Marauder,
    'colossus':    Colossus,
    'obliterator': Obliterator,
    # Ch5
    'reaper':      Reaper,
    'predator':    Predator,
    'titan':       Titan,
    'nemesis':     Nemesis,
}


def spawn_enemy(game, kind: str, x: float = None, y: float = -40) -> Enemy:
    if x is None:
        x = random.uniform(40, SCREEN_WIDTH - 40)
    cls = _ENEMY_CLASSES.get(kind, Scout)
    e   = cls(game, x, y, level=game.current_level)
    if random.random() < 0.08:
        e.make_elite()
    game.enemies.add(e)
    game.all_sprites.add(e)
    return e
