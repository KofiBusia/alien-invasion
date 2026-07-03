"""Omega Nemesis — the ultimate final boss after all 5 chapters."""

import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, IS_ANDROID
from bullet import EnemyBullet, BossLaser
from powerup import Coin
from enemy import spawn_enemy


class UltimateBoss(pygame.sprite.Sprite):
    """
    4-phase final boss. Phases trigger at 75%, 50%, 25% and 10% HP.
    Summons chapter enemies as minions. Massive health and attack variety.
    """

    def __init__(self, game):
        super().__init__()
        self.game = game

        self.max_health = 28000
        self.health     = self.max_health
        self.base_dmg   = 50

        self.x  = float(SCREEN_WIDTH // 2)
        self.y  = -240.0
        self.vx = 2.2
        self._entry = True

        self._tick            = 0
        self._phase           = 0
        self._attack_timer    = 0
        self._attack_cd       = 85
        self._pattern_idx     = 0
        self._hit_flash       = 0

        self._shield_hp       = 0
        self._shield_active   = False
        self._shield_cd       = 380

        self._rage_mode       = False
        self._rage_triggered  = False

        self._summon_timer    = 220
        self._phase_done      = set()   # which phase thresholds already triggered

        self._laser_warning       = False
        self._laser_warning_timer = 0
        self._laser_warning_x     = 0

        self._warn_played = False

        self.image = self._build_image()
        self._orig = self.image.copy()
        self.rect  = self.image.get_rect(center=(int(self.x), int(self.y)))

    # ── Image ─────────────────────────────────────────────────────────────────
    def _build_image(self) -> pygame.Surface:
        w, h = 230, 190
        s    = pygame.Surface((w, h), pygame.SRCALPHA)

        # Core body — void-black warship
        pts = [(w//2, 0), (w-5, h//4), (w-18, h-12), (18, h-12), (5, h//4)]
        pygame.draw.polygon(s, (18, 0, 28), pts)
        pygame.draw.polygon(s, (190, 0, 255), pts, 3)

        # Side wings
        lwing = [(0, h//3), (28, h//5), (w//4, h*9//16), (0, h*2//3)]
        rwing = [(w, h//3), (w-28, h//5), (w*3//4, h*9//16), (w, h*2//3)]
        pygame.draw.polygon(s, (12, 0, 22), lwing)
        pygame.draw.polygon(s, (12, 0, 22), rwing)
        pygame.draw.polygon(s, (140, 0, 210), lwing, 2)
        pygame.draw.polygon(s, (140, 0, 210), rwing, 2)

        # Armour mid-band
        pygame.draw.rect(s, (8, 0, 16), (22, h//3, w-44, h//3), border_radius=6)
        pygame.draw.rect(s, (160, 0, 230), (24, h//3+2, w-48, h//3-4), border_radius=5, width=1)

        # Triple cannon array
        for cx2 in [w//5, w//2, w*4//5]:
            pygame.draw.rect(s, (28, 0, 48), (cx2-9, h-28, 18, 30), border_radius=4)
            pygame.draw.circle(s, (255, 50, 255), (cx2, h-4), 10)

        # Side wing cannons
        for sx in [4, w-24]:
            pygame.draw.rect(s, (28, 0, 48), (sx, h//3+8, 20, 55), border_radius=4)
            pygame.draw.circle(s, (200, 0, 255), (sx+10, h//3+63), 11)

        # Glowing core eye
        pygame.draw.ellipse(s, (70, 0, 110),   (w//2-30, 20, 60, 40))
        pygame.draw.ellipse(s, (255, 0, 255),  (w//2-20, 26, 40, 28))
        pygame.draw.ellipse(s, (255, 180, 255),(w//2-10, 32, 20, 16))
        pygame.draw.ellipse(s, (255, 255, 255),(w//2-5,  36, 10,  8))

        # Engine pods (3 large)
        for ex2 in [w//5, w//2, w*4//5]:
            pygame.draw.ellipse(s, (20, 0, 32), (ex2-15, h-18, 30, 20))
            pygame.draw.ellipse(s, (200, 100, 255), (ex2-10, h-16, 20, 16))

        # Decorative warning stripes
        for i in range(3):
            yi = h // 2 + i * 15
            pygame.draw.line(s, (80, 0, 120), (26, yi), (w-26, yi), 1)

        return s

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        self._tick += 1

        # Entry glide-in
        if self._entry:
            self.y += 1.6
            if self.y >= 160:
                self._entry = False
                self.game.screen_flash((200, 0, 255), 180)
                self.game.particles.shake(22)
                self.game.ui.show_message(
                    'OMEGA NEMESIS AWAKENS',
                    SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 110,
                    (255, 0, 255), 'xl')
            self.rect.center = (int(self.x), int(self.y))
            return

        if not self._warn_played:
            self._warn_played = True
            self.game.audio.play('boss_warn')

        # Phase thresholds: 75%, 50%, 25%, 10%
        ratio = self.health / self.max_health
        for thr, phase_num in ((0.75, 1), (0.50, 2), (0.25, 3), (0.10, 4)):
            if ratio <= thr and thr not in self._phase_done:
                self._phase_done.add(thr)
                self._phase = phase_num
                self._on_phase_change(phase_num)
                break

        # Rage at 10%
        if not self._rage_triggered and ratio <= 0.10:
            self._rage_triggered = True
            self._rage_mode      = True
            self._trigger_rage()

        # Telegraph countdown
        if self._laser_warning:
            self._laser_warning_timer -= 1
            if self._laser_warning_timer <= 0:
                self._laser_warning = False
                self._fire_telegraphed_laser()

        # Periodic void shield (phase 2+)
        if self._phase >= 2:
            self._shield_cd = max(0, self._shield_cd - 1)
            if self._shield_cd == 0 and not self._shield_active:
                self._shield_active = True
                self._shield_hp     = 500
                self._shield_cd     = 480
                self.game.ui.show_message(
                    'VOID SHIELD ACTIVATED',
                    SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 65,
                    (100, 0, 255), 'md')

        # Ally summons
        self._summon_timer = max(0, self._summon_timer - 1)
        if self._summon_timer == 0:
            self._summon_minions()
            self._summon_timer = max(100, 240 - self._phase * 35)

        self._move()

        # Attack
        self._attack_timer += 1
        cd = max(28, self._attack_cd - self._phase * 12)
        if self._rage_mode:
            cd = max(18, cd // 2)
        if self._attack_timer >= cd:
            self._attack_timer = 0
            self._do_attack()

        # Hit flash
        if self._hit_flash > 0:
            self._hit_flash -= 1
            flash = self._orig.copy()
            flash.fill((255, 255, 255, 190), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = flash
        else:
            self.image = self._orig

        self.rect.center = (int(self.x), int(self.y))

    def _move(self):
        spd = 1.8 + self._phase * 0.45
        if self._rage_mode:
            spd *= 1.7
        self.x += self.vx * spd
        # Sinusoidal vertical drift
        self.y = 155 + self._phase * 18 + math.sin(self._tick * 0.018) * 35
        if self.x < 130 or self.x > SCREEN_WIDTH - 130:
            self.vx *= -1
            self.x   = max(130, min(SCREEN_WIDTH - 130, self.x))

    def _on_phase_change(self, phase: int):
        msgs  = ['', 'PHASE II — SHADOW ASSAULT', 'PHASE III — VOID STORM',
                 'PHASE IV — OMEGA FURY', 'FINAL PHASE — TOTAL ANNIHILATION']
        cols  = [(0,0,0), (180,0,200), (100,0,255), (255,0,100), (255,120,0)]
        col   = cols[min(phase, len(cols)-1)]
        msg   = msgs[min(phase, len(msgs)-1)]
        self.game.particles.mega_explosion(int(self.x), int(self.y), col)
        self.game.particles.shake(22)
        self.game.screen_flash(col, 140)
        if msg:
            self.game.ui.show_message(msg, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 95, col, 'xl')
        self.game.audio.play('boss_warn')
        self._summon_minions(force=True)

    def _trigger_rage(self):
        self.game.particles.mega_explosion(int(self.x), int(self.y), (255, 0, 255))
        self.game.particles.shake(32)
        self.game.screen_flash((255, 0, 255), 190)
        self.game.ui.show_message('OMEGA NEMESIS ENRAGED!',
                                  SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 95,
                                  (255, 0, 255), 'xl')
        self.game.audio.play('boss_warn')

    def _summon_minions(self, force=False):
        n = 2 + self._phase + (3 if force else 0)
        pools = {
            0: ['scout', 'fighter'],
            1: ['reaper', 'predator', 'titan'],
            2: ['shade', 'marauder', 'colossus', 'reaper', 'predator'],
            3: ['specter', 'raptor', 'shade', 'predator', 'titan', 'nemesis'],
            4: ['nemesis', 'titan', 'obliterator', 'predator', 'reaper', 'nemesis'],
        }
        pool = pools.get(min(self._phase, 4), ['scout'])
        for _ in range(n):
            kind = random.choice(pool)
            x    = random.randint(80, SCREEN_WIDTH - 80)
            spawn_enemy(self.game, kind, x, self.y + 110)

    # ── Attack patterns ───────────────────────────────────────────────────────
    PATTERNS = ['void_burst', 'quad_laser', 'death_spiral',
                'particle_storm', 'aimed_volley', 'supernova']

    def _do_attack(self):
        avail   = self.PATTERNS[:max(2, 2 + self._phase * 1)]
        pattern = avail[self._pattern_idx % len(avail)]
        self._pattern_idx += 1
        getattr(self, f'_atk_{pattern}', self._atk_void_burst)()

    def _atk_void_burst(self):
        n     = 12 + self._phase * 5 + (8 if self._rage_mode else 0)
        spd   = 5.5 + self._phase * 0.7 + (3 if self._rage_mode else 0)
        offset = (self._tick * 14) % 360
        for i in range(n):
            ang = math.radians(offset + (360 / n) * i)
            b   = EnemyBullet(int(self.x), int(self.y) + 80,
                              math.sin(ang) * spd, math.cos(ang) * spd,
                              self.base_dmg)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_quad_laser(self):
        positions = [SCREEN_WIDTH//5, 2*SCREEN_WIDTH//5,
                     3*SCREEN_WIDTH//5, 4*SCREEN_WIDTH//5]
        n = min(2 + self._phase, 4)
        for lx in positions[:n]:
            if not self._laser_warning:
                self._laser_warning       = True
                self._laser_warning_timer = 52
                self._laser_warning_x     = lx
            else:
                laser = BossLaser(lx, self.rect.bottom, 30, self.base_dmg // 6)
                self.game.enemy_bullets.add(laser)
                self.game.all_sprites.add(laser)

    def _fire_telegraphed_laser(self):
        laser = BossLaser(self._laser_warning_x, self.rect.bottom, 30, self.base_dmg // 6)
        self.game.enemy_bullets.add(laser)
        self.game.all_sprites.add(laser)

    def _atk_death_spiral(self):
        n   = 18 + (12 if self._rage_mode else 0)
        spd = 4.5 + self._phase + (2 if self._rage_mode else 0)
        offset = (self._tick * 9) % 360
        for i in range(n):
            ang = math.radians(offset + (360 / n) * i)
            b   = EnemyBullet(int(self.x), int(self.y) + 80,
                              math.sin(ang) * spd, math.cos(ang) * spd,
                              self.base_dmg // 2)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_particle_storm(self):
        count = 5 + self._phase * 4 + (8 if self._rage_mode else 0)
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH - 60)
            b = EnemyBullet(x, self.rect.bottom,
                            random.uniform(-2.5, 2.5), 5 + self._phase,
                            self.base_dmg, explosive=True)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_aimed_volley(self):
        px, py = self.game.player.x, self.game.player.y
        n      = 4 + self._phase * 2 + (5 if self._rage_mode else 0)
        for i in range(n):
            dx  = px - self.x + random.uniform(-50, 50)
            dy  = py - self.y
            d   = math.hypot(dx, dy) or 1
            spd = 7 + self._phase + (3 if self._rage_mode else 0)
            b   = EnemyBullet(int(self.x), int(self.y) + 80,
                              dx / d * spd, dy / d * spd, self.base_dmg)
            self.game.enemy_bullets.add(b)
            self.game.all_sprites.add(b)

    def _atk_supernova(self):
        if self._phase < 2:
            self._atk_void_burst()
            return
        for ring in range(3):
            n   = 16
            spd = 3 + ring * 2 + (2 if self._rage_mode else 0)
            off = ring * 40
            for i in range(n):
                ang = math.radians(off + (360 / n) * i)
                b   = EnemyBullet(int(self.x), int(self.y) + 80,
                                  math.sin(ang) * spd, math.cos(ang) * spd,
                                  self.base_dmg)
                self.game.enemy_bullets.add(b)
                self.game.all_sprites.add(b)

    # ── Damage ────────────────────────────────────────────────────────────────
    def take_damage(self, amount: int) -> bool:
        if self._shield_active:
            self._shield_hp -= amount
            self.game.particles.damage_number(int(self.x), int(self.y) - 55, amount, 'shield')
            if self._shield_hp <= 0:
                self._shield_active = False
                self.game.particles.shockwave_ring(int(self.x), int(self.y), (180, 0, 255))
                self.game.particles.explosion(int(self.x), int(self.y), (100, 0, 200), 30, 8)
                self.game.ui.show_message('VOID SHIELD BROKEN!',
                                          SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 65,
                                          (255, 180, 255), 'md')
            return False

        self.health    -= amount
        self._hit_flash = 6
        self.game.save.increment_stat('damage_dealt', amount)

        if self.health <= 0:
            self._die()
            return True
        return False

    def _die(self):
        px, py = int(self.x), int(self.y)
        for _ in range(10):
            dx = random.randint(-150, 150)
            dy = random.randint(-110, 110)
            self.game.particles.mega_explosion(px + dx, py + dy, (255, 0, 255))
            self.game.particles.shockwave_ring(px + dx, py + dy,
                                               (200, 100, 255), 220, 7)
        self.game.particles.shake(45)
        self.game.screen_flash((255, 255, 255), 255)
        self.game.audio.play('explosion')
        self.game.save.increment_stat('bosses_killed')

        # Massive coin shower
        for _ in range(60):
            cx2 = px + random.randint(-180, 180)
            cy2 = py + random.randint(-100, 100)
            c   = Coin(cx2, cy2, random.choice([10, 25, 25, 50, 100, 100]))
            c.vy = random.uniform(1.5, 4.5)
            c.vx = random.uniform(-3.5, 3.5)
            self.game.coins_group.add(c)
            self.game.all_sprites.add(c)

        self.game.ui.show_message(
            'OMEGA NEMESIS DEFEATED!',
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            (255, 220, 0), 'xl')
        self.kill()

    # ── HUD ───────────────────────────────────────────────────────────────────
    def draw_hud(self, surface: pygame.Surface):
        bw    = 620
        bh    = 22
        bx    = (SCREEN_WIDTH - bw) // 2
        by    = 8
        ratio = max(0, self.health / self.max_health)

        pygame.draw.rect(surface, (20, 0, 30),  (bx-3, by-3, bw+6, bh+6), border_radius=7)
        pygame.draw.rect(surface, (55, 0, 75),  (bx, by, bw, bh),          border_radius=6)

        phase_cols = [(180,0,255), (140,0,220), (100,0,200), (255,0,150), (255,80,0)]
        col = phase_cols[min(self._phase, len(phase_cols)-1)]
        if self._rage_mode:
            t   = int((self._tick % 8) < 4)
            col = (255, t * 50, 255 - t * 55)
        pygame.draw.rect(surface, col, (bx, by, int(bw * ratio), bh), border_radius=6)

        # Shield overlay
        if self._shield_active:
            sr = max(0, self._shield_hp / 500)
            pygame.draw.rect(surface, (120, 160, 255),
                             (bx, by, int(bw * sr * ratio), bh // 3), border_radius=3)

        # Phase markers at 25%, 50%, 75%
        for pct in (0.25, 0.50, 0.75):
            mx = bx + int(bw * pct)
            pygame.draw.line(surface, (255, 200, 255), (mx, by), (mx, by+bh), 2)

        # Shine
        if not IS_ANDROID and int(bw * ratio) > 0:
            sh = pygame.Surface((int(bw * ratio), bh // 3), pygame.SRCALPHA)
            sh.fill((255, 255, 255, 32))
            surface.blit(sh, (bx, by))

        if not hasattr(UltimateBoss, '_hud_font'):
            UltimateBoss._hud_font = pygame.font.SysFont('consolas', 14, bold=True)
        font = UltimateBoss._hud_font
        if self._rage_mode:
            label = f'OMEGA NEMESIS  * ENRAGED *  PHASE {self._phase + 1} / 4'
            col2  = (255, 120, 255)
        else:
            label = f'OMEGA NEMESIS  —  PHASE {self._phase + 1} / 4'
            col2  = (255, 180, 255)
        txt = font.render(label, True, col2)
        surface.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, by + bh + 12)))

    def draw_shield(self, surface: pygame.Surface):
        if not self._shield_active:
            return
        bx, by = int(self.x) - 135, int(self.y) - 115
        t = self._tick
        if IS_ANDROID:
            pygame.draw.ellipse(surface, (100, 0, 255), (bx, by, 270, 230), 5)
        else:
            alpha = int(90 + 50 * math.sin(t * 0.07))
            rs    = pygame.Surface((270, 230), pygame.SRCALPHA)
            pygame.draw.ellipse(rs, (100, 0, 255, alpha),     (0, 0, 270, 230), 5)
            pygame.draw.ellipse(rs, (180, 100, 255, alpha//3), (0, 0, 270, 230))
            surface.blit(rs, (bx, by))

    def draw_rage_aura(self, surface: pygame.Surface):
        if not self._rage_mode:
            # Still draw laser telegraph when not raging
            self._draw_laser_telegraph(surface)
            return
        bx, by = int(self.x), int(self.y)
        t      = self._tick
        pulse  = math.sin(t * 0.08) * 0.5 + 0.5
        r      = int(145 + pulse * 45)
        if IS_ANDROID:
            fade = int(90 + pulse * 75)
            pygame.draw.circle(surface, (fade, 0, min(255, fade + 65)), (bx, by), r, 9)
        else:
            alpha = int(70 + pulse * 75)
            srf   = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
            pygame.draw.circle(srf, (255, 0, 255, alpha),    (r+5, r+5), r, 9)
            pygame.draw.circle(srf, (180, 0, 255, alpha//2), (r+5, r+5), r+18, 4)
            surface.blit(srf, (bx-r-5, by-r-5))
        self._draw_laser_telegraph(surface)

    def _draw_laser_telegraph(self, surface: pygame.Surface):
        if not self._laser_warning:
            return
        lx         = self._laser_warning_x
        warn_alpha = int(200 * (self._laser_warning_timer / 52))
        if IS_ANDROID:
            col = (min(255, warn_alpha + 60), 0, min(255, warn_alpha))
            pygame.draw.line(surface, col, (lx, 0), (lx, SCREEN_HEIGHT), 6)
        else:
            ws = pygame.Surface((8, SCREEN_HEIGHT), pygame.SRCALPHA)
            ws.fill((255, 0, 255, warn_alpha))
            surface.blit(ws, (lx - 4, 0))
            for dx2 in (-14, -7, 7, 14):
                gs = pygame.Surface((4, SCREEN_HEIGHT), pygame.SRCALPHA)
                gs.fill((200, 0, 255, warn_alpha // 4))
                surface.blit(gs, (lx - 2 + dx2, 0))
