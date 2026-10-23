#!/usr/bin/env python3
"""Stage340: opt-in diagnostics for the *pinned* classic FCEUX 2.6.5 PPU.

The instrumented source is for a private local build, not a GitHub vendored file.
Neither a modified source file nor unit tests constitute an original-game trace.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

UPSTREAM_BLOB = 'aa7502eb956595c29096856ab8beddb5eecc301b'
MAX_INPUT = 250_000

HOOK = r'''// BEGIN VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS (opt-in)
#ifdef VPD_STAGE340_DIAGNOSTICS
extern int newppu;
static unsigned long vpd340_core_frame = 0;
static unsigned long vpd340_count = 0;
static unsigned long vpd340_start = 380;
static unsigned long vpd340_end = 640;
static bool vpd340_opened = false;
static bool vpd340_truncated = false;
static FILE *vpd340_file = 0;
static bool vpd340_parse_ulong(const char *v, unsigned long *out) {
  if (!v || !*v) return false;
  unsigned long x = 0;
  for (const char *p=v; *p; ++p) {
    if (*p<'0' || *p>'9' || x>100000UL) return false;
    x = 10*x + (unsigned long)(*p-'0');
  }
  if (x>100000UL) return false;
  *out=x;
  return true;
}
static void vpd340_emit(const char *event, int renderer_pixel) {
  if (newppu) return;
  if (!vpd340_opened) {
    vpd340_opened=true;
    const char *path=std::getenv("VPD_STAGE340_TRACE_FILE");
    if (!path || path[0]!='/') return; // no default or relative file
    const char *start=std::getenv("VPD_STAGE340_MIN_CORE_FRAME");
    const char *end=std::getenv("VPD_STAGE340_MAX_CORE_FRAME");
    if ((start && !vpd340_parse_ulong(start,&vpd340_start)) ||
        (end && !vpd340_parse_ulong(end,&vpd340_end)) ||
        vpd340_start>vpd340_end || vpd340_end-vpd340_start>1000UL) return;
    // 'x' is an exclusive create on Linux. Do not overwrite any earlier trace.
    vpd340_file=std::fopen(path,"wx");
    if (!vpd340_file) return;
    std::fprintf(vpd340_file,"core_frame_ordinal\tcpu_timestamp\tevent\tlegacy_scanline\trenderer_pixel_not_dot\trefresh_addr\ttemp_addr\twrite_toggle\tfine_x\tppu_mask\n");
  }
  if (!vpd340_file || vpd340_truncated ||
      vpd340_core_frame<vpd340_start || vpd340_core_frame>vpd340_end) return;
  if (vpd340_count>=500000UL) {
    std::fprintf(vpd340_file,"VPD_STAGE340_TRUNCATED\n");
    std::fflush(vpd340_file);
    vpd340_truncated=true;
    return;
  }
  std::fprintf(vpd340_file,"%lu\t%u\t%s\t%d\t%d\t%04x\t%04x\t%u\t%u\t%u\n",
               vpd340_core_frame,(unsigned int)timestamp,event,scanline,renderer_pixel,
               (unsigned int)(RefreshAddr & 0x7fff),(unsigned int)(TempAddr & 0x7fff),
               (unsigned int)vtoggle,(unsigned int)XOffset,(unsigned int)PPU[1]);
  ++vpd340_count;
  if ((vpd340_count & 1023UL)==0) std::fflush(vpd340_file);
}
static void vpd340_frame_enter(void) { ++vpd340_core_frame; vpd340_emit("core_frame_start",-1); }
#else
static inline void vpd340_emit(const char *,int) {}
static inline void vpd340_frame_enter(void) {}
#endif
// END VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS
'''


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def only_once(source: str, anchor: str, replacement: str) -> str:
    if source.count(anchor) != 1:
        raise ValueError('Stage340 source anchor absent or ambiguous')
    return source.replace(anchor,replacement,1)


def within(source: str, beginning: str, end: str, original: str, replacement: str) -> str:
    begin=source.find(beginning)
    last=source.find(end,begin+len(beginning))
    if begin==-1 or last==-1 or begin>=last:
        raise ValueError('Stage340 source function layout changed')
    chunk=source[begin:last]
    changed=only_once(chunk,original,replacement)
    return source[:begin]+changed+source[last:]


def patch(source: bytes, *, expected_blob: str=UPSTREAM_BLOB) -> bytes:
    if len(source)<1000 or len(source)>MAX_INPUT or git_blob(source)!=expected_blob:
        raise ValueError('source is not the pristine, pinned FCEUX v2.6.5 src/ppu.cpp')
    text=source.decode('utf-8')
    if 'VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS' in text:
        raise ValueError('refuse to patch an already instrumented source')
    newline='\r\n' if b'\r\n' in source else '\n'
    normalized=text.replace('\r\n','\n')
    normalized=only_once(normalized,'uint8 PPU[4];','uint8 PPU[4];\n'+HOOK)
    normalized=only_once(normalized,'int FCEUPPU_Loop(int skip) {','int FCEUPPU_Loop(int skip) {\n\tif (!newppu) vpd340_frame_enter();')
    normalized=within(normalized,'static INLINE void Fixit2(void) {','static void Fixit1(void) {',
        'RefreshAddr = rad;','RefreshAddr = rad;\n\t\tvpd340_emit("legacy_horizontal_reload",-1);')
    normalized=within(normalized,'static void Fixit1(void) {','void MMC5_hb(int);',
        'RefreshAddr = rad;','RefreshAddr = rad;\n\t\tvpd340_emit("legacy_vertical_increment",-1);')
    normalized=within(normalized,'static DECLFW(B2006) {','static DECLFW(B2007) {',
        'RefreshAddr = TempAddr;\n\t\tDummyRead = 1;',
        'RefreshAddr = TempAddr;\n\t\tDummyRead = 1;\n\t\tvpd340_emit("cpu_second_2006",-1);')
    normalized=within(normalized,'static void DoLine(void) {','#define V_FLIP',
        '\tX6502_Run(256);\n\tEndRL();',
        '\tvpd340_emit("legacy_line_start",-1);\n\tX6502_Run(256);\n\tvpd340_emit("legacy_line_256_cpu_slice",-1);\n\tEndRL();')
    normalized=within(normalized,'static void DoLine(void) {','#define V_FLIP',
        '\tscanline++;\n\tif (scanline < 240)',
        '\tvpd340_emit("legacy_line_end",-1);\n\tscanline++;\n\tif (scanline < 240)')
    # Format preservation: the pinned upstream Git source uses CRLF.
    return normalized.replace('\n',newline).encode('utf-8')


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream-ppu',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.upstream_ppu.is_symlink() or not a.upstream_ppu.is_file():
        p.error('require a regular pristine upstream source')
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        p.error('output path must not exist and must have an existing parent')
    payload=patch(a.upstream_ppu.read_bytes())
    with a.output.open('xb') as f:
        f.write(payload)
    print('VPD_STAGE340_PINNED_CLASSIC_PPU_PATCHED')
    print('DIAGNOSTIC_BINARY_BUILT=false ORIGINAL_PPU_WITNESS_CAPTURED=false')


if __name__=='__main__':
    main()
