"""Mid-run perk selection — shown after every 5 completed levels."""

import math
import os
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

_IS_ANDROID = bool(os.environ.get('ANDROID_ROOT'))

# ── Perk catalogue ────────────────────────────────────────────────────────────
PERKS = [
    # id               name              desc line 1          desc line 2            colour            rarity
    ('rapid_core',   'RAPID CORE',    'Fire rate +30%',    'Stackable',           (255, 200,   0), 'common'),
    ('twin_cannon',  'TWIN CANNON',   'Fire extra side',   'bullets per shot',    (  0, 200, 255), 'rare'),
    ('void_shield',  'VOID SHIELD',   '+60 max shield',    '+2 regen/sec',        ( 80,  80, 255), 'common'),
    ('overdrive',    'OVERDRIVE',     'Move speed +40%',   'Stackable',           (  0, 255, 100), 'common'),
    ('life_surge',   'LIFE SURGE',    'Restore +50 HP',    'Instant heal',        (255,  60,  80), 'common'),
    ('chain_blast',  'CHAIN BLAST',   'Kills chain-',      'explode nearby',      (255, 120,   0), 'rare'),
    ('armor_plate',  'ARMOR PLATE',   '-25% damage',       'taken  Stackable',    (160, 160, 190), 'common'),
    ('phoenix_core', 'PHOENIX CORE',  'Auto-revive once',  'at 50% HP',           (255, 100,   0), 'legendary'),
    ('void_lance',   'VOID LANCE',    'All bullets',       'pierce enemies',      (180,   0, 255), 'rare'),
    ('coin_magnet',  'COIN MAGNET',   'Auto-collect',      'all coins',           (255, 215,   0), 'uncommon'),
    ('vital_core',   'VITAL CORE',    '+60 max HP',        '+60 current HP',      (255, 100, 100), 'uncommon'),
    ('lucky_shot',   'LUCKY SHOT',    '30% crit chance',   '= double damage',     (255,  50, 200), 'rare'),
    ('turbo_shot',   'TURBO SHOT',    'Bullet speed +50%', 'Stackable',           (  0, 240, 200), 'common'),
    ('gold_rush',    'GOLD RUSH',     'Coin value x1.5',   'Rest of run',         (255, 200,  40), 'uncommon'),
    ('bullet_storm', 'BULLET STORM',  '25% chance: fire',  'triple bullets',      (255,  80, 255), 'rare'),
]

PERK_DEFS = {p[0]: {'id':p[0],'name':p[1],'desc':[p[2],p[3]],'color':p[4],'rarity':p[5]}
             for p in PERKS}

RARITY_COLORS = {
    'common':    (120, 120, 145),
    'uncommon':  ( 50, 200,  60),
    'rare':      ( 60, 130, 255),
    'legendary': (255, 150,  20),
}

RARITY_WEIGHT = {'common': 5, 'uncommon': 3, 'rare': 2, 'legendary': 1}


def pick_3_perks(exclude_ids: list | None = None) -> list:
    exclude = set(exclude_ids or [])
    pool = [p for p in PERK_DEFS.values() if p['id'] not in exclude]
    chosen, used = [], set()
    for _ in range(3):
        available = [p for p in pool if p['id'] not in used]
        if not available:
            break
        w = [RARITY_WEIGHT.get(p['rarity'], 3) for p in available]
        total = sum(w)
        r = random.uniform(0, total)
        cumul = 0
        for p, wt in zip(available, w):
            cumul += wt
            if r <= cumul:
                chosen.append(p)
                used.add(p['id'])
                break
    # Guarantee at least one rare+ perk if none selected
    rarities = {p['rarity'] for p in chosen}
    if 'rare' not in rarities and 'legendary' not in rarities and len(chosen) == 3:
        # Swap last card for a random rare
        rares = [p for p in PERK_DEFS.values()
                 if p['rarity'] in ('rare', 'legendary') and p['id'] not in used]
        if rares:
            chosen[-1] = random.choice(rares)
    return chosen[:3]


# ── Screen ────────────────────────────────────────────────────────────────────
class PerkScreen:
    CW  = 310    # card width
    CH  = 255    # card height
    GAP = 25     # gap between cards

    def __init__(self):
        self._perks:   list = []
        self._tick:    int  = 0
        self._level_completed: int = 0
        self._history: list = []    # list of chosen perk dicts (for display strip)
        self._fonts_built = False

    # ── Public ────────────────────────────────────────────────────────────────
    def show(self, perks: list, level_completed: int = 0):
        self._perks = perks
        self._tick  = 0
        self._level_completed = level_completed

    def record_pick(self, perk: dict):
        self._history.append(perk)

    def handle_event(self, event) -> int:
        """Return 0-2 if a card was tapped/clicked, else -1."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._hit(event.pos)
        if event.type == pygame.FINGERDOWN:
            x = int(event.x * SCREEN_WIDTH)
            y = int(event.y * SCREEN_HEIGHT)
            return self._hit((x, y))
        return -1

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        self._tick += 1
        t = self._tick

        # ── Background dim ────────────────────────────────────────────────────
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        dim.fill((4, 6, 22))
        dim.set_alpha(200)
        surface.blit(dim, (0, 0))

        # ── Header ────────────────────────────────────────────────────────────
        pulse = 0.5 + 0.5 * math.sin(t * 0.10)
        if self._level_completed:
            lv_col = self._level_color(self._level_completed)
            hdr = self._f_title.render(f'LEVEL  {self._level_completed}  COMPLETE!', True, lv_col)
        else:
            hdr = self._f_title.render('UPGRADE AVAILABLE', True, (255, 210, 40))
        surface.blit(hdr, hdr.get_rect(centerx=SCREEN_WIDTH // 2, y=36))

        sub = self._f_sub.render(
            'Choose one upgrade  —  it lasts the entire run', True, (170, 175, 210))
        surface.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=86))

        # ── Perk history strip ─────────────────────────────────────────────────
        if self._history:
            self._draw_history(surface, 118)

        # ── Divider ───────────────────────────────────────────────────────────
        div_y = 140 if self._history else 116
        pygame.draw.line(surface, (45, 50, 80),
                         (SCREEN_WIDTH // 2 - 320, div_y),
                         (SCREEN_WIDTH // 2 + 320, div_y), 1)

        # ── Cards ─────────────────────────────────────────────────────────────
        mx, my = pygame.mouse.get_pos()
        for i, (perk, rect) in enumerate(zip(self._perks, self._card_rects())):
            # Staggered slide-in: card i waits i*6 extra frames
            delay  = i * 6
            local_t = max(0, t - delay)
            slide  = min(1.0, local_t / 18.0)
            ease   = 1.0 - (1.0 - slide) ** 3  # cubic ease-out
            y_off  = int((1.0 - ease) * 260)

            draw_rect = rect.move(0, y_off)
            hovered   = rect.collidepoint(mx, my) and not _IS_ANDROID
            self._draw_card(surface, draw_rect, perk, hovered, t, i)

        # ── Tap hint ──────────────────────────────────────────────────────────
        if _IS_ANDROID and t > 20:
            hint_a = min(255, (t - 20) * 12)
            ht = self._f_hint.render('TAP A CARD TO CHOOSE', True, (130, 130, 170))
            ht.set_alpha(hint_a)
            surface.blit(ht, ht.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    # ── Internal ──────────────────────────────────────────────────────────────
    def _card_rects(self):
        total_w = 3 * self.CW + 2 * self.GAP
        sx = (SCREEN_WIDTH - total_w) // 2
        cy = 158
        return [pygame.Rect(sx + i * (self.CW + self.GAP), cy, self.CW, self.CH)
                for i in range(3)]

    def _hit(self, pos) -> int:
        for i, r in enumerate(self._card_rects()):
            if r.inflate(10, 10).collidepoint(pos):
                return i
        return -1

    def _draw_card(self, surface, rect, perk, hovered, t, idx):
        col  = perk['color']
        rare = perk['rarity']
        rc   = RARITY_COLORS[rare]
        dim  = tuple(max(0, v - 120) for v in col)

        # Shadow layer
        sr = rect.inflate(4, 6).move(0, 4)
        pygame.draw.rect(surface, (0, 0, 0), sr, border_radius=16)

        # Outer glow when hovered (desktop)
        if hovered:
            gr = rect.inflate(10, 10)
            pygame.draw.rect(surface, dim, gr, border_radius=18)

        # Card body
        pygame.draw.rect(surface, (11, 13, 32), rect, border_radius=14)

        # Top colour stripe
        top_bar = pygame.Rect(rect.x + 2, rect.y, rect.w - 4, 5)
        pygame.draw.rect(surface, col, top_bar, border_radius=14)

        # Subtle inner highlight
        hi = pygame.Rect(rect.x + 3, rect.y + 7, rect.w - 6, 2)
        pygame.draw.rect(surface, tuple(min(255, v + 60) for v in col), hi)

        # Border — brighter & thicker on hover
        b_col = col if hovered else (50, 56, 80)
        b_w   = 2 if hovered else 1
        pygame.draw.rect(surface, b_col, rect, border_radius=14, width=b_w)

        # Rarity pill
        rw, rh = 84, 18
        rx = rect.centerx - rw // 2
        ry = rect.y + 12
        pygame.draw.rect(surface, tuple(v // 5 for v in rc), (rx, ry, rw, rh), border_radius=9)
        pygame.draw.rect(surface, rc, (rx, ry, rw, rh), border_radius=9, width=1)
        rt = self._f_rare.render(rare.upper(), True, rc)
        surface.blit(rt, rt.get_rect(center=(rect.centerx, ry + rh // 2)))

        # Icon
        icon_cy = rect.y + 100
        self._draw_icon(surface, rect.centerx, icon_cy, perk['id'], col, dim, hovered, t)

        # Perk name
        nt = self._f_name.render(perk['name'], True, (255, 255, 255))
        surface.blit(nt, nt.get_rect(centerx=rect.centerx, y=rect.y + 158))

        # Desc lines
        for j, line in enumerate(perk['desc']):
            dt = self._f_desc.render(line, True, (165, 190, 220))
            surface.blit(dt, dt.get_rect(centerx=rect.centerx, y=rect.y + 184 + j * 20))

    def _draw_icon(self, surface, cx, cy, pid, col, dim, hovered, t):
        r  = 30
        # Animated pulse on hover
        if hovered:
            pulse = int(3 * math.sin(t * 0.18))
            r += pulse
        pygame.draw.circle(surface, dim, (cx, cy), r + 6)
        pygame.draw.circle(surface, tuple(max(0, v - 60) for v in col), (cx, cy), r + 3)
        pygame.draw.circle(surface, col, (cx, cy), r, 3)

        if pid == 'rapid_core':
            pts = [(cx-8,cy-24),(cx+2,cy-4),(cx-5,cy-4),(cx+8,cy+24),(cx-2,cy+4),(cx+5,cy+4)]
            pygame.draw.polygon(surface, col, pts)
        elif pid == 'twin_cannon':
            for dx in (-11, 11):
                pygame.draw.rect(surface, col, (cx+dx-4, cy-20, 8, 32), border_radius=3)
                pygame.draw.circle(surface, col, (cx+dx, cy-20), 5)
        elif pid == 'void_shield':
            pygame.draw.arc(surface, col, (cx-22, cy-24, 44, 44), 0, math.pi, 4)
            pygame.draw.line(surface, col, (cx-22, cy-2), (cx+22, cy-2), 4)
            pygame.draw.line(surface, col, (cx-4, cy-2), (cx-4, cy+16), 3)
            pygame.draw.line(surface, col, (cx+4, cy-2), (cx+4, cy+16), 3)
        elif pid == 'overdrive':
            for dx in (-18, -9, 0, 9, 18):
                pygame.draw.line(surface, col, (cx+dx, cy+14), (cx+dx+7, cy-14), 3)
        elif pid == 'life_surge':
            pygame.draw.rect(surface, col, (cx-4, cy-20, 8, 40), border_radius=3)
            pygame.draw.rect(surface, col, (cx-18, cy-6, 36, 8), border_radius=3)
        elif pid == 'chain_blast':
            for deg in (0, 45, 90, 135, 180, 225, 270, 315):
                a  = math.radians(deg)
                x2 = cx + int(22 * math.cos(a))
                y2 = cy + int(22 * math.sin(a))
                pygame.draw.line(surface, col, (cx, cy), (x2, y2), 2)
            pygame.draw.circle(surface, col, (cx, cy), 10)
        elif pid == 'armor_plate':
            pts = [(cx, cy-24),(cx+20,cy-10),(cx+20,cy+10),(cx,cy+24),(cx-20,cy+10),(cx-20,cy-10)]
            pygame.draw.polygon(surface, col, pts, 4)
        elif pid == 'phoenix_core':
            for deg in range(0, 360, 45):
                a  = math.radians(deg)
                x2 = cx + int(24 * math.cos(a))
                y2 = cy + int(24 * math.sin(a))
                pygame.draw.line(surface, col, (cx, cy), (x2, y2), 3)
            pygame.draw.circle(surface, (255, 210, 60), (cx, cy), 10)
        elif pid == 'void_lance':
            pygame.draw.line(surface, col, (cx, cy-26), (cx, cy+26), 6)
            pygame.draw.polygon(surface, col, [(cx-12, cy-8),(cx+12, cy-8),(cx, cy-28)])
        elif pid == 'coin_magnet':
            pygame.draw.circle(surface, col, (cx, cy), 14, 4)
            pygame.draw.line(surface, col, (cx-11, cy-24), (cx-11, cy-4), 4)
            pygame.draw.line(surface, col, (cx+11, cy-24), (cx+11, cy-4), 4)
        elif pid == 'vital_core':
            pygame.draw.polygon(surface, col,
                [(cx-20,cy-8),(cx-8,cy-20),(cx,cy-14),(cx+8,cy-20),(cx+20,cy-8),(cx,cy+20)])
        elif pid == 'lucky_shot':
            for deg in range(0, 360, 60):
                a  = math.radians(deg)
                pygame.draw.line(surface, col,
                    (cx+int(12*math.cos(a)), cy+int(12*math.sin(a))),
                    (cx+int(26*math.cos(a)), cy+int(26*math.sin(a))), 3)
            pygame.draw.circle(surface, col, (cx, cy), 8)
        elif pid == 'turbo_shot':
            for i, dy in enumerate((-18, -8, 2)):
                w = 18 - i * 4
                pygame.draw.rect(surface, col, (cx - w//2, cy+dy, w, 6), border_radius=3)
        elif pid == 'gold_rush':
            pygame.draw.circle(surface, col, (cx, cy), 18, 4)
            pygame.draw.circle(surface, (255, 240, 100), (cx, cy), 9)
            gt = self._f_rare.render('$', True, (20, 10, 0))
            surface.blit(gt, gt.get_rect(center=(cx, cy)))
        elif pid == 'bullet_storm':
            for dx in (-14, 0, 14):
                pygame.draw.line(surface, col, (cx+dx, cy+18), (cx+dx, cy-20), 3)
                pygame.draw.polygon(surface, col,
                    [(cx+dx-5, cy-16), (cx+dx+5, cy-16), (cx+dx, cy-26)])
        else:
            pygame.draw.circle(surface, col, (cx, cy), 18)

    def _draw_history(self, surface, y):
        lbl = self._f_hint.render('ACTIVE PERKS:', True, (100, 105, 140))
        surface.blit(lbl, (SCREEN_WIDTH // 2 - 300, y + 2))
        for i, p in enumerate(self._history[-12:]):   # max 12 shown
            cx = SCREEN_WIDTH // 2 - 300 + 110 + i * 22
            pygame.draw.circle(surface, p['color'], (cx, y + 9), 7)
            pygame.draw.circle(surface, (255, 255, 255), (cx, y + 9), 7, 1)

    @staticmethod
    def _level_color(level: int) -> tuple:
        chapter = (level - 1) // 20 + 1
        colors = {1: (90, 200, 255), 2: (80, 255, 120), 3: (255, 160, 40),
                  4: (200, 80, 255), 5: (255, 60, 60)}
        return colors.get(chapter, (255, 220, 50))

    def _ensure_fonts(self):
        if self._fonts_built:
            return
        def sf(sz, bold=False):
            for n in ('segoeui', 'tahoma', 'arial', 'consolas'):
                try:
                    f = pygame.font.SysFont(n, sz, bold=bold)
                    if f:
                        return f
                except Exception:
                    pass
            return pygame.font.Font(None, sz)
        self._f_title = sf(36, bold=True)
        self._f_sub   = sf(17)
        self._f_name  = sf(22, bold=True)
        self._f_desc  = sf(15)
        self._f_rare  = sf(12, bold=True)
        self._f_hint  = sf(14)
        self._fonts_built = True
