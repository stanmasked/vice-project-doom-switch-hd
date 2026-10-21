#include "driving_raster_witness.hpp"
#include "driving_scene_bridge.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
static void ensure(bool ok,const char* why) {if(!ok)throw std::runtime_error(why);}
int main() {
    constexpr int w=vpd::kDrivingPreviewWidth,h=vpd::kDrivingPreviewHeight;
    constexpr int stride=w+29;
    std::vector<uint32_t> pixels(static_cast<std::size_t>(stride)*h,0xdeadbeefu);
    vpd::DrivingState car;
    auto v=vpd::makeDrivingSceneView(car);
    ensure(vpd::drawDrivingPreview(pixels.data(),w,h,stride,v),"first draw failed");
    auto sample=vpd::sampleDrivingRaster(pixels.data(),stride,v);
    ensure(sample.matched && sample.hud==vpd::driving_detail::rgba(211,85,91),
           "undamaged vehicle HUD sampled at wrong source pixel");
    ensure(!vpd::sampleDrivingRaster(nullptr,stride,v).matched,
           "null framebuffer accepted");
    ensure(!vpd::sampleDrivingRaster(pixels.data(),w-1,v).matched,
           "short framebuffer stride accepted");
    car.health=4;
    v=vpd::makeDrivingSceneView(car);
    ensure(vpd::drawDrivingPreview(pixels.data(),w,h,stride,v),"HP4 draw failed");
    sample=vpd::sampleDrivingRaster(pixels.data(),stride,v);
    ensure(sample.matched && sample.hud==vpd::driving_detail::kHudBase,
           "fifth health pip did not disappear");
    car.hit_cooldown=44;
    car.frame=8; // even flash phase
    v=vpd::makeDrivingSceneView(car);
    ensure(v.impact_flash,"collision flash expected");
    ensure(vpd::drawDrivingPreview(pixels.data(),w,h,stride,v),"flash draw failed");
    sample=vpd::sampleDrivingRaster(pixels.data(),stride,v);
    ensure(sample.matched &&
           sample.car==vpd::driving_detail::rgba(232,200,126),
           "real car body pixel does not match impact flash");
    // Pixel tampering must fail closed rather than produce native evidence.
    pixels[648*stride+535]=0x12345678u;
    ensure(!vpd::sampleDrivingRaster(pixels.data(),stride,v).matched,
           "modified HUD pixel accepted");
    std::cout<<"VPD_ROMFREE_DRIVING_SAME_FRAME_RASTER_PASS"
             <<" body_pixel=1 fifth_health_pip=1 impact_flash=1"
             <<" original_assets_used=0\n";
}
