"""Entry point for Alien Invasion."""

import sys

# ── Windows DPI blurriness fix ────────────────────────────────────────────────
# Must happen BEFORE pygame.init() — tells Windows not to blur-scale the window
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI-aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import pygame
from game import Game


def _patch_sysfont():
    """Make SysFont safe on Android where system fonts may be missing."""
    _orig = pygame.font.SysFont
    def _safe(name, size, bold=False, italic=False):
        try:
            f = _orig(name, size, bold=bold, italic=italic)
            if f:
                return f
        except Exception:
            pass
        return pygame.font.Font(None, max(8, size))
    pygame.font.SysFont = _safe


def main():
    pygame.init()
    _patch_sysfont()
    game = Game()
    game.run()


if __name__ == '__main__':
    main()
