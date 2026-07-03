"""UI: world-class HUD, animated menus, cinematic overlays."""

import math
import random
import pygame
import os as _os
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WEAPONS, WEAPON_ORDER, TOTAL_LEVELS,
    WHITE, BLACK, GOLD, CYAN, RED, GREEN, BLUE, ORANGE, PURPLE,
    UI_BG, UI_BORDER, UI_TEXT, UI_HIGHLIGHT, UI_BUTTON, UI_BUTTON_HOV,
    UI_SUCCESS, UI_DANGER, ACHIEVEMENTS
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
        a  = int(255 * self.life / self.max_life)
        sz = max(1, self.size)
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

        # Drop shadow
        sh = pygame.Surface((r.width+4, r.height+5), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0,0,0,75), sh.get_rect(), border_radius=self.border_radius+2)
        surface.blit(sh, (r.x-2, r.y+4))

        # Body
        pygame.draw.rect(surface, col, r, border_radius=self.border_radius)

        # Inner shine
        shine = pygame.Surface((r.width-4, r.height//2), pygame.SRCALPHA)
        pygame.draw.rect(shine, (255,255,255,int(25*t+12)),
                         shine.get_rect(), border_radius=self.border_radius-2)
        surface.blit(shine, (r.x+2, r.y+2))

        # Border
        bc = tuple(min(255,int(self.border_color[i]*(0.65+0.35*t))) for i in range(3))
        pygame.draw.rect(surface, bc, r, border_radius=self.border_radius, width=1+int(t))

        # Top accent
        ac = self.accent_color
        pygame.draw.line(surface, (*ac, int(110+110*t)),
                         (r.x+self.border_radius, r.y+1),
                         (r.right-self.border_radius, r.y+1), 1)

        # Label
        txt = self.font.render(self.label, True, self.text_color)
        surface.blit(txt, txt.get_rect(center=r.center))

    def clicked(self, event) -> bool:
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


# ── UIManager ─────────────────────────────────────────────────────────────────
class UIManager:
    BTN_W   = 310
    BTN_H   = 56
    BTN_GAP = 13

    _hud_bottom_cache = None
    _hud_top_cache    = None
    _menu_bg_cache    = None
    _vignette_cache   = None

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

        y0 = 410
        self._vict_btns = [
            btn(cx, y0,       'PLAY AGAIN',  (18,95,28),  (38,155,48),  (0,200,80), (80,255,120)),
            btn(cx, y0+gap,   'MAIN MENU'),
            btn(cx, y0+gap*2, 'QUIT',        (95,18,18),  (155,38,38),  (255,60,60),(255,120,80)),
        ]

        sw = 135
        y0 = 305
        self._settings_btns = [
            btn(cx-sw, y0,      'MUSIC  -',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx+sw, y0,      'MUSIC  +',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx-sw, y0+gap,  'SFX    -',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx+sw, y0+gap,  'SFX    +',  (28,38,88),(48,68,148),(0,100,200),(60,150,255)),
            btn(cx, y0+gap*2,   'TOGGLE FPS'),
            btn(cx, y0+gap*3,   'BACK'),
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

        # Title sparks
        self._spark_cd -= 1
        if self._spark_cd <= 0:
            self._spark_cd  = random.randint(2, 6)
            self._spark_hue = (self._spark_hue + 11) % 360
            cx = SCREEN_WIDTH // 2
            cy = 142
            self._sparks.append(_TitleSpark(cx, cy, self._spark_hue))
        self._sparks = [s for s in self._sparks if s.update()]

        # Menu decor
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

        if UIManager._vignette_cache:
            surface.blit(UIManager._vignette_cache, (0,0))

    # ── TOP BAR ──────────────────────────────────────────────────────────────
    def _draw_top_bar(self, surface, p, lvl):
        H   = 44
        surface.blit(UIManager._hud_top_cache, (0, 0))

        # Level badge
        lc  = GOLD if lvl >= TOTAL_LEVELS else (90,200,255)
        lt  = self._f_hud.render(f'LEVEL  {lvl} / {TOTAL_LEVELS}', True, lc)
        surface.blit(lt, (16, (H-lt.get_height())//2))

        # Score (center) — pulses on new kills
        sc  = self._f_md.render(f'{p.score:,}', True, GOLD)
        surface.blit(sc, sc.get_rect(centerx=SCREEN_WIDTH//2, centery=H//2+1))

        # Coins (right)
        ct = self._f_hud.render(f'  {p.coins:,}', True, GOLD)
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
        kt = kf.render(f'KILLS: {kills:,}', True, kc)
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

    # ── BOTTOM BAR ───────────────────────────────────────────────────────────
    def _draw_bottom_bar(self, surface, p):
        BH = 80
        BY = SCREEN_HEIGHT - BH
        if UIManager._hud_bottom_cache:
            surface.blit(UIManager._hud_bottom_cache, (0, BY))

        PAD = 16

        # Lives as glowing ship icons
        for i in range(p.lives):
            lx = PAD + i * 30
            ly = BY + 10
            pts = [(lx+10,ly),(lx,ly+18),(lx+4,ly+14),(lx+16,ly+14),(lx+20,ly+18)]
            pygame.draw.polygon(surface, (50,130,255), pts)
            pygame.draw.polygon(surface, (130,210,255), pts, 1)

        # HP segmented bar
        BAR_W = 270; BAR_H = 18
        bx = PAD; by = BY + 34
        ratio = max(0.0, p.health / max(p.max_health,1))
        hcol  = (45,215,65) if ratio > 0.50 else (215,175,0) if ratio > 0.25 else (215,45,45)
        _seg_bar(surface, bx, by, BAR_W, BAR_H, ratio, hcol, segments=10)
        pygame.draw.rect(surface, (60,20,20), (bx,by,BAR_W,BAR_H), border_radius=3, width=1)
        ht = self._f_xs.render(f'HP  {p.health}/{p.max_health}', True, (240,240,240))
        surface.blit(ht, (bx+4, by+1))

        # Shield segmented bar
        SBW = 200; SBH = 12
        sby = by + BAR_H + 6
        sr  = max(0.0, p.shield / max(p.max_shield,1))
        _seg_bar(surface, bx, sby, SBW, SBH, sr, (55,115,255), segments=8, bg=(8,10,38))
        pygame.draw.rect(surface, (25,35,95), (bx,sby,SBW,SBH), border_radius=3, width=1)
        st = self._f_xs.render(f'SH  {p.shield}/{p.max_shield}', True, (150,195,255))
        surface.blit(st, (bx+3, sby+1))

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

        wt = self._f_xs.render(name, True, col)
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
        # Animated ships behind everything
        self._menu_decor.draw(surface)
        # Title sparks
        for sp in self._sparks:
            sp.draw(surface)
        self._draw_title(surface)
        for b in self._main_btns:
            b.draw(surface)
        hint = self._f_xs.render(
            'WASD / Arrows  ·  Space to shoot  ·  Q/E or Scroll to switch weapon  ·  F11 = Fullscreen',
            True, (72,82,122))
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH//2, y=SCREEN_HEIGHT-26))
        # Daily bonus banner — visible all session once claimed today
        daily = getattr(self.game, '_daily_bonus', 0)
        if daily > 0:
            alpha  = int(190 + 65 * math.sin(self._tick * 0.05))
            banner = self._f_md.render(f'  DAILY BONUS  +{daily} COINS  ', True, GOLD)
            banner.set_alpha(alpha)
            surface.blit(banner, banner.get_rect(centerx=SCREEN_WIDTH//2, y=SCREEN_HEIGHT-68))

    # ── PAUSE ─────────────────────────────────────────────────────────────────
    def draw_pause(self, surface: pygame.Surface):
        dim = pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0,0,0,155))
        surface.blit(dim,(0,0))

        CW,CH = 390,350
        cx,cy = SCREEN_WIDTH//2, SCREEN_HEIGHT//2
        card  = pygame.Surface((CW,CH), pygame.SRCALPHA)
        card.fill((6,10,28,235))
        pygame.draw.rect(card,(0,130,255),(0,0,CW,CH),border_radius=16,width=2)
        pygame.draw.line(card,(0,175,255),(20,1),(CW-20,1),1)
        surface.blit(card,(cx-CW//2,cy-CH//2))

        y_off = int(3*math.sin(self._tick*0.05))
        title = self._f_lg.render('PAUSED', True, GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=cy-CH//2+22+y_off))
        for b in self._pause_btns:
            b.draw(surface)

    # ── GAME OVER ─────────────────────────────────────────────────────────────
    def draw_game_over(self, surface: pygame.Surface):
        # Dark red dim
        dim = pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((22,0,0,195))
        surface.blit(dim,(0,0))

        t = self._tick
        # Scanline flicker
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
        ps = pygame.Surface((PW,PH), pygame.SRCALPHA)
        ps.fill((22,5,5,210))
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
        dim = pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0,22,0,165))
        surface.blit(dim,(0,0))

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

        audio = self.game.audio
        save  = self.game.save
        rows  = [
            ('Music Volume', f'{int(audio.music_vol*100):3d} %'),
            ('SFX Volume',   f'{int(audio.sfx_vol*100):3d} %'),
            ('Show FPS',     'ON' if save.get_setting('show_fps') else 'OFF'),
        ]
        PW = 510; PH = len(rows)*66+24
        ps = pygame.Surface((PW,PH), pygame.SRCALPHA)
        ps.fill((7,10,28,215))
        pygame.draw.rect(ps,(0,115,215),(0,0,PW,PH),border_radius=14,width=2)
        surface.blit(ps, ps.get_rect(centerx=SCREEN_WIDTH//2, y=148))
        for i,(k,v) in enumerate(rows):
            y = 160+i*66
            kt = self._f_md.render(k, True,(175,195,255))
            vt = self._f_md.render(v, True, GOLD)
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
        ps=pygame.Surface((PW,PH), pygame.SRCALPHA)
        ps.fill((7,10,28,215))
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
        for y in range(0, SCREEN_HEIGHT, 2):
            t = y/SCREEN_HEIGHT
            pygame.draw.line(surface, (int(5+t*7),int(3+t*4),int(20+t*26)),
                             (0,y),(SCREEN_WIDTH,y+1))
        if UIManager._vignette_cache:
            surface.blit(UIManager._vignette_cache,(0,0))

    def _draw_title(self, surface: pygame.Surface):
        t   = self._tick
        bob = int(5*math.sin(t*0.034))

        # Pulsing background glow ellipse
        ga  = int(50+35*math.sin(t*0.055))
        gw, gh = 740, 130
        glow = pygame.Surface((gw,gh), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (25,70,190,ga), glow.get_rect())
        surface.blit(glow, glow.get_rect(centerx=SCREEN_WIDTH//2, centery=148+bob))

        # Drop shadow
        sh = self._f_xl.render('ALIEN  INVASION', True,(0,0,0))
        surface.blit(sh, sh.get_rect(centerx=SCREEN_WIDTH//2+5, y=108+bob+5))

        # Animated title: hue-shifted "ALIEN" and "INVASION"
        hue1 = (t*1.2) % 360
        hue2 = (t*1.2 + 180) % 360
        c1   = _hue_rgb(hue1)
        c2   = _hue_rgb(hue2)
        t1   = self._f_xl.render('ALIEN', True, c1)
        t2   = self._f_xl.render('INVASION', True, c2)
        gap  = 20
        total_w = t1.get_width()+gap+t2.get_width()
        x0 = SCREEN_WIDTH//2 - total_w//2
        surface.blit(t1,(x0, 108+bob))
        surface.blit(t2,(x0+t1.get_width()+gap, 108+bob))

        # Subtitle
        sub = self._f_sm.render("Earth's Last Defense  |  Version 3.0", True,(150,180,255))
        surface.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH//2, y=180+bob))

        # Divider
        dw=280
        pygame.draw.line(surface,(0,90,185),
                         (SCREEN_WIDTH//2-dw,210),(SCREEN_WIDTH//2+dw,210),1)
        for dx in (-dw,-dw//2,0,dw//2,dw):
            pygame.draw.circle(surface,(0,130,240),(SCREEN_WIDTH//2+dx,210),3)

    @staticmethod
    def _hue_rgb(h):
        return _hue_rgb(h)
