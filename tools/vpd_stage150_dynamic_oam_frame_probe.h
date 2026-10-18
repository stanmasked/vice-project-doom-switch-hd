// Stage150: actual newppu OAM selection -> XBuf across a CPU OAM update.
// Header is installed ONLY in a pinned temporary FCEUX and disabled by default.
#ifndef VPD_STAGE150_DYNAMIC_OAM_FRAME_PROBE_H
#define VPD_STAGE150_DYNAMIC_OAM_FRAME_PROBE_H
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace vpd_ppu_probe {
#ifdef VPD_NATIVE_SYNTHETIC_DYNAMIC_OAM_FRAMES
struct Stage150Frame {
    unsigned count=0,status=0,samples=0,first_color=0;
    unsigned raw=0,bg=0,oam7_x=0,oam8_y=0,oam8_x=0;
    bool sprite=false,evaluated=false;
};
struct Stage150Audit {
    Stage150Frame before,after;
    unsigned invalid=0;
    bool emitted=false;
};
inline Stage150Audit& stage150_state(){
    static Stage150Audit audit;
    return audit;
}
inline int stage150_mode(){
    static const char* v=std::getenv("VPD_STAGE150_DYNAMIC_OAM_CASE");
    if(v && std::strcmp(v,"activate_ninth")==0)return 1;
    if(v && std::strcmp(v,"preserve_eight")==0)return 0;
    return -1;
}
inline bool stage150_enabled(){
    static const char* v=std::getenv("VPD_STAGE150_DYNAMIC_OAM_PROBE");
    return v && std::strcmp(v,"1")==0 && stage150_mode()>=0 &&
           stage149_oam_enabled();
}
inline bool stage150_indices_valid(const unsigned* ids,unsigned count){
    if(count!=8U)return false;
    for(unsigned i=0;i<8U;i++)if(ids[i]!=i)return false;
    return true;
}
inline void stage150_eval(unsigned yp,unsigned count,unsigned status,
                          unsigned oam7_x,unsigned oam8_y,unsigned oam8_x,
                          unsigned i0,unsigned i1,unsigned i2,unsigned i3,
                          unsigned i4,unsigned i5,unsigned i6,unsigned i7){
    if(!stage150_enabled() || yp!=124U)return;
    Stage150Audit& a=stage150_state();
    if(a.emitted)return;
    const Stage149OamAudit& cpu=stage149_oam_state();
    if(cpu.writes!=0U && cpu.writes!=5U)return;
    const bool changed=cpu.writes==5U;
    Stage150Frame& f=changed?a.after:a.before;
    if(f.evaluated)return;
    const unsigned ids[]={i0,i1,i2,i3,i4,i5,i6,i7};
    if(!stage150_indices_valid(ids,count))return;
    // Discard partially initialized startup frames. This only accepts
    // a genuine previously configured OAM7 and OAM8 record.
    if(!changed && (oam7_x!=64U || oam8_y!=255U || oam8_x!=255U ||
                    (status&0x20U)!=0U))return;
    if(changed && (!a.before.evaluated || a.before.samples!=8U)) {
        ++a.invalid;
        return;
    }
    f.evaluated=true;
    f.count=count;
    f.status=status;
    f.oam7_x=oam7_x;
    f.oam8_y=oam8_y;
    f.oam8_x=oam8_x;
    if(changed){
        const bool activated=stage150_mode()==1;
        if(oam7_x!=(activated?160U:64U) ||
           oam8_y!=(activated?120U:255U) ||
           oam8_x!=(activated?64U:255U) ||
           ((status&0x20U)!=0)!=activated ||
           cpu.high_reads==0U || cpu.addr_writes!=1U ||
           !cpu.emitted || cpu.invalid)++a.invalid;
    }
}
inline void stage150_pixel(unsigned sl,unsigned x,unsigned count,
                           unsigned status,unsigned xbuf,bool sprite16,
                           unsigned raw,bool havepixel,unsigned bgpattern){
    if(!stage150_enabled() || sl!=126U || x<64U || x>=72U)return;
    Stage150Audit& a=stage150_state();
    if(a.emitted)return;
    const Stage149OamAudit& cpu=stage149_oam_state();
    if(cpu.writes!=0U && cpu.writes!=5U)return;
    const bool changed=cpu.writes==5U;
    Stage150Frame& f=changed?a.after:a.before;
    if(!f.evaluated || f.samples>=8U)return;
    const bool activated=changed && stage150_mode()==1;
    const unsigned expected_xbuf=activated?143U:170U;
    const unsigned expected_raw=activated?15U:42U;
    const bool expected_sprite=!activated;
    if(f.count!=8U || count!=8U || sprite16 ||
       ((status&0x20U)!=0)!=activated ||
       xbuf!=expected_xbuf || raw!=expected_raw ||
       havepixel!=expected_sprite || bgpattern!=0U)++a.invalid;
    if(f.samples==0U){
        f.first_color=xbuf;f.raw=raw;f.sprite=havepixel;f.bg=bgpattern;
    }
    ++f.samples;
    if(!changed || f.samples<8U)return;
    if(a.before.samples!=8U || !a.before.evaluated ||
       cpu.writes!=5U || !cpu.emitted || cpu.invalid)++a.invalid;
    const char* name=stage150_mode()==1?"activate_ninth":"preserve_eight";
    std::fprintf(stderr,
        "VPD_STAGE150_NATIVE_OAM_FRAME_%s case=%s "
        "before_count=%u after_count=%u before_overflow=%s "
        "after_overflow=%s before_xbuf=%u after_xbuf=%u "
        "before_raw=%u after_raw=%u before_sprite=%u after_sprite=%u "
        "oam7_before=%u oam7_after=%u oam8_y_before=%u "
        "oam8_y_after=%u cpu_writes=%u samples=16 invalid=%u "
        "synthetic_only=yes original_game_dynamic_oam_proven=no\n",
        a.invalid?"REJECT":"PASS",name,
        a.before.count,a.after.count,
        (a.before.status&0x20U)?"yes":"no",
        (a.after.status&0x20U)?"yes":"no",
        a.before.first_color,a.after.first_color,
        a.before.raw,a.after.raw,
        a.before.sprite?1U:0U,a.after.sprite?1U:0U,
        a.before.oam7_x,a.after.oam7_x,
        a.before.oam8_y,a.after.oam8_y,cpu.writes,
        a.invalid);
    std::fflush(stderr);
    a.emitted=true;
}
#endif
} // namespace vpd_ppu_probe
#endif
