// ROM-free Switch fixed-tick gameplay scaffold.
// Contains no recovered game physics, map, sprites, or sound.
#include <switch.h>
#include "simulation.hpp"
#include "combat_demo.hpp"
#include "demo_witness_sd.hpp"
#include <cstdio>
#include <cstdint>

namespace {
constexpr int kViewportTiles=40;
void drawAscii(const vpd::Simulation& game,bool replay_demo,bool checkpoint_ok){
    std::printf("\x1b[1;1HVICE: PROJECT DOOM | NATIVE GAME SCAFFOLD\n");
    std::printf("ROM-free test scene; NOT original game or HD art.\n");
    if(replay_demo && checkpoint_ok)
        std::printf("DEMO CORE STATE MATCH (frame 200 verified)\n");
    std::printf("MODE: %s (StickL click to toggle)\n",
                replay_demo?"REPLAY DEMO":"MANUAL");
    std::printf("D-pad: move   A/B: jump   Y: fire   Plus: exit\n");
    std::printf("Target health: %u / 3 | hits: %u\n",
        static_cast<unsigned>(game.trainingTarget().health),
        static_cast<unsigned>(game.trainingTarget().hits));
    std::printf("Frame: %-7u X: %-5ld Y: %-5ld Ground: %d\n",
        game.frame(),static_cast<long>(game.player().x/vpd::kFixed),
        static_cast<long>(game.player().y/vpd::kFixed),
        game.player().grounded?1:0);
    std::printf("\n");
    const int camera_tile=game.cameraX()/vpd::kTileSize;
    const int hero_x=game.player().x/(vpd::kFixed*vpd::kTileSize);
    const int hero_y=(game.player().y+vpd::kPlayerHeight*vpd::kFixed/2)/
                      (vpd::kFixed*vpd::kTileSize);
    for(int y=0;y<vpd::kMapHeight;++y){
        char row[kViewportTiles+1];
        for(int x=0;x<kViewportTiles;++x){
            const int world_x=x+camera_tile;
            row[x]=game.scene().cell(world_x,y);
            const auto& target=game.trainingTarget();
            if(target.health>0 &&
               world_x==target.x/(vpd::kFixed*vpd::kTileSize) &&
               y==target.y/(vpd::kFixed*vpd::kTileSize))
                row[x]='T';
            for(const auto& shot:game.projectiles()){
                if(!shot.active)continue;
                const int sx=shot.x/(vpd::kFixed*vpd::kTileSize);
                const int sy=shot.y/(vpd::kFixed*vpd::kTileSize);
                if(world_x==sx && y==sy)row[x]='*';
            }
            if(world_x==hero_x && y==hero_y)row[x]='@';
        }
        row[kViewportTiles]='\0';
        std::printf("|%s|\n",row);
    }
    std::printf("\nThis is a deterministic physics demonstrator.   \n");
}
}
int main(int,char**){
    consoleInit(nullptr);
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    vpd::Simulation game;
    vpd::CombatDemo demo;
    const Result sd_mount=fsdevMountSdmc();
    const bool we_mounted_sd=R_SUCCEEDED(sd_mount);
    const bool has_sd=we_mounted_sd ||
                      fsdevGetDeviceFileSystem("sdmc")!=nullptr;
    unsigned witness_cycles=0;
    bool checkpoint_ok=false;
    std::printf("\x1b[2J");
    while(appletMainLoop()){
        padUpdate(&pad);
        const u64 buttons=padGetButtons(&pad);
        const u64 pressed=padGetButtonsDown(&pad);
        if(buttons&HidNpadButton_Plus)break;
        if(pressed&HidNpadButton_StickL){
            demo.toggle(game);
            checkpoint_ok=false;
        }
        uint8_t input=0;
        if(buttons&(HidNpadButton_Left|HidNpadButton_StickLLeft))input|=vpd::Left;
        if(buttons&(HidNpadButton_Right|HidNpadButton_StickLRight))input|=vpd::Right;
        if(buttons&(HidNpadButton_A|HidNpadButton_B))input|=vpd::Jump;
        if(buttons&HidNpadButton_Y)input|=vpd::Fire;
        if(demo.enabled())demo.tick(game);
        else game.tick(vpd::Input{input});
        if((game.frame()%2u)==0u){
            drawAscii(game,demo.enabled(),checkpoint_ok);
            consoleUpdate(nullptr);
        }
        // A record is possible only after a successful terminal update.
        if(vpd::demoCheckpointReached(demo,game)){
            checkpoint_ok=vpd::demoCheckpointMatches(game);
            if(witness_cycles<vpd::kDemoWitnessMaxRecords){
                ++witness_cycles;
                (void)vpd::persistDemoWitness(game,witness_cycles,has_sd);
            }
        }
        // Preliminary pacing only; not a verified hardware 60 FPS game loop.
        svcSleepThread(16666667);
    }
    if(we_mounted_sd)fsdevUnmountDevice("sdmc");
    consoleExit(nullptr);
    return 0;
}
