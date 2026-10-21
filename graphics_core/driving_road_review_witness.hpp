#pragma once
#include "driving_profile_review_mode.hpp"
#include "driving_raster_witness.hpp"
#include <cstdint>
#include <cstdio>

// Native, source-owned proof that an actual gamepad gesture caused the
// observed numeric image-space swatch to appear on the NRO framebuffer.
// A source screenshot scanline, camera speed and car collision remain unknown.
namespace vpd {
struct RoadReviewGuestEvent {
    bool valid=false;
    unsigned seq=0;
    unsigned original_frame=0;
    unsigned drive_frame=0;
    int left_hd=0,right_hd=0;
    uint32_t outside_left=0,edge_left=0,edge_right=0,outside_right=0;
    uint32_t off_pixel=0,car_pixel=0,hud_pixel=0;
    unsigned health=0,flash=0;
    std::uint64_t platform_fp=0;
};
class RoadReviewGuestProof {
public:
    RoadReviewGuestEvent observe(
        bool manual,bool driving,bool actual_three_key_edge,
        const RoadProfileReviewMode& mode,const DrivingPreviewView& view,
        const std::uint32_t* pixels,int stride,std::uint64_t platform) {
        if(!manual || !driving || !actual_three_key_edge ||
           !pixels || stride<kDrivingPreviewWidth || next_>8 ||
           (next_>1 && platform!=platform_) ||
           (next_>1 && view.frame<=drive_frame_))
            return {};
        const unsigned index=next_;
        const auto* original=index==8?nullptr:&road_reference::kObserved[index-1];
        const unsigned expected_frame=original?original->frame:0;
        if(mode.originalFrame()!=expected_frame ||
           view.observed_road_frame!=expected_frame)
            return {};
        const auto vehicle=sampleDrivingRaster(pixels,stride,view);
        if(!vehicle.matched)return {};
        RoadReviewGuestEvent out{};
        out.seq=index;
        out.original_frame=expected_frame;
        out.drive_frame=view.frame;
        out.health=view.health;
        out.flash=static_cast<unsigned>(view.impact_flash);
        out.car_pixel=vehicle.car;
        out.hud_pixel=vehicle.hud;
        out.platform_fp=platform;
        if(original){
            const auto band=road_reference::toHdImageSpace(*original);
            out.left_hd=band.left;
            out.right_hd=band.right_inclusive;
            constexpr int y=171;
            out.outside_left=pixels[y*stride+band.left-1];
            out.edge_left=pixels[y*stride+band.left];
            out.edge_right=pixels[y*stride+band.right_inclusive];
            out.outside_right=pixels[y*stride+band.right_inclusive+1];
            if(out.outside_left!=driving_detail::rgba(14,24,34) ||
               out.outside_right!=driving_detail::rgba(14,24,34) ||
               out.edge_left!=driving_detail::rgba(233,190,117) ||
               out.edge_right!=driving_detail::rgba(233,190,117))
                return {};
        }else{
            out.off_pixel=pixels[171*stride+40];
            if(out.off_pixel!=driving_detail::rgba(61,80,76))
                return {};
        }
        if(next_==1)platform_=platform;
        drive_frame_=view.frame;
        ++next_;
        out.valid=true;
        return out;
    }
private:
    unsigned next_=1;
    unsigned drive_frame_=0;
    std::uint64_t platform_=0;
};
inline void resetRoadReviewGuest(bool has_sd) {
    if(!has_sd)return;
    if(auto* f=std::fopen(
            "sdmc:/switch/vice_project_doom/road_review_guest.txt","w"))
        std::fclose(f);
}
inline bool appendRoadReviewGuest(bool has_sd,const RoadReviewGuestEvent& e){
    if(!has_sd || !e.valid)return false;
    auto* f=std::fopen(
         "sdmc:/switch/vice_project_doom/road_review_guest.txt","a");
    if(!f)return false;
    const int printed=std::fprintf(f,
        "VPD_ROAD_REVIEW_V1 seq=%u original_frame=%u drive_frame=%u "
        "left_hd=%d right_hd=%d "
        "outside_left=%08x edge_left=%08x edge_right=%08x "
        "outside_right=%08x off_pixel=%08x "
        "car_pixel=%08x hud_pixel=%08x health=%u flash=%u "
        "platform_fp=%016llx source=libnx_drawScene "
        "source_art=none collision_proven=0\n",
        e.seq,e.original_frame,e.drive_frame,e.left_hd,e.right_hd,
        static_cast<unsigned>(e.outside_left),
        static_cast<unsigned>(e.edge_left),
        static_cast<unsigned>(e.edge_right),
        static_cast<unsigned>(e.outside_right),
        static_cast<unsigned>(e.off_pixel),
        static_cast<unsigned>(e.car_pixel),
        static_cast<unsigned>(e.hud_pixel),e.health,e.flash,
        static_cast<unsigned long long>(e.platform_fp));
    const bool closed=std::fclose(f)==0;
    return printed>0 && closed;
}
} // namespace vpd
