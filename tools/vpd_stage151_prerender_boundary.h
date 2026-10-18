// Stage151: actual FCEUX pre-render PPU reset separating CPU OAM write
// and next rendered XBuf frame. Synthetic-only, opt-in, private native build.
#ifndef VPD_STAGE151_PRERENDER_BOUNDARY_H
#define VPD_STAGE151_PRERENDER_BOUNDARY_H
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace vpd_ppu_probe {
#ifdef VPD_NATIVE_SYNTHETIC_OAM_PRERENDER_BOUNDARY
struct Stage151Audit {
    unsigned accepted=0,invalid=0,before_status=0,after_status=0;
    bool pending=false,emitted=false;
};
inline Stage151Audit& stage151_state(){
    static Stage151Audit a;
    return a;
}
inline bool stage151_enabled(){
    static const char* value=std::getenv("VPD_STAGE151_BOUNDARY_PROBE");
    return value && std::strcmp(value,"1")==0 &&
           stage150_enabled() && stage149_oam_enabled();
}
inline void stage151_before_reset(unsigned status){
    if(!stage151_enabled())return;
    Stage151Audit& a=stage151_state();
    const Stage150Audit& frame=stage150_state();
    const Stage149OamAudit& cpu=stage149_oam_state();
    if(a.emitted || a.pending || a.accepted>0U)return;
    // Count only an actual pre-render reset following the completed,
    // source-proven CPU writes, and the fully observed earlier frame.
    // Ignore earlier startup/pre-update reset events entirely.
    if(frame.before.samples!=8U || !frame.before.evaluated ||
       frame.after.evaluated || frame.after.samples ||
       cpu.writes!=5U || cpu.addr_writes!=1U ||
       cpu.high_reads==0U || !cpu.emitted || cpu.invalid)return;
    a.pending=true;
    a.before_status=status;
}
inline void stage151_after_reset(unsigned status){
    if(!stage151_enabled())return;
    Stage151Audit& a=stage151_state();
    if(a.emitted || !a.pending)return;
    a.after_status=status;
    if(status!=0U || a.accepted>0U)++a.invalid;
    ++a.accepted;
    a.pending=false;
}
inline void stage151_after_pixel(){
    if(!stage151_enabled())return;
    Stage151Audit& a=stage151_state();
    Stage150Audit& frame=stage150_state();
    Stage149OamAudit& cpu=stage149_oam_state();
    if(a.emitted || !frame.emitted)return;
    if(a.pending || a.accepted!=1U || a.after_status!=0U ||
       frame.before.samples!=8U || frame.after.samples!=8U ||
       frame.invalid || !cpu.emitted || cpu.invalid)++a.invalid;
    std::fprintf(stderr,
        "VPD_STAGE151_NATIVE_PRERENDER_OAM_BOUNDARY_%s "
        "case=%s resets_between_frames=%u reset_after_status=%u "
        "before_samples=%u after_samples=%u cpu_writes=%u "
        "invalid=%u synthetic_only=yes "
        "original_game_frame_timing_proven=no\n",
        a.invalid?"REJECT":"PASS",
        stage150_mode()==1?"activate_ninth":"preserve_eight",
        a.accepted,a.after_status,frame.before.samples,
        frame.after.samples,cpu.writes,a.invalid);
    std::fflush(stderr);
    a.emitted=true;
}
#endif
} // namespace vpd_ppu_probe
#endif
