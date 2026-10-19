#pragma once
// A third-playthrough first-guard kill witnessed from real pad-driven gameplay.
// This is NOT evidence that original NES Vice mechanics have been recovered.
#include "simulation.hpp"
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kThirdGuardClearPath=
    "sdmc:/switch/vice_project_doom/third_guard_clear_witness.txt";
inline bool writeThirdGuardClear(std::FILE* f,const Simulation& game,
                                uint8_t input,uint8_t previous_guard_hp,
                                uint16_t previous_hits){
    const auto& guard=game.guardEnemy();
    const uint32_t shots=game.shotsFired();
    if(!f || !game.enemyEncounterEnabled() || input!=Fire ||
       game.frame()==0 || game.frame()>300 ||
       game.playerHealth()!=5 || guard.attacks!=0 ||
       previous_guard_hp!=1 || previous_hits!=2 ||
       guard.health!=0 || guard.projectile_hits!=3 ||
       shots<3 || shots>15 || game.sentry().health!=2 ||
       game.secondWaveActive() || game.stageCleared() ||
       game.dashEverUsed() ||
       game.player().x < (3*16+16)*kFixed ||
       game.player().x > (3*16+80)*kFixed)return false;
    char line[300]{};
    const int size=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_THIRD_GUARD_CLEAR_V1 event=guard_clear frame=%u "
        "hero_x=%ld hero_hp=5 guard_hp=0 previous_guard_hp=1 "
        "guard_hits=3 previous_guard_hits=2 guard_attacks=0 shots=%u "
        "sentry_hp=2 wave=0 clear=0 dash=0 input_fire=1 "
        "source=live_guest original_game_proven=no\n",
        game.frame(),static_cast<long>(game.player().x),shots);
    return size>0 && static_cast<std::size_t>(size)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(size),f)==
               static_cast<std::size_t>(size) &&
           std::fflush(f)==0;
}
inline void resetThirdGuardClear(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kThirdGuardClearPath,"w"))
        std::fclose(f);
}
inline bool appendThirdGuardClear(bool sd,const Simulation& game,
                                  uint8_t input,uint8_t previous_guard_hp,
                                  uint16_t previous_hits){
    if(!sd)return false;
    std::FILE* f=std::fopen(kThirdGuardClearPath,"a");
    if(!f)return false;
    const bool ok=writeThirdGuardClear(
        f,game,input,previous_guard_hp,previous_hits);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
