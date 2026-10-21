#include "driving_road_review_witness.hpp"
#include "driving_scene_bridge.hpp"
#include "simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
static void ensure(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(){
    constexpr int width=vpd::kDrivingPreviewWidth,height=vpd::kDrivingPreviewHeight;
    constexpr int pitch=width+11;
    std::vector<std::uint32_t> framebuffer(
        static_cast<std::size_t>(pitch)*height);
    vpd::RoadProfileReviewMode mode;
    vpd::RoadReviewGuestProof proof;
    vpd::DrivingState car;
    vpd::Simulation platform;
    const auto fp=platform.fingerprint();
    auto v=vpd::makeDrivingSceneView(car);
    ensure(vpd::drawDrivingPreview(framebuffer.data(),width,height,pitch,v),
           "baseline draw failed");
    ensure(!proof.observe(true,true,false,mode,v,framebuffer.data(),pitch,fp).valid,
           "host-only gesture forged native guest proof");
    ensure(!proof.observe(false,true,true,mode,v,framebuffer.data(),pitch,fp).valid,
           "autoplay forged guest record");
    for(unsigned i=0;i<8;++i) {
        ensure(mode.cycle(true,true,true),"source selector rejected pad edge");
        car.tick({});
        v=vpd::makeDrivingSceneView(car);
        v.observed_road_frame=mode.originalFrame();
        ensure(vpd::drawDrivingPreview(framebuffer.data(),width,height,pitch,v),
               "guest road raster not drawn");
        if(i==0){
            const auto& ref=vpd::road_reference::kObserved[i];
            const auto band=vpd::road_reference::toHdImageSpace(ref);
            const auto pixel=framebuffer[171*pitch+band.right_inclusive+1];
            framebuffer[171*pitch+band.right_inclusive+1]=0x12345678u;
            ensure(!proof.observe(true,true,true,mode,v,framebuffer.data(),pitch,fp).valid,
                   "tampered source pixel forged evidence");
            framebuffer[171*pitch+band.right_inclusive+1]=pixel;
        }
        const auto rec=proof.observe(
            true,true,true,mode,v,framebuffer.data(),pitch,fp);
        ensure(rec.valid && rec.seq==i+1 && rec.drive_frame==car.frame &&
               rec.platform_fp==fp && rec.original_frame==mode.originalFrame(),
               "guest did not report exact original observation selected");
        if(i==7)
            ensure(!mode.active() && rec.original_frame==0 &&
                   rec.off_pixel==vpd::driving_detail::rgba(61,80,76),
                   "source swatch was not fully disabled");
        else
            ensure(rec.left_hd==
                vpd::road_reference::toHdImageSpace(
                    vpd::road_reference::kObserved[i]).left,
                "guest framebuffer left X does not match source value");
        ensure(!proof.observe(
                true,true,true,mode,v,framebuffer.data(),pitch,fp).valid,
               "same native frame produced duplicate guest record");
    }
    ensure(!proof.observe(
            true,true,true,mode,v,framebuffer.data(),pitch,fp).valid,
           "guest recorded a ninth source frame");
    ensure(platform.fingerprint()==fp,
           "source image diagnostic modified platform simulation");
    std::cout<<"VPD_ROMFREE_ROAD_REVIEW_GUEST_WITNESS_PASS"
             <<" gesture_edges=8 numeric_samples=7 pixels=source_owned"
             <<" platform_frozen=yes original_art=no\n";
}
