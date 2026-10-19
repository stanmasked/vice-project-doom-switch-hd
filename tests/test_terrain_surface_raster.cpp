// Full ROM-free native scene integration: backdrop, terrain and actors.
#include "scene_renderer.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
bool solid(void*,int x,int y){
    return (y==14 && x>=0 && x<64) ||
           (y==11 && x>=12 && x<20);
}
uint64_t fingerprint(const std::vector<uint32_t>& pixels,int stride){
    uint64_t hash=14695981039346656037ull;
    for(int y=0;y<vpd::kSceneHeight;++y)
        for(int x=0;x<vpd::kSceneWidth;++x){
            uint32_t pixel=pixels[static_cast<std::size_t>(y)*stride+x];
            for(unsigned k=0;k<4;++k){
                hash^=(pixel>>(8*k))&255u;hash*=1099511628211ull;
            }
        }
    return hash;
}
} // namespace
int main(){
 try{
    constexpr int w=vpd::kSceneWidth,h=vpd::kSceneHeight,stride=w+13;
    constexpr uint32_t sentinel=0x5689abcdu;
    std::vector<uint32_t> legacy(static_cast<std::size_t>(stride)*h,sentinel);
    std::vector<uint32_t> compare=legacy;
    vpd::SceneView view;
    view.solid_at=solid;
    view.player_x_px=48;
    view.player_y_px=210;
    view.grounded=true;
    view.guard={160,210,3,true,true,0};
    view.manual_controls=true;
    require(vpd::drawScene(legacy.data(),w,h,stride,view),
            "ordinary live scene render failed");
    const auto original=fingerprint(legacy,stride);
    view.hd_terrain_detail=true;
    require(vpd::drawScene(compare.data(),w,h,stride,view),
            "new surface depth render failed");
    const auto detailed=fingerprint(compare,stride);
    require(detailed!=original,
            "opt-in authored ledge surface failed to affect world pixels");
    const int px=160*2+10,py=(210+80)*2+15;
    constexpr uint32_t red=0xff5d67dcu;
    require(compare[static_cast<std::size_t>(py)*stride+px]==red,
            "surface detail overwrote source-authenticated guard torso");
    require(legacy[static_cast<std::size_t>(py)*stride+px]==red,
            "source guard baseline color changed independently");
    require(vpd::drawScene(compare.data(),w,h,stride,view) &&
            fingerprint(compare,stride)==detailed,
            "opt-in surface raster is not repeatable");
    view.external_terrain_asset=true;
    require(vpd::drawScene(compare.data(),w,h,stride,view) &&
            fingerprint(compare,stride)==original,
            "external user-provided terrain was modified by authored detail");
    view.external_terrain_asset=false;
    view.manual_controls=false;
    view.hd_terrain_detail=false;
    require(vpd::drawScene(legacy.data(),w,h,stride,view),
            "ROM-free auto-demo baseline render failed");
    const auto demo=fingerprint(legacy,stride);
    view.hd_terrain_detail=true;
    require(vpd::drawScene(compare.data(),w,h,stride,view) &&
            fingerprint(compare,stride)==demo,
            "opt-in terrain detail contaminated approved autoplay frame");
    for(int y=0;y<h;++y)
        for(int x=w;x<stride;++x)
            require(compare[static_cast<std::size_t>(y)*stride+x]==sentinel,
                    "full-scene terrain detail wrote framebuffer padding");
    std::puts("VPD_HD_TERRAIN_SCENE_PASS manual_world_changed=yes "
              "legacy_demo_unchanged=yes external_terrain_unchanged=yes "
              "guard_source_rgb_unchanged=yes deterministic=yes "
              "stride_padding_intact=yes original_game_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_HD_TERRAIN_SCENE_FAIL %s\n",e.what());
    return 1;
 }
}
