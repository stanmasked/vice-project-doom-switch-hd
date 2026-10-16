// Independent libnx native raster scene; no NES emulator or proprietary art.
#include <switch.h>
#include "simulation.hpp"
#include "scene_renderer.hpp"
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
    vpd::Simulation game;
    while(appletMainLoop()){
        padUpdate(&pad);
        const u64 buttons=padGetButtons(&pad);
        if(buttons&HidNpadButton_Plus)break;
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
        const bool drawn=vpd::drawScene(pixels,vpd::kSceneWidth,
                vpd::kSceneHeight,static_cast<int>(stride/sizeof(uint32_t)),view);
        framebufferEnd(&fb);
        if(!drawn)break;
        // Diagnostic pacing only, actual Switch frame timing unmeasured.
        svcSleepThread(16666667);
    }
    framebufferClose(&fb);
    return 0;
}
