#include "driving_profile_review_mode.hpp"
#include "driving_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include "simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
static void need(bool yes,const char* error) {
    if(!yes)throw std::runtime_error(error);
}
static std::uint64_t hashRange(const std::vector<std::uint32_t>& pixels,
                               int stride,int first,int last) {
    std::uint64_t hash=14695981039346656037ull;
    for(int y=first;y<last;++y)
        for(int x=0;x<vpd::kDrivingPreviewWidth;++x) {
            const auto p=pixels[static_cast<std::size_t>(y)*stride+x];
            for(unsigned shift=0;shift<32;shift+=8) {
                hash^=(p>>shift)&255u;
                hash*=1099511628211ull;
            }
        }
    return hash;
}
int main() {
    constexpr int w=vpd::kDrivingPreviewWidth,h=vpd::kDrivingPreviewHeight;
    constexpr int pitch=w+19;
    constexpr std::uint32_t padding=0x12345678u;
    std::vector<std::uint32_t> pixels(
        static_cast<std::size_t>(pitch)*h,padding);
    std::vector<std::uint32_t> standard(pixels.size(),padding);
    vpd::Simulation platform;
    vpd::DrivingState driving;
    const auto platform_fp=platform.fingerprint();
    const int source_car=driving.car_x;
    const std::uint8_t source_hp=driving.health;
    const auto view=vpd::makeDrivingSceneView(driving);
    need(vpd::drawDrivingPreview(standard.data(),w,h,pitch,view),
         "standard driving stage source draw failed");
    const auto base_road=hashRange(standard,pitch,0,vpd::kDrivingHudTop);
    const auto base_hud=hashRange(standard,pitch,vpd::kDrivingHudTop,h);
    const auto base_car=standard[450*pitch+driving.car_x];
    vpd::RoadProfileReviewMode selector;
    need(!selector.cycle(false,true,true) && !selector.active(),
         "automatic demo exposed original numerical overlay");
    need(!selector.cycle(true,false,true) && !selector.active(),
         "overlay left manually selected driving prototype");
    need(!selector.cycle(true,true,false) && !selector.active(),
         "overlay activated without fresh pad chord");
    need(selector.originalFrame()==0,"default sample is nonzero");
    for(std::size_t i=0;i<vpd::road_reference::kObserved.size();++i) {
        need(selector.cycle(true,true,true),"manual cycling rejected");
        const auto& section=vpd::road_reference::kObserved[i];
        need(selector.active() && selector.originalFrame()==section.frame,
             "review cycles do not preserve original frame order");
        const auto interval=vpd::road_reference::toHdImageSpace(section);
        auto snap=view;
        snap.observed_road_frame=selector.originalFrame();
        need(vpd::drawDrivingPreview(pixels.data(),w,h,pitch,snap),
             "review raster render failed");
        constexpr int y=171;
        constexpr auto panel=vpd::driving_detail::rgba(14,24,34);
        constexpr auto fill=vpd::driving_detail::rgba(98,143,132);
        constexpr auto edge=vpd::driving_detail::rgba(233,190,117);
        auto at=[&](int x){return pixels[y*pitch+x];};
        need(interval.width==section.width()*5,
             "original-to-HD source image conversion failed");
        need(at(interval.left-1)==panel && at(interval.left)==edge &&
             at(interval.left+15)==fill && at(interval.right_inclusive-15)==fill &&
             at(interval.right_inclusive)==edge &&
             at(interval.right_inclusive+1)==panel,
             "source-owned RGB interval measured at incorrect HD X");
        need(hashRange(pixels,pitch,0,vpd::kDrivingHudTop)!=base_road,
             "source numeric swatch did not affect review road");
        need(hashRange(pixels,pitch,vpd::kDrivingHudTop,h)==base_hud,
             "diagnostic road changed existing health/timer HUD");
        need(pixels[450*pitch+source_car]==base_car,
             "reference-road rectangle changed the source car sprite");
        for(int row=0;row<h;++row)
            for(int x=w;x<pitch;++x)
                need(pixels[row*pitch+x]==padding,
                     "reference image-strip wrote into libnx pitch padding");
        need(platform.fingerprint()==platform_fp &&
             driving.car_x==source_car && driving.health==source_hp &&
             driving.frame==0,
             "original source numeric shape mutated synthetic physics");
    }
    need(selector.cycle(true,true,true) && !selector.active() &&
         selector.originalFrame()==0,"source-review cycle must end OFF");
    need(vpd::drawDrivingPreview(pixels.data(),w,h,pitch,view),
         "restore default ROM-free road failed");
    need(hashRange(pixels,pitch,0,vpd::kDrivingHudTop)==base_road &&
         hashRange(pixels,pitch,vpd::kDrivingHudTop,h)==base_hud,
         "default synthetic road/HUD changed after numeric review");
    selector.cycle(true,true,true);
    selector.reset();
    need(!selector.active() && selector.originalFrame()==0,
         "mode reset leaked source reference into next session");
    // The very same input reaches SceneView, but never changes platform.
    vpd::SceneView scene{};
    scene.manual_controls=true;
    scene.driving_stage_preview=true;
    scene.driving=view;
    scene.driving.observed_road_frame=600;
    need(vpd::drawScene(pixels.data(),w,h,pitch,scene),
         "shared Nintendo Switch SceneView source interval failed");
    need(pixels[171*pitch+330]==
             vpd::driving_detail::rgba(233,190,117),
         "shared scene selected the wrong original numerical frame");
    scene.driving_stage_preview=false;
    need(vpd::drawScene(pixels.data(),w,h,pitch,scene),
         "legacy platform renderer did not restore");
    need(platform.fingerprint()==platform_fp,
         "observational raster touched original platform physics");
    std::cout<<"VPD_ROMFREE_DRIVING_NUMERIC_ROAD_REVIEW_PASS"
             <<" real_observation_anchors=7 source_pixels_included=0"
             <<" source_collision_proven=0 source_camera_proven=0"
             <<" hud_intact=yes platform_intact=yes\n";
}
