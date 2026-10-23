#!/usr/bin/env python3
"""Source-free, deterministic NTSC NES PPU Loopy-scroll dot transitions.

This is a reference *model*, NOT observation of the owner's original game.
Keep `v` unknown for real captures until an independent PPU-dot witness exists.
Only writes to $2000/$2001/$2005/$2006 and $2002 reads are represented;
$2007 accesses, rendering fetch bytes, palette/sprite/CHR and odd-frame
skipped dot are outside scope. Do not infer effective rendered scroll from
CPU register-bus traces alone.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PPUScroll:
    v: int = 0
    t: int = 0
    x: int = 0
    w: int = 0
    ctrl: int = 0
    mask: int = 0

    def __post_init__(self):
        if any(type(a) is not int for a in (self.v, self.t, self.x, self.w, self.ctrl, self.mask)):
            raise ValueError('PPU register snapshot must contain integers')
        if not (0 <= self.v <= 0x7fff and 0 <= self.t <= 0x7fff and
                0 <= self.x <= 7 and self.w in (0, 1) and
                0 <= self.ctrl <= 0xff and 0 <= self.mask <= 0xff):
            raise ValueError('PPU register snapshot outside hardware ranges')

    @property
    def rendering_enabled(self) -> bool:
        return bool(self.mask & 0x18)

    @staticmethod
    def _byte(d: int) -> int:
        if type(d) is not int or not 0 <= d <= 0xff:
            raise ValueError('PPU bus value must be one byte')
        return d

    def write2000(self, d: int):
        d = self._byte(d)
        self.ctrl = d
        self.t = (self.t & 0x73ff) | ((d & 0x03) << 10)

    def write2001(self, d: int):
        self.mask = self._byte(d)

    def read2002(self):
        self.w = 0

    def write2005(self, d: int):
        d = self._byte(d)
        if self.w == 0:
            self.t = (self.t & 0x7fe0) | (d >> 3)
            self.x = d & 7
            self.w = 1
        else:
            self.t = (self.t & 0x0c1f) | ((d & 0xf8) << 2) | ((d & 7) << 12)
            self.w = 0

    def write2006(self, d: int):
        d = self._byte(d)
        if self.w == 0:
            self.t = (self.t & 0x00ff) | ((d & 0x3f) << 8)
            self.w = 1
        else:
            self.t = (self.t & 0x7f00) | d
            self.v = self.t
            self.w = 0

    def increment_x(self):
        if (self.v & 0x1f) == 31:
            self.v = (self.v & 0x7fe0) ^ 0x0400
        else:
            self.v += 1

    def increment_y(self):
        if (self.v & 0x7000) != 0x7000:
            self.v += 0x1000
            return
        self.v &= 0x0fff
        coarse_y = (self.v & 0x03e0) >> 5
        if coarse_y == 29:
            coarse_y = 0
            self.v ^= 0x0800
        elif coarse_y == 31:
            coarse_y = 0
        else:
            coarse_y += 1
        self.v = (self.v & 0x7c1f) | (coarse_y << 5)

    def reload_horizontal(self):
        self.v = (self.v & 0x7be0) | (self.t & 0x041f)

    def reload_vertical(self):
        self.v = (self.v & 0x041f) | (self.t & 0x7be0)

    def dot(self, scanline: int, dot: int) -> tuple[str, ...]:
        """Apply dot-scheduled Loopy v updates; returns transition labels.

        Scanline -1 represents NTSC pre-render; 0..239 are visible. CPU
        actions at a PPU dot must be ordered separately by a real witness.
        The PPU odd-frame skipped dot is deliberately NOT synthesized here.
        """
        if type(scanline) is not int or type(dot) is not int or not (-1 <= scanline <= 260) or not (0 <= dot <= 340):
            raise ValueError('invalid NTSC PPU scanline/dot')
        if not self.rendering_enabled or not (scanline == -1 or 0 <= scanline <= 239):
            return ()
        operations: list[str] = []
        # Background fetch tile boundaries, including the two prefetch tiles.
        if dot % 8 == 0 and ((8 <= dot <= 256) or dot in (328, 336)):
            self.increment_x()
            operations.append('increment_x')
        if dot == 256:
            self.increment_y()
            operations.append('increment_y')
        if dot == 257:
            self.reload_horizontal()
            operations.append('reload_horizontal')
        if scanline == -1 and 280 <= dot <= 304:
            self.reload_vertical()
            operations.append('reload_vertical')
        return tuple(operations)

    def snap(self) -> tuple[int, int, int, int, int, int]:
        return self.v, self.t, self.x, self.w, self.ctrl, self.mask
