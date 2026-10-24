#pragma once
#include "driving_source_scroll_demo.hpp"
#include <cstdint>
#include <cstdio>

// Stage365: real libnx framebuffer evidence for every state of the source-safe
// 41-state numeric DEMO. This is NOT an original NES ROM/PPU capture.
namespace vpd {
struct ScrollDemoRasterWitness {
    bool valid=false;
    bool last=false;
    std::uint32_t original_pair_start=0;
    std::uint32_t guest_frame=0;
    std::uint8_t image_shift=0;
    std::uint32_t panel_pixel=0,edge_pixel=0,glyph_pixel=0;
    std::uint64_t simulation_fingerprint=0;
};
inline ScrollDemoRasterWitness inspectScrollDemoRaster(
    bool manual,bool driving,bool chord,ScrollDemoState status,
    const DrivingPreviewView& view,const std::uint32_t* pixels,int stride,
    std::uint64_t platform_fingerprint) noexcept {
    ScrollDemoRasterWitness out{};
    const std::uint32_t pair=view.source_scroll_review_pair;
    const bool first=chord && status==ScrollDemoState::Preview && pair==519u;
    const bool middle=status==ScrollDemoState::Preview &&
                      pair>=520u && pair<=558u;
    const bool last=status==ScrollDemoState::LastFrame && pair==559u;
    if(!manual || !driving || !(first||middle||last) || !pixels ||
       stride<kDrivingPreviewWidth ||
       !view.source_scroll_review_visible ||
       !view.source_scroll_review_demo ||
       view.source_scroll_review_shift!=stage362FiniteShift(pair))
        return out;
    out.panel_pixel=pixels[270*stride+1040];
    out.edge_pixel=pixels[260*stride+1034];
    out.glyph_pixel=pixels[269*stride+1052];
    if(out.panel_pixel!=driving_detail::rgba(24,65,91) ||
       out.edge_pixel!=driving_detail::rgba(102,218,239) ||
       out.glyph_pixel!=driving_detail::rgba(102,218,239))
        return {};
    out.valid=true;
    out.last=last;
    out.original_pair_start=pair;
    out.guest_frame=view.frame;
    out.image_shift=view.source_scroll_review_shift;
    out.simulation_fingerprint=platform_fingerprint;
    return out;
}
inline void resetScrollDemoGuest(bool has_sd) noexcept {
    if(!has_sd)return;
    if(auto* f=std::fopen(
        "sdmc:/switch/vice_project_doom/scroll_demo_guest.txt","w"))
        (void)std::fclose(f);
    if(auto* f=std::fopen(
        "sdmc:/switch/vice_project_doom/scroll_demo_guest_v2.txt","w"))
        (void)std::fclose(f);
}
inline bool appendScrollDemoGuest(
    bool has_sd,const ScrollDemoRasterWitness& w) noexcept {
    if(!has_sd || !w.valid)return false;
    const char* event=w.original_pair_start==519u?"on":
                      w.last?"last":"frame";
    auto* f=std::fopen(
        "sdmc:/switch/vice_project_doom/scroll_demo_guest_v2.txt","a");
    if(!f)return false;
    const int n=std::fprintf(f,
        "VPD_STAGE365_NUMERIC_DEMO_V2 event=%s "
        "original_pair_start=%u guest_frame=%u image_shift=%u "
        "panel_pixel=%08x edge_pixel=%08x demo_glyph_pixel=%08x "
        "platform_fp=%016llx source=libnx_drawScene "
        "actual_original_rom_source_verification=0 "
        "original_game_physics_proven=0 raw_rom_fm2_present=0\n",
        event,static_cast<unsigned>(w.original_pair_start),
        static_cast<unsigned>(w.guest_frame),
        static_cast<unsigned>(w.image_shift),
        static_cast<unsigned>(w.panel_pixel),
        static_cast<unsigned>(w.edge_pixel),
        static_cast<unsigned>(w.glyph_pixel),
        static_cast<unsigned long long>(w.simulation_fingerprint));
    const bool v2_ok=std::fclose(f)==0 && n>0;
    // Keep the Stage364 endpoint witness format available to its historical
    // audit. The full Stage365 trace is a separate file and schema.
    if(w.original_pair_start!=519u && !w.last)return v2_ok;
    f=std::fopen(
        "sdmc:/switch/vice_project_doom/scroll_demo_guest.txt","a");
    if(!f)return false;
    const int legacy_n=std::fprintf(f,
        "VPD_STAGE363_NUMERIC_DEMO_V1 event=%s "
        "original_pair_start=%u guest_frame=%u image_shift=%u "
        "panel_pixel=%08x edge_pixel=%08x demo_glyph_pixel=%08x "
        "platform_fp=%016llx source=libnx_drawScene "
        "actual_original_rom_source_verification=0 "
        "original_game_physics_proven=0 raw_rom_fm2_present=0\n",
        w.last?"last":"on",static_cast<unsigned>(w.original_pair_start),
        static_cast<unsigned>(w.guest_frame),
        static_cast<unsigned>(w.image_shift),
        static_cast<unsigned>(w.panel_pixel),
        static_cast<unsigned>(w.edge_pixel),
        static_cast<unsigned>(w.glyph_pixel),
        static_cast<unsigned long long>(w.simulation_fingerprint));
    return v2_ok && std::fclose(f)==0 && legacy_n>0;
}
} // namespace vpd
