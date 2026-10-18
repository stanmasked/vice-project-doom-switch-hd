// Stage149: synthetic-only, opt-in FCEUX CPU OAM-write provenance.
// Header used ONLY in the temporary pinned emulator build.
#ifndef VPD_STAGE149_CPU_OAM_PROBE_H
#define VPD_STAGE149_CPU_OAM_PROBE_H
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace vpd_ppu_probe {
#ifdef VPD_NATIVE_SYNTHETIC_OAM_CPU_WRITES
struct Stage149OamAudit {
    unsigned high_reads=0, addr_writes=0, writes=0, invalid=0;
    unsigned address=0, observed[5]={0,0,0,0,0}, attr_stored=0;
    unsigned long long high_tick=0, addr_tick=0;
    bool emitted=false;
};
inline Stage149OamAudit& stage149_oam_state(){
    static Stage149OamAudit audit;
    return audit;
}
inline bool stage149_oam_enabled(){
    static const char* opt=std::getenv("VPD_STAGE149_OAM_WRITES_PROBE");
    return opt && std::strcmp(opt,"1")==0;
}
inline int stage149_oam_mode(){
    static const char* choice=std::getenv("VPD_STAGE149_OAM_WRITES_CASE");
    if(choice && std::strcmp(choice,"activate_ninth")==0)return 1;
    if(choice && std::strcmp(choice,"preserve_eight")==0)return 0;
    return -1;
}
inline void stage149_status_read(bool high){
    if(!stage149_oam_enabled() || stage149_oam_mode()<0)return;
    Stage149OamAudit& a=stage149_oam_state();
    if(a.emitted || a.addr_writes || !high)return;
    ++a.high_reads;
    a.high_tick=channel().internal_tick_units;
}
inline void stage149_oam_address(unsigned value,unsigned stored,bool newppu){
    if(!stage149_oam_enabled() || stage149_oam_mode()<0 || value!=31U)return;
    Stage149OamAudit& a=stage149_oam_state();
    if(a.emitted)return;
    ++a.addr_writes;
    a.address=stored;
    a.addr_tick=channel().internal_tick_units;
    if(!newppu || a.addr_writes!=1U || stored!=31U ||
       a.high_reads==0U || a.addr_tick<a.high_tick ||
       a.addr_tick-a.high_tick>3000ULL)++a.invalid;
}
inline void stage149_oam_data(unsigned address,unsigned written,
                              unsigned stored,bool newppu){
    if(!stage149_oam_enabled() || stage149_oam_mode()<0)return;
    Stage149OamAudit& a=stage149_oam_state();
    if(a.emitted || !a.addr_writes)return;
    if(a.writes>=5U){++a.invalid;return;}
    const unsigned activate[]={160U,120U,2U,0U,64U};
    const unsigned preserve[]={64U,255U,255U,255U,255U};
    const unsigned* expected=stage149_oam_mode()==1?activate:preserve;
    const unsigned i=a.writes;
    a.observed[i]=written;
    if(i==3U)a.attr_stored=stored;
    if(!newppu || a.addr_writes!=1U || address!=31U+i ||
       written!=expected[i] ||
       stored!=((address&3U)==2U?(written&0xE3U):written) ||
       channel().internal_tick_units<a.addr_tick ||
       channel().internal_tick_units-a.addr_tick>3000ULL)++a.invalid;
    ++a.writes;
    if(a.writes!=5U)return;
    std::fprintf(stderr,
        "VPD_STAGE149_NATIVE_VBLANK_OAM_WRITE_%s "
        "case=%s status_high_read=%s oamaddr=%u writes=%u "
        "first_oam=31 last_oam=35 "
        "oam7_x=%u oam8_y=%u oam8_tile=%u oam8_attr=%u oam8_x=%u "
        "attr_stored=%u invalid=%u synthetic_only=yes "
        "original_game_oam_writes_proven=no\n",
        a.invalid?"REJECT":"PASS",
        stage149_oam_mode()==1?"activate_ninth":"preserve_eight",
        a.high_reads?"yes":"no",a.address,a.writes,
        a.observed[0],a.observed[1],a.observed[2],
        a.observed[3],a.observed[4],a.attr_stored,a.invalid);
    std::fflush(stderr);
    a.emitted=true;
}
#endif
} // namespace vpd_ppu_probe
#endif
