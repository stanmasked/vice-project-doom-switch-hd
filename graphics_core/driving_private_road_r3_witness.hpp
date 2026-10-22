#pragma once
#include "driving_private_review_mode.hpp"
#include "driving_raster_witness.hpp"
#include <cstdint>
#include <cstdio>

// Proof of an ACTUAL libnx R3 edge and the source-owned 1280x720 raster
// on that exact guest frame. This never measures original NES world
// coordinates, PPU-effective scroll, camera motion or collision bounds.
namespace vpd {
struct PrivateRoadR3Event {
    bool valid=false;
    unsigned seq=0,source_frame=0,drive_frame=0;
    int left_hd=0,right_hd=0;
    std::uint32_t outside_left=0,edge_left=0,edge_right=0,outside_right=0;
    std::uint32_t off_pixel=0,marker_pixel=0,car_pixel=0,hud_pixel=0;
    unsigned health=0,flash=0;
    std::uint64_t platform_fp=0;
};
class PrivateRoadR3GuestProof {
public:
    PrivateRoadR3Event observe(
        bool manual,bool driving,bool real_three_key_edge,
        const private_road::PrivateRoadBundle& bundle,
        const PrivateRoadReviewMode& mode,const DrivingPreviewView& view,
        const std::uint32_t* pixels,int stride,std::uint64_t fp) {
        if(!manual || !driving || !real_three_key_edge ||
           !bundle.loaded() || !pixels || stride<kDrivingPreviewWidth ||
           next_>38 || (next_>1 && fp!=platform_fp_) ||
           (next_>1 && view.frame<=last_drive_frame_))return {};
        const auto* sample=next_<=37?bundle.byIndex(next_-1):nullptr;
        if(mode.selected(bundle)!=sample ||
           view.private_road_enabled!=(sample!=nullptr))return {};
        const auto car=sampleDrivingRaster(pixels,stride,view);
        if(!car.matched)return {};
        PrivateRoadR3Event out{};
        out.seq=next_;
        out.source_frame=sample?sample->frame:0;
        out.drive_frame=view.frame;
        out.platform_fp=fp;
        out.health=view.health;
        out.flash=static_cast<unsigned>(view.impact_flash);
        out.car_pixel=car.car;
        out.hud_pixel=car.hud;
        if(sample) {
            if(view.private_original_frame!=sample->frame ||
               view.private_left!=sample->left ||
               view.private_right!=sample->right)return {};
            const auto hd=road_reference::toHdImageSpace(*sample);
            constexpr int y=171;
            out.left_hd=hd.left;
            out.right_hd=hd.right_inclusive;
            out.outside_left=pixels[y*stride+hd.left-1];
            out.edge_left=pixels[y*stride+hd.left];
            out.edge_right=pixels[y*stride+hd.right_inclusive];
            out.outside_right=pixels[y*stride+hd.right_inclusive+1];
            out.marker_pixel=pixels[154*stride+190];
            if(out.outside_left!=driving_detail::rgba(14,24,34) ||
               out.outside_right!=driving_detail::rgba(14,24,34) ||
               out.edge_left!=driving_detail::rgba(233,190,117) ||
               out.edge_right!=driving_detail::rgba(233,190,117) ||
               out.marker_pixel!=driving_detail::rgba(233,190,117))
                return {};
        }else{
            out.off_pixel=pixels[171*stride+40];
            if(out.off_pixel!=driving_detail::rgba(61,80,76))
                return {};
        }
        if(next_==1)platform_fp_=fp;
        last_drive_frame_=view.frame;
        ++next_;
        out.valid=true;
        return out;
    }
private:
    unsigned next_=1,last_drive_frame_=0;
    std::uint64_t platform_fp_=0;
};
inline void resetPrivateRoadR3Guest(bool has_sd){
    if(!has_sd)return;
    if(auto* f=std::fopen(
       "sdmc:/switch/vice_project_doom/private_road_r3_guest.txt","w"))
        std::fclose(f);
}
inline bool appendPrivateRoadR3Guest(bool has_sd,const PrivateRoadR3Event& e){
    if(!has_sd || !e.valid)return false;
    auto* f=std::fopen(
        "sdmc:/switch/vice_project_doom/private_road_r3_guest.txt","a");
    if(!f)return false;
    const int n=std::fprintf(f,
        "VPD_PRIVATE_ROAD_R3_V1 seq=%u source_frame=%u drive_frame=%u "
        "left_hd=%d right_hd=%d outside_left=%08x edge_left=%08x "
        "edge_right=%08x outside_right=%08x marker_pixel=%08x "
        "off_pixel=%08x car_pixel=%08x hud_pixel=%08x health=%u "
        "flash=%u platform_fp=%016llx source=libnx_framebuffer "
        "original_art=none camera_collision_proven=no\n",
        e.seq,e.source_frame,e.drive_frame,e.left_hd,e.right_hd,
        static_cast<unsigned>(e.outside_left),
        static_cast<unsigned>(e.edge_left),
        static_cast<unsigned>(e.edge_right),
        static_cast<unsigned>(e.outside_right),
        static_cast<unsigned>(e.marker_pixel),
        static_cast<unsigned>(e.off_pixel),
        static_cast<unsigned>(e.car_pixel),
        static_cast<unsigned>(e.hud_pixel),
        e.health,e.flash,
        static_cast<unsigned long long>(e.platform_fp));
    const bool closed=std::fclose(f)==0;
    return n>0 && closed;
}
} // namespace vpd
