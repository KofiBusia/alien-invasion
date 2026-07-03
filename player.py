"""Player spaceship — movement, shooting, shields, power-ups."""

import math
import random
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_SPEED, PLAYER_HEALTH,
    PLAYER_SHIELD, PLAYER_LIVES, PLAYER_INVINCIBILITY_MS, WEAPONS, WEAPON_ORDER,
    IS_ANDROID
)
from bullet import Bullet, RainbowBullet, PlasmaBullet, MissileBullet
from trails import TrailSystem


class Player(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self._apply_upgrades()

        # ── State ─────────────────────────────────────────────────────────────
        self.health             = self.max_health
        self.shield             = self.max_shield
        self.lives              = PLAYER_LIVES
        self.score              = 0
        self.coins              = 0
        self.level_damage_taken = 0

        # ── Weapons ───────────────────────────────────────────────────────────
        save                  = game.save
        self.unlocked_weapons = list(save.get('unlocked_weapons', ['laser']))
        self.weapon_idx       = 0
        self.weapon_key       = self.unlocked_weapons[0]
        self._last_shot_ms    = 0          # ms-based cooldown (reliable at any FPS)
        self._shoot_cd_pct    = 0.0        # 0–1 used for HUD indicator

        # ── Active timed effects (name -> expiry ms) ──────────────────────────
        self._effects: dict[str, int] = {}

        # ── Invincibility / blink ─────────────────────────────────────────────
        self._inv_until  = 0              # absolute ms timestamp
        self._blink_tick = 0

        # ── Position / velocity ───────────────────────────────────────────────
        self.x    = float(SCREEN_WIDTH  // 2)
        self.y    = float(SCREEN_HEIGHT - 90)
        self.vx   = 0.0
        self.vy   = 0.0

        # ── Visuals ───────────────────────────────────────────────────────────
        self._tilt       = 0.0          # current roll angle (degrees), smooth lerp
        self._eng_tick   = 0
        self._base_img   = self._build_ship()
        self.image       = self._base_img.copy()
        self.rect        = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._thruster_particles: list[dict] = []
        # Purchased trail system
        self.trail = TrailSystem()
        active = game.save.get('active_trail')
        if active and game.save.has_trail(active):
            self.trail.set_trail(active)
        # Engine nozzle relative offsets (x from ship center, y from ship center)
        W = 56
        self._engine_offsets = [
            (W//4 - W//2, 26),
            (W//2 - W//2, 26),
            (W*3//4 - W//2, 26),
        ]

    # ── Upgrades ──────────────────────────────────────────────────────────────
    def _apply_upgrades(self):
        lvls             = self.game.save.get('upgrades', {})
        self.max_health  = PLAYER_HEALTH + lvls.get('max_health',    0) * 25
        self.max_shield  = PLAYER_SHIELD + lvls.get('shield_power',  0) * 20
        self.speed       = PLAYER_SPEED  + lvls.get('move_speed',    0) * 0.5
        self.dmg_mult    = 1.0           + lvls.get('weapon_damage', 0) * 0.15
        self.cd_mult     = max(0.3, 1.0  - lvls.get('fire_rate',     0) * 0.08)
        self.crit_chance = lvls.get('crit_chance', 0) * 0.05
        self.coin_mult   = 1.0           + lvls.get('coin_bonus',    0) * 0.12

    def refresh_upgrades(self):
        self._apply_upgrades()
        self.health = min(self.health, self.max_health)
        self.shield = min(self.shield, self.max_shield)

    # ── Ship image ────────────────────────────────────────────────────────────
    def _build_ship(self) -> pygame.Surface:
        W, H = 56, 68
        s = pygame.Surface((W, H), pygame.SRCALPHA)

        # === Body ===
        body = [(W//2, 0), (W-4, H-22), (W*3//4, H-14), (W//4, H-14), (4, H-22)]
        pygame.draw.polygon(s, (30, 65, 150), body)
        pygame.draw.polygon(s, (70, 130, 240), body, 2)

        # === Side wings ===
        lwing = [(4, H-22), (0, H-4),  (W//4, H-10), (W//4, H-14)]
        rwing = [(W-4, H-22), (W, H-4), (W*3//4, H-10), (W*3//4, H-14)]
        pygame.draw.polygon(s, (25, 55, 130), lwing)
        pygame.draw.polygon(s, (25, 55, 130), rwing)
        pygame.draw.polygon(s, (60, 120, 220), lwing, 1)
        pygame.draw.polygon(s, (60, 120, 220), rwing, 1)

        # === Wing accent lines ===
        pygame.draw.line(s, (80, 180, 255), (W//4, H-14), (2, H-6),  1)
        pygame.draw.line(s, (80, 180, 255), (W*3//4, H-14), (W-2, H-6), 1)

        # === Armour panel (center stripe) ===
        pygame.draw.rect(s, (40, 80, 170), (W//2-8, 10, 16, H-30), border_radius=3)
        pygame.draw.line(s, (90, 160, 255), (W//2, 8), (W//2, H-26), 1)

        # === Cockpit ===
        pygame.draw.ellipse(s, (0, 180, 255, 220), (W//2-9, 10, 18, 22))
        pygame.draw.ellipse(s, (120, 230, 255, 160), (W//2-6, 12, 12, 14))
        pygame.draw.ellipse(s, (220, 245, 255, 90),  (W//2-4, 13, 8, 8))

        # === Side cannons ===
        for cx in (W//4 - 3, W*3//4 - 3):
            pygame.draw.rect(s, (20, 50, 120), (cx, H-24, 6, 14), border_radius=2)
            pygame.draw.rect(s, (0, 200, 255),  (cx+1, H-26, 4, 4), border_radius=1)

        # === Engine nozzles ===
        for ex in (W//4, W//2, W*3//4):
            pygame.draw.ellipse(s, (40, 80, 200), (ex-5, H-10, 10, 12))
            pygame.draw.ellipse(s, (80, 160, 255, 200), (ex-4, H-9, 8, 10))

        return s

    # ── Engine flame (drawn separately each frame) ────────────────────────────
    def _draw_flame(self, surface: pygame.Surface):
        self._eng_tick += 1
        thrust = max(0.3, (abs(self.vx) + abs(self.vy)) / (self.speed * 1.414))
        W = 56
        for i, ex in enumerate([W//4, W//2, W*3//4]):
            wx = int(self.x) - W//2 + ex
            wy = int(self.y) + 26
            flicker = math.sin(self._eng_tick * 0.5 + i) * 4
            fh = int((10 + flicker + (i==1)*6) * thrust)
            for j in range(fh):
                ratio = j / max(fh, 1)
                if ratio < 0.3:
                    c = (100, 180, 255)
                elif ratio < 0.6:
                    c = (255, 200, 60)
                else:
                    c = (255, 80, 20)
                pygame.draw.circle(surface, c, (wx, wy + j), 1)

    # ── Input ─────────────────────────────────────────────────────────────────
    def handle_input(self):
        keys  = pygame.key.get_pressed()
        spd   = self.speed * (1.55 if self.has_effect('speed_boost') else 1.0)
        dx = dy = 0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1
        if dx and dy:
            dx *= 0.7071; dy *= 0.7071
        self.vx = dx * spd
        self.vy = dy * spd
        if keys[pygame.K_SPACE]:
            self.shoot()

    def handle_mouse_target(self, tx: float, ty: float, fire: bool):
        """Drive ship toward (tx, ty) — used for mouse and touch control."""
        spd = self.speed * (1.55 if self.has_effect('speed_boost') else 1.0)
        dx  = tx - self.x
        dy  = ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 6:
            # Proportional speed: faster when far, slows smoothly on approach
            factor = min(1.0, dist / 120) * spd
            self.vx = dx / dist * factor
            self.vy = dy / dist * factor
        else:
            self.vx = 0.0
            self.vy = 0.0
        if fire:
            self.shoot()

    def switch_weapon(self, direction: int):
        if len(self.unlocked_weapons) <= 1:
            return
        self.weapon_idx = (self.weapon_idx + direction) % len(self.unlocked_weapons)
        self.weapon_key = self.unlocked_weapons[self.weapon_idx]
        self._last_shot_ms = 0   # reset cooldown on switch so it's instant

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        now = pygame.time.get_ticks()

        self.handle_input()

        # Virtual joystick (Android) — overrides keyboard when active
        jdx = getattr(self.game, '_joy_dx', 0.0)
        jdy = getattr(self.game, '_joy_dy', 0.0)
        if jdx or jdy:
            spd = self.speed * (1.55 if self.has_effect('speed_boost') else 1.0)
            self.vx = jdx * spd
            self.vy = jdy * spd
            if getattr(self.game, '_mouse_firing', False):
                self.shoot()
        else:
            # Mouse/touch — only when no keyboard direction pressed
            mt = getattr(self.game, '_mouse_target', None)
            if mt is not None and self.vx == 0 and self.vy == 0:
                fire = getattr(self.game, '_mouse_firing', False)
                self.handle_mouse_target(mt[0], mt[1], fire)
            elif getattr(self.game, '_mouse_firing', False) and mt is None:
                self.shoot()

        # Move + clamp
        self.x += self.vx
        self.y += self.vy
        hw = self.rect.width  // 2
        hh = self.rect.height // 2
        self.x = max(hw, min(SCREEN_WIDTH  - hw, self.x))
        self.y = max(hh, min(SCREEN_HEIGHT - hh - 60, self.y))  # stay above HUD

        # Ship tilt — smooth lerp toward vx-based angle
        target_tilt = (self.vx / (self.speed or 1)) * 18
        self._tilt += (target_tilt - self._tilt) * 0.14

        # Rotate image
        if abs(self._tilt) > 0.5:
            self.image = pygame.transform.rotate(self._base_img, -self._tilt)
        else:
            self.image = self._base_img
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        # Blink counter
        self._blink_tick = (self._blink_tick + 1) % 8

        # Purchased trail system
        moving = math.hypot(self.vx, self.vy) > 0.4
        eng_world = [(self.x + dx, self.y + dy) for dx, dy in self._engine_offsets]
        self.trail.emit(eng_world, moving)
        self.trail.update()

        # Expire effects
        self._effects = {k: v for k, v in self._effects.items() if now < v}

        # Slow shield regen (1 HP per second)
        if now % 1000 < 17 and self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + 1)

        # Update cooldown percentage for HUD arc
        cfg       = WEAPONS.get(self.weapon_key, {})
        cd        = int(cfg.get('cooldown', 250) * self.cd_mult)
        if self.has_effect('rapid_fire'): cd = int(cd * 0.4)
        elapsed   = now - self._last_shot_ms
        self._shoot_cd_pct = min(1.0, elapsed / max(cd, 1))

    # ── Shooting ──────────────────────────────────────────────────────────────
    def shoot(self):
        now = pygame.time.get_ticks()
        cfg = WEAPONS[self.weapon_key]
        cd  = int(cfg['cooldown'] * self.cd_mult)
        if self.has_effect('rapid_fire'): cd = int(cd * 0.4)
        if now - self._last_shot_ms < cd:
            return
        self._last_shot_ms = now
        self._fire(cfg)
        self.game.audio.play(
            'plasma'  if self.weapon_key == 'plasma'  else
            'missile' if self.weapon_key == 'missile' else 'laser')
        self.game.save.increment_stat('shots_fired')

    def _fire(self, cfg):
        dmg    = cfg['damage']
        spd    = cfg['speed']
        color  = cfg['color'] or (255, 255, 255)
        size   = cfg['size']
        mult   = self.dmg_mult * (2.0 if self.has_effect('damage_boost') else 1.0)
        if random.random() < self.crit_chance:
            mult *= 2.0
        damage = int(dmg * mult)
        bullets = self.game.player_bullets
        cx, cy  = self.x, self.y - self.rect.height // 2 + 4

        def add(b):
            bullets.add(b)
            self.game.all_sprites.add(b)

        if self.weapon_key == 'rainbow':
            add(RainbowBullet(cx, cy, 0, -spd, damage))
        elif self.weapon_key == 'plasma':
            add(PlasmaBullet(cx, cy, 0, -spd, damage))
        elif self.weapon_key == 'missile':
            add(MissileBullet(cx, cy, -spd, damage, self.game.enemies))
        elif cfg['pattern'] == 'double':
            for dx in (-cfg['spread']//2, cfg['spread']//2):
                add(Bullet(cx + dx, cy, 0, -spd, damage, color, size))
        elif cfg['pattern'] == 'triple':
            for ang in (-cfg['spread']//2, 0, cfg['spread']//2):
                r = math.radians(ang)
                add(Bullet(cx, cy, math.sin(r)*spd, -math.cos(r)*spd, damage, color, size))
        elif cfg['pattern'] == 'spread5':
            angles = [-cfg['spread']//2, -cfg['spread']//4, 0, cfg['spread']//4, cfg['spread']//2]
            for ang in angles:
                r = math.radians(ang)
                add(Bullet(cx, cy, math.sin(r)*spd, -math.cos(r)*spd, damage, color, size))
        else:
            add(Bullet(cx, cy, 0, -spd, damage, color, size))

    # ── Damage / healing ─────────────────────────────────────────────────────
    def take_damage(self, amount: int):
        now = pygame.time.get_ticks()
        if now < self._inv_until or self.has_effect('invincibility'):
            return
        if self.shield > 0:
            absorbed    = min(self.shield, amount)
            self.shield -= absorbed
            amount      -= absorbed
            if absorbed:
                self.game.particles.shield_ripple(self.x, self.y, 34)
                self.game.audio.play('shield')
        if amount > 0:
            self.health             -= amount
            self.level_damage_taken += amount
            self.game.particles.hit_sparks(self.x, self.y, (255, 80, 80))
            self.game.particles.shake(10)
            self._inv_until = now + PLAYER_INVINCIBILITY_MS
            self.game.save.increment_stat('damage_taken', amount)
            if self.health <= 0:
                self._die()

    def heal(self, amount: int):
        self.health = min(self.max_health, self.health + amount)

    def _die(self):
        self.lives -= 1
        self.game.particles.explosion(self.x, self.y, (100, 180, 255), count=45, speed=9)
        self.game.particles.shake(20)
        self.game.audio.play('explosion')
        if self.lives > 0:
            self.health    = self.max_health
            self.shield    = self.max_shield
            self._inv_until= pygame.time.get_ticks() + 3000
        else:
            self.game.change_state('GAME_OVER')

    # ── Effects ───────────────────────────────────────────────────────────────
    def add_effect(self, name: str, duration_ms: int):
        self._effects[name] = pygame.time.get_ticks() + duration_ms

    def has_effect(self, name: str) -> bool:
        return name in self._effects

    def effect_remaining(self, name: str) -> int:
        if name not in self._effects:
            return 0
        return max(0, self._effects[name] - pygame.time.get_ticks())

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        now = pygame.time.get_ticks()

        # Purchased trail (drawn behind ship + engines)
        self.trail.draw(surface)

        # Engine thrust flames (always shown behind ship)
        self._draw_flame(surface)

        # Blink during invincibility
        if now < self._inv_until and self._blink_tick < 4:
            return

        # Shield bubble
        if self.shield > 0:
            ratio = self.shield / self.max_shield
            r     = self.rect.width // 2 + 14
            cx, cy = self.rect.centerx, self.rect.centery
            if IS_ANDROID:
                # Direct draw — no SRCALPHA surface
                fade = int(120 * ratio)
                col  = (int(50 * ratio), int(120 * ratio), min(255, int(255 * ratio)))
                pygame.draw.ellipse(surface, col, (cx-r, cy-r, r*2, r*2), 2)
            else:
                ss    = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                alpha = int(55 * ratio)
                pygame.draw.ellipse(ss, (50, 120, 255, alpha), ss.get_rect())
                pygame.draw.ellipse(ss, (100, 200, 255, 180), ss.get_rect(), 2)
                surface.blit(ss, (cx - r, cy - r))

        surface.blit(self.image, self.rect)

        # Invincibility — rotating dual-hex shield
        if self.has_effect('invincibility'):
            t   = pygame.time.get_ticks()
            ang = t * 0.0028
            cx, cy = int(self.x), int(self.y)
            R   = 42
            pts_out = [(cx + int(R * math.cos(ang + i * math.tau / 6)),
                        cy + int(R * math.sin(ang + i * math.tau / 6)))
                       for i in range(6)]
            if IS_ANDROID:
                # Direct polygon draw — no SRCALPHA surface
                pygame.draw.polygon(surface, (200, 0, 255), pts_out, 3)
                Ri = 26
                pts_in = [(cx + int(Ri * math.cos(-ang * 1.6 + i * math.tau / 6)),
                           cy + int(Ri * math.sin(-ang * 1.6 + i * math.tau / 6)))
                          for i in range(6)]
                pygame.draw.polygon(surface, (180, 60, 220), pts_in, 2)
            else:
                a   = int(160 + 80 * math.sin(t * 0.009))
                os_ = pygame.Surface((R*2+8, R*2+8), pygame.SRCALPHA)
                lp  = [(p[0]-cx+R+4, p[1]-cy+R+4) for p in pts_out]
                pygame.draw.polygon(os_, (200, 0, 255, a), lp, 3)
                surface.blit(os_, (cx-R-4, cy-R-4))
                Ri = 26
                pts_in = [(cx + int(Ri * math.cos(-ang * 1.6 + i * math.tau / 6)),
                           cy + int(Ri * math.sin(-ang * 1.6 + i * math.tau / 6)))
                          for i in range(6)]
                is_ = pygame.Surface((Ri*2+8, Ri*2+8), pygame.SRCALPHA)
                lp2 = [(p[0]-cx+Ri+4, p[1]-cy+Ri+4) for p in pts_in]
                pygame.draw.polygon(is_, (255, 100, 255, int(a * 0.65)), lp2, 2)
                surface.blit(is_, (cx-Ri-4, cy-Ri-4))

        # Damage boost — pulsing energy wings
        if self.has_effect('damage_boost') and not IS_ANDROID:
            t2  = pygame.time.get_ticks()
            pa  = int(180 + 60 * math.sin(t2 * 0.012))
            for sign in (-1, 1):
                wx = int(self.x) + sign * 24
                wy = self.rect.top + 6
                pts = [(wx, wy), (wx + sign*12, wy+14), (wx + sign*4, wy+20),
                       (wx + sign*2, wy+10)]
                ws = pygame.Surface((40, 30), pygame.SRCALPHA)
                lp = [(p[0]-wx+18, p[1]-wy+2) for p in pts]
                pygame.draw.polygon(ws, (255, 120, 0, pa), lp)
                pygame.draw.polygon(ws, (255, 220, 80, pa//2), lp, 1)
                surface.blit(ws, (wx - 18, wy - 2))
