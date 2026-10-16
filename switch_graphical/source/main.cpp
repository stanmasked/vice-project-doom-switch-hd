// Independent libnx native raster scene; no NES emulator or proprietary art.
#include <switch.h>
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "asset_atlas.hpp"
#include "asset_bundle.hpp"
#include "animation.hpp"
#include "demo_animation.hpp"
#include "demo_atlas.hpp"
#include "demo_terrain.hpp"
#include "terrain_source.hpp"
#include <cstdint>
namespace {
bool solidAt(void* context,int x,int y) {
    return static_cast<const vpd::Scene*>(context)->solid(x,y);
}
}
int main(int,char**) {
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    Framebuffer fb{};
    Result rc=framebufferCreate(&fb,nwindowGetDefault(),vpd::kSceneWidth,
                                vpd::kSceneHeight,PIXEL_FORMAT_RGBA_8888,2);
    if(R_FAILED(rc))return 2;
    rc=framebufferMakeLinear(&fb);
    if(R_FAILED(rc)){framebufferClose(&fb);return 3;}
    // Optional development asset. Missing or damaged SD data never blocks launch.
    constexpr const char* kExternalAtlasPath=
        "sdmc:/switch/vice_project_doom/hero.vpat";
    constexpr const char* kExternalAnimationPath=
        "sdmc:/switch/vice_project_doom/hero.vanm";
    vpd::AssetBundle assets;
    if(!assets.initialize(vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes,
                          vpd_demo::kAnimationBank)) {
        framebufferClose(&fb);return 4;
    }
    const Result sd_mount=fsdevMountSdmc();
    const bool we_mounted_sd=R_SUCCEEDED(sd_mount);
    const bool has_sd=we_mounted_sd || fsdevGetDeviceFileSystem("sdmc")!=nullptr;
    if(has_sd)assets.reload(kExternalAtlasPath,kExternalAnimationPath);
    bool reload_failed=false;
    constexpr const char* kExternalTerrainPath=
        "sdmc:/switch/vice_project_doom/terrain.vpat";
    vpd::TerrainSource terrain;
    if(!terrain.initialize(vpd_terrain::kAtlasBlob,vpd_terrain::kAtlasBytes)) {
        framebufferClose(&fb);
        if(we_mounted_sd)fsdevUnmountDevice("sdmc");
        return 5;
    }
    if(has_sd)terrain.reload(kExternalTerrainPath);
    bool terrain_reload_failed=false;
    vpd::AnimationPlayer animation;
    vpd::Simulation game;
    while(appletMainLoop()){
        padUpdate(&pad);
        const u64 buttons=padGetButtons(&pad);
        const u64 pressed=padGetButtonsDown(&pad);
        if(buttons&HidNpadButton_Plus)break;
        if(pressed&HidNpadButton_X) {
            const vpd::BundleReload result=has_sd ?
                assets.reload(kExternalAtlasPath,kExternalAnimationPath) :
                vpd::BundleReload::MissingAtlas;
            reload_failed=result!=vpd::BundleReload::LoadedPair &&
                          result!=vpd::BundleReload::LoadedAtlasOnly;
            if(!reload_failed)animation.reset(); // clip counts/ticks may change
        }
        if(pressed&HidNpadButton_Y) {
            assets.reset();
            animation.reset();
            reload_failed=false;
        }
        if(pressed&HidNpadButton_ZL) {
            terrain_reload_failed= !has_sd ||
                terrain.reload(kExternalTerrainPath)!=vpd::TerrainReload::Loaded;
        }
        if(pressed&HidNpadButton_ZR) {
            terrain.reset();
            terrain_reload_failed=false;
        }
        uint8_t input=0;
        if(buttons&(HidNpadButton_Left|HidNpadButton_StickLLeft))input|=vpd::Left;
        if(buttons&(HidNpadButton_Right|HidNpadButton_StickLRight))input|=vpd::Right;
        if(buttons&(HidNpadButton_A|HidNpadButton_B))input|=vpd::Jump;
        game.tick(vpd::Input{input});
        u32 stride=0;
        auto* pixels=static_cast<uint32_t*>(framebufferBegin(&fb,&stride));
        const auto& actor=game.player();
        vpd::SceneView view{
            actor.x/vpd::kFixed,actor.y/vpd::kFixed,game.cameraX(),
            game.frame(),actor.grounded,
            const_cast<vpd::Scene*>(&game.scene()),solidAt
        };
        view.sprite_atlas=&assets.atlas();
        view.external_sprite_asset=assets.externalAtlas();
        view.external_animation_source=assets.externalAnimation();
        view.asset_reload_failed=reload_failed;
        view.moving=actor.vx!=0;
        if(!animation.tick(assets.animation(),
                vpd::MotionSample{actor.grounded,actor.vx!=0,actor.vy,actor.vx}))break;
        view.sprite_frame=animation.frame(assets.animation());
        view.facing_left=animation.facingLeft();
        view.terrain_atlas=&terrain.atlas();
        view.external_terrain_asset=terrain.external();
        view.terrain_reload_failed=terrain_reload_failed;
        const bool drawn=vpd::drawScene(pixels,vpd::kSceneWidth,
                vpd::kSceneHeight,static_cast<int>(stride/sizeof(uint32_t)),view);
        framebufferEnd(&fb);
        if(!drawn)break;
        // Diagnostic pacing only, actual Switch frame timing unmeasured.
        svcSleepThread(16666667);
    }
    framebufferClose(&fb);
    if(we_mounted_sd)fsdevUnmountDevice("sdmc");
    return 0;
}
