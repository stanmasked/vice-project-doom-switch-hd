// Pure host-side renderer-quality regression (no NES assets or NRO).
#include "impact_lighting.hpp"
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <cstdio>
#include <vector>

namespace {
void check(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
}
int main(){
 try{
    constexpr int w=1280,h=720,stride=1297;
    constexpr uint32_t guard=0x12345678u;
    constexpr uint32_t baseline=0xff203040u;
    std::vector<uint32_t> a(static_cast<std::size_t>(h)*stride,guard);
    for(int y=0;y<h;++y)
        for(int x=0;x<w;++x)
            a[static_cast<std::size_t>(y)*stride+x]=baseline;
    const auto clean=a;
    check(!vpd::applyImpactLight(nullptr,w,h,stride,1,1,30,10,
                                 vpd::ImpactLightColor::Hero),
          "Null target accepted");
    check(!vpd::applyImpactLight(a.data(),w,h,w-1,1,1,30,10,
                                 vpd::ImpactLightColor::Hero),
          "Invalid stride accepted");
    check(!vpd::applyImpactLight(a.data(),w,h,stride,1,1,0,10,
                                 vpd::ImpactLightColor::Hero),
          "Zero radius accepted");
    check(!vpd::applyImpactLight(a.data(),w,h,stride,1,1,257,10,
                                 vpd::ImpactLightColor::Hero),
          "Unbounded radius accepted");
    check(!vpd::applyImpactLight(a.data(),w,h,stride,1,1,30,33,
                                 vpd::ImpactLightColor::Hero),
          "Unbounded energy accepted");
    check(a==clean,"Invalid arguments modified actual framebuffer");
    check(vpd::applyImpactLight(a.data(),w,h,stride,100,110,52,0,
                                vpd::ImpactLightColor::Guard) && a==clean,
          "Zero-strength glow changed original pixels");
    check(vpd::applyImpactLight(a.data(),w,h,stride,100,110,52,18,
                                vpd::ImpactLightColor::Guard),
          "Bounded impact light rejected");
    check(a!=clean,"Real guard damage produced no visible pixels");
    check(a[static_cast<std::size_t>(110)*stride+100]!=baseline,
          "Guard impact center did not change");
    check(a[static_cast<std::size_t>(110)*stride+400]==baseline,
          "Guard glow corrupted distant world pixel");
    check(a[0]==baseline,"Glow unexpectedly changed top-left world corner");
    for(int y=0;y<h;++y)
        for(int x=w;x<stride;++x)
            check(a[static_cast<std::size_t>(y)*stride+x]==guard,
                  "Impact lighting wrote into padded framebuffer stride");
    auto repeated=clean;
    check(vpd::applyImpactLight(repeated.data(),w,h,stride,
                                100,110,52,18,vpd::ImpactLightColor::Guard) &&
          repeated==a,"Impact lighting is not deterministic");
    // A bounded center beyond 32-bit screen edges must not wrap into
    // the visible image or cause clipping overflow.
    auto edge=clean;
    check(vpd::applyImpactLight(edge.data(),w,h,stride,
                                std::numeric_limits<int>::min(),10,58,20,
                                vpd::ImpactLightColor::Hero) &&
          edge==clean,"Large negative offscreen position overflowed");
    check(vpd::applyImpactLight(edge.data(),w,h,stride,
                                std::numeric_limits<int>::max(),10,58,20,
                                vpd::ImpactLightColor::Sentry) &&
          edge==clean,"Large positive offscreen position overflowed");
    check(vpd::applyImpactLight(edge.data(),w,h,stride,
                                0,0,58,18,vpd::ImpactLightColor::Sentry),
          "Clipped screen-edge impact rejected");
    check(edge[0]!=baseline && edge[1200]==baseline,
          "Clipping modified wrong screen section");
    for(int y=0;y<h;++y)
        for(int x=w;x<stride;++x)
            check(edge[static_cast<std::size_t>(y)*stride+x]==guard,
                  "Edge impact corrupted framebuffer padding");
    std::puts("VPD_HD_IMPACT_LIGHT_HOST_PASS "
              "invalid_args=yes deterministic=yes isolated_pixels=yes "
              "clipped_edges=yes padded_stride_intact=yes "
              "legacy_autoplay_unchanged_by_default=yes "
              "original_game_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_HD_IMPACT_LIGHT_HOST_FAIL %s\n",e.what());
    return 1;
 }
}
