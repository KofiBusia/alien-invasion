"""UI: world-class HUD, animated menus, cinematic overlays."""

import math
import random
import pygame
import os as _os
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WEAPONS, WEAPON_ORDER, TOTAL_LEVELS, FPS,
    WHITE, BLACK, GOLD, CYAN, RED, GREEN, BLUE, ORANGE, PURPLE,
    UI_BG, UI_BORDER, UI_TEXT, UI_HIGHLIGHT, UI_BUTTON, UI_BUTTON_HOV,
    UI_SUCCESS, UI_DANGER, ACHIEVEMENTS, SHIP_SKINS, SKIN_ORDER
)
_IS_ANDROID = bool(_os.environ.get('ANDROID_ROOT'))


# ── Helpers ───────────────────────────────────────────────────────────────────
def _vgradient(w: int, h: int, top_col, bot_col, alpha_top=255, alpha_bot=255):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_col[0] + (bot_col[0]-top_col[0])*t)
        g = int(top_col[1] + (bot_col[1]-top_col[1])*t)
        b = int(top_col[2] + (bot_col[2]-top_col[2])*t)
        a = int(alpha_top  + (alpha_bot -alpha_top )*t)
        pygame.draw.line(s, (r,g,b,a), (0,y), (w,y))
    return s

def _hue_rgb(h):
    h  = h / 60
    i  = int(h) % 6
    f  = h - int(h)
    t  = int(f * 255)
    q  = 255 - t
    return [(255,t,0),(q,255,0),(0,255,t),(0,q,255),(t,0,255),(255,0,q)][i]


# ── Animated menu background decoration ──────────────────────────────────────
class _MenuDecor:
    """Alien ships silently patrolling behind the main menu."""

    class _Ship:
        KINDS = {
            'scout':   {'col': (0,210,100),  'w': 26, 'h': 30, 'spd': (0.35, 0.80)},
            'fighter': {'col': (210,90,0),   'w': 34, 'h': 38, 'spd': (0.28, 0.65)},
            'tank':    {'col': (180,0,70),   'w': 44, 'h': 48, 'spd': (0.18, 0.42)},
        }

        def __init__(self):
            self._reset()

        def _reset(self):
            kind       = random.choice(list(self.KINDS))
            cfg        = self.KINDS[kind]
            self.col   = cfg['col']
            self.w     = cfg['w']
            self.h     = cfg['h']
            self.alpha = random.randint(55, 130)
            lo, hi     = cfg['spd']
            self.vy    = random.uniform(-0.15, 0.15)
            if random.random() < 0.5:
                self.x   = float(SCREEN_WIDTH + 80)
                self.vx  = -random.uniform(lo, hi)
            else:
                self.x   = -80.0
                self.vx  = random.uniform(lo, hi)
            self.y = random.uniform(80, SCREEN_HEIGHT - 220)
            self._surf = self._build()

        def _build(self):
            W, H = self.w, self.h
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            c = self.col; a = self.alpha
            cx = W // 2
            # Body
            body = [(cx, 0), (W-3, H-14), (W*3//4, H-8), (W//4, H-8), (3, H-14)]
            pygame.draw.polygon(s, (*c, a), body)
            lw = [(3,H-14),(0,H-3),(W//4,H-5),(W//4,H-8)]
            rw = [(W-3,H-14),(W,H-3),(W*3//4,H-5),(W*3//4,H-8)]
            dc = tuple(max(0,v-40) for v in c)
            pygame.draw.polygon(s, (*dc, a), lw)
            pygame.draw.polygon(s, (*dc, a), rw)
            bc = tuple(min(255,v+80) for v in c)
            pygame.draw.ellipse(s, (*bc, int(a*0.85)), (cx-5,5,10,12))
            # Engine glow
            pygame.draw.circle(s, (*bc, int(a*0.7)), (cx, H-4), 4)
            # Border
            pygame.draw.polygon(s, (*bc, int(a*0.5)), body, 1)
            return s

        def update(self):
            self.x += self.vx
            self.y  = max(80, min(SCREEN_HEIGHT-220, self.y + self.vy))

        def draw(self, surface):
            s = self._surf
            if self.vx > 0:
                s = pygame.transform.flip(s, True, False)
            surface.blit(s, (int(self.x) - self.w//2, int(self.y) - self.h//2))

        @property
        def offscreen(self):
            return self.x < -160 or self.x > SCREEN_WIDTH + 160

    def __init__(self):
        self._ships: list = []
        self._cd = 60

    def update(self):
        self._cd -= 1
        if self._cd <= 0:
            self._cd = random.randint(90, 260)
            self._ships.append(self._Ship())
        for s in self._ships:
            s.update()
        self._ships = [s for s in self._ships if not s.offscreen]

    def draw(self, surface):
        for s in self._ships:
            s.draw(surface)


# ── Title particle sparkle ─────────────────────────────────────────────────────
class _TitleSpark:
    __slots__ = ('x','y','vx','vy','life','max_life','r','g','b','size')

    def __init__(self, cx, cy, hue):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(0.5, 2.2)
        self.x, self.y   = cx + random.uniform(-160,160), cy + random.uniform(-20,20)
        self.vx, self.vy = math.cos(ang)*spd, math.sin(ang)*spd - 1.0
        self.life = self.max_life = random.randint(30, 70)
        r, g, b = _hue_rgb(hue)
        self.r, self.g, self.b = r, g, b
        self.size = random.randint(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.04
        self.vx *= 0.97
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        sz = max(1, self.size)
        if _IS_ANDROID:
            # no per-spark SRCALPHA surface on Android
            if self.life > 4:
                pygame.draw.circle(surface, (self.r, self.g, self.b),
                                   (int(self.x), int(self.y)), sz)
            return
        a  = int(255 * self.life / self.max_life)
        s  = pygame.Surface((sz*2+2,sz*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (self.r,self.g,self.b,a), (sz+1,sz+1), sz+1)
        surface.blit(s, (int(self.x)-sz-1, int(self.y)-sz-1))


# ── Segmented bar ─────────────────────────────────────────────────────────────
def _seg_bar(surface, x, y, w, h, ratio, color, segments=10, bg=(22,8,8)):
    gap   = 2
    sw    = max(4, (w - gap*(segments-1)) // segments)
    filled= ratio * segments
    for i in range(segments):
        sx = x + i*(sw+gap)
        if i < int(filled):
            pygame.draw.rect(surface, color, (sx,y,sw,h), border_radius=2)
            shine = tuple(min(255,v+55) for v in color)
            pygame.draw.rect(surface, shine, (sx+1,y+1,sw-2,max(1,h//3)), border_radius=1)
        elif i == int(filled) and filled % 1 > 0.02:
            pw = max(2, int(sw*(filled%1)))
            pygame.draw.rect(surface, bg, (sx,y,sw,h), border_radius=2)
            pygame.draw.rect(surface, color, (sx,y,pw,h), border_radius=2)
        else:
            pygame.draw.rect(surface, bg, (sx,y,sw,h), border_radius=2)


# ── Button ────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, font,
                 color=(28,48,100), hover_color=(48,78,158),
                 text_color=WHITE, border_color=None, border_radius=12,
                 accent_color=None):
        self.rect          = pygame.Rect(rect)
        self.label         = label
        self.font          = font
        self.color         = color
        self.hover_color   = hover_color
        self.text_color    = text_color
        self.border_color  = border_color or (0,140,255)
        self.border_radius = border_radius
        self.accent_color  = accent_color or (80,180,255)
        self.hovered       = False
        self._hover_t      = 0.0

    def update(self):
        self.hovered  = self.rect.collidepoint(pygame.mouse.get_pos())
        self._hover_t += ((1.0 if self.hovered else 0.0) - self._hover_t) * 0.18

    def draw(self, surface: pygame.Surface):
        t   = self._hover_t
        col = tuple(int(self.color[i]+(self.hover_color[i]-self.color[i])*t) for i in range(3))
        r   = self.rect

        # Outer glow on hover (desktop only — performance guard)
        if t > 0.05 and not _IS_ANDROID:
            bc3 = self.border_color
            for expand in (8, 5, 3):
                ga  = int(45 * t / (expand // 2 + 1))
                gr  = r.inflate(expand * 2, expand * 2)
                gs  = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*bc3, ga), gs.get_rect(),
                                 border_radius=self.border_radius + expand)
                surface.blit(gs, (gr.x, gr.y))

        # Drop shadow — skip on Android (per-frame SRCALPHA alloc is too expensive)
        if not _IS_ANDROID:
            sh = pygame.Surface((r.width+4, r.height+5), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0,0,0,80), sh.get_rect(), border_radius=self.border_radius+2)
            surface.blit(sh, (r.x-2, r.y+4))

        # Body
        pygame.draw.rect(surface, col, r, border_radius=self.border_radius)

        # Inner shine — skip on Android
        if not _IS_ANDROID:
            shine = pygame.Surface((r.width-4, r.height//2), pygame.SRCALPHA)
            pygame.draw.rect(shine, (255,255,255,int(30*t+14)),
                             shine.get_rect(), border_radius=self.border_radius-2)
            surface.blit(shine, (r.x+2, r.y+2))

        # Border (brightens on hover)
        bc = tuple(min(255,int(self.border_color[i]*(0.6+0.4*t))) for i in range(3))
        pygame.draw.rect(surface, bc, r, border_radius=self.border_radius, width=1+int(t))

        # Top accent line
        ac = self.accent_color
        pygame.draw.line(surface, (*ac, int(110+110*t)),
                         (r.x+self.border_radius, r.y+1),
                         (r.right-self.border_radius, r.y+1), 1)

        # Bottom neon underline sweep on hover
        if t > 0.3 and not _IS_ANDROID:
            pygame.draw.line(surface, (*ac, int(160*t)),
                             (r.x+self.border_radius, r.bottom-2),
                             (r.right-self.border_radius, r.bottom-2), 1)

        # Left indicator bar on hover
        if t > 0.2:
            bar_h = int(r.height * t * 0.7)
            by    = r.centery - bar_h // 2
            pygame.draw.rect(surface, (*ac, int(200*t)),
                             (r.x - 4, by, 3, bar_h), border_radius=2)

        # Label
        txt = self.font.render(self.label, True, self.text_color)
        surface.blit(txt, txt.get_rect(center=r.center))

    def clicked(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        if event.type == pygame.FINGERDOWN:
            x = int(event.x * SCREEN_WIDTH)
            y = int(event.y * SCREEN_HEIGHT)
            return self.rect.collidepoint(x, y)
        return False


# ── UIManager ─────────────────────────────────────────────────────────────────
class UIManager:
    BTN_W   = 370
    BTN_H   = 70
    BTN_GAP = 14

    _hud_bottom_cache  = None
    _hud_top_cache     = None
    _menu_bg_cache     = None   # cached semi-transparent menu dim overlay
    _vignette_cache    = None
    _pause_dim_cache   = None
    _pause_card_cache  = None
    _go_dim_cache      = None
    _vict_dim_cache    = None
    _ls_vignette_cache = None   # last-stand border pattern (colorkey)

    def __init__(self, game):
        self.game = game
        pygame.font.init()

        def sf(size, bold=False):
            for name in ('segoeui','tahoma','arial','consolas'):
                try:
                    f = pygame.font.SysFont(name, size, bold=bold)
                    if f: return f
                except Exception:
                    pass
            return pygame.font.Font(None, size)

        self._f_xl  = sf(62, bold=True)
        self._f_lg  = sf(36, bold=True)
        self._f_md  = sf(22, bold=True)
        self._f_sm  = sf(17)
        self._f_xs  = sf(14)
        self._f_hud = sf(15, bold=True)

        self._tick        = 0
        self._float_msgs  : list[dict] = []
        self._achievement_queue: list[str] = []
        self._ach_timer   = 0
        self._kill_flash  = 0       # frames of kill-counter highlight
        self._kills_shown = 0       # smoothed displayed kill count

        # Title particles
        self._sparks: list[_TitleSpark] = []
        self._spark_cd  = 0
        self._spark_hue = 0

        # Menu decor
        self._menu_decor = _MenuDecor()

        # Victory firework timer
        self._fw_timer = 0

        # Weapon icon colours
        self._wpn_cols = {
            'laser':        (0,220,255),
            'double_laser': (0,160,255),
            'triple_laser': (80,255,80),
            'plasma':       (200,0,255),
            'missile':      (255,140,0),
            'spread':       (255,230,0),
            'rainbow':      (255,80,200),
        }

        self._hud_cache: dict = {}   # (key, text, color) → Surface — avoids per-frame font.render

        self._build_menus()
        self._build_hud_panel()
        self._build_vignette()

    # ── One-time builders ─────────────────────────────────────────────────────
    def _build_hud_panel(self):
        h = 80
        s = _vgradient(SCREEN_WIDTH, h, (3,5,18), (6,10,28), alpha_top=0, alpha_bot=240)
        pygame.draw.line(s, (0,110,210), (0,0), (SCREEN_WIDTH,0), 2)
        UIManager._hud_bottom_cache = s

        H   = 44
        top = _vgradient(SCREEN_WIDTH, H, (3,5,20), (5,9,26), alpha_top=195, alpha_bot=225)
        pygame.draw.line(top, (0,110,210), (0,H-1), (SCREEN_WIDTH,H-1), 1)
        UIManager._hud_top_cache = top

    def _build_vignette(self):
        s = pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT), pygame.SRCALPHA)
        for cx,cy in [(0,0),(SCREEN_WIDTH,0),(0,SCREEN_HEIGHT),(SCREEN_WIDTH,SCREEN_HEIGHT)]:
            for r in range(300, 0, -12):
                a = int(160*(1-r/300)**2)
                pygame.draw.circle(s, (0,0,0,a), (cx,cy), r)
        UIManager._vignette_cache = s

    def _cached_render(self, key: str, text: str, font, color) -> pygame.Surface:
        """Return a cached font surface — only re-renders when text or color changes."""
        cache_key = (key, text, color)
        surf = self._hud_cache.get(cache_key)
        if surf is not None:
            return surf
        if len(self._hud_cache) > 300:
            self._hud_cache.clear()
        surf = font.render(text, True, color)
        self._hud_cache[cache_key] = surf
        return surf

    def _build_menus(self):
        cx  = SCREEN_WIDTH // 2
        gap = self.BTN_H + self.BTN_GAP

        def btn(x, y, label, col=(28,48,108), hov=(48,78,165),
                bc=(0,140,255), ac=(80,180,255), tc=WHITE):
            r = pygame.Rect(x-self.BTN_W//2, y, self.BTN_W, self.BTN_H)
            return Button(r, label, self._f_md, col, hov, tc, bc, 12, ac)

        y0 = 318
        self._main_btns = [
            btn(cx, y0,       'NEW GAME',    (18,95,28),  (38,155,48),  (0,200,80), (80,255,120)),
            btn(cx, y0+gap,   'CONTINUE'),
            btn(cx, y0+gap*2, 'HOW TO PLAY'),
            btn(cx, y0+gap*3, 'HIGH SCORES'),
            btn(cx, y0+gap*4, 'SETTINGS'),
            btn(cx, y0+gap*5, 'QUIT',        (95,18,18),  (155,38,38),  (255,60,60),(255,120,80)),
        ]

        y0 = 255
        self._pause_btns = [
            btn(cx, y0,       'RESUME',      (18,95,28),  (38,155,48),  (0,200,80), (80,255,120)),
            btn(cx, y0+gap,   'SETTINGS'),
            btn(cx, y0+gap*2, 'MAIN MENU',   (75,48,8),   (125,78,18),  (200,140,0),(255,200,60)),
            btn(cx, y0+gap*3, 'QUIT',        (95,18,18),  (155,38,38),  (255,60,60),(255,120,80)),
        ]

        y0 = 400
        self._go_btns = [
            btn(cx, y0,       'TRY AGAIN',   (18,95,28),  (38,155,48),  (0,200,80), (80,255,120)),
            btn(cx, y0+gap,   'MAIN MENU'),
            btn(cx, y0+gap*2, 'QUIT',        (95,18,18),  (155,38,38),  (255,60,60),(255,120,80)),
        ]

        y0 = 400
        self._vict_btns = [
            btn(cx, y0,       'PLAY AGAIN',       (18,95,28),  (38,155,48),  (0,200,80),  (80,255,120)),
            btn(cx, y0+gap,   'ENDLESS SURVIVAL', (120,48,8),  (180,78,18),  (255,140,0), (255,200,60)),
            btn(cx, y0+gap*2, 'MAIN MENU'),
            btn(cx, y0+gap*3, 'QUIT',             (95,18,18),  (155,38,38),  (255,60,60), (255,120,80)),
        ]

        sw = 135
        y0 = 305
        self._settings_btns = [
            btn(cx-sw, y0,        'MUSIC  -',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx+sw, y0,        'MUSIC  +',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx-sw, y0+gap,    'SFX    -',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx+sw, y0+gap,    'SFX    +',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx-sw, y0+gap*2,  'SKIN   <',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx+sw, y0+gap*2,  'SKIN   >',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx, y0+gap*3,     'TOGGLE FPS'),
            btn(cx, y0+gap*4,     'BACK'),
        ]

        self._hs_btns  = None
        self._htp_btns = None

    def ensure_secondary_menus(self):
        cx = SCREEN_WIDTH // 2
        def btn(x, y, label):
            r = pygame.Rect(x-self.BTN_W//2, y, self.BTN_W, self.BTN_H)
            return Button(r, label, self._f_md)
        if self._hs_btns  is None:
            self._hs_btns  = [btn(cx, SCREEN_HEIGHT-85, 'BACK')]
        if self._htp_btns is None:
            self._htp_btns = [btn(cx, SCREEN_HEIGHT-85, 'BACK')]

    # ── Public messages / achievements ────────────────────────────────────────
    def show_message(self, text, x, y, color=WHITE, size='sm'):
        font = {'xl':self._f_xl,'lg':self._f_lg,'md':self._f_md,
                'sm':self._f_sm,'xs':self._f_xs}.get(size, self._f_sm)
        self._float_msgs.append({'text':text,'x':float(x),'y':float(y),
                                  'vy':1.5,'timer':85,'color':color,'font':font})

    def show_achievement(self, ach_id):
        self._achievement_queue.append(ach_id)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        self._tick += 1
        for b in self._all_buttons():
            b.update()
        self._float_msgs = [m for m in self._float_msgs if m['timer'] > 0]
        for m in self._float_msgs:
            m['y']     -= m['vy']
            m['timer'] -= 1
        if self._ach_timer > 0:
            self._ach_timer -= 1
        elif self._achievement_queue:
            self._ach_timer = 210

        # Title sparks + menu decor — skip on Android
        if not _IS_ANDROID:
            self._spark_cd -= 1
            if self._spark_cd <= 0:
                self._spark_cd  = random.randint(2, 6)
                self._spark_hue = (self._spark_hue + 11) % 360
                cx = SCREEN_WIDTH // 2
                cy = 142
                self._sparks.append(_TitleSpark(cx, cy, self._spark_hue))
            self._sparks = [s for s in self._sparks if s.update()]
            self._menu_decor.update()

        if self._kill_flash > 0:
            self._kill_flash -= 1
        if self._fw_timer > 0:
            self._fw_timer -= 1

    # ── HUD ──────────────────────────────────────────────────────────────────
    def draw_hud(self, surface: pygame.Surface):
        p   = self.game.player
        lm  = self.game.level_manager
        lvl = self.game.current_level

        self._draw_top_bar(surface, p, lvl)
        self._draw_bottom_bar(surface, p)
        self._draw_weapon_hud(surface, p)
        self._draw_effects_bar(surface, p)
        self._draw_float_msgs(surface)
        self._draw_achievement_popup(surface)
        lm.draw_wave_progress(surface)

        for boss in self.game.boss_group:
            boss.draw_hud(surface)

        if UIManager._vignette_cache and not _IS_ANDROID:
            surface.blit(UIManager._vignette_cache, (0,0))

        # Overlay elements (on top of vignette)
        self._draw_combo_display(surface)
        self._draw_challenge_hud(surface)
        self._draw_last_stand_vignette(surface)

    # ── TOP BAR ──────────────────────────────────────────────────────────────
    def _draw_top_bar(self, surface, p, lvl):
        H   = 44
        surface.blit(UIManager._hud_top_cache, (0, 0))

        # Level / endless wave badge
        if getattr(self.game, '_endless_mode', False):
            wave = getattr(self.game, '_endless_wave', 0)
            lc   = (255, 120, 0)
            lt   = self._cached_render('level', f'ENDLESS  WAVE {wave}', self._f_hud, lc)
        else:
            lc = GOLD if lvl >= TOTAL_LEVELS else (90, 200, 255)
            lt = self._cached_render('level', f'LEVEL  {lvl} / {TOTAL_LEVELS}', self._f_hud, lc)
        surface.blit(lt, (16, (H-lt.get_height())//2))

        # Score (center) with micro-label and NEW RECORD flash
        sc  = self._cached_render('score', f'{p.score:,}', self._f_md, GOLD)
        surface.blit(sc, sc.get_rect(centerx=SCREEN_WIDTH//2, centery=H//2+1))
        slbl = self._cached_render('slbl', 'SCORE', self._f_xs, (90, 120, 180))
        surface.blit(slbl, slbl.get_rect(centerx=SCREEN_WIDTH//2, centery=H//2-10))
        if p.score > 0 and p.score > self.game.save.get('high_score', 0):
            nr_a = int(180 + 75 * math.sin(self._tick * 0.22))
            nr   = self._f_xs.render('▲ NEW RECORD', True, (255, 255, 80))
            nr.set_alpha(nr_a)
            surface.blit(nr, nr.get_rect(centerx=SCREEN_WIDTH//2, y=H - 12))

        # Coins (right)
        ct = self._cached_render('coins', f'  {p.coins:,}', self._f_hud, GOLD)
        bx = SCREEN_WIDTH - ct.get_width() - 22
        pygame.draw.circle(surface, GOLD, (bx-8, H//2), 8)
        pygame.draw.circle(surface, (255,240,110), (bx-8, H//2), 5)
        surface.blit(ct, (bx, (H-ct.get_height())//2))

        # Kill counter (right side under coins)
        kills = self.game.save.get('stats',{}).get('kills', 0)
        kf    = self._f_xs
        if self._kill_flash > 0:
            kc = (255, 200, 50)
        else:
            kc = (130, 150, 190)
        kt = self._cached_render('kills', f'KILLS: {kills:,}', kf, kc)
        surface.blit(kt, (SCREEN_WIDTH-kt.get_width()-16, H-14))

        # Perk build dots — colored circles for each perk the player has picked
        try:
            history = self.game._perk_screen._history
            if history:
                dot_x0 = 200
                for i, pk in enumerate(history[:18]):
                    col  = pk.get('color', (180, 180, 180))
                    dxc  = dot_x0 + i * 16
                    pygame.draw.circle(surface, col, (dxc, H // 2), 6)
                    bright = tuple(min(255, v + 80) for v in col)
                    pygame.draw.circle(surface, bright, (dxc, H // 2), 3)
        except Exception:
            pass

    def _draw_combo_display(self, surface):
        combo = self.game._combo
        if combo < 5:
            return
        mult  = self.game._combo_mult
        timer = self.game._combo_timer
        pulse = int(200 + 55 * math.sin(self._tick * 0.18))
        col   = (255, 215, 50) if mult < 2.5 else \
                (255, 100, 20) if mult < 4.0 else (200, 50, 255)
        ms = self._f_xl.render(f'×{mult:.1f}', True, col)
        ms.set_alpha(pulse)
        surface.blit(ms, ms.get_rect(centerx=SCREEN_WIDTH // 2, y=50))
        # Kill streak badge
        ks = self.game._kill_streak
        if ks >= 10:
            kscols = {10: (255,200,50), 25: (255,100,20), 50: (50,255,255), 100: (200,50,255)}
            kc = kscols.get(max(k for k in kscols if k <= ks), (255,200,50))
            kt = self._f_sm.render(f'STREAK  ×{ks}', True, kc)
            surface.blit(kt, kt.get_rect(centerx=SCREEN_WIDTH // 2,
                                         y=50 + ms.get_height() + 2))

    def _draw_challenge_hud(self, surface):
        if not getattr(self.game, '_challenge_active', False):
            return
        frames = self.game._challenge_frames
        total  = self.game._challenge_total_frames or 1
        done   = self.game._challenge_done
        goal   = self.game._challenge_goal
        secs   = max(0, frames // 60 + 1)
        urgent = secs <= 5
        col    = (255, 50, 50) if urgent else (255, 200, 0)
        label  = self._f_sm.render(f'⚡ CHALLENGE: {done}/{goal} kills  |  {secs}s', True, col)
        bw     = label.get_width() + 24
        bh     = label.get_height() + 12
        bx     = SCREEN_WIDTH // 2 - bw // 2
        by     = 56
        if _IS_ANDROID:
            pygame.draw.rect(surface, (15, 15, 15), (bx, by, bw, bh), border_radius=6)
            pygame.draw.rect(surface, col, (bx, by, bw, bh), 1, border_radius=6)
        else:
            bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 170))
            pygame.draw.rect(bg, col, (0, 0, bw, bh), 1, border_radius=6)
            surface.blit(bg, (bx, by))
        surface.blit(label, (bx + 12, by + 6))
        # Progress bar
        bar_w  = int(bw * done / max(goal, 1))
        if bar_w > 0:
            pygame.draw.rect(surface, (*col, 80), (bx, by + bh, bar_w, 4))

    def _draw_last_stand_vignette(self, surface):
        if not getattr(self.game, '_last_stand_active', False):
            return
        pulse = int(55 + 45 * math.sin(self._tick * 0.12))
        # Build once: colorkey (0,0,0) makes background transparent, set_alpha drives brightness
        if UIManager._ls_vignette_cache is None:
            v = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            v.fill((0, 0, 0))
            v.set_colorkey((0, 0, 0))
            for i in range(0, 50, 6):
                pygame.draw.rect(v, (220, 15, 15),
                                 (i, i, SCREEN_WIDTH - i * 2, SCREEN_HEIGHT - i * 2), 3)
            UIManager._ls_vignette_cache = v
        UIManager._ls_vignette_cache.set_alpha(pulse)
        surface.blit(UIManager._ls_vignette_cache, (0, 0))
        # Timer bar at bottom
        timer = self.game._last_stand_timer
        total = FPS * 8
        ratio = max(0.0, timer / total)
        bw    = int((SCREEN_WIDTH - 40) * ratio)
        if bw > 0:
            pygame.draw.rect(surface, (255, 40, 40, 200),
                             (20, SCREEN_HEIGHT - 8, bw, 6), border_radius=3)

    # ── BOTTOM BAR ───────────────────────────────────────────────────────────
    def _draw_bottom_bar(self, surface, p):
        BH = 80
        BY = SCREEN_HEIGHT - BH
        if UIManager._hud_bottom_cache:
            surface.blit(UIManager._hud_bottom_cache, (0, BY))

        PAD = 16

        # Lives as glowing ship icons (with engine-glow dot)
        for i in range(p.lives):
            lx = PAD + i * 32
            ly = BY + 9
            pts = [(lx+10,ly),(lx,ly+19),(lx+4,ly+15),(lx+16,ly+15),(lx+20,ly+19)]
            life_col = (50, 140, 255)
            pygame.draw.polygon(surface, life_col, pts)
            pygame.draw.polygon(surface, (140, 215, 255), pts, 1)
            pygame.draw.circle(surface, (120, 200, 255), (lx+10, ly+20), 2)

        # HP segmented bar
        BAR_W = 270; BAR_H = 18
        bx = PAD; by = BY + 34
        ratio = max(0.0, p.health / max(p.max_health, 1))
        if ratio > 0.50:
            hcol = (45, 215, 65)
        elif ratio > 0.25:
            hcol = (215, 175, 0)
        else:
            # Critical: pulse the bar color
            pulse_t = (math.sin(pygame.time.get_ticks() * 0.009) + 1) / 2
            hcol    = (int(180 + 75 * pulse_t), int(20 + 20 * pulse_t), 20)
        _seg_bar(surface, bx, by, BAR_W, BAR_H, ratio, hcol, segments=10)
        pygame.draw.rect(surface, (60, 20, 20), (bx, by, BAR_W, BAR_H),
                         border_radius=3, width=1)
        ht = self._cached_render('hp', f'HP  {int(p.health)}/{p.max_health}', self._f_xs, (240, 240, 240))
        surface.blit(ht, (bx + 4, by + 1))
        # Critical warning text
        if ratio <= 0.25 and p.health > 0:
            crit_a = int(170 + 85 * math.sin(pygame.time.get_ticks() * 0.009))
            crit   = self._f_xs.render('⚠ CRITICAL', True, (255, 55, 55))
            crit.set_alpha(crit_a)
            surface.blit(crit, (bx + BAR_W + 7, by + 2))

        # Shield segmented bar
        SBW = 200; SBH = 12
        sby = by + BAR_H + 6
        sr  = max(0.0, p.shield / max(p.max_shield, 1))
        _seg_bar(surface, bx, sby, SBW, SBH, sr, (55, 115, 255), segments=8, bg=(8, 10, 38))
        pygame.draw.rect(surface, (25, 35, 95), (bx, sby, SBW, SBH), border_radius=3, width=1)
        st = self._cached_render('sh', f'SH  {int(p.shield)}/{p.max_shield}', self._f_xs, (150, 195, 255))
        surface.blit(st, (bx + 3, sby + 1))

    # ── WEAPON HUD ────────────────────────────────────────────────────────────
    def _draw_weapon_hud(self, surface, p):
        BH = 80; BY = SCREEN_HEIGHT - BH
        wpn = WEAPONS.get(p.weapon_key, {})
        col = self._wpn_cols.get(p.weapon_key, CYAN)
        name= wpn.get('name','?')

        cx_ = SCREEN_WIDTH - 54
        cy_ = BY + 38
        R   = 28
        pct = p._shoot_cd_pct

        pygame.draw.circle(surface, (18,22,48), (cx_,cy_), R+3)
        pygame.draw.circle(surface, (40,48,90), (cx_,cy_), R, 2)

        if pct > 0.01:
            arc_rect  = pygame.Rect(cx_-R, cy_-R, R*2, R*2)
            end_angle = -math.pi/2 + pct*2*math.pi
            try:
                pygame.draw.arc(surface, col, arc_rect, -math.pi/2, end_angle, 6)
            except Exception:
                pass

        # Center dot — full = white flash
        if pct >= 1.0:
            pygame.draw.circle(surface, (255,255,255), (cx_,cy_), 9)
            if not _IS_ANDROID:
                t  = self._tick
                fa = int(180 + 75*math.sin(t*0.25))
                glow = pygame.Surface((R*2,R*2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*col,fa), (R,R), R)
                surface.blit(glow, (cx_-R, cy_-R), special_flags=pygame.BLEND_ADD)
        else:
            dc = tuple(int(v*0.55) for v in col)
            pygame.draw.circle(surface, dc, (cx_,cy_), 5)

        wt = self._cached_render('wpn', name, self._f_xs, col)
        surface.blit(wt, wt.get_rect(centerx=cx_, y=BY+66))

        # Weapon index pips
        uw    = p.unlocked_weapons
        pip_y = BY + 4
        pip_x = SCREEN_WIDTH - 16 - len(uw)*13
        for i, wk in enumerate(uw):
            pc = self._wpn_cols.get(wk,(100,100,100))
            if wk == p.weapon_key:
                pygame.draw.circle(surface, pc, (pip_x+i*13,pip_y), 5)
                pygame.draw.circle(surface, WHITE,(pip_x+i*13,pip_y), 5, 1)
            else:
                pygame.draw.circle(surface, tuple(v//3 for v in pc),(pip_x+i*13,pip_y), 4)

    # ── EFFECTS pills ─────────────────────────────────────────────────────────
    def _draw_effects_bar(self, surface, p):
        BH = 80; BY = SCREEN_HEIGHT - BH
        EFF = {
            'rapid_fire':   ((255,210,0),'RAPID'),
            'damage_boost': ((255,100,0),'DMG×2'),
            'speed_boost':  ((0,240,200),'SPEED'),
            'coin_magnet':  ((255,215,0),'MAGNET'),
            'invincibility':((200,0,255),'INVNC'),
        }
        active = [(k,p.effect_remaining(k)) for k in EFF if p.has_effect(k)]
        if not active:
            return
        total_w = len(active)*84 + (len(active)-1)*8
        sx = SCREEN_WIDTH//2 - total_w//2
        sy = BY + 7
        for eff, rem in active:
            col, lbl = EFF[eff]
            secs     = rem / 1000
            pr       = pygame.Rect(sx, sy, 82, 26)
            pygame.draw.rect(surface, (*col, 35), pr, border_radius=13)
            pygame.draw.rect(surface, col, pr, border_radius=13, width=2)
            fw = int(82 * min(1.0, secs/8.0))
            if fw > 0:
                pygame.draw.rect(surface, (*col,65),(sx,sy,fw,26), border_radius=13)
            lt = self._f_xs.render(f'{lbl} {secs:.1f}', True, WHITE)
            surface.blit(lt, lt.get_rect(center=pr.center))
            sx += 92

    # ── Float messages ────────────────────────────────────────────────────────
    def _draw_float_msgs(self, surface):
        for m in self._float_msgs:
            alpha = min(255, int(m['timer']*5.5))
            txt   = m['font'].render(m['text'], True, m['color'])
            txt.set_alpha(alpha)
            surface.blit(txt, txt.get_rect(centerx=int(m['x']), centery=int(m['y'])))

    # ── Achievement popup ─────────────────────────────────────────────────────
    def _draw_achievement_popup(self, surface):
        if not self._achievement_queue or self._ach_timer <= 0:
            return
        ach_id     = self._achievement_queue[0]
        name, desc = ACHIEVEMENTS.get(ach_id, ('Achievement',''))
        if self._ach_timer < 28:
            self._achievement_queue.pop(0)
            return
        T   = self._ach_timer
        MAX = 210
        ease_in  = min(1.0, (MAX-T+25)/25)
        ease_out = min(1.0, T/25)
        slide    = min(ease_in, ease_out)
        W  = 360; H = 72
        x  = int(SCREEN_WIDTH - W - 14 + (1-slide)*(W+24))
        y  = 52

        if _IS_ANDROID:
            s = pygame.Surface((W, H))
            s.fill((8, 28, 8))
        else:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((8, 28, 8, 215))
        pygame.draw.rect(s,(55,195,55),(0,0,W,H),border_radius=11,width=2)
        pygame.draw.rect(s,(28,115,28),(0,0,7,H),border_radius=5)

        # Star icon
        star = self._f_md.render('★', True, GOLD)
        s.blit(star, (14, 8))

        ht = self._f_xs.render('ACHIEVEMENT UNLOCKED!', True, (130,255,130))
        nt = self._f_md.render(name, True, GOLD)
        dt = self._f_xs.render(desc,  True, (155,215,155))
        s.blit(ht, (40, 7))
        s.blit(nt, (40, 26))
        s.blit(dt, (40, 50))
        surface.blit(s, (x, y))

    # ── MAIN MENU ─────────────────────────────────────────────────────────────
    def draw_main_menu(self, surface: pygame.Surface):
        self._draw_menu_bg(surface)
        if not _IS_ANDROID:
            self._menu_decor.draw(surface)
            for sp in self._sparks:
                sp.draw(surface)
        self._draw_title(surface)

        # ── Neon side accent lines flanking buttons ──
        if not _IS_ANDROID:
            cx   = SCREEN_WIDTH // 2
            btn_l= cx - self.BTN_W // 2 - 18
            btn_r= cx + self.BTN_W // 2 + 18
            y0   = self._main_btns[0].rect.top  - 8
            y1   = self._main_btns[-1].rect.bottom + 8
            a    = int(110 + 55 * math.sin(self._tick * 0.04))
            for bx in (btn_l, btn_r):
                lv = pygame.Surface((3, y1 - y0), pygame.SRCALPHA)
                for i in range(y1 - y0):
                    fa = int(a * math.sin(math.pi * i / max(y1 - y0, 1)))
                    lv.fill((0, 140, 255, fa), (0, i, 3, 1))
                surface.blit(lv, (bx, y0))

        for b in self._main_btns:
            b.draw(surface)

        # ── High score badge ──
        hs = self.game.save.get('high_score', 0)
        if hs > 0:
            hs_lbl = self._f_xs.render('BEST SCORE', True, (120, 155, 210))
            hs_val = self._f_md.render(f'{hs:,}', True, GOLD)
            surface.blit(hs_lbl, (SCREEN_WIDTH - hs_val.get_width() - 18, 10))
            surface.blit(hs_val, (SCREEN_WIDTH - hs_val.get_width() - 12, 26))

        # ── Hint bar ──
        hint = self._f_xs.render(
            'WASD · Space to fire · Q/E switch weapon · F11 fullscreen',
            True, (65, 80, 118))
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 24))

        # ── Daily bonus banner ──
        daily = getattr(self.game, '_daily_bonus', 0)
        if daily > 0:
            alpha  = int(190 + 65 * math.sin(self._tick * 0.05))
            banner = self._f_md.render(f'  DAILY BONUS  +{daily} COINS  ', True, GOLD)
            banner.set_alpha(alpha)
            surface.blit(banner, banner.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 68))

    # ── PAUSE ─────────────────────────────────────────────────────────────────
    def draw_pause(self, surface: pygame.Surface):
        if UIManager._pause_dim_cache is None:
            d = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            d.fill((0, 0, 0)); d.set_alpha(155)
            UIManager._pause_dim_cache = d
        surface.blit(UIManager._pause_dim_cache, (0, 0))

        CW,CH = 390,350
        cx,cy = SCREEN_WIDTH//2, SCREEN_HEIGHT//2
        if UIManager._pause_card_cache is None:
            card = pygame.Surface((CW,CH), pygame.SRCALPHA)
            card.fill((6,10,28,235))
            pygame.draw.rect(card,(0,130,255),(0,0,CW,CH),border_radius=16,width=2)
            pygame.draw.line(card,(0,175,255),(20,1),(CW-20,1),1)
            UIManager._pause_card_cache = card
        surface.blit(UIManager._pause_card_cache,(cx-CW//2,cy-CH//2))

        y_off = int(3*math.sin(self._tick*0.05))
        title = self._f_lg.render('PAUSED', True, GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=cy-CH//2+22+y_off))
        for b in self._pause_btns:
            b.draw(surface)

    # ── GAME OVER ─────────────────────────────────────────────────────────────
    def draw_game_over(self, surface: pygame.Surface):
        if UIManager._go_dim_cache is None:
            d = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            d.fill((22, 0, 0)); d.set_alpha(195)
            UIManager._go_dim_cache = d
        surface.blit(UIManager._go_dim_cache, (0, 0))

        t = self._tick
        if not _IS_ANDROID:
            for y in range(0, SCREEN_HEIGHT, 4):
                if (y//4 + t//3) % 5 == 0:
                    pygame.draw.line(surface,(0,0,0,30),(0,y),(SCREEN_WIDTH,y))

        y_off = int(5*math.sin(t*0.04))

        # Multi-layer glowing title
        for off, alpha in ((5,25),(3,60),(1,120),(0,255)):
            col = (min(255,200+off*10), 25, 25)
            txt = self._f_xl.render('MISSION FAILED', True, col)
            if off: txt.set_alpha(alpha)
            surface.blit(txt, txt.get_rect(centerx=SCREEN_WIDTH//2+off, y=108+y_off+off))

        # Sub text
        sub = self._f_sm.render('The aliens have won... this time.', True, (180,80,80))
        sub.set_alpha(200)
        surface.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH//2, y=198+y_off))

        # Stats panel
        p    = self.game.player
        save = self.game.save
        items = [
            ('SCORE',      f'{p.score:,}',                               GOLD),
            ('LEVEL',      f'{self.game.current_level} / {TOTAL_LEVELS}',(180,200,255)),
            ('KILLS',      f'{save.get("stats",{}).get("kills",0):,}',   (220,180,180)),
            ('COINS',      f'{p.coins:,}',                               GOLD),
            ('HIGH SCORE', f'{save.get("high_score",0):,}',              (220,180,90)),
        ]
        PW = 430; PH = len(items)*48+22
        ps = pygame.Surface((PW,PH))
        ps.fill((22,5,5)); ps.set_alpha(210)
        pygame.draw.rect(ps,(175,28,28),(0,0,PW,PH),border_radius=13,width=2)
        surface.blit(ps, ps.get_rect(centerx=SCREEN_WIDTH//2, y=230))

        for i,(label,val,col) in enumerate(items):
            y = 242+i*48
            # Label left
            lt = self._f_sm.render(label, True, (180,110,110))
            surface.blit(lt, (SCREEN_WIDTH//2-200, y))
            # Value right (counting animation for score)
            vt = self._f_md.render(val, True, col)
            surface.blit(vt, vt.get_rect(right=SCREEN_WIDTH//2+200, y=y-2))
            # Divider
            pygame.draw.line(surface,(90,25,25),
                             (SCREEN_WIDTH//2-200,y+38),(SCREEN_WIDTH//2+200,y+38), 1)

        for b in self._go_btns:
            b.draw(surface)

    # ── VICTORY ───────────────────────────────────────────────────────────────
    def draw_victory(self, surface: pygame.Surface):
        if UIManager._vict_dim_cache is None:
            d = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            d.fill((0, 22, 0)); d.set_alpha(165)
            UIManager._vict_dim_cache = d
        surface.blit(UIManager._vict_dim_cache, (0, 0))

        t = self._tick

        # Periodic fireworks via particles
        self._fw_timer -= 1
        if self._fw_timer <= 0:
            self._fw_timer = random.randint(15, 40)
            fw_x = random.randint(100, SCREEN_WIDTH-100)
            fw_y = random.randint(80, 320)
            col  = _hue_rgb(random.randint(0,359))
            self.game.particles.explosion(fw_x, fw_y, col, count=45, speed=8, size=4)
            self.game.particles.fire_ring(fw_x, fw_y, col, count=20, radius=35)
            self.game.particles.shockwave_ring(fw_x, fw_y, col, max_radius=80, speed=6)

        # Particles are drawn separately in game.py; just draw the UI layer here
        hue   = (t*2) % 360
        col   = _hue_rgb(hue)
        y_off = int(7*math.sin(t*0.05))

        for off,al in ((5,22),(2,70),(0,255)):
            tc = col if not off else GOLD
            txt= self._f_xl.render('VICTORY!', True, tc)
            if off: txt.set_alpha(al)
            surface.blit(txt, txt.get_rect(centerx=SCREEN_WIDTH//2+off, y=90+y_off+off))

        sub = self._f_lg.render("Earth has been saved!", True, (150,255,150))
        surface.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH//2, y=180+y_off))

        star_row = self._f_md.render('★  ★  ★', True, GOLD)
        surface.blit(star_row, star_row.get_rect(centerx=SCREEN_WIDTH//2, y=218+y_off))

        # Stats
        p    = self.game.player
        save = self.game.save
        items = [
            ('FINAL SCORE', f'{p.score:,}',              GOLD),
            ('COINS',       f'{p.coins:,}',              GOLD),
            ('HIGH SCORE',  f'{save.get("high_score",0):,}',(220,200,90)),
        ]
        for i,(label,val,c) in enumerate(items):
            y = 278+i*46
            lt = self._f_sm.render(label, True, (130,195,130))
            vt = self._f_md.render(val,   True, c)
            surface.blit(lt, (SCREEN_WIDTH//2-195, y))
            surface.blit(vt, vt.get_rect(right=SCREEN_WIDTH//2+195, y=y-2))

        for b in self._vict_btns:
            b.draw(surface)

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    def draw_settings(self, surface: pygame.Surface):
        self._draw_menu_bg(surface)
        title = self._f_lg.render('SETTINGS', True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH//2, y=80))

        audio    = self.game.audio
        save     = self.game.save
        skin_id  = save.get('ship_skin', 'cyan')
        skin_dat = SHIP_SKINS.get(skin_id, SHIP_SKINS['cyan'])
        rows = [
            ('Music Volume', f'{int(audio.music_vol*100):3d} %', GOLD),
            ('SFX Volume',   f'{int(audio.sfx_vol*100):3d} %',   GOLD),
            ('Show FPS',     'ON' if save.get_setting('show_fps') else 'OFF', GOLD),
            ('Ship Skin',    skin_dat['name'],                    skin_dat['neon']),
        ]
        PW = 510; PH = len(rows)*66+24
        ps = pygame.Surface((PW,PH))
        ps.fill((7,10,28)); ps.set_alpha(215)
        pygame.draw.rect(ps,(0,115,215),(0,0,PW,PH),border_radius=14,width=2)
        surface.blit(ps, ps.get_rect(centerx=SCREEN_WIDTH//2, y=148))
        for i,(k,v,col) in enumerate(rows):
            y = 160+i*66
            kt = self._f_md.render(k, True,(175,195,255))
            vt = self._f_md.render(v, True, col)
            surface.blit(kt, (SCREEN_WIDTH//2-235, y))
            surface.blit(vt, vt.get_rect(right=SCREEN_WIDTH//2+235, y=y))
        for b in self._settings_btns:
            b.draw(surface)

    # ── HIGH SCORES ───────────────────────────────────────────────────────────
    def draw_high_scores(self, surface: pygame.Surface):
        self._draw_menu_bg(surface)
        title = self._f_lg.render('HIGH SCORES', True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH//2, y=48))

        save  = self.game.save
        stats = save.get('stats',{})
        rows  = [
            ('High Score',   f'{save.get("high_score",0):,}',          GOLD),
            ('Best Level',   f'{save.get("best_level",0)} / {TOTAL_LEVELS}',(175,215,255)),
            ('Total Kills',  f'{stats.get("kills",0):,}',              (215,195,175)),
            ('Bosses Slain', f'{stats.get("bosses_killed",0)}',        (255,145,95)),
            ('Total Coins',  f'{save.get("total_coins",0):,}',         GOLD),
            ('Shots Fired',  f'{stats.get("shots_fired",0):,}',        (175,195,215)),
            ('Damage Dealt', f'{stats.get("damage_dealt",0):,}',       (215,145,145)),
        ]
        PW=570; PH=len(rows)*48+22
        ps=pygame.Surface((PW,PH))
        ps.fill((7,10,28)); ps.set_alpha(215)
        pygame.draw.rect(ps,(0,115,215),(0,0,PW,PH),border_radius=14,width=2)
        surface.blit(ps, ps.get_rect(centerx=SCREEN_WIDTH//2, y=108))
        for i,(label,val,col) in enumerate(rows):
            y=120+i*48
            lt=self._f_sm.render(label,True,(155,185,225))
            vt=self._f_md.render(val,  True, col)
            surface.blit(lt, (SCREEN_WIDTH//2-265, y))
            surface.blit(vt, vt.get_rect(right=SCREEN_WIDTH//2+265, y=y-3))

        earned = save.get('achievements',[])
        ay = 108+PH+32
        ah = self._f_md.render('ACHIEVEMENTS', True, GOLD)
        surface.blit(ah, ah.get_rect(centerx=SCREEN_WIDTH//2, y=ay))
        ay += 40
        for aid,(name,desc) in ACHIEVEMENTS.items():
            unlocked = aid in earned
            col      = (90,215,90) if unlocked else (65,75,95)
            icon     = '★' if unlocked else '○'
            t = self._f_sm.render(f'{icon}  {name}  —  {desc}', True, col)
            surface.blit(t, t.get_rect(centerx=SCREEN_WIDTH//2, y=ay))
            ay += 30
        if self._hs_btns:
            for b in self._hs_btns: b.draw(surface)

    # ── HOW TO PLAY ───────────────────────────────────────────────────────────
    def draw_how_to_play(self, surface: pygame.Surface):
        self._draw_menu_bg(surface)
        title = self._f_lg.render('HOW  TO  PLAY', True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH//2, y=40))

        sections = [
            ('CONTROLS',[
                ('Move',           'WASD  or  Arrow Keys'),
                ('Shoot',          'SPACE  (hold = rapid fire)  or  Left Click'),
                ('Switch Weapon',  'Q / E  ·  Mouse Scroll  ·  Right Click'),
                ('Pause',          'ESC  or  P'),
                ('Fullscreen',     'F11'),
            ]),
            ('OBJECTIVE',[
                ('Goal',     'Survive 20 waves  —  defeat bosses every 5 levels'),
                ('Upgrades', 'Earn coins  ·  spend them in the shop between levels'),
                ('Trails',   'Buy ship trails in the TRAILS shop tab (cosmetic)'),
                ('Quiz',     'Answer maths/English questions for bonus coins!'),
            ]),
            ('POWER-UPS',[
                ('H  Health    S  Shield     R  Rapid Fire',''),
                ('D  Damage   V  Speed      M  Coin Magnet',''),
                ('I  Invincible     B  Screen Bomb',        ''),
            ]),
        ]
        y = 106
        for section_name, items in sections:
            sh = self._f_md.render(section_name, True, (75,175,255))
            pygame.draw.line(surface,(38,75,155),
                             (SCREEN_WIDTH//2-265,y+23),(SCREEN_WIDTH//2+265,y+23),1)
            surface.blit(sh,(SCREEN_WIDTH//2-265,y))
            y += 32
            for lbl,val in items:
                lt=self._f_sm.render(lbl, True,(195,215,255))
                surface.blit(lt,(SCREEN_WIDTH//2-248,y))
                if val:
                    vt=self._f_sm.render(val, True, GOLD)
                    surface.blit(vt,vt.get_rect(right=SCREEN_WIDTH//2+265,y=y))
                y += 30
            y += 16
        if self._htp_btns:
            for b in self._htp_btns: b.draw(surface)

    # ── Event routing ─────────────────────────────────────────────────────────
    def handle_main_menu(self, event) -> str:
        for b in self._main_btns:
            if b.clicked(event):
                self.game.audio.play('click')
                return b.label
        return ''

    def handle_pause(self, event) -> str:
        for b in self._pause_btns:
            if b.clicked(event):
                self.game.audio.play('click')
                return b.label
        return ''

    def handle_game_over(self, event) -> str:
        for b in self._go_btns:
            if b.clicked(event):
                self.game.audio.play('click')
                return b.label
        return ''

    def handle_victory(self, event) -> str:
        for b in self._vict_btns:
            if b.clicked(event):
                self.game.audio.play('click')
                return b.label
        return ''

    def handle_settings(self, event) -> str:
        audio = self.game.audio
        save  = self.game.save
        labels = {'MUSIC  -':('music',-0.1),'MUSIC  +':('music',+0.1),
                  'SFX    -':('sfx',  -0.1),'SFX    +':('sfx',  +0.1)}
        for b in self._settings_btns:
            if b.clicked(event):
                self.game.audio.play('click')
                lbl = b.label
                if lbl in labels:
                    kind,delta = labels[lbl]
                    if kind=='music': audio.set_music_volume(audio.music_vol+delta)
                    else:             audio.set_sfx_volume(audio.sfx_vol+delta)
                elif lbl in ('SKIN   <', 'SKIN   >'):
                    cur = save.get('ship_skin', 'cyan')
                    idx = SKIN_ORDER.index(cur) if cur in SKIN_ORDER else 0
                    delta = -1 if lbl == 'SKIN   <' else 1
                    new_skin = SKIN_ORDER[(idx + delta) % len(SKIN_ORDER)]
                    save.set('ship_skin', new_skin)
                    if self.game.player:
                        self.game.player.set_skin(new_skin)
                elif lbl=='TOGGLE FPS':
                    save.set_setting('show_fps', not save.get_setting('show_fps'))
                elif lbl=='BACK':
                    return 'back'
        return ''

    def handle_high_scores(self, event) -> str:
        if self._hs_btns:
            for b in self._hs_btns:
                if b.clicked(event):
                    self.game.audio.play('click')
                    return b.label
        return ''

    def handle_how_to_play(self, event) -> str:
        if self._htp_btns:
            for b in self._htp_btns:
                if b.clicked(event):
                    self.game.audio.play('click')
                    return b.label
        return ''

    # ── Internal ──────────────────────────────────────────────────────────────
    def _all_buttons(self):
        for attr in ('_main_btns','_pause_btns','_settings_btns','_go_btns','_vict_btns'):
            for b in getattr(self,attr,[]) or []:
                yield b
        for attr in ('_hs_btns','_htp_btns'):
            for b in (getattr(self,attr,None) or []):
                yield b

    def _draw_menu_bg(self, surface: pygame.Surface):
        if _IS_ANDROID:
            from background import Background
            if Background._grad:
                surface.blit(Background._grad, (0, 0))
        else:
            self.game.background.draw(surface)
        # Dark overlay — build once, reuse (set_alpha avoids per-frame SRCALPHA alloc)
        if UIManager._menu_bg_cache is None:
            d = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            d.fill((0, 4, 20))
            d.set_alpha(88)
            UIManager._menu_bg_cache = d
        surface.blit(UIManager._menu_bg_cache, (0, 0))
        if not _IS_ANDROID:
            for y in range(0, SCREEN_HEIGHT, 3):
                pygame.draw.line(surface, (0, 0, 0, 14), (0, y), (SCREEN_WIDTH, y))
        if UIManager._vignette_cache:
            surface.blit(UIManager._vignette_cache, (0, 0))

    def _draw_title(self, surface: pygame.Surface):
        t   = self._tick
        bob = int(5 * math.sin(t * 0.034))
        cx  = SCREEN_WIDTH // 2

        # Large pulsing glow orb behind title (skip on Android — per-frame large SRCALPHA)
        if not _IS_ANDROID:
            ga  = int(45 + 35 * math.sin(t * 0.050))
            gw, gh = 860, 170
            glow = pygame.Surface((gw, gh), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (15, 45, 160, ga), glow.get_rect())
            surface.blit(glow, glow.get_rect(centerx=cx, centery=148 + bob))

        # ── Chromatic aberration shadow layers ──
        title_full = 'ALIEN  INVASION'
        for ox, col, alpha in ((-4, (220, 0, 100), 55), (4, (0, 150, 255), 55)):
            sh = self._f_xl.render(title_full, True, col)
            sh.set_alpha(alpha)
            surface.blit(sh, sh.get_rect(centerx=cx + ox, y=108 + bob))

        # ── Two-tone animated main title ──
        hue1 = (t * 1.1) % 360
        hue2 = (t * 1.1 + 165) % 360
        c1   = _hue_rgb(hue1)
        c2   = _hue_rgb(hue2)
        t1   = self._f_xl.render('ALIEN', True, c1)
        t2   = self._f_xl.render('INVASION', True, c2)
        gap  = 22
        total_w = t1.get_width() + gap + t2.get_width()
        x0   = cx - total_w // 2
        surface.blit(t1, (x0, 108 + bob))
        surface.blit(t2, (x0 + t1.get_width() + gap, 108 + bob))

        # ── Animated light sweep across title ──
        if not _IS_ANDROID:
            prog     = (math.sin(t * 0.016) + 1) / 2
            sweep_x  = int(x0 + total_w * prog)
            sw_surf  = pygame.Surface((5, 70), pygame.SRCALPHA)
            for i in range(5):
                sw_surf.fill((255, 255, 255, max(0, 110 - i * 22)), (i, 0, 1, 70))
            surface.blit(sw_surf, (sweep_x, 106 + bob))

        # ── Subtitle ──
        sub = self._f_sm.render(
            "Earth's Last Defense   ·   v2.0  LEGENDARY", True, (160, 195, 255))
        sub.set_alpha(210)
        surface.blit(sub, sub.get_rect(centerx=cx, y=184 + bob))

        # ── Animated divider with traveling dot ──
        dw = 310
        pygame.draw.line(surface, (0, 85, 175), (cx - dw, 218), (cx + dw, 218), 1)
        pygame.draw.line(surface, (0, 55, 130), (cx - dw, 220), (cx + dw, 220), 1)
        dot_x = cx - dw + int(dw * 2 * ((t % 140) / 140))
        pygame.draw.circle(surface, (80, 200, 255), (dot_x, 219), 3)
        for dx in (-dw, -dw//2, 0, dw//2, dw):
            pygame.draw.circle(surface, (0, 110, 230), (cx + dx, 219), 2)

    @staticmethod
    def _hue_rgb(h):
        return _hue_rgb(h)
