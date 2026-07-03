"""Between-level upgrade shop — four tabs: Upgrades · Weapons · Trails · Allies."""

import math
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SHOP_UPGRADES, WEAPONS, WEAPON_ORDER,
    WHITE, GOLD, DARK_BLUE, UI_BG, UI_BORDER, UI_TEXT, UI_HIGHLIGHT,
    UI_BUTTON, UI_BUTTON_HOV, UI_SUCCESS, UI_DANGER
)
from trails import TRAIL_CATALOGUE, _hsv
from ally import ALLY_CONFIGS, ALLY_ORDER


def _upgrade_cost(upgrade: dict, current_level: int) -> int:
    return int(upgrade['base_cost'] * (upgrade['mult'] ** current_level))


class ShopItem:
    def __init__(self, rect: pygame.Rect, data: dict, lvl: int, coins: int,
                 is_weapon: bool = False, is_trail: bool = False):
        self.rect        = rect
        self.data        = data
        self.current_lvl = lvl
        self.can_afford  = False
        self.is_weapon   = is_weapon
        self.is_trail    = is_trail
        self.owned       = False
        self.active      = False
        self.hovered     = False

        if is_weapon or is_trail:
            self.cost  = data.get('cost', 0)
            self.maxed = False
        else:
            self.cost  = _upgrade_cost(data, lvl)
            self.maxed = (lvl >= data['max_lvl'])
        self.can_afford = coins >= self.cost and not self.maxed and not self.owned


class Shop:
    COLS     = 3
    ITEM_W   = 260
    ITEM_H   = 112
    MARGIN   = 16
    HEADER_H = 115
    FOOTER_H = 70

    def __init__(self, game):
        self.game      = game
        self._font_lg  = pygame.font.SysFont('consolas', 28, bold=True)
        self._font_md  = pygame.font.SysFont('consolas', 18, bold=True)
        self._font_sm  = pygame.font.SysFont('consolas', 14)
        self._font_xs  = pygame.font.SysFont('consolas', 12)
        self._items    : list[ShopItem] = []
        self._tab      = 'upgrades'
        self._ally_tab_pulse = 0
        self._tab_rects: dict[str, pygame.Rect] = {}
        self._notify   = ''
        self._notify_t = 0
        self._tick     = 0
        self._bg       = self._make_bg()

    # ── Public ────────────────────────────────────────────────────────────────
    def open(self):
        self._tick   = 0
        self._notify = ''
        self._rebuild_items()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = event.pos
            for name, r in self._tab_rects.items():
                if r.collidepoint(mp):
                    self._tab = name
                    self._rebuild_items()
                    self.game.audio.play('click')
                    return False
            if self._continue_rect.collidepoint(mp):
                self.game.audio.play('click')
                return True
            for item in self._items:
                if item.rect.collidepoint(mp):
                    if item.is_trail and item.owned:
                        self._equip_trail(item)
                    elif item.can_afford:
                        self._purchase(item)
                    return False
        return False

    def update(self):
        self._tick += 1
        mp = pygame.mouse.get_pos()
        for item in self._items:
            item.hovered = item.rect.collidepoint(mp)
        if self._notify_t > 0:
            self._notify_t -= 1

    def draw(self, surface: pygame.Surface):
        surface.blit(self._bg, (0, 0))
        self._draw_header(surface)
        self._draw_tabs(surface)
        self._draw_items(surface)
        self._draw_footer(surface)
        self._draw_notification(surface)

    # ── Private: background ───────────────────────────────────────────────────
    def _make_bg(self) -> pygame.Surface:
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            a = int(230 * (0.65 + 0.35 * t))
            pygame.draw.line(s, (4, 4, 24, a), (0, y), (SCREEN_WIDTH, y))
        return s

    # ── Private: rebuild ──────────────────────────────────────────────────────
    def _rebuild_items(self):
        self._items    = []
        coins          = self.game.save.get('current_coins', 0)
        unlocked_w     = self.game.save.get('unlocked_weapons', ['laser'])
        unlocked_t     = self.game.save.get('unlocked_trails', [])
        active_t       = self.game.save.get('active_trail')
        upgrades       = self.game.save.get('upgrades', {})

        cols   = self.COLS
        item_w = self.ITEM_W
        item_h = self.ITEM_H
        margin = self.MARGIN
        start_x = (SCREEN_WIDTH - (cols * item_w + (cols - 1) * margin)) // 2
        start_y = self.HEADER_H + 58

        if self._tab == 'upgrades':
            for idx, upg in enumerate(SHOP_UPGRADES):
                col = idx % cols;  row = idx // cols
                x   = start_x + col * (item_w + margin)
                y   = start_y + row * (item_h + margin)
                lvl = upgrades.get(upg['id'], 0)
                self._items.append(ShopItem(
                    pygame.Rect(x, y, item_w, item_h), upg, lvl, coins))

        elif self._tab == 'weapons':
            for idx, key in enumerate(WEAPON_ORDER):
                wpn = WEAPONS[key]
                col = idx % cols;  row = idx // cols
                x   = start_x + col * (item_w + margin)
                y   = start_y + row * (item_h + margin)
                item = ShopItem(
                    pygame.Rect(x, y, item_w, item_h), wpn, 0, coins, is_weapon=True)
                item.owned      = key in unlocked_w
                item.can_afford = (not item.owned) and coins >= wpn['cost']
                self._items.append(item)

        elif self._tab == 'trails':
            for idx, trail in enumerate(TRAIL_CATALOGUE):
                col = idx % cols;  row = idx // cols
                x   = start_x + col * (item_w + margin)
                y   = start_y + row * (item_h + margin)
                item = ShopItem(
                    pygame.Rect(x, y, item_w, item_h), trail, 0, coins, is_trail=True)
                item.owned      = trail['id'] in unlocked_t
                item.active     = (trail['id'] == active_t)
                item.can_afford = (not item.owned) and coins >= trail['cost']
                self._items.append(item)

        elif self._tab == 'allies':
            unlocked_a = self.game.save.get('unlocked_allies', [])
            for idx, key in enumerate(ALLY_ORDER):
                cfg = ALLY_CONFIGS[key]
                col = idx % cols;  row = idx // cols
                x   = start_x + col * (item_w + margin)
                y   = start_y + row * (item_h + margin)
                # Wrap ally config to match ShopItem expectations
                ally_data = {
                    'id':         key,
                    'name':       cfg['name'],
                    'desc':       cfg['desc'],
                    'cost':       cfg['cost'],
                    'color':      cfg['color'],
                    'description': cfg['desc'],
                }
                item = ShopItem(
                    pygame.Rect(x, y, item_w, item_h), ally_data, 0, coins, is_weapon=True)
                item.owned      = key in unlocked_a
                item.can_afford = (not item.owned) and coins >= cfg['cost']
                self._items.append(item)

        self._continue_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 135, SCREEN_HEIGHT - self.FOOTER_H + 10, 270, 48)

    # ── Private: purchase / equip ─────────────────────────────────────────────
    def _purchase(self, item: ShopItem):
        save = self.game.save

        if item.is_weapon:
            idx = self._items.index(item)
            if self._tab == 'allies':
                key = ALLY_ORDER[idx]
                if save.spend_coins(item.cost):
                    allies = save.data.setdefault('unlocked_allies', [])
                    if key not in allies:
                        allies.append(key)
                    self.game.audio.play('powerup')
                    self._notify = f'Ally recruited: {item.data["name"]}!'
                    self._notify_t = 140
                    # Spawn the ally immediately if in a game
                    if self.game.player:
                        from ally import Ally
                        slot = ALLY_ORDER.index(key)
                        a    = Ally(self.game, key, slot)
                        self.game.allies.add(a)
                        self.game.all_sprites.add(a)
                    self._rebuild_items()
            else:
                key = WEAPON_ORDER[idx]
                if save.spend_coins(item.cost):
                    save.unlock_weapon(key)
                    self.game.player.unlocked_weapons = list(save.get('unlocked_weapons'))
                    self.game.audio.play('powerup')
                    self._notify = f'Weapon unlocked: {item.data["name"]}!'
                    self._notify_t = 140
                    self._rebuild_items()

        elif item.is_trail:
            tid = item.data['id']
            if save.spend_coins(item.cost):
                save.unlock_trail(tid)
                save.set('active_trail', tid)
                if self.game.player:
                    self.game.player.trail.set_trail(tid)
                self.game.audio.play('powerup')
                self._notify = f'{item.data["name"]} purchased & equipped!'
                self._notify_t = 140
                self._rebuild_items()

        else:
            if save.spend_coins(item.cost):
                lvl = save.get_upgrade_level(item.data['id'])
                save.set_upgrade_level(item.data['id'], lvl + 1)
                self.game.player.refresh_upgrades()
                self.game.audio.play('powerup')
                self._notify = f'{item.data["name"]} upgraded to Lv {lvl + 1}!'
                self._notify_t = 140
                self._rebuild_items()

    def _equip_trail(self, item: ShopItem):
        save = self.game.save
        tid  = item.data['id']
        cur  = save.get('active_trail')
        if cur == tid:
            save.set('active_trail', None)
            if self.game.player:
                self.game.player.trail.set_trail(None)
            self._notify = 'Trail removed.'
        else:
            save.set('active_trail', tid)
            if self.game.player:
                self.game.player.trail.set_trail(tid)
            self._notify = f'{item.data["name"]} equipped!'
        self._notify_t = 110
        self._rebuild_items()

    # ── Private: draw ─────────────────────────────────────────────────────────
    def _draw_header(self, surface: pygame.Surface):
        t     = self._tick
        pulse = int(28 * math.sin(t * 0.05))
        col   = (min(255, 218 + pulse), min(255, 168 + pulse // 2), 0)
        title = self._font_lg.render('  UPGRADE SHOP  ', True, col)
        tr    = title.get_rect(centerx=SCREEN_WIDTH // 2, y=14)
        pygame.draw.line(surface, (80, 55, 0),
                         (tr.left - 18, tr.bottom + 3),
                         (tr.right + 18, tr.bottom + 3), 3)
        pygame.draw.line(surface, col,
                         (tr.left - 18, tr.bottom + 3),
                         (tr.right + 18, tr.bottom + 3), 1)
        surface.blit(title, tr)

        coins = self.game.save.get('current_coins', 0)
        ctxt  = self._font_md.render(f'  {coins:,} coins', True, GOLD)
        surface.blit(ctxt, ctxt.get_rect(centerx=SCREEN_WIDTH // 2, y=52))

        lvl  = self.game.current_level
        ltxt = self._font_sm.render(
            f'Level {lvl} complete!   Preparing Level {lvl + 1}...', True, (155, 155, 220))
        surface.blit(ltxt, ltxt.get_rect(centerx=SCREEN_WIDTH // 2, y=84))

    def _draw_tabs(self, surface: pygame.Surface):
        tabs  = [('upgrades', 'Upgrades'), ('weapons', 'Weapons'),
                 ('trails', 'Trails'), ('allies', 'Allies')]
        tw    = 162
        gap   = 8
        total = len(tabs) * tw + (len(tabs) - 1) * gap
        tx    = (SCREEN_WIDTH - total) // 2
        ty    = self.HEADER_H + 6
        self._tab_rects = {}

        for name, label in tabs:
            r      = pygame.Rect(tx, ty, tw, 40)
            active = (name == self._tab)

            if name == 'allies' and not active:
                bg_col = (40, 15, 65)
                bd_col = (120, 50, 200)
            else:
                bg_col = (48, 85, 155) if active else (18, 28, 58)
                bd_col = (100, 155, 255) if active else (45, 65, 115)

            pygame.draw.rect(surface, bg_col, r, border_radius=7)
            pygame.draw.rect(surface, bd_col, r, border_radius=7, width=2)

            if name == 'allies' and not active:
                tc = (200, 130, 255)
            else:
                tc = (220, 220, 255) if active else (100, 115, 175)
            txt = self._font_md.render(label, True, tc)
            surface.blit(txt, txt.get_rect(center=r.center))

            # Badge hints
            if name == 'trails':
                owned_count = len(self.game.save.get('unlocked_trails', []))
                if owned_count < len(TRAIL_CATALOGUE):
                    badge = self._font_xs.render('BUY', True, (255, 220, 40))
                    surface.blit(badge, (r.right - 32, r.top + 5))
            elif name == 'allies':
                owned_a = len(self.game.save.get('unlocked_allies', []))
                if owned_a < len(ALLY_ORDER):
                    badge = self._font_xs.render('NEW', True, (180, 80, 255))
                    surface.blit(badge, (r.right - 34, r.top + 5))

            self._tab_rects[name] = r
            tx += tw + gap

    def _draw_items(self, surface: pygame.Surface):
        for item in self._items:
            self._draw_item(surface, item)

    def _draw_item(self, surface: pygame.Surface, item: ShopItem):
        r    = item.rect
        data = item.data
        t    = self._tick

        if item.is_trail and item.active:
            bg = (8, 42, 26)
        elif item.owned or item.maxed:
            bg = (14, 36, 16)
        elif item.hovered and item.can_afford:
            bg = (32, 52, 98)
        elif not item.can_afford:
            bg = (26, 16, 16)
        else:
            bg = (16, 26, 50)

        # Draw item card background — solid rect avoids per-item SRCALPHA on Android
        from settings import IS_ANDROID as _IS_AND
        if _IS_AND:
            pygame.draw.rect(surface, bg, r, border_radius=8)
        else:
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            s.fill((*bg, 218))
            if item.hovered and item.can_afford:
                sa = int(18 * math.sin(t * 0.13) + 18)
                s.fill((255, 255, 255, sa), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(s, r.topleft)

        if item.is_trail and item.active:
            bc = (60, 240, 100)
        elif item.owned or item.maxed:
            bc = (35, 170, 35)
        elif item.can_afford:
            bc = (75, 115, 215)
        else:
            bc = (65, 32, 32)
        pygame.draw.rect(surface, bc, r, border_radius=8, width=2)

        # Colour stripe
        icon_col = data.get('color')
        if icon_col is None:
            for yi in range(r.height - 8):
                hue = int(360 * yi / (r.height - 8))
                rc2, gc2, bc2 = _hsv(hue)
                pygame.draw.line(surface, (rc2, gc2, bc2),
                                 (r.x + 1, r.y + 4 + yi),
                                 (r.x + 5, r.y + 4 + yi))
        else:
            pygame.draw.rect(surface, icon_col,
                             (r.x + 1, r.y + 4, 5, r.height - 8), border_radius=3)

        # Name
        surface.blit(
            self._font_md.render(data.get('name', '?'), True, WHITE),
            (r.x + 14, r.y + 10))

        # Description
        desc = data.get('desc') or data.get('description', '')
        surface.blit(
            self._font_xs.render(desc, True, (165, 165, 205)),
            (r.x + 14, r.y + 34))

        # Upgrade pips
        if not item.is_weapon and not item.is_trail:
            lvl_txt = f'Lv {item.current_lvl} / {data["max_lvl"]}'
            surface.blit(
                self._font_xs.render(lvl_txt, True, (110, 190, 110)),
                (r.x + 14, r.y + 54))
            pip_total = data['max_lvl']
            pip_w     = max(4, (r.width - 80) // max(pip_total, 1))
            for i in range(pip_total):
                pc = (55, 155, 55) if i < item.current_lvl else (35, 35, 55)
                pygame.draw.rect(surface, pc,
                                 (r.x + 14 + i * (pip_w + 2),
                                  r.y + 73, pip_w, 6), border_radius=2)

        if item.is_trail:
            if item.active:
                surface.blit(
                    self._font_xs.render('EQUIPPED  (tap to remove)', True, (80, 250, 110)),
                    (r.x + 14, r.y + 56))
            elif item.owned:
                surface.blit(
                    self._font_xs.render('Owned  -  tap to equip', True, (150, 195, 150)),
                    (r.x + 14, r.y + 56))

        # Status / cost
        if item.owned or item.maxed:
            lbl = 'EQUIPPED' if (item.is_trail and item.active) else \
                  ('OWNED' if item.owned else 'MAXED')
            st  = self._font_sm.render(lbl, True, (75, 215, 75))
            surface.blit(st, st.get_rect(bottomright=(r.right - 10, r.bottom - 8)))
        else:
            cc = UI_SUCCESS if item.can_afford else UI_DANGER
            ct = self._font_sm.render(f'  {item.cost:,}', True, cc)
            surface.blit(ct, ct.get_rect(bottomright=(r.right - 10, r.bottom - 8)))

    def _draw_footer(self, surface: pygame.Surface):
        r   = self._continue_rect
        t   = self._tick
        mp  = pygame.mouse.get_pos()
        hov = r.collidepoint(mp)
        p   = int(18 * math.sin(t * 0.08))
        col = (55 + p, 165 + p, 55 + p) if hov else (28, 120, 28)
        pygame.draw.rect(surface, col, r, border_radius=10)
        pygame.draw.rect(surface,
                         (110, 255, 110) if hov else (55, 175, 55),
                         r, border_radius=10, width=2)
        txt = self._font_md.render('CONTINUE  TO NEXT LEVEL', True, WHITE)
        surface.blit(txt, txt.get_rect(center=r.center))

    def _draw_notification(self, surface: pygame.Surface):
        if not self._notify or self._notify_t <= 0:
            return
        alpha = min(255, self._notify_t * 4)
        w     = max(420, len(self._notify) * 11 + 50)
        s     = pygame.Surface((w, 44), pygame.SRCALPHA)
        s.fill((0, 155, 65, int(alpha * 0.88)))
        pygame.draw.rect(s, (80, 255, 120, alpha // 2), s.get_rect(),
                         border_radius=8, width=1)
        txt = self._font_md.render(self._notify, True, (255, 255, 255))
        s.blit(txt, txt.get_rect(center=(w // 2, 22)))
        s.set_alpha(alpha)
        surface.blit(s, s.get_rect(centerx=SCREEN_WIDTH // 2,
                                    y=SCREEN_HEIGHT - 136))
