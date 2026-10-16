#!/usr/bin/env python3
"""Compare two private PPU snapshots; output summarized changes only."""
import argparse,json
from pathlib import Path
from render_ppu_snapshot import load_snapshot,palette_color

def count_changed(a,b):
    return sum(x!=y for x,y in zip(a,b))

def compare(before,after):
    a,ar,am=before
    b,br,bm=after
    if len(a)!=16384 or len(b)!=16384:
        raise ValueError('Expected two 16KiB PPU snapshots')
    nt=[]
    for n in range(4):
        start=0x2000+n*1024
        va=a[start:start+1024]
        vb=b[start:start+1024]
        tile_positions=[i for i in range(960) if va[i]!=vb[i]]
        attr_count=count_changed(va[960:],vb[960:])
        bounds=({'left':min(i%32 for i in tile_positions),
                 'top':min(i//32 for i in tile_positions),
                 'right':max(i%32 for i in tile_positions),
                 'bottom':max(i//32 for i in tile_positions)}
                if tile_positions else None)
        nt.append({'nametable':n,'changed_tile_cells':len(tile_positions),
                   'changed_attribute_bytes':attr_count,
                   'tile_bbox':bounds})
    palette=[]
    for slot in range(32):
        # Universal background palette aliases should not count twice.
        if slot in (16,20,24,28):continue
        p,q=palette_color(a,slot),palette_color(b,slot)
        if p!=q:palette.append({'entry':slot,'old':p,'new':q})
    result={'frame_before':am.get('frame'),'frame_after':bm.get('frame'),
            'ppu_changed_bytes':count_changed(a,b),
            'mapped_chr_1k_changed_bytes':[
                count_changed(a[n*1024:(n+1)*1024],b[n*1024:(n+1)*1024])
                for n in range(8)],
            'nametables':nt,'palette_entries_changed':palette,
            'limitations':['Snapshot comparison, not scanline IRQ execution trace',
                           'Mirroring may duplicate nametable and palette entries']}
    if ar is not None and br is not None:
        if len(ar)!=2048 or len(br)!=2048:
            raise ValueError('Expected 2KiB CPU RAM captures')
        result['chr_register_ram_changes']=[
            {'register':n,'before':ar[0x3d+n],'after':br[0x3d+n]}
            for n in range(6) if ar[0x3d+n]!=br[0x3d+n]]
        result['queue_changed_bytes']=count_changed(ar[0x600:0x700],br[0x600:0x700])
        result['oam_dma_0700_changed_slots']=sum(
            ar[0x700+n*4:0x704+n*4]!=br[0x700+n*4:0x704+n*4]
            for n in range(64))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('before',type=Path)
    p.add_argument('after',type=Path)
    p.add_argument('--out',type=Path,default=None,
                   help='Ignored private JSON report path')
    a=p.parse_args()
    report=compare(load_snapshot(a.before),load_snapshot(a.after))
    text=json.dumps(report,indent=2)+'\n'
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(text,encoding='utf-8')
    print(text,end='')

if __name__=='__main__':main()
