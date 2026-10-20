// Portable L+R HD-effects toggle and pixel-layer acceptance.
#include "hd_fx_toggle.hpp"
#include "scene_renderer.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>
namespace {
void check(bool value,const char* why){if(!value)throw std::runtime_error(why);}
uint64_t digest(const std::vector<uint32_t>& image,int stride){
    uint64_t h=14695981039346656037ull;
    for(int y=0;y<vpd::kSceneHeight;++y)
        for(int x=0;x<vpd::kSceneWidth;++x){
            const uint32_t p=image[static_cast<std::size_t>(y)*stride+x];
            h^=p;h*=1099511628211ull;
        }
    return h;
}
}
int main(){
 try{
    using namespace vpd;
    HdFxRuntimeMode fx{};
    check(fx.enabled && fx.activeForGameplay(true) &&
          !fx.activeForGameplay(false),"visuals should default on only in manual mode");
    check(!fx.acceptShoulders(true,true,false,true,false) && fx.enabled,
          "single L backdrop reload consumed or changed HD state");
    check(!fx.acceptShoulders(true,false,true,false,true) && fx.enabled,
          "single R backdrop reset consumed or changed HD state");
    check(fx.acceptShoulders(true,true,true,false,true) && !fx.enabled,
          "manual L+R chord did not disable effects");
    for(int frame=0;frame<45;++frame)
        check(fx.acceptShoulders(true,true,true,false,false) && !fx.enabled,
              "held L+R chord re-toggled effects or triggered art commands");
    check(!fx.acceptShoulders(true,false,false,false,false) && !fx.enabled,
          "releasing shoulder chord changed active effects");
    check(fx.acceptShoulders(true,true,true,true,true) && fx.enabled,
          "new L+R edge did not re-enable HD visuals");
    check(!fx.acceptShoulders(false,true,true,true,true) && fx.enabled,
          "autoplay consumed art controls or changed persisted visual mode");

    constexpr int stride=kSceneWidth+9;
    const uint32_t padding=0x3a4b5c6du;
    std::vector<uint32_t> on(static_cast<std::size_t>(stride)*kSceneHeight,padding);
    std::vector<uint32_t> off(on.size(),padding),repeat(on.size(),padding);
    SceneView scene{};
    scene.manual_controls=true;
    scene.player_x_px=80;
    scene.player_y_px=210;
    scene.moving=true;
    scene.grounded=true;
    scene.frame=19;
    scene.hd_atmospheric_haze=fx.activeForGameplay(true);
    scene.hd_footstep_dust=fx.activeForGameplay(true);
    scene.hd_hit_lighting=fx.activeForGameplay(true);
    scene.hd_hostile_projectile_halo=fx.activeForGameplay(true);
    check(drawScene(on.data(),kSceneWidth,kSceneHeight,stride,scene),
          "HD ON source frame did not render");
    check(drawScene(repeat.data(),kSceneWidth,kSceneHeight,stride,scene) &&
          digest(on,stride)==digest(repeat,stride),
          "HD ON rendering is not deterministic");
    fx.acceptShoulders(true,true,true,true,true);
    check(!fx.activeForGameplay(true),"HD OFF chord unrecognized");
    scene.hd_atmospheric_haze=fx.activeForGameplay(true);
    scene.hd_footstep_dust=fx.activeForGameplay(true);
    scene.hd_hit_lighting=fx.activeForGameplay(true);
    scene.hd_hostile_projectile_halo=fx.activeForGameplay(true);
    check(drawScene(off.data(),kSceneWidth,kSceneHeight,stride,scene) &&
          digest(off,stride)!=digest(on,stride),
          "HD OFF did not change manually controlled authored effects");
    // Independently check the HUD indicator changes without changing
    // the established attract-mode pixels.
    scene.hd_fx_status_visible=true;
    scene.hd_fx_status_enabled=false;
    check(drawScene(off.data(),kSceneWidth,kSceneHeight,stride,scene),
          "OFF status overlay failed");
    const uint64_t off_label=digest(off,stride);
    scene.hd_fx_status_enabled=true;
    check(drawScene(off.data(),kSceneWidth,kSceneHeight,stride,scene) &&
          digest(off,stride)!=off_label,"ON and OFF HUD labels matched");
    scene.manual_controls=false;
    scene.hd_fx_status_enabled=false;
    check(drawScene(off.data(),kSceneWidth,kSceneHeight,stride,scene),
          "autoplay disabled-status draw failed");
    const auto auto_hash=digest(off,stride);
    scene.hd_fx_status_enabled=true;
    check(drawScene(off.data(),kSceneWidth,kSceneHeight,stride,scene) &&
          digest(off,stride)==auto_hash,
          "HD mode indicator leaked into approved autoplay pixels");
    for(int y=0;y<kSceneHeight;++y)
        for(int x=kSceneWidth;x<stride;++x)
            check(off[static_cast<std::size_t>(y)*stride+x]==padding,
                  "HUD or HD state touched framebuffer padding");
    std::puts("VPD_HD_FX_TOGGLE_HOST_PASS single_buttons_unmodified=yes "
              "L_R_chord_edge_debounced=yes no_guest_tick=yes "
              "autoplay_pixels_identical=yes manual_pixels_change=yes "
              "physical_switch_proven=no original_game_proven=no");
    return 0;
 }catch(const std::exception& error){
    std::fprintf(stderr,"VPD_HD_FX_TOGGLE_HOST_FAIL %s\n",error.what());
    return 1;
 }
}
