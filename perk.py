"""Mid-run perk selection — roguelite upgrade screen shown every 15 kills."""

import math
import os
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT

_IS_ANDROID = bool(os.environ.get('ANDROID_ROOT'))

PERKS = [
    {'id': 'rapid_core',   'name': 'RAPID CORE',    'desc': ['Fire rate +30%',      'Stackable'],          'color': (255, 200,   0), 'rarity': 'common'},
    {'id': 'twin_cannon',  'name': 'TWIN CANNON',   'desc': ['Fire 2 bullets',      'per shot'],           'color': (  0, 200, 255), 'rarity': 'rare'},
    {'id': 'void_shield',  'name': 'VOID SHIELD',   'desc': ['+60 max shield',      '+2 regen / sec'],     'color': ( 80,  80, 255), 'rarity': 'common'},
    {'id': 'overdrive',    'name': 'OVERDRIVE',     'desc': ['Move speed +40%',     'Stackable'],          'color': (  0, 255, 100), 'rarity': 'common'},
    {'id': 'life_surge',   'name': 'LIFE SURGE',    'desc': ['Restore +50 HP',      'Instant'],            'color': (255,  60,  80), 'rarity': 'common'},
    {'id': 'chain_blast',  'name': 'CHAIN BLAST',   'desc': ['Kills chain-explode', 'nearby enemies'],     'color': (255, 120,   0), 'rarity': 'rare'},
    {'id': 'armor_plate',  'name': 'ARMOR PLATE',   'desc': ['-25% damage taken',   'Stackable'],          'color': (160, 160, 190), 'rarity': 'common'},
    {'id': 'phoenix_core', 'name': 'PHOENIX CORE',  'desc': ['Auto-revive once',    'at 50% HP'],          'color': (255, 100,   0), 'rarity': 'legendary'},
    {'id': 'void_lance',   'name': 'VOID LANCE',    'desc': ['Bullets pierce',      'all enemies'],        'color': (180,   0, 255), 'rarity': 'rare'},
    {'id': 'coin_magnet',  'name': 'COIN MAGNET',   'desc': ['Auto-collect coins',  'large radius'],       'color': (255, 215,   0), 'rarity': 'uncommon'},
    {'id': 'vital_core',   'name': 'VITAL CORE',    'desc': ['+60 max HP',          '+60 current HP'],     'color': (255, 100, 100), 'rarity': 'uncommon'},
    {'id': 'lucky_shot',   'name': 'LUCKY SHOT',    'desc': ['30% crit chance',     '= double damage'],    'color': (255,  50, 200), 'rarity': 'rare'},
]

RARITY_COLORS = {
    'common':    (120, 120, 140),
    'uncommon':  ( 50, 200,  50),
    'rare':      ( 50, 120, 255),
    'legendary': (255, 150,  20),
}


def pick_3_perks():
    weights = {'common': 5, 'uncommon': 3, 'rare': 2, 'legendary': 1}
    pool = list(PERKS)
    chosen, used = [], set()
    for _ in range(3):
        available = [p for p in pool if p['id'] not in used]
        if not available:
            break
        w = [weights.get(p['rarity'], 3) for p in available]
        total = sum(w)
        r = random.uniform(0, total)
        cumul = 0
        for p, wt in zip(available, w):
            cumul += wt
            if r <= cumul:
                chosen.append(p)
                used.add(p['id'])
                break
    return chosen[:3]


class PerkScreen:
    CW = 320
    CH = 240
    GAP = 22

    def __init__(self):
        self._perks: list = []
        self._tick = 0
        self._fonts_built = False

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
        self._f_title = sf(34, bold=True)
        self._f_sub   = sf(18)
        self._f_name  = sf(21, bold=True)
        self._f_desc  = sf(15)
        self._f_rare  = sf(12, bold=True)
        self._fonts_built = True

    def show(self, perks: list):
        self._perks = perks
        self._tick  = 0

    def handle_event(self, event) -> int:
        """Return index 0-2 if a card was chosen, else -1."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._hit(event.pos)
        if event.type == pygame.FINGERDOWN:
            x = int(event.x * SCREEN_WIDTH)
            y = int(event.y * SCREEN_HEIGHT)
            return self._hit((x, y))
        return -1

    def _card_rects(self):
        total_w = 3 * self.CW + 2 * self.GAP
        sx = (SCREEN_WIDTH - total_w) // 2
        cy = SCREEN_HEIGHT // 2 - self.CH // 2 + 20
        return [pygame.Rect(sx + i * (self.CW + self.GAP), cy, self.CW, self.CH)
                for i in range(3)]

    def _hit(self, pos) -> int:
        for i, r in enumerate(self._card_rects()):
            if r.collidepoint(pos):
                return i
        return -1

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        self._tick += 1
        t = self._tick

        # Semi-transparent overlay (solid surface for Android performance)
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        dim.fill((0, 0, 10))
        dim.set_alpha(190)
        surface.blit(dim, (0, 0))

        # Animated title
        pulse = int(15 * abs(math.sin(t * 0.08)))
        col   = (255, 220 + pulse, 40)
        ttxt  = self._f_title.render('CHOOSE YOUR UPGRADE', True, col)
        surface.blit(ttxt, ttxt.get_rect(centerx=SCREEN_WIDTH // 2, y=60))

        stxt = self._f_sub.render('Tap a card  —  chosen power lasts the entire run', True, (160, 160, 200))
        surface.blit(stxt, stxt.get_rect(centerx=SCREEN_WIDTH // 2, y=104))

        # Divider
        pygame.draw.line(surface, (60, 60, 90),
                         (SCREEN_WIDTH // 2 - 300, 128),
                         (SCREEN_WIDTH // 2 + 300, 128), 1)

        # Cards
        mx, my = pygame.mouse.get_pos()
        for i, (perk, rect) in enumerate(zip(self._perks, self._card_rects())):
            hovered = rect.collidepoint(mx, my)
            self._draw_card(surface, rect, perk, hovered, t)

    def _draw_card(self, surface, rect, perk, hovered, t):
        col  = perk['color']
        rare = perk['rarity']
        rc   = RARITY_COLORS[rare]

        # Outer glow when hovered
        if hovered:
            gr = rect.inflate(10, 10)
            pygame.draw.rect(surface, tuple(v // 3 for v in col), gr, border_radius=18)

        # Card body
        pygame.draw.rect(surface, (10, 12, 30), rect, border_radius=14)

        # Top colour bar
        pygame.draw.rect(surface, col,
                         pygame.Rect(rect.x, rect.y, rect.width, 5), border_radius=14)

        # Border
        border_col = col if hovered else (50, 55, 75)
        pygame.draw.rect(surface, border_col, rect, border_radius=14, width=2 if hovered else 1)

        # Rarity badge
        rt = self._f_rare.render(rare.upper(), True, rc)
        surface.blit(rt, rt.get_rect(centerx=rect.centerx, y=rect.y + 10))

        # Icon
        self._draw_icon(surface, rect.centerx, rect.y + 90, perk['id'], col)

        # Perk name
        nt = self._f_name.render(perk['name'], True, (255, 255, 255))
        surface.blit(nt, nt.get_rect(centerx=rect.centerx, y=rect.y + 148))

        # Description lines
        for j, line in enumerate(perk['desc']):
            dt = self._f_desc.render(line, True, (170, 190, 220))
            surface.blit(dt, dt.get_rect(centerx=rect.centerx, y=rect.y + 174 + j * 19))

    def _draw_icon(self, surface, cx, cy, perk_id, col):
        r  = 30
        bg = tuple(max(0, v - 110) for v in col)
        pygame.draw.circle(surface, bg,  (cx, cy), r + 5)
        pygame.draw.circle(surface, col, (cx, cy), r, 3)

        if perk_id == 'rapid_core':
            pts = [(cx - 8, cy - 24), (cx + 2, cy - 4), (cx - 5, cy - 4),
                   (cx + 8, cy + 24), (cx - 2, cy + 4), (cx + 5, cy + 4)]
            pygame.draw.polygon(surface, col, pts)
        elif perk_id == 'twin_cannon':
            for dx in (-10, 10):
                pygame.draw.rect(surface, col, (cx + dx - 4, cy - 20, 8, 30), border_radius=3)
                pygame.draw.circle(surface, col, (cx + dx, cy - 20), 5)
        elif perk_id == 'void_shield':
            pygame.draw.arc(surface, col, (cx - 22, cy - 24, 44, 44), 0, math.pi, 4)
            pygame.draw.line(surface, col, (cx - 22, cy - 2), (cx + 22, cy - 2), 4)
            pygame.draw.line(surface, col, (cx - 4, cy - 2), (cx - 4, cy + 16), 3)
            pygame.draw.line(surface, col, (cx + 4, cy - 2), (cx + 4, cy + 16), 3)
        elif perk_id == 'overdrive':
            for i, dx in enumerate((-18, -9, 0, 9, 18)):
                pygame.draw.line(surface, col, (cx + dx, cy + 14), (cx + dx + 7, cy - 14), 3)
        elif perk_id == 'life_surge':
            pygame.draw.rect(surface, col, (cx - 4, cy - 20, 8, 40), border_radius=3)
            pygame.draw.rect(surface, col, (cx - 18, cy - 6, 36, 8),  border_radius=3)
        elif perk_id == 'chain_blast':
            for deg in (0, 45, 90, 135, 180, 225, 270, 315):
                a  = math.radians(deg)
                x2 = cx + int(22 * math.cos(a))
                y2 = cy + int(22 * math.sin(a))
                pygame.draw.line(surface, col, (cx, cy), (x2, y2), 2)
            pygame.draw.circle(surface, col, (cx, cy), 10)
        elif perk_id == 'armor_plate':
            pts = [(cx,     cy - 24), (cx + 20, cy - 10), (cx + 20, cy + 10),
                   (cx,     cy + 24), (cx - 20, cy + 10), (cx - 20, cy - 10)]
            pygame.draw.polygon(surface, col, pts, 4)
        elif perk_id == 'phoenix_core':
            for deg in range(0, 360, 45):
                a  = math.radians(deg)
                x2 = cx + int(24 * math.cos(a))
                y2 = cy + int(24 * math.sin(a))
                pygame.draw.line(surface, col, (cx, cy), (x2, y2), 3)
            pygame.draw.circle(surface, (255, 210, 60), (cx, cy), 10)
        elif perk_id == 'void_lance':
            pygame.draw.line(surface, col, (cx, cy - 26), (cx, cy + 26), 6)
            pygame.draw.polygon(surface, col,
                                [(cx - 12, cy - 8), (cx + 12, cy - 8), (cx, cy - 28)])
        elif perk_id == 'coin_magnet':
            pygame.draw.circle(surface, col, (cx, cy), 16, 4)
            pygame.draw.line(surface, col, (cx - 11, cy - 24), (cx - 11, cy - 4), 4)
            pygame.draw.line(surface, col, (cx + 11, cy - 24), (cx + 11, cy - 4), 4)
        elif perk_id == 'vital_core':
            pygame.draw.polygon(surface, col,
                [(cx - 20, cy - 8), (cx - 8, cy - 20), (cx, cy - 14),
                 (cx + 8, cy - 20), (cx + 20, cy - 8), (cx, cy + 20)])
        elif perk_id == 'lucky_shot':
            for deg in range(0, 360, 60):
                a  = math.radians(deg)
                pygame.draw.line(surface, col,
                                 (cx + int(12 * math.cos(a)), cy + int(12 * math.sin(a))),
                                 (cx + int(26 * math.cos(a)), cy + int(26 * math.sin(a))), 3)
            pygame.draw.circle(surface, col, (cx, cy), 8)
        else:
            pygame.draw.circle(surface, col, (cx, cy), 18)
