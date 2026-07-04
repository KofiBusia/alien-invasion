"""Boss class with multiple attack phases, rage mode, and telegraph effects."""

import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, IS_ANDROID
from bullet import EnemyBullet, BossLaser
from powerup import Coin, PowerUp
from enemy import spawn_enemy


class Boss(pygame.sprite.Sprite):
    def __init__(self, game, level: int):
        super().__init__()
        self.game  = game
        self.level = level

        lc              = game.level_cfg
        self.max_health = lc['boss_health']
        self.health     = self.max_health
        self.base_dmg   = lc['boss_damage']

        self.x   = float(SCREEN_WIDTH // 2)
        self.y   = -120.0
        self.vx  = 1.5
        self.vy  = 0.6
        self._entry = True

        self._tick          = 0
        self._phase         = 0
        self._attack_timer  = 0
        self._attack_cd     = 120
        self._pattern_idx   = 0
        self._hit_flash     = 0
        self._laser_charge  = 0
        self._shield_hp     = 200
        self._shield_active = False
        self._summon_cd     = 500

        # Phase 2 cinematic (triggered at 50% HP)
        self._half_triggered = False

        # Rage mode (triggered at 25% HP)
        self._rage_mode      = False
        self._rage_triggered = False
        self._rage_pulse     = 0.0   # oscillating for the rage aura

        # Laser telegraph
        self._laser_warning      = False
        self._laser_warning_timer= 0
        self._laser_warning_x    = 0

        self._warn_played = False

        self.image = self._build_image()
        self._orig = self.image.copy()
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))

    # ── Image ─────────────────────────────────────────────────────────────────
    def _build_image(self) -> pygame.Surface:
        w, h = 160, 120
        s    = pygame.Surface((w, h), pygame.SRCALPHA)
        tier  = min(3, self.level // 5)
        body  = [(140,0,0),(160,0,80),(80,0,160)][tier-1] if tier else (140,0,0)
        glow  = tuple(min(255,v+80) for v in body)
        dim   = tuple(max(0,v-40) for v in body)

        # Main hull
        pts = [(w//2,0),(w,h//3),(w-10,h),(10,h),(0,h//3)]
        pygame.draw.polygon(s, body, pts)
        pygame.draw.polygon(s, glow, pts, 3)

        # Armour panels
        pygame.draw.rect(s, dim, (10, h//2, w-20, h//3), border_radius=6)
        pygame.draw.rect(s, glow, (12, h//2+2, w-24, h//3-4), border_radius=4, width=1)

        # Side cannons
        for sx in [10, w-30]:
            pygame.draw.rect(s, dim, (sx, h//3+5, 20, 40), border_radius=4)
            pygame.draw.rect(s, glow, (sx+2, h//3+7, 16, 36), border_radius=3, width=1)
            pygame.draw.circle(s, glow, (sx+10, h//3+45), 8)

        # Central cannon
        pygame.draw.rect(s, (60,0,0), (w//2-14, h-20, 28, 22), border_radius=5)
        pygame.draw.circle(s, (255,50,50), (w//2, h-4), 10)

        # Eye / cockpit
        pygame.draw.ellipse(s, (255,50,50,200), (w//2-18, 14, 36, 26))
        pygame.draw.ellipse(s, (255,200,200,240), (w//2-10, 18, 20, 16))
        pygame.draw.ellipse(s, (255,255,255), (w//2-5, 22, 10, 8))

        # Engine pods
        for ex in [w//4, w*3//4]:
            pygame.draw.ellipse(s, dim, (ex-12, h-14, 24, 16))
            pygame.draw.ellipse(s, (255,120,0,160), (ex-8, h-12, 16, 12))

        return s

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        self._tick += 1

        # Entry sequence
        if self._entry:
            self.y += 1.2
            if self.y >= 140:
                self._entry = False
            self.rect.center = (int(self.x), int(self.y))
            return

        # Show boss warning once
        if not self._warn_played:
            self._warn_played = True
            self.game.audio.play('boss_warn')

        # Phase transitions (66% / 33%)
        ratio     = self.health / self.max_health
        old_phase = self._phase
        if ratio < 0.33:
            self._phase = 2
        elif ratio < 0.66:
            self._phase = 1

        if self._phase != old_phase:
            self._on_phase_change()

        # Phase 2 cinematic at 50% HP
        if not self._half_triggered and ratio < 0.50:
            self._half_triggered = True
            self._on_half_hp()

        # Rage mode at 25%
        if not self._rage_triggered and ratio < 0.25:
            self._rage_triggered = True
            self._trigger_rage()

        # Laser telegraph countdown
        if self._laser_warning:
            self._laser_warning_timer -= 1
            if self._laser_warning_timer <= 0:
                self._laser_warning = False
                self._fire_telegraphed_laser()

        # Movement
        self._move()

        # Shield (phase 2)
        if self._phase == 2 and self._tick % 300 == 0:
            self._shield_active = True
            self._shield_hp     = 150

        # Rage pulse oscillation
        if self._rage_mode:
            self._rage_pulse = math.sin(self._tick * 0.08)

        # Attack timer
        self._attack_timer += 1
        cd = max(40, self._attack_cd - self._phase * 25)
        if self._rage_mode:
            cd = max(25, cd // 2)
        if self._attack_timer >= cd:
            self._attack_timer = 0
            self._do_attack()

        # Hit flash
        if self._hit_flash > 0:
            self._hit_flash -= 1
            flash = self._orig.copy()
            flash.fill((255,255,255,160), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = flash
        else:
            self.image = self._orig

        self.rect.center = (int(self.x), int(self.y))

    def _move(self):
        speed_mult = 1.5 if self._rage_mode else 1.0
        self.x += self.vx * (1 + self._phase * 0.3) * speed_mult
        self.y += 0.08 * (self._phase + 1)
        if self.x < 100 or self.x > SCREEN_WIDTH - 100:
            self.vx *= -1
        max_y = 200 + self._phase * 30
        if self.y > max_y:
            self.y = max_y
        if self.y < 80:
            self.y = 80

    def _on_phase_change(self):
        self.game.particles.stars_burst(int(self.x), int(self.y), count=60)
        self.game.particles.shake(15)
        self.game.screen_flash((200, 50, 255), 70)

    def _on_half_hp(self):
        """Dramatic cinematic when boss drops to 50% — announces Phase 2."""
        self.game._hitstop_frames = max(self.game._hitstop_frames, 14)
        self.game.screen_flash((255, 80, 0), 110)
        self.game.particles.mega_explosion(int(self.x), int(self.y), (255, 80, 0))
        self.game.particles.shake(22)
        self.game.ui.show_message(
            'PHASE  2', SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90,
            (255, 80, 0), 'xl')
        self.game.ui.show_message(
            'WARNING: Systems Override!', SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30,
            (255, 200, 80), 'md')
        self.game.audio.play('boss_warn')
        # Speed and fire rate escalate
        self.vx *= 1.4
        self._attack_cd = max(60, int(self._attack_cd * 0.75))

    def _trigger_rage(self):
        """Boss goes berserk at 25% HP."""
        self._rage_mode = True
        self.game.particles.mega_explosion(int(self.x), int(self.y), (255, 20, 20))
        self.game.particles.shake(25)
        self.game.screen_flash((255, 0, 0), 130)
        self.game.ui.show_message(
            '⚠ ENRAGED! ⚠', SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80,
            (255, 30, 30), 'xl')
        self.game.audio.play('boss_warn')

    # ── Attack patterns ───────────────────────────────────────────────────────
    PATTERNS = ['spread_burst', 'aimed_volley', 'laser_beam',
                'missile_rain', 'summon_minions', 'spiral']

    def _do_attack(self):
        available = self.PATTERNS[:max(2, 2 + self._phase * 2)]
        pattern   = available[self._pattern_idx % len(available)]
        self._pattern_idx += 1
        getattr(self, f'_atk_{pattern}', self._atk_spread_burst)()

    def _atk_spread_burst(self):
        n     = (8 + self._phase * 4) * (2 if self._rage_mode else 1)
        speed = 5 + self._phase + (2 if self._rage_mode else 0)
        for i in range(n):
            ang = (360 / n) * i
            rad = math.radians(ang)
            b   = EnemyBullet(int(self.x), int(self.y)+50,
                              math.sin(rad)*speed, math.cos(rad)*speed,
                              self.base_dmg)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_aimed_volley(self):
        px, py = self.game.player.x, self.game.player.y
        n      = (3 + self._phase) * (2 if self._rage_mode else 1)
        for i in range(n):
            dx = px - self.x + random.uniform(-30, 30)
            dy = py - self.y
            d  = math.hypot(dx, dy) or 1
            spd= 6 + self._phase + (3 if self._rage_mode else 0)
            b  = EnemyBullet(int(self.x), int(self.y)+50,
                             dx/d*spd, dy/d*spd, self.base_dmg)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_laser_beam(self):
        # Telegraph: show red warning line before firing
        n = 1 + self._phase
        positions = [SCREEN_WIDTH//4, SCREEN_WIDTH//2, SCREEN_WIDTH*3//4]
        for i in range(n):
            lx = positions[i % len(positions)]
            if not self._laser_warning:
                self._laser_warning       = True
                self._laser_warning_timer = 45
                self._laser_warning_x     = lx
            else:
                self._fire_laser_at(lx)

    def _fire_telegraphed_laser(self):
        laser = BossLaser(self._laser_warning_x, self.rect.bottom, 22, self.base_dmg // 8)
        self.game.enemy_bullets.add(laser)
        self.game.all_sprites.add(laser)

    def _fire_laser_at(self, lx: int):
        laser = BossLaser(lx, self.rect.bottom, 22, self.base_dmg // 8)
        self.game.enemy_bullets.add(laser)
        self.game.all_sprites.add(laser)

    def _atk_missile_rain(self):
        count = (3 + self._phase * 2) + (4 if self._rage_mode else 0)
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH-60)
            b = EnemyBullet(x, self.rect.bottom,
                            random.uniform(-1.5, 1.5), 5+self._phase,
                            self.base_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_summon_minions(self):
        n = (2 + self._phase) * (2 if self._rage_mode else 1)
        for _ in range(n):
            kind = random.choice(['scout','fighter'])
            x    = random.randint(60, SCREEN_WIDTH-60)
            spawn_enemy(self.game, kind, x, self.y + 80)

    def _atk_spiral(self):
        n      = 12 + (8 if self._rage_mode else 0)
        speed  = 5 + (2 if self._rage_mode else 0)
        offset = (self._tick * 10) % 360
        for i in range(n):
            ang = math.radians(offset + (360/n)*i)
            b   = EnemyBullet(int(self.x), int(self.y)+50,
                              math.sin(ang)*speed, math.cos(ang)*speed,
                              self.base_dmg // 2)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    # ── Damage ────────────────────────────────────────────────────────────────
    def take_damage(self, amount: int) -> bool:
        if self._shield_active:
            self._shield_hp -= amount
            self.game.particles.damage_number(int(self.x), int(self.y)-40, amount, 'shield')
            if self._shield_hp <= 0:
                self._shield_active = False
                self.game.particles.explosion(int(self.x), int(self.y),
                                              (50,100,255), 30, 8)
                self.game.particles.shockwave_ring(int(self.x), int(self.y), (80,160,255))
            return False

        self.health    -= amount
        self._hit_flash = 5
        self.game.save.increment_stat('damage_dealt', amount)

        if self.health <= 0:
            self._die()
            return True
        return False

    def _die(self):
        px, py = int(self.x), int(self.y)
        # Multi-wave mega explosion
        self.game.particles.mega_explosion(px, py, (255, 80, 20))
        for _ in range(4):
            dx = random.randint(-100, 100)
            dy = random.randint(-80, 80)
            self.game.particles.shockwave_ring(px+dx, py+dy, (255,120,40), 150, 6)
        self.game.particles.shake(28)
        self.game.screen_flash((255, 160, 0), 140)
        self.game.audio.play('explosion')
        self.game.save.increment_stat('bosses_killed')

        # Coin shower on boss death
        for _ in range(20):
            cx = px + random.randint(-80, 80)
            cy = py + random.randint(-50, 50)
            c  = Coin(cx, cy, random.choice([5, 10, 10, 25]))
            c.vy = random.uniform(1.5, 4.0)
            c.vx = random.uniform(-2, 2)
            self.game.coins_group.add(c)
            self.game.all_sprites.add(c)

        self.game.ui.show_message(
            'BOSS DEFEATED!',
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            (255, 200, 50), 'xl')

        self.kill()   # remove from all sprite groups — stops further attacks

    # ── HUD ───────────────────────────────────────────────────────────────────
    def draw_hud(self, surface: pygame.Surface):
        """Boss HP bar at top center of screen."""
        bw  = 400
        bh  = 18
        bx  = (SCREEN_WIDTH - bw) // 2
        by  = 8
        ratio= max(0, self.health / self.max_health)

        # Background
        pygame.draw.rect(surface, (40, 0, 0),   (bx-2, by-2, bw+4, bh+4), border_radius=5)
        pygame.draw.rect(surface, (80, 0, 0),   (bx,   by,   bw,   bh),   border_radius=4)

        # Fill — changes color by phase
        phase_cols = [(200,0,0), (220,50,0), (180,0,180)]
        col = phase_cols[min(self._phase, 2)]
        if self._rage_mode:
            t   = int((self._tick % 10) < 5)
            col = (255, t*60, t*60)
        pygame.draw.rect(surface, col,
                         (bx, by, int(bw*ratio), bh), border_radius=4)

        # Shine stripe (desktop only — SRCALPHA allocation too costly on Android)
        if not IS_ANDROID and int(bw * ratio) > 0:
            sh = pygame.Surface((int(bw*ratio), bh//3), pygame.SRCALPHA)
            sh.fill((255,255,255,40))
            surface.blit(sh, (bx, by))

        # Phase markers at 33% and 66%
        for pct in (0.33, 0.66):
            mx = bx + int(bw * pct)
            pygame.draw.line(surface, (200,200,200), (mx, by), (mx, by+bh), 2)

        # Label
        if not hasattr(Boss, '_hud_font'):
            Boss._hud_font = pygame.font.SysFont('consolas', 13, bold=True)
        font = Boss._hud_font
        label= 'BOSS ⚠ ENRAGED' if self._rage_mode else f'BOSS — PHASE {self._phase+1}'
        col2 = (255, 80, 80) if self._rage_mode else (255, 200, 200)
        txt  = font.render(label, True, col2)
        surface.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, by + bh + 10)))

    def draw_shield(self, surface: pygame.Surface):
        if not self._shield_active:
            return
        ix, iy = int(self.x) - 100, int(self.y) - 80
        if IS_ANDROID:
            pygame.draw.ellipse(surface, (50, 100, 255), (ix, iy, 200, 160), 4)
        else:
            t     = pygame.time.get_ticks()
            alpha = int(80 + 40 * math.sin(t * 0.006))
            rs    = pygame.Surface((200, 160), pygame.SRCALPHA)
            pygame.draw.ellipse(rs, (50, 100, 255, alpha), (0, 0, 200, 160), 4)
            pygame.draw.ellipse(rs, (100, 180, 255, alpha // 3), (0, 0, 200, 160))
            surface.blit(rs, (ix, iy))

    def draw_rage_aura(self, surface: pygame.Surface):
        """Pulsing red corona drawn around the boss when enraged."""
        if not self._rage_mode:
            return
        bx, by = int(self.x), int(self.y)
        if IS_ANDROID:
            # Direct circles — no SRCALPHA allocation
            t     = pygame.time.get_ticks()
            pulse = math.sin(t * 0.01) * 0.5 + 0.5
            r     = int(110 + pulse * 30)
            fade  = int(80 + pulse * 60)
            col   = (min(255, fade), 0, 0)
            pygame.draw.circle(surface, col, (bx, by), r, 6)
        else:
            t     = pygame.time.get_ticks()
            pulse = math.sin(t * 0.01) * 0.5 + 0.5
            r     = int(110 + pulse * 30)
            alpha = int(60 + pulse * 60)
            s     = pygame.Surface((r*2+8, r*2+8), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 20, 20, alpha),    (r+4, r+4), r, 6)
            pygame.draw.circle(s, (255, 80, 0, alpha//2),  (r+4, r+4), r+10, 3)
            surface.blit(s, (bx - r - 4, by - r - 4))

        # Laser telegraph
        if self._laser_warning:
            warn_alpha = int(200 * (self._laser_warning_timer / 45))
            lx = self._laser_warning_x
            if IS_ANDROID:
                fade_col = (min(255, warn_alpha), 0, 0)
                pygame.draw.line(surface, fade_col, (lx, 0), (lx, SCREEN_HEIGHT), 5)
            else:
                warn_col = (255, 30, 30, warn_alpha)
                ws = pygame.Surface((6, SCREEN_HEIGHT), pygame.SRCALPHA)
                ws.fill(warn_col)
                surface.blit(ws, (lx - 3, 0))
                for dx in (-12, -6, 6, 12):
                    gs = pygame.Surface((4, SCREEN_HEIGHT), pygame.SRCALPHA)
                    gs.fill((255, 0, 0, warn_alpha // 4))
                    surface.blit(gs, (lx - 2 + dx, 0))
