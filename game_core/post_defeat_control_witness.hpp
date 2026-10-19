#pragma once
// Source-only proof that the third attempt is actually playable after a
// victory retry followed by a real guard-caused death and second Minus.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kPostDefeatControlPath=
    "sdmc:/switch/vice_project_doom/post_defeat_control_witness.txt";
inline bool writePostDefeatControl(std::FILE* f,const Simulation& game,
                                   uint8_t input,int32_t previous_x,
                                   uint32_t previous_frame){
    constexpr int32_t spawn=3*kTileSize*kFixed;
    constexpr int32_t step=2*kFixed;
    const auto now=game.player().x;
    if(!f || !game.enemyEncounterEnabled() || input!=Right ||
       game.frame()==0 || game.frame()>100 ||
       game.frame()!=previous_frame+1 || previous_x<spawn ||
       now-previous_x!=step || game.player().vx!=step ||
       now<spawn+16*kFixed || now>spawn+120*kFixed ||
       game.playerHealth()!=5 || game.playerHitFlashTicks()!=0 ||
       game.guardEnemy().health!=3 || game.guardEnemy().attacks!=0 ||
       game.sentry().health!=2 || game.shotsFired()!=0 ||
       game.dashEverUsed() || game.secondWaveActive() ||
       game.stageCleared())return false;
    char line[340]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_THIRD_RUN_V1 event=move frame=%u "
        "before_frame=%u before_x=%ld after_x=%ld delta_fixed=%d "
        "hero_hp=5 guard_hp=3 guard_attacks=0 sentry_hp=2 "
        "shots=0 dash=0 wave=0 clear=0 input_right=1 "
        "source=live_guest original_game_proven=no\n",
        game.frame(),previous_frame,static_cast<long>(previous_x),
        static_cast<long>(now),static_cast<int>(step));
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),f)==
               static_cast<std::size_t>(n) &&
           std::fflush(f)==0;
}
inline void resetPostDefeatControl(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kPostDefeatControlPath,"w"))
        std::fclose(f);
}
inline bool appendPostDefeatControl(bool sd,const Simulation& game,
                                    uint8_t input,int32_t previous_x,
                                    uint32_t previous_frame){
    if(!sd)return false;
    std::FILE* f=std::fopen(kPostDefeatControlPath,"a");
    if(!f)return false;
    const bool ok=writePostDefeatControl(f,game,input,
                                          previous_x,previous_frame);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
