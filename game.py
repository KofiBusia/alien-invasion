"""Main game class: state machine, event loop, collision resolution."""

import sys
import random
import math
import pygame

from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    TOTAL_LEVELS, ACHIEVEMENTS, POWERUP_CONFIGS, get_level_config, GOLD,
    IS_ANDROID, get_chapter, get_chapter_color
)
from save_system    import SaveSystem
from audio          import AudioManager
from particles      import ParticleSystem
from background     import Background
from player         import Player
from levels         import LevelManager
from shop           import Shop
from ui             import UIManager
from quiz           import QuizManager
from ally           import Ally, AllyBullet, ALLY_CONFIGS, ALLY_ORDER
from ultimate_boss  import UltimateBoss
from perk           import PerkScreen, pick_3_perks
from asteroid       import Asteroid, AsteroidField


STATES = frozenset([
    'MAIN_MENU', 'PLAYING', 'PAUSED', 'SHOP',
    'GAME_OVER', 'VICTORY', 'QUIZ',
    'SETTINGS', 'HIGH_SCORES', 'HOW_TO_PLAY',
    'ULTIMATE_BOSS', 'PERK_SELECT',
])

_BACK = {
    'SETTINGS':    None,
    'HIGH_SCORES': 'MAIN_MENU',
    'HOW_TO_PLAY': 'MAIN_MENU',
}


class Game:
    def __init__(self):
        pygame.init()
        if IS_ANDROID:
            # On Android: render game to a fixed logical surface then scale to display
            self._display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.screen   = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            self._display = None
            self.screen   = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock  = pygame.time.Clock()

        # Core systems
        self.save       = SaveSystem()
        self.audio      = AudioManager(self.save)
        self.particles  = ParticleSystem()
        self.background = Background()

        # Sprite groups
        self.all_sprites   = pygame.sprite.Group()
        self.player_group  = pygame.sprite.GroupSingle()
        self.enemies       = pygame.sprite.Group()
        self.boss_group    = pygame.sprite.Group()
        self.player_bullets= pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.powerups      = pygame.sprite.Group()
        self.coins_group   = pygame.sprite.Group()
        self.allies        = pygame.sprite.Group()
        self.ally_bullets  = pygame.sprite.Group()

        # Ultimate boss state
        self._ub_spawned        = False
        self._ub_complete_timer = 0

        # Asteroid hazard
        self.asteroids       = pygame.sprite.Group()
        self._asteroid_field = AsteroidField(self)

        # Mid-run perk system (triggered every 5 completed levels)
        self._perk_screen  = PerkScreen()

        self.player        = None
        self.level_manager = None
        self.level_cfg     = get_level_config(1)
        self.current_level = 1

        self.ui   = UIManager(self)
        self.shop = Shop(self)
        self.quiz = QuizManager(self)

        # State
        self._state           = 'MAIN_MENU'
        self._prev_state      = 'MAIN_MENU'
        self._settings_origin = 'MAIN_MENU'
        self._font_fps        = pygame.font.SysFont('consolas', 14)
        self._font_combo_big  = pygame.font.SysFont('consolas', 36, bold=True)
        self._font_combo_small= pygame.font.SysFont('consolas', 18)
        self._pending_achievement: list[str] = []

        self._q_held = self._e_held = False

        # ── Display / fullscreen ─────────────────────────────────────────────
        self._fullscreen = False

        # ── Mouse / touch input ───────────────────────────────────────────────
        self._mouse_target  = None
        self._mouse_firing  = False
        self._touch_fingers: dict = {}
        self._fire_finger   = None

        # ── Virtual joystick (left thumb) ────────────────────────────────────
        if IS_ANDROID:
            _JX, _JY         = 190, SCREEN_HEIGHT - 190
            self._joy_base_r = 150
            self._joy_knob_r = 72
        else:
            _JX, _JY         = 155, SCREEN_HEIGHT - 155
            self._joy_base_r = 115
            self._joy_knob_r = 52
        self._joy_center  = (_JX, _JY)
        self._joy_pos     = (_JX, _JY)
        self._joy_finger  = None
        self._joy_dx      = 0.0
        self._joy_dy      = 0.0

        # ── Fire button (large circle, bottom-right) ──────────────────────
        if IS_ANDROID:
            self._fire_center = (SCREEN_WIDTH - 135, SCREEN_HEIGHT - 185)
            self._fire_r      = 118
        else:
            self._fire_center = (SCREEN_WIDTH - 105, SCREEN_HEIGHT - 158)
            self._fire_r      = 85

        # ── Weapon switch buttons (bottom, left of fire button) ───────────
        if IS_ANDROID:
            self._obtn_prev = pygame.Rect(SCREEN_WIDTH - 460, SCREEN_HEIGHT - 90, 152, 80)
            self._obtn_next = pygame.Rect(SCREEN_WIDTH - 303, SCREEN_HEIGHT - 90, 152, 80)
        else:
            self._obtn_prev = pygame.Rect(SCREEN_WIDTH - 355, SCREEN_HEIGHT - 75, 115, 62)
            self._obtn_next = pygame.Rect(SCREEN_WIDTH - 230, SCREEN_HEIGHT - 75, 115, 62)

        # ── Pre-rendered control surfaces (built once, blitted each frame) ─
        self._ctrl_joy_base, self._ctrl_joy_knob_idle, self._ctrl_joy_knob_active, \
            self._ctrl_fire_idle, self._ctrl_fire_active, \
            self._ctrl_prev_surf, self._ctrl_next_surf = self._build_ctrl_surfs()

        # ── Pause button (top-right corner, Android) ──────────────────────
        self._pause_btn_rect  = pygame.Rect(SCREEN_WIDTH - 100, 6, 90, 56)
        self._ctrl_pause_surf = self._build_pause_surf()

        # ── Pre-rendered low-health vignette ──────────────────────────────
        self._vignette_surf = self._build_vignette_surf()

        # ── Combat juice ──────────────────────────────────────────────────────
        # Combo system
        self._combo      = 0          # consecutive kills
        self._combo_mult = 1.0        # score multiplier (1.0 + combo * 0.1)
        self._combo_timer= 0          # frames until combo resets

        # Kill streak (resets when player takes real damage)
        self._kill_streak = 0

        # Last Stand Mode (once per life when HP ≤ 25%)
        self._last_stand_triggered = False
        self._last_stand_active    = False
        self._last_stand_timer     = 0

        # Challenge bounty missions
        self._challenge_active       = False
        self._challenge_goal         = 0
        self._challenge_done         = 0
        self._challenge_frames       = 0
        self._challenge_total_frames = 0
        self._challenge_reward       = 0
        self._wave_challenge_checked = False

        # Level rank (set by LevelManager.complete)
        self._last_level_rank = ('', (180, 180, 180))

        # Endless survival mode
        self._endless_mode = False
        self._endless_wave = 0

        # Daily login bonus (0 if already claimed today)
        self._daily_bonus = self.save.check_daily_bonus()

        # Screen flash (damage / pickup / boss rage)
        self._flash_surf   = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._flash_alpha  = 0
        self._flash_color  = (255, 0, 0)

        # Glow / bloom layer
        self._glow_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._glow_surf.set_colorkey((0, 0, 0))

        # Chromatic aberration: frames remaining + strength
        self._chroma_frames   = 0
        self._chroma_strength = 0

        # Hitstop: freeze game updates for N frames on big hits
        self._hitstop_frames  = 0

        self.audio.play_music('bg')

    # ── State machine ─────────────────────────────────────────────────────────
    def change_state(self, new_state: str):
        assert new_state in STATES, f'Unknown state: {new_state}'
        self._prev_state = self._state
        self._state      = new_state

        if new_state == 'PLAYING' and self._prev_state == 'PAUSED':
            self._mouse_firing = False
        elif new_state == 'SHOP':
            self.shop.open()
        elif new_state == 'MAIN_MENU':
            self.audio.stop_music()
            self.audio.play_music('bg')
        elif new_state == 'QUIZ':
            self.quiz.start(self.current_level)
        elif new_state == 'GAME_OVER':
            self._finalize_run()
            self.audio.stop_music()
            self.audio.play('gameover')
        elif new_state == 'VICTORY':
            self._finalize_run()
            self.audio.stop_music()
            self.audio.play('victory')
        elif new_state == 'ULTIMATE_BOSS':
            pass   # handled by _start_ultimate_boss directly

    # ── Game start / reset ────────────────────────────────────────────────────
    def start_new_game(self, level: int = 1):
        self._clear_sprites()
        self.current_level  = level
        self.level_cfg      = get_level_config(level)
        self._ub_spawned    = False
        self._ub_complete_timer = 0

        self.player = Player(self)
        self.player_group.add(self.player)
        self.all_sprites.add(self.player)

        self._spawn_allies()

        self.level_manager = LevelManager(self)
        self.level_manager.start_level(level)

        # Reset combat state on new game
        self._combo        = 0
        self._combo_mult   = 1.0
        self._combo_timer  = 0
        self._kill_streak  = 0
        self._last_stand_triggered   = False
        self._last_stand_active      = False
        self._last_stand_timer       = 0
        self._challenge_active       = False
        self._challenge_done         = 0
        self._challenge_frames       = 0
        self._challenge_total_frames = 0
        self._wave_challenge_checked = False
        self._endless_mode = False
        self._endless_wave = 0
        self._perk_screen._history.clear()
        self.asteroids.empty()
        self._asteroid_field.reset()
        self.background.set_theme(get_chapter(level))

        self.ui.ensure_secondary_menus()
        self.change_state('PLAYING')

    def _next_level(self):
        completed = self.current_level
        self.current_level += 1
        if not self._endless_mode and self.current_level > TOTAL_LEVELS:
            self._start_ultimate_boss()
            return
        self._clear_enemies_and_bullets()
        self._spawn_allies()
        self.level_cfg = get_level_config(self.current_level)
        self.level_manager.start_level(self.current_level)
        self.background.set_theme(get_chapter(min(self.current_level, TOTAL_LEVELS)))
        self._wave_challenge_checked = False
        self._last_stand_triggered   = False  # reset per life (triggered per level)

        if self._endless_mode:
            self._endless_wave += 1
            self.save.increment_stat('endless_waves')
            best = self.save.get('best_endless_wave', 0)
            if self._endless_wave > best:
                self.save.set('best_endless_wave', self._endless_wave)
            self.change_state('PLAYING')
            return

        # Perk upgrade screen every 5 completed levels
        if completed % 5 == 0:
            exclude = [p['id'] for p in self._perk_screen._history]
            self._perk_screen.show(pick_3_perks(exclude), completed)
            self.change_state('PERK_SELECT')
        else:
            self.change_state('PLAYING')

    def _spawn_allies(self):
        """Spawn all purchased ally ships for the current level."""
        # Clear any existing allies first
        for a in list(self.allies):
            a.kill()
        unlocked = self.save.get('unlocked_allies', [])
        for key in ALLY_ORDER:
            if key in unlocked:
                slot = ALLY_ORDER.index(key)
                a    = Ally(self, key, slot)
                self.allies.add(a)
                self.all_sprites.add(a)

    def start_endless_mode(self):
        """Begin endless survival — called from the victory screen."""
        self._endless_mode  = True
        self._endless_wave  = 0
        self.current_level  = TOTAL_LEVELS + 1
        self._clear_enemies_and_bullets()
        self._spawn_allies()
        self.level_cfg = get_level_config(self.current_level)
        self.level_manager.start_level(self.current_level)
        self.background.set_theme(5)
        self.change_state('PLAYING')
        self.screen_flash((255, 100, 0), 100)
        self.ui.show_message('ENDLESS SURVIVAL!',
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
            (255, 160, 0), 'xl')

    def _start_ultimate_boss(self):
        """Trigger the ultimate boss battle after level 100."""
        self._clear_enemies_and_bullets()
        self._spawn_allies()
        self._ub_spawned        = True
        self._ub_complete_timer = 0
        boss = UltimateBoss(self)
        self.boss_group.add(boss)
        self.all_sprites.add(boss)
        self._state = 'ULTIMATE_BOSS'
        self.audio.stop_music()
        self.audio.play_music('bg')
        # Announce the final battle
        self.screen_flash((150, 0, 255), 120)
        self.particles.shake(15)
        self.ui.show_message(
            'FINAL BATTLE', SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120,
            (255, 0, 255), 'xl')

    def _clear_sprites(self):
        self.all_sprites.empty()
        self.player_group.empty()
        self.enemies.empty()
        self.boss_group.empty()
        self.player_bullets.empty()
        self.enemy_bullets.empty()
        self.powerups.empty()
        self.coins_group.empty()
        self.allies.empty()
        self.ally_bullets.empty()
        self.asteroids.empty()

    def _clear_enemies_and_bullets(self):
        for grp in (self.enemies, self.boss_group, self.player_bullets,
                    self.enemy_bullets, self.powerups, self.coins_group,
                    self.allies, self.ally_bullets):
            for s in list(grp):
                s.kill()

    def _finalize_run(self):
        if self.player:
            self.save.update_high_score(self.player.score)
            self.save.add_coins(self.player.coins)
            self.player.coins = 0
        self._check_achievements()
        self.save.save()

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()

    # ── Events ────────────────────────────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save.save()
                pygame.quit()
                sys.exit()

            # Global F11 fullscreen toggle (works in any state)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self._toggle_fullscreen()

            if self._state == 'MAIN_MENU':
                self._handle_main_menu_event(event)
            elif self._state == 'PERK_SELECT':
                idx = self._perk_screen.handle_event(event)
                if idx >= 0:
                    perks = self._perk_screen._perks
                    if idx < len(perks) and self.player:
                        chosen = perks[idx]
                        self.player.apply_perk(chosen['id'])
                        self._perk_screen.record_pick(chosen)
                        self.ui.show_message(
                            chosen['name'] + ' ACQUIRED!',
                            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50,
                            chosen['color'], 'lg')
                        self.screen_flash(chosen['color'], 60)
                        self.particles.stars_burst(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 40)
                    self.change_state('PLAYING')
            elif self._state in ('PLAYING', 'ULTIMATE_BOSS'):
                self._handle_playing_event(event)
            elif self._state == 'PAUSED':
                self._handle_pause_event(event)
            elif self._state == 'QUIZ':
                self.quiz.handle_event(event)
            elif self._state == 'SHOP':
                if self.shop.handle_event(event):
                    self._next_level()
            elif self._state == 'GAME_OVER':
                self._handle_game_over_event(event)
            elif self._state == 'VICTORY':
                self._handle_victory_event(event)
            elif self._state == 'SETTINGS':
                result = self.ui.handle_settings(event)
                if result == 'back':
                    self.change_state(self._settings_origin)
            elif self._state == 'HIGH_SCORES':
                result = self.ui.handle_high_scores(event)
                if result == 'BACK':
                    self.change_state('MAIN_MENU')
            elif self._state == 'HOW_TO_PLAY':
                result = self.ui.handle_how_to_play(event)
                if result == 'BACK':
                    self.change_state('MAIN_MENU')

    def _handle_main_menu_event(self, event):
        label = self.ui.handle_main_menu(event)
        if label == 'NEW GAME':
            self.save.reset_run()
            self.start_new_game(1)
        elif label == 'CONTINUE':
            bl  = self.save.get('best_level', 0)
            lvl = max(1, bl) if bl > 0 else 1
            self.start_new_game(lvl)
        elif label == 'HOW TO PLAY':
            self.ui.ensure_secondary_menus()
            self.change_state('HOW_TO_PLAY')
        elif label == 'HIGH SCORES':
            self.ui.ensure_secondary_menus()
            self.change_state('HIGH_SCORES')
        elif label == 'SETTINGS':
            self._settings_origin = 'MAIN_MENU'
            self.ui.ensure_secondary_menus()
            self.change_state('SETTINGS')
        elif label == 'QUIT':
            self.save.save()
            pygame.quit()
            sys.exit()

    def _handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.change_state('PAUSED')
            elif event.key == pygame.K_q:
                self.player.switch_weapon(-1)
                self.audio.play('click')
            elif event.key == pygame.K_e:
                self.player.switch_weapon(1)
                self.audio.play('click')
            elif event.key == pygame.K_F11:
                self._toggle_fullscreen()

        if event.type == pygame.MOUSEWHEEL:
            self.player.switch_weapon(-event.y)

        # Mouse: move ship to mouse position + fire
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            # Avoid setting target when cursor is over HUD
            if my < SCREEN_HEIGHT - 80:
                self._mouse_target = (float(mx), float(my))
            else:
                self._mouse_target = None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if self._pause_btn_rect.collidepoint(mx, my):
                    self.change_state('PAUSED')
                elif self._obtn_prev.collidepoint(mx, my):
                    self.player.switch_weapon(-1)
                    self.audio.play('click')
                elif self._obtn_next.collidepoint(mx, my):
                    self.player.switch_weapon(1)
                    self.audio.play('click')
                else:
                    self._mouse_firing = True
            elif event.button == 3:
                self.player.switch_weapon(1)
                self.audio.play('click')

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._mouse_firing = False

        # Touch finger events
        if event.type == pygame.FINGERDOWN:
            self._on_finger_down(event.finger_id, event.x, event.y)
        if event.type == pygame.FINGERMOTION:
            self._on_finger_motion(event.finger_id, event.x, event.y)
        if event.type == pygame.FINGERUP:
            self._on_finger_up(event.finger_id)

    def _toggle_fullscreen(self):
        if IS_ANDROID:
            return   # always fullscreen on Android
        self._fullscreen = not self._fullscreen
        flags = pygame.FULLSCREEN if self._fullscreen else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    def _update_joystick(self, x, y):
        jx, jy = self._joy_center
        dx = x - jx
        dy = y - jy
        dist = math.hypot(dx, dy)
        if dist > self._joy_base_r:
            dx = dx / dist * self._joy_base_r
            dy = dy / dist * self._joy_base_r
        self._joy_pos = (jx + dx, jy + dy)
        self._joy_dx  = dx / self._joy_base_r
        self._joy_dy  = dy / self._joy_base_r

    def _on_finger_down(self, fid, fx, fy):
        x, y = fx * SCREEN_WIDTH, fy * SCREEN_HEIGHT
        self._touch_fingers[fid] = (x, y)

        # Pause button — highest priority
        if self._pause_btn_rect.collidepoint(x, y):
            self.audio.play('click')
            self.change_state('PAUSED')
            return

        # Weapon buttons take priority
        if self._obtn_prev.collidepoint(x, y):
            if self.player:
                self.player.switch_weapon(-1)
                self.audio.play('click')
            return
        if self._obtn_next.collidepoint(x, y):
            if self.player:
                self.player.switch_weapon(1)
                self.audio.play('click')
            return

        # Joystick zone: left half of screen or close to joystick center
        jx, jy = self._joy_center
        near_joy = math.hypot(x - jx, y - jy) < self._joy_base_r * 2.2
        if (x < SCREEN_WIDTH * 0.50 or near_joy) and self._joy_finger is None:
            self._joy_finger = fid
            self._update_joystick(x, y)
            return

        # Fire zone: right side
        self._fire_finger  = fid
        self._mouse_firing = True

    def _on_finger_motion(self, fid, fx, fy):
        x, y = fx * SCREEN_WIDTH, fy * SCREEN_HEIGHT
        self._touch_fingers[fid] = (x, y)
        if fid == self._joy_finger:
            self._update_joystick(x, y)

    def _on_finger_up(self, fid):
        self._touch_fingers.pop(fid, None)
        if fid == self._joy_finger:
            self._joy_finger = None
            self._joy_pos    = self._joy_center
            self._joy_dx     = 0.0
            self._joy_dy     = 0.0
        if fid == self._fire_finger:
            self._fire_finger  = None
            self._mouse_firing = False

    def _handle_pause_event(self, event):
        resume = self._prev_state if self._prev_state in ('PLAYING', 'ULTIMATE_BOSS') else 'PLAYING'
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.change_state(resume)
            return
        label = self.ui.handle_pause(event)
        if label == 'RESUME':
            self.change_state(resume)
        elif label == 'SETTINGS':
            self._settings_origin = 'PAUSED'
            self.ui.ensure_secondary_menus()
            self.change_state('SETTINGS')
        elif label == 'MAIN MENU':
            self._finalize_run()
            self.change_state('MAIN_MENU')
        elif label == 'QUIT':
            self.save.save()
            pygame.quit()
            sys.exit()

    def _handle_game_over_event(self, event):
        label = self.ui.handle_game_over(event)
        if label == 'TRY AGAIN':
            self.save.set('current_coins', 0)
            self.start_new_game(1)
        elif label == 'MAIN MENU':
            self.change_state('MAIN_MENU')
        elif label == 'QUIT':
            self.save.save()
            pygame.quit()
            sys.exit()

    def _handle_victory_event(self, event):
        label = self.ui.handle_victory(event)
        if label == 'PLAY AGAIN':
            self.save.set('current_coins', 0)
            self.start_new_game(1)
        elif label == 'ENDLESS SURVIVAL':
            self.start_endless_mode()
        elif label == 'MAIN MENU':
            self.change_state('MAIN_MENU')
        elif label == 'QUIT':
            self.save.save()
            pygame.quit()
            sys.exit()

    # ── Update ────────────────────────────────────────────────────────────────
    def _update(self):
        self.background.update()
        self.ui.update()
        self.particles.update()

        # Decay screen flash
        if self._flash_alpha > 0:
            self._flash_alpha = max(0, self._flash_alpha - 8)

        if self._state == 'PLAYING':
            self._update_playing()
        elif self._state == 'ULTIMATE_BOSS':
            self._update_ultimate_boss()
        elif self._state == 'PERK_SELECT':
            pass  # game frozen during perk selection
        elif self._state == 'QUIZ':
            self.quiz.update()
            if self.quiz.done:
                self.change_state('SHOP')
        elif self._state == 'SHOP':
            self.shop.update()

    def _update_playing(self):
        # Hitstop — freeze game simulation for a few frames on big hits
        if self._hitstop_frames > 0:
            self._hitstop_frames -= 1
            # Still update particles and background for juice
            self.particles.update()
            self.background.update()
            return
        self.all_sprites.update()
        self.level_manager.update()
        self._handle_collisions()
        self._handle_coin_magnet()
        self._handle_asteroids()
        self._handle_perk_magnet()
        self._process_bomb_effect()
        self._check_achievements()
        self._update_last_stand()
        self._update_challenge()

        # Decay combo timer
        if self._combo_timer > 0:
            self._combo_timer -= 1
            if self._combo_timer == 0 and self._combo >= 3:
                self.ui.show_message(
                    f'COMBO x{self._combo} ENDED',
                    SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
                    (255, 200, 50), 'md')
        if self._combo_timer == 0 and self._combo > 0:
            prev_max = self.save.data['stats'].get('max_combo', 0)
            if self._combo > prev_max:
                self.save.data['stats']['max_combo'] = self._combo
            self._combo      = 0
            self._combo_mult = 1.0

    def _update_ultimate_boss(self):
        if self._hitstop_frames > 0:
            self._hitstop_frames -= 1
            self.particles.update()
            self.background.update()
            return
        self.all_sprites.update()
        self._handle_collisions()
        self._handle_coin_magnet()
        self._check_achievements()

        # Decay combo
        if self._combo_timer > 0:
            self._combo_timer -= 1
            if self._combo_timer == 0 and self._combo >= 3:
                self.ui.show_message(
                    f'COMBO x{self._combo} ENDED',
                    SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
                    (255, 200, 50), 'md')
        if self._combo_timer == 0 and self._combo > 0:
            prev_max = self.save.data['stats'].get('max_combo', 0)
            if self._combo > prev_max:
                self.save.data['stats']['max_combo'] = self._combo
            self._combo      = 0
            self._combo_mult = 1.0

        # Victory check — boss is dead
        if self._ub_spawned and len(self.boss_group) == 0:
            self._ub_complete_timer += 1
            if self._ub_complete_timer >= 200:
                self._ub_spawned = False
                self.save.unlock_achievement('ultimate_slayer')
                self.save.unlock_achievement('earth_defender')
                self.change_state('VICTORY')

    # ── Combo ─────────────────────────────────────────────────────────────────
    def _on_kill(self, enemy):
        """Call whenever an enemy is destroyed — handles combo, kill streak, score."""
        self._combo      += 1
        self._combo_timer = 220   # ~3.6 s at 60 fps
        self._combo_mult  = min(5.0, 1.0 + self._combo * 0.1)

        ex = int(getattr(enemy, 'x', SCREEN_WIDTH  // 2))
        ey = int(getattr(enemy, 'y', SCREEN_HEIGHT // 2))
        ecol = getattr(enemy, 'color', (255, 160, 40))

        # Milestone combos get a fanfare
        if self._combo in (5, 10, 20, 50):
            cols = {5:(255,220,50), 10:(255,140,20), 20:(255,50,200), 50:(50,255,255)}
            col  = cols[self._combo]
            self.ui.show_message(f'{self._combo}x COMBO!', ex, ey - 30, col, 'lg')
            self.particles.stars_burst(ex, ey, 30)

        # Kill streak — resets when player takes real damage
        self._kill_streak += 1
        ks = self._kill_streak
        _KS_ANNOUNCE = {
            10:  (200,  (255, 210, 50),  'KILLING SPREE!'),
            25:  (600,  (255, 110, 20),  'R A M P A G E ! !'),
            50:  (1500, (50,  255, 255), 'G O D L I K E'),
            100: (5000, (255, 50,  255), 'L E G E N D A R Y'),
        }
        if ks in _KS_ANNOUNCE:
            reward, kscol, announce = _KS_ANNOUNCE[ks]
            if self.player:
                self.player.coins += reward
            self.ui.show_message(announce,
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120, kscol, 'xl')
            self.ui.show_message(f'+{reward} COINS',
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, GOLD, 'lg')
            self.particles.stars_burst(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 80)
            self.screen_flash(kscol, 90)
            self._hitstop_frames = max(self._hitstop_frames, 6)

        # Track elite kills + special fanfare
        if getattr(enemy, 'is_elite', False):
            self.save.increment_stat('elite_kills')
            self.ui.show_message('ELITE SLAIN!', ex, ey - 40, (255, 215, 0), 'lg')
            self.particles.stars_burst(ex, ey, 35)
            self._hitstop_frames = max(self._hitstop_frames, 5)

        # Challenge kill counter
        if self._challenge_active:
            self._challenge_done += 1

        # Shockwave ring on every kill (desktop only — avoids Android overdraw)
        if not IS_ANDROID:
            self.particles.shockwave_ring(ex, ey, ecol, max_radius=58, speed=6)

        # Chain blast perk
        if self.player and self.player.perk_chain_blast and random.random() < 0.35:
            self._area_damage(ex, ey, 80, 18, source='chain')


    def _update_last_stand(self):
        if not self.player:
            return
        hp_ratio = self.player.health / max(self.player.max_health, 1)
        # Reset trigger when healed back above 60% (after respawn or full heal)
        if hp_ratio > 0.60:
            self._last_stand_triggered = False
            self._last_stand_active    = False
        # Trigger Last Stand at ≤ 25% HP (once per life)
        if not self._last_stand_triggered and 0 < hp_ratio <= 0.25:
            self._last_stand_triggered = True
            self._last_stand_active    = True
            self._last_stand_timer     = int(FPS * 8)
            self.player.add_effect('damage_boost', 8000)
            self.player.add_effect('speed_boost',  8000)
            self.particles.mega_explosion(
                int(self.player.x), int(self.player.y), (255, 40, 0))
            self.particles.shake(22)
            self.screen_flash((200, 0, 0), 130)
            self.ui.show_message('LAST  STAND!',
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80,
                (255, 40, 0), 'xl')
            self.ui.show_message('2× DAMAGE  |  SPEED UP',
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10,
                (255, 180, 80), 'md')
            self.audio.play('boss_warn')
        # Countdown
        if self._last_stand_active:
            self._last_stand_timer -= 1
            if self._last_stand_timer <= 0:
                self._last_stand_active = False

    def _update_challenge(self):
        if not self._challenge_active:
            # Check if we should start a challenge this wave
            lm = self.level_manager
            if (lm and lm.phase == 'wave' and not self._wave_challenge_checked
                    and not lm.cfg.get('is_boss', False)):
                self._wave_challenge_checked = True
                if random.random() < 0.28:
                    self._start_challenge()
            return
        self._challenge_frames -= 1
        if self._challenge_frames <= 0:
            self._challenge_active = False
            self.ui.show_message('CHALLENGE FAILED',
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                (255, 60, 60), 'lg')
            return
        if self._challenge_done >= self._challenge_goal:
            self._challenge_active = False
            if self.player:
                self.player.coins += self._challenge_reward
                self.save.add_coins(self._challenge_reward)
            self.screen_flash((255, 200, 0), 80)
            self.particles.stars_burst(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 60)
            self.ui.show_message(f'CHALLENGE COMPLETE!  +{self._challenge_reward}',
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
                (255, 215, 0), 'xl')
            self.audio.play('powerup')

    def _start_challenge(self):
        total = sum(self.level_manager._totals.values()) if self.level_manager else 8
        goal  = max(4, total // 2)
        secs  = max(10, int(goal * 1.6))
        self._challenge_active       = True
        self._challenge_goal         = goal
        self._challenge_done         = 0
        self._challenge_frames       = secs * FPS
        self._challenge_total_frames = secs * FPS
        self._challenge_reward       = goal * 90 + self.current_level * 5
        self.screen_flash((255, 200, 0), 60)
        self.ui.show_message(
            f'⚡ CHALLENGE!  Kill {goal} in {secs}s',
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
            (255, 210, 0), 'lg')
        self.audio.play('powerup')

    def _area_damage(self, cx, cy, radius, dmg, source='explosion'):
        self.particles.explosion(int(cx), int(cy), (255, 160, 40), count=18, speed=5)
        self.particles.shake(6)
        for enemy in list(self.enemies):
            dist = math.hypot(enemy.x - cx, enemy.y - cy)
            if dist < radius:
                killed = enemy.take_damage(dmg)
                if killed:
                    self._on_kill(enemy)
        if self.player:
            dist = math.hypot(self.player.x - cx, self.player.y - cy)
            if dist < radius * 0.5 and source != 'chain':
                self.player.take_damage(dmg // 3)

    def screen_flash(self, color=(255,0,0), alpha=90):
        """Trigger a full-screen color flash (damage, boss, etc.)."""
        if IS_ANDROID:
            return  # SRCALPHA fill+blit is expensive; skip on mobile
        self._flash_color = color
        self._flash_alpha = max(self._flash_alpha, alpha)

    # ── Collision detection ───────────────────────────────────────────────────
    def _handle_collisions(self):
        player = self.player

        # Player bullets vs enemies
        hits = pygame.sprite.groupcollide(
            self.player_bullets, self.enemies, False, False,
            collided=pygame.sprite.collide_rect)
        for bullet, enemies_hit in hits.items():
            piercing = getattr(bullet, 'piercing', False)
            hit_set  = getattr(bullet, '_hit_set', None)

            for enemy in enemies_hit:
                # Ion cannon: skip if already hit this enemy this frame
                if piercing and hit_set is not None:
                    eid = id(enemy)
                    if eid in hit_set:
                        continue
                    hit_set.add(eid)

                dmg = bullet.damage
                is_crit = random.random() < player.crit_chance
                if is_crit:
                    dmg = int(dmg * 2.0)

                killed = enemy.take_damage(dmg)
                kind = 'crit' if is_crit else 'normal'
                self.particles.damage_number(
                    bullet.rect.centerx, bullet.rect.centery - 10, dmg, kind)
                self.particles.hit_sparks(
                    bullet.rect.centerx, bullet.rect.centery,
                    bullet.color if bullet.color else (255, 255, 100))
                if is_crit:
                    self._hitstop_frames = max(self._hitstop_frames, 3)
                    self.particles.fire_ring(
                        bullet.rect.centerx, bullet.rect.centery,
                        (255,200,0), count=12, radius=16)

                if killed:
                    base_score = int(enemy.score_val * self._combo_mult)
                    player.score += base_score - enemy.score_val
                    self._on_kill(enemy)
                    self.ui._kill_flash = 22
                    bname = type(bullet).__name__
                    ex, ey = int(enemy.x), int(enemy.y)
                    if bname == 'MissileBullet':
                        self.particles.mega_explosion(ex, ey, (255, 140, 0))
                        self._splash_damage(enemy.x, enemy.y, 130, 50)
                        self._hitstop_frames = max(self._hitstop_frames, 6)
                    elif bname == 'PlasmaBullet':
                        self.particles.shockwave_ring(ex, ey, (200, 0, 255),
                                                      max_radius=100, speed=7)
                        self.particles.explosion(ex, ey, (180, 0, 255),
                                                 count=30, speed=6, size=6)
                        self.screen_flash((60, 0, 130), 35)
                        self._splash_damage(enemy.x, enemy.y, 85, 30)
                    elif bname == 'RainbowBullet':
                        self.particles.stars_burst(ex, ey, count=30)
                        self.particles.fire_ring(ex, ey, enemy.color, count=20, radius=28)
                    elif bname == 'IonBullet':
                        self.particles.hit_sparks(ex, ey, (80, 220, 255), count=14)
                        self.particles.fire_ring(ex, ey, (80, 200, 255), count=10, radius=18)
                    elif bname == 'DarkMatterBullet':
                        # Gravity pull — push all nearby enemies toward kill point
                        self.particles.shockwave_ring(ex, ey, (110, 0, 210),
                                                      max_radius=120, speed=6)
                        self.screen_flash((50, 0, 100), 40)
                        for near_e in list(self.enemies):
                            if near_e.alive():
                                d = math.hypot(near_e.x - ex, near_e.y - ey)
                                if 0 < d < 140:
                                    near_e.take_damage(int(bullet.damage * 0.25))
                    elif bname == 'OmegaBullet':
                        self.particles.mega_explosion(ex, ey, (255, 235, 0))
                        self._splash_damage(enemy.x, enemy.y, 180, 80)
                        self.screen_flash((255, 220, 0), 60)
                        self._hitstop_frames = max(self._hitstop_frames, 8)
                    elif bname == 'QuantumBullet':
                        self.particles.explosion(ex, ey, (255, 60, 220),
                                                 count=20, speed=5)
                        self.particles.fire_ring(ex, ey, (200, 0, 255), count=14, radius=22)
                    else:
                        self.particles.fire_ring(ex, ey, enemy.color, count=18, radius=26)

                if not piercing:
                    bullet.kill()
                    break

        # Player bullets vs boss
        for bullet in list(self.player_bullets):
            for boss in list(self.boss_group):
                if bullet.rect.colliderect(boss.rect):
                    dmg     = bullet.damage
                    is_crit = random.random() < player.crit_chance
                    if is_crit:
                        dmg = int(dmg * 2.0)

                    killed  = boss.take_damage(dmg)
                    kind    = 'crit' if is_crit else 'normal'
                    self.particles.damage_number(
                        bullet.rect.centerx, bullet.rect.centery - 10, dmg, kind)
                    self.particles.hit_sparks(
                        bullet.rect.centerx, bullet.rect.centery, (255, 100, 50))
                    if is_crit:
                        self._hitstop_frames = max(self._hitstop_frames, 4)
                        self.particles.fire_ring(
                            bullet.rect.centerx, bullet.rect.centery,
                            (255,200,0), count=16, radius=20)
                    bullet.kill()
                    self.save.increment_stat('damage_dealt', dmg)

                    if killed:
                        self._on_kill(boss)
                    break

        # Enemy bullets vs player
        for bullet in list(self.enemy_bullets):
            if bullet.rect.colliderect(player.rect):
                dmg = bullet.damage
                _was_inv = (pygame.time.get_ticks() < player._inv_until
                            or player.has_effect('invincibility'))
                player.take_damage(dmg)
                if not _was_inv and self._kill_streak > 0:
                    self._kill_streak = 0
                bullet.kill()
                if dmg > 0:
                    self.particles.damage_number(
                        player.rect.centerx, player.rect.top - 10, dmg, 'player')
                    self.screen_flash((220, 30, 30), 80)
                    self._chroma_frames   = 7
                    self._chroma_strength = 5
                if hasattr(bullet, 'explosive') and bullet.explosive:
                    self.particles.explosion(
                        bullet.rect.centerx, bullet.rect.centery,
                        (255, 140, 0), count=20)

        # Enemy contact with player
        for enemy in list(self.enemies):
            if enemy.rect.colliderect(player.rect):
                dmg = enemy.damage
                _was_inv = (pygame.time.get_ticks() < player._inv_until
                            or player.has_effect('invincibility'))
                player.take_damage(dmg)
                if not _was_inv and self._kill_streak > 0:
                    self._kill_streak = 0
                enemy.take_damage(enemy.max_health)
                if dmg > 0:
                    self.screen_flash((220, 30, 30), 80)
                    self._chroma_frames   = 8
                    self._chroma_strength = 6

        # Player picking up power-ups
        for pu in list(self.powerups):
            if pu.rect.colliderect(player.rect):
                msg = pu.apply(player, self.particles)
                if msg == 'BOMB!':
                    self._trigger_bomb()
                elif msg == 'FREEZE!':
                    self._trigger_freeze_bomb()
                else:
                    self.ui.show_message(msg, player.x, player.y - 40,
                                         pu.color, 'md')
                    self.screen_flash((80, 200, 80), 40)
                self.audio.play('powerup')
                pu.kill()

        # Ally bullets vs enemies
        hits = pygame.sprite.groupcollide(
            self.ally_bullets, self.enemies, True, False,
            collided=pygame.sprite.collide_rect)
        for bullet, enemies_hit in hits.items():
            for enemy in enemies_hit:
                killed = enemy.take_damage(bullet.damage)
                self.particles.hit_sparks(
                    bullet.rect.centerx, bullet.rect.centery, bullet.color, count=6)
                if killed:
                    self._on_kill(enemy)
                    self.ui._kill_flash = 22
                break

        # Ally bullets vs boss
        for bullet in list(self.ally_bullets):
            for boss in list(self.boss_group):
                if bullet.rect.colliderect(boss.rect):
                    killed = boss.take_damage(bullet.damage)
                    self.particles.hit_sparks(
                        bullet.rect.centerx, bullet.rect.centery, bullet.color, count=6)
                    bullet.kill()
                    if killed:
                        self._on_kill(boss)
                    break

        # Enemy bullets vs allies
        for bullet in list(self.enemy_bullets):
            for ally in list(self.allies):
                if bullet.rect.colliderect(ally.rect):
                    ally.take_damage(bullet.damage)
                    self.particles.hit_sparks(
                        bullet.rect.centerx, bullet.rect.centery, (255, 80, 80), count=5)
                    bullet.kill()
                    break

        # Enemy contact with allies
        for enemy in list(self.enemies):
            for ally in list(self.allies):
                if enemy.rect.colliderect(ally.rect):
                    ally.take_damage(enemy.damage // 2)
                    break

        # Player collecting coins — combo multiplier at 10/20/50 streak
        for coin in list(self.coins_group):
            if coin.rect.colliderect(player.rect):
                combo = self._combo
                mult  = 5 if combo >= 50 else 3 if combo >= 20 else (2 if combo >= 10 else 1)
                value = coin.value * mult
                player.coins += value
                self.save.add_coins(value)
                self.audio.play('coin')
                coin.kill()

    def _handle_coin_magnet(self):
        if not self.player.has_effect('coin_magnet'):
            return
        cx, cy  = self.player.x, self.player.y
        magnet_r= 180
        for obj in list(self.coins_group) + list(self.powerups):
            dx = cx - obj.x
            dy = cy - obj.y
            if (dx*dx + dy*dy) < magnet_r*magnet_r:
                obj.attract(cx, cy)

    def _trigger_bomb(self):
        for enemy in list(self.enemies):
            self.particles.explosion(int(enemy.x), int(enemy.y), enemy.color, 20)
            self._on_kill(enemy)
            enemy.kill()
        for boss in list(self.boss_group):
            boss.take_damage(boss.max_health // 4)
        for bullet in list(self.enemy_bullets):
            bullet.kill()
        self.particles.shake(18)
        self.particles.shockwave_ring(SCREEN_WIDTH//2, SCREEN_HEIGHT//2,
                                      (255, 80, 200), max_radius=300, speed=10)
        self.screen_flash((255, 80, 200), 100)
        self.audio.play('explosion')
        self.ui.show_message('BOMB!', SCREEN_WIDTH//2, SCREEN_HEIGHT//2,
                             (255,50,150), 'xl')

    def _trigger_freeze_bomb(self):
        """Freeze Bomb: wipe all enemy bullets and weaken every enemy."""
        for bullet in list(self.enemy_bullets):
            self.particles.hit_sparks(
                bullet.rect.centerx, bullet.rect.centery, (0, 200, 255), count=4)
            bullet.kill()
        for enemy in list(self.enemies):
            killed = enemy.take_damage(30)
            self.particles.hit_sparks(int(enemy.x), int(enemy.y), (0, 200, 255), count=6)
            if killed:
                self._on_kill(enemy)
                self.ui._kill_flash = 22
        for boss in list(self.boss_group):
            boss.take_damage(boss.max_health // 10)
        self.particles.shockwave_ring(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, (0, 200, 255), max_radius=340, speed=12)
        self.screen_flash((0, 180, 255), 90)
        self.audio.play('explosion')
        self.ui.show_message('FREEZE BOMB!', SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                             (0, 200, 255), 'xl')

    def _splash_damage(self, x: float, y: float, radius: float, dmg: int):
        """Area damage after a kill — creates spectacular chain reactions."""
        for enemy in list(self.enemies):
            if not enemy.alive():
                continue
            dist = math.hypot(enemy.x - x, enemy.y - y)
            if 0 < dist < radius:
                falloff = max(0.2, 1.0 - dist / radius)
                splash  = int(dmg * falloff)
                if splash > 0:
                    killed = enemy.take_damage(splash)
                    self.particles.damage_number(int(enemy.x), int(enemy.y) - 12,
                                                 splash, 'normal')
                    if killed:
                        self._on_kill(enemy)
                        self.ui._kill_flash = 22

    def _handle_perk_magnet(self):
        """Pull all coins toward player if perk_magnet perk is active."""
        if not self.player or not self.player.perk_magnet:
            return
        px, py = self.player.x, self.player.y
        for coin in self.coins_group:
            dx = px - coin.rect.centerx
            dy = py - coin.rect.centery
            dist = math.hypot(dx, dy) or 1
            spd  = min(8.0, 320.0 / dist)
            coin.rect.x += int(dx / dist * spd)
            coin.rect.y += int(dy / dist * spd)

    def _handle_asteroids(self):
        """Spawn, update, and resolve asteroid collisions."""
        self._asteroid_field.update(self.asteroids)
        for ast in list(self.asteroids):
            ast.update()
            if ast.offscreen:
                ast.kill()
                continue

            # Player bullet hits asteroid
            hits = pygame.sprite.spritecollide(ast, self.player_bullets, False,
                                               pygame.sprite.collide_circle_ratio(0.85))
            for bullet in hits:
                if not getattr(bullet, 'piercing', False):
                    bullet.kill()
                if ast.take_damage(bullet.damage // 10 + 1):
                    self._explode_asteroid(ast)
                    break

            # Asteroid hits player
            if self.player and pygame.sprite.collide_circle_ratio(0.75)(ast, self.player):
                self.player.take_damage(ast.dmg)
                self._explode_asteroid(ast)

            # Asteroid hits enemies
            for enemy in list(self.enemies):
                if pygame.sprite.collide_circle_ratio(0.7)(ast, enemy):
                    enemy.take_damage(ast.dmg)
                    ast.hp -= 1
                    if ast.hp <= 0:
                        self._explode_asteroid(ast)
                        break

    def _explode_asteroid(self, ast: 'Asteroid'):
        if not ast.alive():
            return
        self.particles.explosion(int(ast.x), int(ast.y), (180, 160, 120),
                                 count=20 + ast.r // 4, speed=4)
        self.particles.shake(5)
        # Coins
        from powerup import Coin
        n_coins = ast.coin_drop()
        for _ in range(n_coins):
            cx = ast.x + random.uniform(-25, 25)
            cy = ast.y + random.uniform(-25, 25)
            c  = Coin(cx, cy)
            self.coins_group.add(c)
            self.all_sprites.add(c)
        # Score
        if self.player:
            self.player.score += ast.score_val
        # Fragment split
        for frag in ast.split():
            self.asteroids.add(frag)
        ast.kill()

    def _process_bomb_effect(self):
        pass

    # ── Achievements ──────────────────────────────────────────────────────────
    def _check_achievements(self):
        stats = self.save.get('stats', {})
        stats['best_level'] = self.save.get('best_level', 0)
        stats['total_coins'] = self.save.get('total_coins', 0)
        stats['unlocked_weapons'] = self.save.get('unlocked_weapons', ['laser'])
        best_lvl = stats.get('best_level', 0)
        conditions = {
            'first_kill':    stats.get('kills', 0) >= 1,
            'kills_100':     stats.get('kills', 0) >= 100,
            'boss_slayer':   stats.get('bosses_killed', 0) >= 1,
            'untouchable':   stats.get('perfect_levels', 0) >= 1,
            'coin_collector':stats.get('total_coins', 0) >= 10000,
            'weapon_master': len(stats.get('unlocked_weapons',[])) >= 11,
            'ch2_clear':     best_lvl >= 40,
            'ch3_clear':     best_lvl >= 60,
            'ch4_clear':     best_lvl >= 80,
            'earth_defender':  best_lvl >= TOTAL_LEVELS,
            'ultimate_slayer': 'ultimate_slayer' in self.save.get('achievements', []),
            'elite_slayer':    stats.get('elite_kills', 0) >= 50,
            'combo_god':       stats.get('max_combo', 0) >= 50,
            'endless_veteran': self.save.get('best_endless_wave', 0) >= 20,
        }
        for aid, cond in conditions.items():
            if cond:
                if self.save.unlock_achievement(aid):
                    self.ui.show_achievement(aid)

    # ── Glow bloom pass ───────────────────────────────────────────────────────
    def _draw_glow_pass(self, target: pygame.Surface):
        """Additive-blend glow on bullets, thrusters, and boss."""
        gs = self._glow_surf
        gs.fill((0, 0, 0))

        def _glow(cx, cy, radius, color, bright_factor=0.5):
            r, g, b = (min(255, int(v * bright_factor)) for v in color)
            pygame.draw.circle(gs, (r//3, g//3, b//3), (cx, cy), radius)
            pygame.draw.circle(gs, (r, g, b),           (cx, cy), radius // 2)

        # Player bullets
        for b in self.player_bullets:
            col = b.color or (0, 200, 255)
            _glow(b.rect.centerx, b.rect.centery, 14, col, 0.8)

        # Enemy bullets (red glow)
        for b in self.enemy_bullets:
            _glow(b.rect.centerx, b.rect.centery, 10, (255, 80, 40), 0.6)

        # Boss — red pulse in rage mode, white otherwise
        for boss in self.boss_group:
            bx, by = int(boss.x), int(boss.y)
            if getattr(boss, '_rage_mode', False):
                t = math.sin(pygame.time.get_ticks() * 0.01) * 0.5 + 0.5
                r = int(80 + t * 80)
                pygame.draw.circle(gs, (r, 0, 0), (bx, by), 90)
                pygame.draw.circle(gs, (r//2, 0, 0), (bx, by), 130)
            else:
                pygame.draw.circle(gs, (40, 0, 0), (bx, by), 70)

        # Destroyer enemy — purple core glow
        for e in self.enemies:
            if getattr(e, 'KIND', '') == 'destroyer':
                ex, ey = int(e.x), int(e.y)
                t2 = math.sin(pygame.time.get_ticks() * 0.009) * 0.5 + 0.5
                r2 = int(30 + t2 * 20)
                pygame.draw.circle(gs, (r2, 0, 80), (ex, ey), 55)
                pygame.draw.circle(gs, (50, 0, 120), (ex, ey), 30)

        # Player thruster glow
        if self.player:
            px, py = int(self.player.x), int(self.player.y) + 28
            pygame.draw.circle(gs, (20, 60, 200), (px, py), 24)
            pygame.draw.circle(gs, (60, 140, 255), (px, py), 10)
            # Extra glow when speed boost or damage boost active
            if self.player.has_effect('speed_boost'):
                pygame.draw.circle(gs, (0, 40, 80), (px, py), 40)
            if self.player.has_effect('damage_boost'):
                pygame.draw.circle(gs, (60, 20, 0), (int(self.player.x), int(self.player.y)), 36)

        target.blit(gs, (0, 0), special_flags=pygame.BLEND_ADD)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        ox, oy = self.particles.offset

        if self._state in ('PLAYING', 'PAUSED', 'ULTIMATE_BOSS', 'PERK_SELECT'):
            self._draw_game_world(ox, oy)
        elif self._state == 'QUIZ':
            self.quiz.draw(self.screen)
        elif self._state == 'SHOP':
            self._draw_game_world(0, 0)
            self.shop.draw(self.screen)
        elif self._state == 'MAIN_MENU':
            self.background.draw(self.screen)
            self.ui.draw_main_menu(self.screen)
        elif self._state == 'GAME_OVER':
            self._draw_game_world(ox, oy)
            self.ui.draw_game_over(self.screen)
        elif self._state == 'VICTORY':
            self._draw_game_world(ox, oy)
            self.ui.draw_victory(self.screen)
        elif self._state == 'SETTINGS':
            self.background.draw(self.screen)
            self.ui.draw_settings(self.screen)
        elif self._state == 'HIGH_SCORES':
            self.background.draw(self.screen)
            self.ui.draw_high_scores(self.screen)
        elif self._state == 'HOW_TO_PLAY':
            self.background.draw(self.screen)
            self.ui.draw_how_to_play(self.screen)

        if self._state == 'PAUSED':
            self.ui.draw_pause(self.screen)

        if self._state == 'PERK_SELECT':
            self._perk_screen.draw(self.screen)

        if self.save.get_setting('show_fps'):
            fps = self._font_fps.render(f'FPS: {int(self.clock.get_fps())}', True, (0,255,0))
            self.screen.blit(fps, (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 22))

        # On Android, scale the logical 1200x800 surface to the actual display
        if self._display is not None:
            pygame.transform.scale(self.screen, self._display.get_size(), self._display)
            pygame.display.flip()
        else:
            pygame.display.flip()

    def _draw_game_world(self, ox: int = 0, oy: int = 0):
        self.background.draw(self.screen)

        if ox or oy:
            game_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            game_surf.blit(self.screen, (0, 0))
            target = game_surf
        else:
            target = self.screen

        if IS_ANDROID:
            # Batch blits: 1 JNI call per group instead of 1 per sprite
            # ox=oy=0 always on Android (shake disabled), so use .topleft directly
            if self.asteroids:
                target.blits([(s.image, s.rect.topleft) for s in self.asteroids])
            if self.powerups:
                target.blits([(s.image, s.rect.topleft) for s in self.powerups])
            if self.coins_group:
                target.blits([(s.image, s.rect.topleft) for s in self.coins_group])
            if self.enemy_bullets:
                target.blits([(s.image, s.rect.topleft) for s in self.enemy_bullets])
            if self.enemies:
                target.blits([(s.image, s.rect.topleft) for s in self.enemies])
            for boss in self.boss_group:
                boss.draw_shield(target)
                target.blit(boss.image, boss.rect.topleft)
                boss.draw_hud(self.screen)
                boss.draw_rage_aura(target)
            if self.allies:
                target.blits([(s.image, s.rect.topleft) for s in self.allies])
            if self.ally_bullets:
                target.blits([(s.image, s.rect.topleft) for s in self.ally_bullets])
            if self.player:
                self.player.draw(target)
            if self.player_bullets:
                target.blits([(s.image, s.rect.topleft) for s in self.player_bullets])
        else:
            # Asteroids (before enemies so they appear behind bullets)
            for ast in self.asteroids:
                target.blit(ast.image, (ast.rect.x + ox, ast.rect.y + oy))

            # Power-ups
            for pu in self.powerups:
                target.blit(pu.image, (pu.rect.x + ox, pu.rect.y + oy))
                pu.draw_label(target)

            # Coins
            for c in self.coins_group:
                target.blit(c.image, (c.rect.x + ox, c.rect.y + oy))

            # Enemy bullet trails + sprites
            for b in self.enemy_bullets:
                if hasattr(b, 'draw_trail'):
                    b.draw_trail(target)
                target.blit(b.image, (b.rect.x + ox, b.rect.y + oy))

            # Enemies + health bars
            for e in self.enemies:
                target.blit(e.image, (e.rect.x + ox, e.rect.y + oy))
                e.draw_health_bar(target)

            # Boss + shield + rage glow
            for boss in self.boss_group:
                boss.draw_shield(target)
                target.blit(boss.image, (boss.rect.x + ox, boss.rect.y + oy))
                boss.draw_hud(self.screen)
                boss.draw_rage_aura(target)

            # Allies + health bars
            for ally in self.allies:
                target.blit(ally.image, (ally.rect.x + ox, ally.rect.y + oy))
                ally.draw_health_bar(target)

            # Ally bullets
            for b in self.ally_bullets:
                target.blit(b.image, (b.rect.x + ox, b.rect.y + oy))

            # Player
            if self.player:
                self.player.draw(target)

            # Player bullet trails + sprites
            for b in self.player_bullets:
                if hasattr(b, 'draw_trail'):
                    b.draw_trail(target)
                target.blit(b.image, (b.rect.x + ox, b.rect.y + oy))

        # Glow pass (additive — desktop only; too expensive on Android)
        if not IS_ANDROID:
            self._draw_glow_pass(target)

        # Particles + damage numbers
        self.particles.draw(target)

        # HUD (never shaken)
        if self.player:
            self.ui.draw_hud(self.screen)

        # Combo display
        if self._combo >= 3:
            self._draw_combo(self.screen)

        # On-screen touch / mouse controls
        self._draw_onscreen_controls(self.screen)

        # Wave progress / ULTIMATE_BOSS ally counter
        if self._state == 'ULTIMATE_BOSS':
            self._draw_ub_ally_hud(self.screen)
        elif self.level_manager:
            self.level_manager.draw_intro(self.screen)

        # Screen flash overlay
        if self._flash_alpha > 0:
            self._flash_surf.fill((*self._flash_color, self._flash_alpha))
            self.screen.blit(self._flash_surf, (0, 0))

        if ox or oy:
            self.screen.blit(game_surf, (0, 0))

        # Low-health vignette
        self._draw_low_health_vignette(self.screen)

        # Chromatic aberration on hit
        if self._chroma_frames > 0:
            self._chroma_frames -= 1
            self._draw_chromatic_aberration(self.screen, self._chroma_strength)

    def _draw_combo(self, surface: pygame.Surface):
        """Draw a kinetic combo counter near the bottom center."""
        font_big  = self._font_combo_big
        font_small= self._font_combo_small

        # Pulsing scale
        t     = pygame.time.get_ticks()
        pulse = 1.0 + 0.06 * math.sin(t * 0.012)
        mult_str = f'x{self._combo_mult:.1f}'
        cnt_str  = f'{self._combo} KILLS'

        # Colors ramp from yellow → orange → red → purple
        if self._combo < 5:
            col = (255, 220, 50)
        elif self._combo < 10:
            col = (255, 140, 20)
        elif self._combo < 20:
            col = (255, 50, 50)
        else:
            col = (200, 50, 255)

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT - 110

        # Multiplier text (big, pulsing)
        mtxt = font_big.render(mult_str, True, col)
        if not IS_ANDROID:
            mw   = int(mtxt.get_width() * pulse)
            mh   = int(mtxt.get_height() * pulse)
            mtxt = pygame.transform.scale(mtxt, (mw, mh))
        mtxt.set_alpha(220)
        surface.blit(mtxt, mtxt.get_rect(center=(cx, cy)))

        # Kill count (small, below)
        ctxt = font_small.render(cnt_str, True, (200, 200, 200))
        ctxt.set_alpha(180)
        surface.blit(ctxt, ctxt.get_rect(center=(cx, cy + 28)))

        # Decay bar — shows time until combo resets
        bar_w = 120
        bar_h = 4
        ratio = self._combo_timer / 220
        bar_x = cx - bar_w // 2
        bar_y = cy + 44
        pygame.draw.rect(surface, (60, 60, 60),  (bar_x, bar_y, bar_w, bar_h), border_radius=2)
        pygame.draw.rect(surface, col,            (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=2)

    def _draw_ub_ally_hud(self, surface: pygame.Surface):
        """Show active ally ships during the final boss battle."""
        if not self.allies:
            return
        if not hasattr(self, '_ally_hud_font'):
            self._ally_hud_font = pygame.font.SysFont('consolas', 14, bold=True)
        font = self._ally_hud_font
        x, y = 10, SCREEN_HEIGHT - 90
        for ally in self.allies:
            cfg = ALLY_CONFIGS.get(ally.ally_type, {})
            col = cfg.get('color', (0, 200, 100))
            name = cfg.get('name', ally.ally_type)
            ratio = max(0.0, ally.health / ally.max_health)
            # Mini HP bar
            pygame.draw.rect(surface, (40, 0, 0),   (x, y, 90, 8))
            pygame.draw.rect(surface, col,           (x, y, int(90 * ratio), 8))
            txt = font.render(name, True, col)
            surface.blit(txt, (x, y + 10))
            x += 110

    # ── Pre-render control surfaces (called once in __init__) ─────────────────
    def _build_ctrl_surfs(self):
        br = self._joy_base_r
        kr = self._joy_knob_r
        fr = self._fire_r

        # Joystick base ring
        joy_base = pygame.Surface((br*2+4, br*2+4), pygame.SRCALPHA)
        pygame.draw.circle(joy_base, (60, 120, 200, 45),  (br+2, br+2), br)
        pygame.draw.circle(joy_base, (80, 160, 255, 130), (br+2, br+2), br, 4)
        pygame.draw.circle(joy_base, (80, 160, 255, 50),  (br+2, br+2), br - 20, 2)

        # Joystick knob (idle)
        joy_knob_idle = pygame.Surface((kr*2+4, kr*2+4), pygame.SRCALPHA)
        pygame.draw.circle(joy_knob_idle, (80, 140, 220, 160), (kr+2, kr+2), kr)
        pygame.draw.circle(joy_knob_idle, (160, 210, 255, 200), (kr+2, kr+2), kr, 3)

        # Joystick knob (active)
        joy_knob_act = pygame.Surface((kr*2+4, kr*2+4), pygame.SRCALPHA)
        pygame.draw.circle(joy_knob_act, (120, 190, 255, 220), (kr+2, kr+2), kr)
        pygame.draw.circle(joy_knob_act, (220, 240, 255, 255), (kr+2, kr+2), kr, 3)
        pygame.draw.circle(joy_knob_act, (180, 230, 255, 100), (kr+2, kr+2), kr//2)

        # Fire button idle
        fire_idle = pygame.Surface((fr*2+4, fr*2+4), pygame.SRCALPHA)
        pygame.draw.circle(fire_idle, (180, 30, 30, 130), (fr+2, fr+2), fr)
        pygame.draw.circle(fire_idle, (255, 80, 80, 180),  (fr+2, fr+2), fr, 4)
        fnt = pygame.font.SysFont('consolas', 24, bold=True)
        t = fnt.render('FIRE', True, (255, 200, 200))
        t.set_alpha(180)
        fire_idle.blit(t, t.get_rect(center=(fr+2, fr+2)))

        # Fire button active
        fire_act = pygame.Surface((fr*2+4, fr*2+4), pygame.SRCALPHA)
        pygame.draw.circle(fire_act, (255, 50, 50, 210), (fr+2, fr+2), fr)
        pygame.draw.circle(fire_act, (255, 140, 60, 255), (fr+2, fr+2), fr, 5)
        pygame.draw.circle(fire_act, (255, 100, 50, 80),  (fr+2, fr+2), fr//2)
        t = fnt.render('FIRE', True, (255, 255, 255))
        t.set_alpha(255)
        fire_act.blit(t, t.get_rect(center=(fr+2, fr+2)))

        # Weapon buttons
        def _wpn_surf(label):
            r = self._obtn_prev
            s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            pygame.draw.rect(s, (30, 70, 160, 140), s.get_rect(), border_radius=14)
            pygame.draw.rect(s, (80, 140, 255, 180), s.get_rect(), 2, border_radius=14)
            wf = pygame.font.SysFont('consolas', 16, bold=True)
            wt = wf.render(label, True, (200, 220, 255))
            wt.set_alpha(200)
            s.blit(wt, wt.get_rect(center=(r.width//2, r.height//2)))
            return s
        prev_s = _wpn_surf('< WPN')
        next_s = _wpn_surf('WPN >')

        return joy_base, joy_knob_idle, joy_knob_act, fire_idle, fire_act, prev_s, next_s

    def _build_vignette_surf(self):
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        depth = 100
        for i in range(depth):
            a = int(255 * ((depth - i) / depth) ** 2)
            col = (200, 0, 0, a)
            pygame.draw.line(s, col, (0, i), (SCREEN_WIDTH, i))
            pygame.draw.line(s, col, (0, SCREEN_HEIGHT-1-i), (SCREEN_WIDTH, SCREEN_HEIGHT-1-i))
            pygame.draw.line(s, col, (i, 0), (i, SCREEN_HEIGHT))
            pygame.draw.line(s, col, (SCREEN_WIDTH-1-i, 0), (SCREEN_WIDTH-1-i, SCREEN_HEIGHT))
        return s

    def _build_pause_surf(self) -> pygame.Surface:
        w, h = self._pause_btn_rect.width, self._pause_btn_rect.height
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        # Dark navy bg with rounded corners
        pygame.draw.rect(s, (8, 18, 55, 195), (0, 0, w, h), border_radius=14)
        # Neon cyan border
        pygame.draw.rect(s, (0, 175, 255, 230), (0, 0, w, h), 2, border_radius=14)
        # Inner dim glow ring
        pygame.draw.rect(s, (0, 100, 200, 60), (3, 3, w-6, h-6), border_radius=12)
        # Pause bars: two vertical rects
        bw, bh = 10, 28
        cx, cy = w // 2, h // 2
        pygame.draw.rect(s, (255, 255, 255, 245), (cx - 14, cy - bh//2, bw, bh), border_radius=3)
        pygame.draw.rect(s, (255, 255, 255, 245), (cx + 4,  cy - bh//2, bw, bh), border_radius=3)
        return s

    # ── On-screen touch / mouse control overlay ───────────────────────────────
    def _draw_onscreen_controls(self, surface: pygame.Surface):
        joy_base, joy_knob_idle, joy_knob_act, fire_idle, fire_act, prev_s, next_s \
            = self._ctrl_joy_base, self._ctrl_joy_knob_idle, self._ctrl_joy_knob_active, \
              self._ctrl_fire_idle, self._ctrl_fire_active, \
              self._ctrl_prev_surf, self._ctrl_next_surf

        # Joystick base
        jx, jy = self._joy_center
        br = self._joy_base_r
        surface.blit(joy_base, (jx - br - 2, jy - br - 2))

        # Direction line when active
        kx, ky = self._joy_pos
        if self._joy_finger is not None and (kx != jx or ky != jy):
            pygame.draw.line(surface, (100, 180, 255, 0), (jx, jy), (int(kx), int(ky)), 3)

        # Joystick knob
        kr = self._joy_knob_r
        knob = joy_knob_act if self._joy_finger is not None else joy_knob_idle
        surface.blit(knob, (int(kx) - kr - 2, int(ky) - kr - 2))

        # Fire button
        fr = self._fire_r
        fcx, fcy = self._fire_center
        fbtn = fire_act if self._mouse_firing else fire_idle
        surface.blit(fbtn, (fcx - fr - 2, fcy - fr - 2))

        # Weapon buttons
        surface.blit(prev_s, self._obtn_prev.topleft)
        surface.blit(next_s, self._obtn_next.topleft)

        # Pause button (top-right corner)
        surface.blit(self._ctrl_pause_surf, self._pause_btn_rect.topleft)

        # Desktop hint (first 8 s only)
        if not IS_ANDROID and pygame.time.get_ticks() < 8000:
            hint = pygame.font.SysFont('consolas', 12)
            h = hint.render('F11 = Fullscreen  |  Mouse = move & fire', True, (120,120,160))
            h.set_alpha(max(0, int(255 * (1 - pygame.time.get_ticks()/8000))))
            surface.blit(h, h.get_rect(centerx=SCREEN_WIDTH//2, bottom=SCREEN_HEIGHT - 82))

    # ── World-class screen effects ────────────────────────────────────────────
    def _draw_low_health_vignette(self, surface: pygame.Surface):
        if IS_ANDROID or not self.player:
            return
        ratio = self.player.health / max(self.player.max_health, 1)
        if ratio >= 0.35:
            return
        t     = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(t * 0.006)
        alpha = int((1 - ratio / 0.35) * 80 * pulse)
        if alpha < 3:
            return
        self._vignette_surf.set_alpha(alpha)
        surface.blit(self._vignette_surf, (0, 0))

    def _draw_chromatic_aberration(self, surface: pygame.Surface, strength: int):
        if IS_ANDROID or strength <= 0:
            return
        copy  = surface.copy()
        # Red ghost shifted left
        r_ghost = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
        r_ghost.blit(copy, (0, 0))
        r_ghost.fill((255, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        r_ghost.set_alpha(70)
        surface.blit(r_ghost, (-strength, 0), special_flags=pygame.BLEND_ADD)
        # Blue ghost shifted right
        b_ghost = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
        b_ghost.blit(copy, (0, 0))
        b_ghost.fill((0, 0, 255, 0), special_flags=pygame.BLEND_RGBA_MULT)
        b_ghost.set_alpha(70)
        surface.blit(b_ghost, (strength, 0), special_flags=pygame.BLEND_ADD)
