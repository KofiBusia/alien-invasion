"""Level manager: spawning waves with formations, tracking completion."""

import random
import pygame
from settings import get_level_config, TOTAL_LEVELS, SCREEN_WIDTH
from enemy import spawn_enemy
from boss import Boss


_V_FORMATION   = 'v'
_LINE_FORMATION= 'line'
_PINCER        = 'pincer'
_ARROW         = 'arrow'


class LevelManager:
    def __init__(self, game):
        self.game        = game
        self.level       = 1
        self.cfg         = get_level_config(1)
        self._phase      = 'intro'
        self._wave_timer = 0.0
        self._spawned    = {'scout': 0, 'fighter': 0, 'tank': 0}
        self._totals     = {}
        self._boss_spawned   = False
        self._complete_timer = 0
        self._intro_timer    = 120
        self._formation_cd   = 0

    # ── Public ────────────────────────────────────────────────────────────────
    def start_level(self, level: int):
        self.level         = level
        self.cfg           = get_level_config(level)
        self.game.level_cfg= self.cfg
        self._phase        = 'intro'
        self._intro_timer  = 90
        self._boss_spawned = False
        self._wave_timer   = 0.0
        self._formation_cd = 0
        self._spawned      = {'scout': 0, 'fighter': 0, 'tank': 0, 'destroyer': 0}
        self._totals       = {
            'scout':     self.cfg['scout_count'],
            'fighter':   self.cfg['fighter_count'],
            'tank':      self.cfg['tank_count'],
            'destroyer': self.cfg['destroyer_count'],
        }

    def update(self):
        if self._phase == 'intro':
            self._intro_timer -= 1
            if self._intro_timer <= 0:
                self._phase = 'boss' if self.cfg['is_boss'] else 'wave'
            return

        if self._phase == 'wave':
            self._update_wave()
        elif self._phase == 'boss':
            self._update_boss()
        elif self._phase == 'complete':
            self._complete_timer += 1
            if self._complete_timer >= 90:
                self.game.change_state('QUIZ')

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def intro_active(self) -> bool:
        return self._phase == 'intro'

    @property
    def wave_done(self) -> bool:
        if self._phase != 'wave':
            return False
        all_spawned = all(self._spawned[k] >= self._totals[k] for k in self._totals)
        return all_spawned and len(self.game.enemies) == 0

    @property
    def boss_done(self) -> bool:
        return self._phase == 'boss' and self._boss_spawned and len(self.game.boss_group) == 0

    def complete(self):
        self._phase          = 'complete'
        self._complete_timer = 0
        lvl  = self.level
        save = self.game.save
        if lvl > save.get('best_level', 0):
            save.set('best_level', lvl)

        if self.game.player.level_damage_taken == 0:
            save.increment_stat('perfect_levels')
            bonus = 200 + lvl * 50
            self.game.player.coins += bonus
            self.game.ui.show_message(
                f'PERFECT! +{bonus} COINS',
                SCREEN_WIDTH // 2, 320,
                (255, 220, 50), 'lg')

        self.game.player.level_damage_taken = 0

        # Wave clear coins bonus
        clear_bonus = 50 + lvl * 20
        self.game.player.coins += clear_bonus
        self.game.ui.show_message(
            f'WAVE CLEAR  +{clear_bonus}',
            SCREEN_WIDTH // 2, 380,
            (80, 220, 100), 'md')
        self.game.particles.stars_burst(SCREEN_WIDTH // 2, 400, 60)
        self.game.screen_flash((80, 220, 80), 50)

    # ── Intro text ────────────────────────────────────────────────────────────
    def draw_intro(self, surface: pygame.Surface):
        if not self.intro_active:
            return
        t   = self._intro_timer   # counts DOWN from 90 to 0
        MAX = 90
        FADE_IN  = 18
        FADE_OUT = 22

        if t > MAX - FADE_IN:
            progress = (MAX - t) / FADE_IN
        else:
            progress = 1.0
        fade_out = t / FADE_OUT if t < FADE_OUT else 1.0
        alpha    = int(255 * progress * fade_out)
        if alpha < 4:
            return

        # Scale zooms in from 1.6 → 1.0 during fade-in
        scale = max(1.0, 1.6 - 0.6 * progress)

        cx = surface.get_width()  // 2
        cy = surface.get_height() // 2

        is_boss = self.cfg['is_boss']
        msg     = f'LEVEL  {self.level}' if not is_boss else '⚠  BOSS  INCOMING  ⚠'
        col     = (255, 55, 55) if is_boss else (255, 230, 0)
        gc      = (200, 20, 20) if is_boss else (180, 140, 0)

        # Glow ellipse behind text
        gw, gh = 640, 130
        gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.ellipse(gs, (*gc, int(alpha * 0.38)), gs.get_rect())
        surface.blit(gs, gs.get_rect(center=(cx, cy)))

        # Main title
        fsz  = int(54 * scale)
        font = pygame.font.SysFont('consolas', fsz, bold=True)
        txt  = font.render(msg, True, col)
        txt.set_alpha(alpha)
        # Drop shadow
        sh = font.render(msg, True, (0, 0, 0))
        sh.set_alpha(alpha // 2)
        surface.blit(sh, sh.get_rect(center=(cx + 3, cy + 3)))
        surface.blit(txt, txt.get_rect(center=(cx, cy)))

        # Subtitle
        if is_boss:
            sub = f'Level {self.level} Boss Battle  —  Good luck!'
        else:
            total = sum(self._totals.values())
            destroyers = self._totals.get('destroyer', 0)
            if destroyers:
                sub = f'{total} aliens inbound  ·  {destroyers} DESTROYER{"S" if destroyers>1 else ""}!'
            else:
                sub = f'{total} alien ships incoming'

        sub_font = pygame.font.SysFont('consolas', int(22 * min(1.0, scale + 0.15)))
        stxt     = sub_font.render(sub, True, (225, 205, 255))
        stxt.set_alpha(int(alpha * 0.88))
        surface.blit(stxt, stxt.get_rect(center=(cx, cy + int(68 * min(1.0, scale + 0.1)))))

    # ── Wave logic ────────────────────────────────────────────────────────────
    def _update_wave(self):
        self._wave_timer   += 1
        self._formation_cd  = max(0, self._formation_cd - 1)
        rate = self.cfg['spawn_rate'] * 60

        if self._wave_timer >= rate:
            self._wave_timer = 0
            self._try_spawn()

        # Occasional formation burst
        remaining = sum(self._totals[k] - self._spawned[k] for k in self._totals)
        if (self._formation_cd == 0
                and remaining >= 5
                and random.random() < 0.004):   # ~once per 250 frames
            self._try_formation()
            self._formation_cd = int(rate * 3)

        if self.wave_done:
            self.complete()

    def _try_spawn(self):
        for kind in ('destroyer', 'tank', 'fighter', 'scout'):
            if self._spawned[kind] < self._totals[kind]:
                if kind == 'destroyer' and self._spawned['scout'] < 3: continue
                if kind == 'tank'      and self._spawned['scout'] < 2: continue
                if kind == 'fighter'   and self._spawned['scout'] < 1: continue
                spawn_enemy(self.game, kind)
                self._spawned[kind] += 1
                return

    # ── Formation spawning ────────────────────────────────────────────────────
    def _try_formation(self):
        scouts_left   = self._totals['scout']   - self._spawned['scout']
        fighters_left = self._totals['fighter'] - self._spawned['fighter']

        if scouts_left >= 5:
            fmt  = random.choice([_V_FORMATION, _LINE_FORMATION, _ARROW])
            kind = 'scout'
            n    = min(scouts_left, random.choice([5, 7]))
        elif fighters_left >= 4:
            fmt  = random.choice([_LINE_FORMATION, _PINCER])
            kind = 'fighter'
            n    = min(fighters_left, 4)
        else:
            return

        self._spawn_formation(kind, fmt, n)

    def _spawn_formation(self, kind: str, fmt: str, n: int):
        cx        = SCREEN_WIDTH // 2
        remaining = self._totals[kind] - self._spawned[kind]
        n = min(n, remaining)
        if n <= 0:
            return

        positions = []

        if fmt == _V_FORMATION:
            for i in range(n):
                offset = abs(i - n // 2)
                x = cx + (i - n // 2) * 70
                y = -50 - offset * 35
                positions.append((x, y))

        elif fmt == _LINE_FORMATION:
            spacing = max(50, SCREEN_WIDTH // (n + 1))
            for i in range(n):
                x = spacing * (i + 1)
                y = -50
                positions.append((x, y))

        elif fmt == _PINCER:
            half = n // 2
            for i in range(half):
                positions.append((60 + i * 45,             -50 - i * 20))
                positions.append((SCREEN_WIDTH-60-i*45,    -50 - i * 20))
            if n % 2 == 1:
                positions.append((cx, -50))

        elif fmt == _ARROW:
            for i in range(n):
                offset = abs(i - n // 2)
                x = cx + (i - n // 2) * 65
                y = -50 + (n // 2 - offset) * 35
                positions.append((x, y))

        for (x, y) in positions:
            spawn_enemy(self.game, kind, x, y)
            self._spawned[kind] += 1

    # ── Boss logic ────────────────────────────────────────────────────────────
    def _update_boss(self):
        if not self._boss_spawned:
            b = Boss(self.game, self.level)
            self.game.boss_group.add(b)
            self.game.all_sprites.add(b)
            self._boss_spawned = True

        if self.boss_done:
            self.complete()

    # ── HUD progress ──────────────────────────────────────────────────────────
    def draw_wave_progress(self, surface: pygame.Surface):
        if self._phase not in ('wave',):
            return
        spawned = sum(self._spawned.values())
        total   = sum(self._totals.values())
        remain  = len(self.game.enemies)
        font    = pygame.font.SysFont('consolas', 13)
        txt = font.render(f'Enemies: {remain}  |  Wave: {spawned}/{total}', True, (180,180,255))
        surface.blit(txt, (10, 70))
