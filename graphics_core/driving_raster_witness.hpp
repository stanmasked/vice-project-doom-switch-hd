#pragma once
#include "driving_preview.hpp"
#include <cstdint>
#include <cstdio>

// Native raster evidence sampled in the same frame as the actual source
// DrivingState event, after libnx drawScene and before framebufferEnd.
// These are invented vehicle/HUD colors, NOT extracted Nintendo art.
namespace vpd {
struct DrivingRasterProof {
    uint32_t car=0,hud=0;
    uint32_t expected_car=0,expected_hud=0;
    bool matched=false;
};
inline DrivingRasterProof sampleDrivingRaster(
    const uint32_t* pixels,int stride,const DrivingPreviewView& view) {
    if(!pixels || stride<kDrivingPreviewWidth ||
       view.car_x<362 || view.car_x>918 || view.health>5)
        return {};
    const uint32_t car=pixels[450*stride+view.car_x];
    const uint32_t hud=pixels[648*stride+535];
    const uint32_t expected_car=view.impact_flash?
        driving_detail::rgba(232,200,126):
        driving_detail::rgba(163,47,63);
    const uint32_t expected_hud=view.health==5?
        driving_detail::rgba(211,85,91):
        driving_detail::kHudBase;
    return {car,hud,expected_car,expected_hud,
            car==expected_car && hud==expected_hud};
}
inline bool appendDrivingRasterProof(
    bool has_sd,unsigned seq,const DrivingPreviewView& view,
    const uint32_t* pixels,int stride) {
    if(!has_sd || (seq!=2 && seq!=4))return false;
    const DrivingRasterProof proof=sampleDrivingRaster(pixels,stride,view);
    if(!proof.matched)return false; // wrong scene/HP is not evidence
    auto* f=std::fopen("sdmc:/switch/vice_project_doom/driving_raster_guest.txt","a");
    if(!f)return false;
    const int n=std::fprintf(f,
        "VPD_DRIVING_RASTER_V1 seq=%u frame=%u car_x=%d health=%u "
        "flash=%u car_pixel=%08x hud_pixel=%08x "
        "car_expected=%08x hud_expected=%08x "
        "source=libnx_drawScene same_frame=yes original_assets_used=0\n",
        seq,view.frame,view.car_x,static_cast<unsigned>(view.health),
        static_cast<unsigned>(view.impact_flash),
        static_cast<unsigned>(proof.car),
        static_cast<unsigned>(proof.hud),
        static_cast<unsigned>(proof.expected_car),
        static_cast<unsigned>(proof.expected_hud));
    const bool closed=std::fclose(f)==0;return n>0 && closed;
}
inline void resetDrivingRasterProof(bool has_sd) {
    if(!has_sd)return;
    if(auto* f=std::fopen("sdmc:/switch/vice_project_doom/driving_raster_guest.txt","w"))
        std::fclose(f);
}
} // namespace vpd
