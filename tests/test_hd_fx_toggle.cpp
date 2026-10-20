// Portable L+R HD-effects toggle and pixel-layer acceptance.
#include "hd_fx_toggle.hpp"
#include "hd_fx_guest_proof.hpp"
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
    // Each authored layer must independently change source-eligible manual
    // pixels, not merely inherit a changed checksum from the haze layer.
    // Keep input/state fixed between OFF and ON renders of each layer.
    for(int effect=0;effect<4;++effect){
        SceneView isolated{};
        isolated.manual_controls=true;
        isolated.player_x_px=80;
        isolated.player_y_px=210;
        isolated.frame=19;
        switch(effect){
            case 0: isolated.player_hit_flash_ticks=7;break;
            case 1: break; // haze needs only manual camera/world coordinates
            case 2: isolated.moving=true;isolated.grounded=true;break;
            case 3:
                isolated.sentry.enabled=true;
                isolated.sentry.health=2;
                isolated.sentry.x_px=210;
                isolated.sentry.y_px=210;
                isolated.enemy_projectiles[0]={150,210,true};
                break;
        }
        std::vector<uint32_t> base(on.size(),padding);
        std::vector<uint32_t> enabled(on.size(),padding);
        check(drawScene(base.data(),kSceneWidth,kSceneHeight,stride,isolated),
              "individual HD layer baseline failed to render");
        switch(effect){
            case 0: isolated.hd_hit_lighting=true;break;
            case 1: isolated.hd_atmospheric_haze=true;break;
            case 2: isolated.hd_footstep_dust=true;break;
            case 3: isolated.hd_hostile_projectile_halo=true;break;
        }
        check(drawScene(enabled.data(),kSceneWidth,kSceneHeight,stride,isolated) &&
              digest(base,stride)!=digest(enabled,stride),
              "individual HD layer produced no source-conditioned pixel change");
        // All four layers must remain completely invisible in autoplay.
        isolated.manual_controls=false;
        check(drawScene(enabled.data(),kSceneWidth,kSceneHeight,stride,isolated),
              "autoplay individual HD render failed");
        const uint64_t autoplay_with_effect=digest(enabled,stride);
        isolated.hd_hit_lighting=false;
        isolated.hd_atmospheric_haze=false;
        isolated.hd_footstep_dust=false;
        isolated.hd_hostile_projectile_halo=false;
        check(drawScene(base.data(),kSceneWidth,kSceneHeight,stride,isolated) &&
              digest(base,stride)==autoplay_with_effect,
              "individual HD layer leaked into legacy autoplay pixels");
        for(int y=0;y<kSceneHeight;++y)
            for(int x=kSceneWidth;x<stride;++x)
                check(base[static_cast<std::size_t>(y)*stride+x]==padding &&
                      enabled[static_cast<std::size_t>(y)*stride+x]==padding,
                      "isolated HD effect overwrote row stride padding");
    }
    // Exclude the ON/OFF label from guest visual evidence: only authored
    // scene pixels inside the fixed foreground/background ROI count.
    const auto on_visual=fingerprintHdFxVisual(
        on.data(),kSceneWidth,kSceneHeight,stride);
    const auto off_visual=fingerprintHdFxVisual(
        off.data(),kSceneWidth,kSceneHeight,stride);
    check(on_visual.pixels==414000 && off_visual.pixels==414000 &&
          on_visual.hash!=off_visual.hash,
          "guest HUD-free visual evidence did not change with effects");
    check(fingerprintHdFxVisual(nullptr,kSceneWidth,kSceneHeight,stride).pixels==0 &&
          fingerprintHdFxVisual(off.data(),899,kSceneHeight,stride).pixels==0,
          "guest witness accepted a missing or undersized framebuffer");
    // Independently check the HUD indicator changes without changing
    // the established attract-mode pixels.
    scene.hd_fx_status_visible=true;
    scene.hd_fx_status_enabled=false;
    check(drawScene(off.data(),kSceneWidth,kSceneHeight,stride,scene),
          "OFF status overlay failed");
    const uint64_t off_label=digest(off,stride);
    check(fingerprintHdFxVisual(
              off.data(),kSceneWidth,kSceneHeight,stride).hash==off_visual.hash,
          "HD status label contaminated the guest effect-only sample");
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
