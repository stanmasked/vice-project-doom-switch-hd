"""Bounded static 2x2 NES nametable scroll model; not a PPU emulator.

Operates on already-mapped 16KiB PPU snapshots. Does not infer scroll from
frame-number-only register logs, simulate MMC3 midframe bank switches,
or reconstruct rendering with raster IRQ/split scroll.
"""
from render_ppu_snapshot import bg_pixel

WIDTH, HEIGHT = 256, 240


def resolve_pixel(nametable, screen_x, screen_y, scroll_x=0, scroll_y=0):
    """Map onscreen pixel to one of four nametables and local coordinates.

    Common NES setup: PPUCTRL selects top-left nametable; PPUSCROLL sets
    X=0..255 and Y=0..239. Y=240..255 would fetch attribute memory as
    tiles and is intentionally rejected until the PPU model supports it.
    """
    if nametable not in (0,1,2,3):
        raise ValueError('Nametable must be 0..3')
    if not (0<=screen_x<WIDTH and 0<=screen_y<HEIGHT):
        raise ValueError('Screen pixel outside 256x240')
    if not (0<=scroll_x<=255 and 0<=scroll_y<=239):
        raise ValueError('Scroll requires X=0..255 and Y=0..239 (normal NES mode)')
    across=scroll_x+screen_x
    down=scroll_y+screen_y
    table=nametable ^ ((across//WIDTH)&1) ^ (((down//HEIGHT)&1)<<1)
    return table,across%WIDTH,down%HEIGHT


def scroll_background_pixel(ppu,nametable,x,y,pattern_base,
                            scroll_x=0,scroll_y=0):
    table,local_x,local_y=resolve_pixel(nametable,x,y,scroll_x,scroll_y)
    return bg_pixel(ppu,table,local_x,local_y,pattern_base)


def opaque_background_pixel(ppu,nametable,x,y,pattern_base,
                            scroll_x=0,scroll_y=0):
    """2bpp background value; zero is transparent for sprite priority."""
    table,px,py=resolve_pixel(nametable,x,y,scroll_x,scroll_y)
    if len(ppu)!=0x4000:
        raise ValueError('PPU snapshot must be 16KiB')
    if pattern_base not in (0,0x1000):
        raise ValueError('Pattern base must be 0 or 0x1000')
    tile=ppu[0x2000+table*0x400+(py//8)*32+(px//8)]
    offset=pattern_base+tile*16+(py%8)
    bit=7-(px%8)
    return ((ppu[offset]>>bit)&1)|(((ppu[offset+8]>>bit)&1)<<1)
