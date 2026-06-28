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
        # Brief spin-out animation before destroying
        self._dying       = True
        self._dying_timer = 8
        px, py = int(self.x), int(self.y)
        self.game.particles.explosion(px, py, self.color, count=22, speed=5)
        self.game.particles.shockwave_ring(px, py, self.color, max_radius=55, speed=4)
        self.game.particles.shake(5)
        self.game.audio.play('explosion')
        self._drop_loot()
        self.game.player.score += self.score_val
        self.game.save.increment_stat('kills')

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


class Fighter(Enemy):
    KIND = 'fighter'

    def __init__(self, game, x: float, y: float, level: int = 1):
        super().__init__(game, x, y, level)
        self._dodge_cd    = random.randint(60, 120)
        self._dodge_dir   = 0
        self._dodge_timer = 0

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
        self.y += self.speed

        # Dodge: scan for nearby player bullets
        self._dodge_cd    = max(0, self._dodge_cd - 1)
        self._dodge_timer = max(0, self._dodge_timer - 1)

        if self._dodge_cd == 0:
            for b in self.game.player_bullets:
                dx = b.rect.centerx - self.x
                dy = b.rect.centery - self.y
                if abs(dy) < 120 and abs(dx) < 50:
                    # Bullet is coming toward us — dodge sideways
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


class Tank(Enemy):
    KIND = 'tank'

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


def spawn_enemy(game, kind: str, x: float = None, y: float = -40) -> Enemy:
    if x is None:
        x = random.uniform(40, SCREEN_WIDTH - 40)
    classes = {'scout': Scout, 'fighter': Fighter, 'tank': Tank}
    cls = classes.get(kind, Scout)
    e   = cls(game, x, y, level=game.current_level)
    game.enemies.add(e)
    game.all_sprites.add(e)
    return e
