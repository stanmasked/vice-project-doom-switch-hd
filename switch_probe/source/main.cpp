// ROM-free Switch fixed-tick gameplay scaffold.
// Contains no recovered game physics, map, sprites, or sound.
#include <switch.h>
#include "simulation.hpp"
#include <cstdio>
#include <cstdint>

namespace {
constexpr int kViewportTiles=40;
void drawAscii(const vpd::Simulation& game){
    std::printf("\x1b[1;1HVICE: PROJECT DOOM | NATIVE GAME SCAFFOLD\n");
    std::printf("ROM-free test scene; NOT original game or HD art.\n");
    std::printf("D-pad: move   A/B: jump   Plus: exit\n");
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
    std::printf("\x1b[2J");
    while(appletMainLoop()){
        padUpdate(&pad);
        const u64 buttons=padGetButtons(&pad);
        if(buttons&HidNpadButton_Plus)break;
        uint8_t input=0;
        if(buttons&(HidNpadButton_Left|HidNpadButton_StickLLeft))input|=vpd::Left;
        if(buttons&(HidNpadButton_Right|HidNpadButton_StickLRight))input|=vpd::Right;
        if(buttons&(HidNpadButton_A|HidNpadButton_B))input|=vpd::Jump;
        game.tick(vpd::Input{input});
        if((game.frame()%2u)==0u){
            drawAscii(game);
            consoleUpdate(nullptr);
        }
        // Preliminary pacing only; not a verified hardware 60 FPS game loop.
        svcSleepThread(16666667);
    }
    consoleExit(nullptr);
    return 0;
}
