"""Level manager: chapter-aware wave spawning with formations."""

import os
import random
import pygame
from settings import (
    get_level_config, get_chapter, get_chapter_level,
    get_chapter_name, get_chapter_color, get_chapter_subtitle,
    TOTAL_LEVELS, SCREEN_WIDTH, LEVELS_PER_CHAPTER
)
from enemy import spawn_enemy

_IS_ANDROID = bool(os.environ.get('ANDROID_ROOT'))
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
        self._spawned: dict[str, int] = {}
        self._totals:  dict[str, int] = {}
        self._kinds:   list[str]      = []
        self._boss_spawned   = False
        self._complete_timer = 0
        self._intro_timer    = 120
        self._formation_cd   = 0
        self._is_chapter_start = False
        self._wave_font  = pygame.font.SysFont('consolas', 13)
        self._intro_font_lg = pygame.font.SysFont('consolas', 64, bold=True)
        self._intro_font_md = pygame.font.SysFont('consolas', 26, bold=True)
        self._intro_font_sm = pygame.font.SysFont('consolas', 20)

    # ── Public ────────────────────────────────────────────────────────────────
    def start_level(self, level: int):
        self.level         = level
        self.cfg           = get_level_config(level)
        self.game.level_cfg= self.cfg
        self._phase        = 'intro'
        self._boss_spawned = False
        self._wave_timer   = 0.0
        self._formation_cd = 0

        self._is_chapter_start = (self.cfg['chapter_level'] == 1 and level > 1)
        self._intro_timer = 150 if self._is_chapter_start else 90

        self._kinds   = list(self.cfg['enemy_kinds'])
        enemy_counts  = self.cfg['enemy_counts']
        self._spawned = {k: 0 for k in enemy_counts}
        self._totals  = dict(enemy_counts)

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
        all_spawned = all(self._spawned.get(k, 0) >= self._totals.get(k, 0)
                         for k in self._totals)
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

        # Chapter clear achievements
        from settings import get_chapter, LEVELS_PER_CHAPTER, get_chapter_name
        ch = get_chapter(lvl)
        ch_lvl = self.cfg['chapter_level']
        if ch_lvl == LEVELS_PER_CHAPTER and ch >= 2:
            ach_map = {2:'ch2_clear', 3:'ch3_clear', 4:'ch4_clear'}
            ach = ach_map.get(ch)
            if ach and save.unlock_achievement(ach):
                self.game.ui.show_achievement(ach)

        if self.game.player.level_damage_taken == 0:
            save.increment_stat('perfect_levels')
            bonus = 200 + lvl * 50
            self.game.player.coins += bonus
            self.game.ui.show_message(
                f'PERFECT! +{bonus} COINS',
                SCREEN_WIDTH // 2, 320,
                (255, 220, 50), 'lg')

        self.game.player.level_damage_taken = 0

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
        t   = self._intro_timer
        MAX = 150 if self._is_chapter_start else 90
        FADE_IN  = 20
        FADE_OUT = 25

        if t > MAX - FADE_IN:
            progress = (MAX - t) / FADE_IN
        else:
            progress = 1.0
        fade_out = t / FADE_OUT if t < FADE_OUT else 1.0
        alpha    = int(255 * progress * fade_out)
        if alpha < 4:
            return

        scale = max(1.0, 1.6 - 0.6 * progress)
        cx    = surface.get_width()  // 2
        cy    = surface.get_height() // 2

        chapter  = self.cfg['chapter']
        ch_level = self.cfg['chapter_level']
        is_boss  = self.cfg['is_boss']
        chap_col = get_chapter_color(chapter)

        if self._is_chapter_start:
            # Chapter start screen
            msg  = f'CHAPTER  {chapter}'
            sub  = get_chapter_name(chapter)
            sub2 = get_chapter_subtitle(chapter)
            col  = chap_col
            gc   = tuple(max(0, v-60) for v in chap_col)
        elif is_boss:
            msg  = '  BOSS  INCOMING  '
            sub  = f'Chapter {chapter} — Level {ch_level} Boss'
            sub2 = 'Prepare for battle!'
            col  = (255, 55, 55)
            gc   = (160, 10, 10)
        else:
            msg  = f'LEVEL  {ch_level}'
            sub  = f'Chapter {chapter}: {get_chapter_name(chapter)}'
            total = sum(self._totals.values())
            destr_kind = self._kinds[3] if len(self._kinds) >= 4 else 'destroyer'
            destroyers = self._totals.get(destr_kind, 0)
            if destroyers:
                sub2 = (f'{total} aliens  ·  {destroyers} '
                        f'{destr_kind.upper()}{"S" if destroyers>1 else ""}!')
            else:
                sub2 = f'{total} alien ships incoming'
            col  = chap_col
            gc   = tuple(max(0, v-80) for v in chap_col)

        # Glow ellipse
        if not _IS_ANDROID:
            gw, gh = 700, 140
            gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
            pygame.draw.ellipse(gs, (*gc, int(alpha * 0.35)), gs.get_rect())
            surface.blit(gs, gs.get_rect(center=(cx, cy)))

        # Main title
        if _IS_ANDROID:
            font = self._intro_font_lg
            txt  = font.render(msg, True, col)
            txt.set_alpha(alpha)
            surface.blit(txt, txt.get_rect(center=(cx, cy)))
            st1 = self._intro_font_md.render(sub, True, (255, 255, 255))
            st1.set_alpha(int(alpha * 0.9))
            surface.blit(st1, st1.get_rect(center=(cx, cy + 58)))
            st2 = self._intro_font_sm.render(sub2, True, (220, 200, 255))
            st2.set_alpha(int(alpha * 0.8))
            surface.blit(st2, st2.get_rect(center=(cx, cy + 88)))
        else:
            fsz  = int((64 if self._is_chapter_start else 54) * scale)
            font = pygame.font.SysFont('consolas', fsz, bold=True)
            txt  = font.render(msg, True, col)
            txt.set_alpha(alpha)
            sh   = font.render(msg, True, (0, 0, 0))
            sh.set_alpha(alpha // 2)
            surface.blit(sh, sh.get_rect(center=(cx + 3, cy + 3)))
            surface.blit(txt, txt.get_rect(center=(cx, cy)))
            sf1 = pygame.font.SysFont('consolas', int(26 * min(1.0, scale + 0.1)), bold=True)
            st1 = sf1.render(sub, True, (255, 255, 255))
            st1.set_alpha(int(alpha * 0.9))
            surface.blit(st1, st1.get_rect(center=(cx, cy + int(55 * min(1.0, scale+0.1)))))
            sf2 = pygame.font.SysFont('consolas', int(20 * min(1.0, scale + 0.15)))
            st2 = sf2.render(sub2, True, (220, 200, 255))
            st2.set_alpha(int(alpha * 0.80))
            surface.blit(st2, st2.get_rect(center=(cx, cy + int(85 * min(1.0, scale+0.1)))))

        # Chapter indicator dots (bottom of screen)
        if self._is_chapter_start:
            from settings import TOTAL_CHAPTERS
            dot_y = cy + 130
            dot_spacing = 30
            total_w = (TOTAL_CHAPTERS - 1) * dot_spacing
            for i in range(1, TOTAL_CHAPTERS + 1):
                dx = cx - total_w // 2 + (i-1) * dot_spacing
                if i < chapter:
                    dcol = (100, 100, 100)
                    dr = 7
                elif i == chapter:
                    dcol = chap_col
                    dr = 10
                else:
                    dcol = (40, 40, 60)
                    dr = 6
                if _IS_ANDROID:
                    pygame.draw.circle(surface, dcol, (dx, dot_y), dr)
                else:
                    ts = pygame.Surface((dr*2+4, dr*2+4), pygame.SRCALPHA)
                    pygame.draw.circle(ts, (*dcol, alpha), (dr+2, dr+2), dr)
                    surface.blit(ts, (dx-dr-2, dot_y-dr-2))

    # ── Wave logic ────────────────────────────────────────────────────────────
    def _update_wave(self):
        self._wave_timer  += 1
        self._formation_cd = max(0, self._formation_cd - 1)
        rate = self.cfg['spawn_rate'] * 60

        if self._wave_timer >= rate:
            self._wave_timer = 0
            self._try_spawn()

        remaining = sum(self._totals.get(k,0) - self._spawned.get(k,0) for k in self._totals)
        if (self._formation_cd == 0
                and remaining >= 5
                and random.random() < 0.004):
            self._try_formation()
            self._formation_cd = int(rate * 3)

        if self.wave_done:
            self.complete()

    def _try_spawn(self):
        kinds = self._kinds
        scout_kind = kinds[0] if kinds else 'scout'

        for kind in reversed(kinds):
            remaining = self._totals.get(kind, 0) - self._spawned.get(kind, 0)
            if remaining <= 0:
                continue
            idx = kinds.index(kind)
            scout_spawned = self._spawned.get(scout_kind, 0)
            if idx == 3 and scout_spawned < 3: continue
            if idx == 2 and scout_spawned < 2: continue
            if idx == 1 and scout_spawned < 1: continue
            spawn_enemy(self.game, kind)
            self._spawned[kind] = self._spawned.get(kind, 0) + 1
            return

    # ── Formation spawning ────────────────────────────────────────────────────
    def _try_formation(self):
        if not self._kinds:
            return
        scout_kind   = self._kinds[0]
        fighter_kind = self._kinds[1] if len(self._kinds) > 1 else scout_kind
        scouts_left   = self._totals.get(scout_kind, 0)   - self._spawned.get(scout_kind, 0)
        fighters_left = self._totals.get(fighter_kind, 0) - self._spawned.get(fighter_kind, 0)

        if scouts_left >= 5:
            fmt  = random.choice([_V_FORMATION, _LINE_FORMATION, _ARROW])
            kind = scout_kind
            n    = min(scouts_left, random.choice([5, 7]))
        elif fighters_left >= 4:
            fmt  = random.choice([_LINE_FORMATION, _PINCER])
            kind = fighter_kind
            n    = min(fighters_left, 4)
        else:
            return

        self._spawn_formation(kind, fmt, n)

    def _spawn_formation(self, kind: str, fmt: str, n: int):
        cx        = SCREEN_WIDTH // 2
        remaining = self._totals.get(kind, 0) - self._spawned.get(kind, 0)
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
                positions.append((spacing * (i + 1), -50))

        elif fmt == _PINCER:
            half = n // 2
            for i in range(half):
                positions.append((60 + i * 45,          -50 - i * 20))
                positions.append((SCREEN_WIDTH-60-i*45, -50 - i * 20))
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
            self._spawned[kind] = self._spawned.get(kind, 0) + 1

    # ── Boss logic ────────────────────────────────────────────────────────────
    def _update_boss(self):
        if not self._boss_spawned:
            b = Boss(self.game, self.level)
            self.game.boss_group.add(b)
            self.game.all_sprites.add(b)
            self._boss_spawned = True
            # Dramatic boss entrance
            self.game.screen_flash((255, 0, 0), 110)
            self.game.particles.shake(18)
            from settings import SCREEN_WIDTH, SCREEN_HEIGHT
            self.game.ui.show_message(
                'BOSS INCOMING!',
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120,
                (255, 50, 50), 'xl')

        if self.boss_done:
            self.complete()

    # ── HUD progress ──────────────────────────────────────────────────────────
    def draw_wave_progress(self, surface: pygame.Surface):
        if self._phase not in ('wave',):
            return
        spawned = sum(self._spawned.values())
        total   = sum(self._totals.values())
        remain  = len(self.game.enemies)
        chapter = self.cfg['chapter']
        ch_lvl  = self.cfg['chapter_level']
        txt = self._wave_font.render(
            f'Ch {chapter} · Lv {ch_lvl}  |  Enemies: {remain}  |  Wave: {spawned}/{total}',
            True, (180,180,255))
        surface.blit(txt, (10, 70))
