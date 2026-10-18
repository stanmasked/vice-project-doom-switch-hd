#!/usr/bin/env python3
"""Stage136 independent sprite overflow and 8-slot selection source/model audit.

Static analysis of pinned upstream FCEUX and independent Python model only.
Does not claim native nine-OAM sprite XBuf evidence or original game proof.
"""
import argparse
from pathlib import Path


class OAMLimitError(ValueError):
    pass


ANCHORS=(
    'const int spriteHeight = Sprite16 ? 16 : 8;',
    'for (int i = 0; i < 64; i++) {',
    'uint8* spr = SPRAM + i * 4;',
    'if (yp >= spr[0] && yp < spr[0] + spriteHeight) {',
    'if (oamcount >= 8 && PPUON) {',
    'PPU_status |= 0x20;',
    'if (maxsprites == 8)',
    'break;',
    'oams[scanslot][oamcount][6] = (uint8)i;',
    'oamcount++;',
    'oamcounts[scanslot] = oamcount;',
)


def verify_source(source):
    if isinstance(source,bytes):
        source=source.decode('latin1')
    if not isinstance(source,str):
        raise OAMLimitError('Missing source text')
    start=ANCHORS[0]
    end=ANCHORS[-1]
    if source.count(start)!=1 or source.count(end)!=1:
        raise OAMLimitError('Ambiguous sprite evaluation boundaries')
    region=source[source.index(start):source.index(end)+len(end)]
    offsets=[]
    for anchor in ANCHORS:
        if region.count(anchor)!=1:
            raise OAMLimitError('Missing or duplicate OAM sprite source operation: '+anchor)
        offsets.append(region.index(anchor))
    if offsets!=sorted(offsets) or len(region)>2800:
        raise OAMLimitError('Unsupported sprite evaluation order')
    return {'native_source_selection_order':True,
            'source_overflow_status_bit':0x20,
            'native_nine_sprite_xbuf_proven':False,
            'original_game_oam_proven':False}


def sprite_scanline_model(oam_y,scanline,*,height=8,ppu_on=True):
    if (not isinstance(oam_y,(tuple,list)) or len(oam_y)!=64 or
            any(type(y) is not int or not 0<=y<=255 for y in oam_y) or
            type(scanline) is not int or not 0<=scanline<240 or
            type(height) is not int or height not in (8,16) or
            ppu_on is not True):
        raise OAMLimitError('Only pinned on-screen sprite-enabled eight-slot model')
    chosen=[]
    overflow=False
    for i,y in enumerate(oam_y):
        if y<=scanline<y+height:
            if len(chosen)>=8:
                overflow=True
                break
            chosen.append(i)
    return {'chosen_oam_indexes':tuple(chosen),
            'selected_count':len(chosen),
            'sprite_overflow_bit':overflow,
            'native_nine_sprite_xbuf_proven':False}


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('pinned_ppu_cpp',type=Path)
    args=cli.parse_args()
    verify_source(args.pinned_ppu_cpp.read_bytes())
    print('STAGE136_PINNED_OAM_EIGHT_LIMIT_SOURCE_PASS '
          'source_only=yes limit=8 overflow_bit=0x20 '
          'native_nine_sprite_xbuf_proven=no original_game_oam_proven=no')
