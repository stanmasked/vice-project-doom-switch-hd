#pragma once
// Guest-native fourth playthrough: the freshly restored first guard dies
// from a third real swept projectile collision in the visible manual NRO.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kFourthGuardClearPath=
    "sdmc:/switch/vice_project_doom/fourth_guard_clear_witness.txt";
inline bool writeFourthGuardClear(std::FILE* f,const Simulation& game,
                                 uint8_t input,uint8_t before_guard_hp,
                                 uint16_t before_guard_hits){
    const auto& guard=game.guardEnemy();
    if(!f || !game.enemyEncounterEnabled() || input!=Fire ||
       game.frame()<1 || game.frame()>300 ||
       game.playerHealth()!=5 || game.playerHitFlashTicks()!=0 ||
       guard.attacks!=0 || before_guard_hp!=1 ||
       before_guard_hits!=2 || guard.health!=0 ||
       guard.projectile_hits!=3 || game.shotsFired()<3 ||
       game.shotsFired()>15 || game.sentry().health!=2 ||
       game.secondWaveActive() || game.stageCleared() ||
       game.dashEverUsed() ||
       game.player().x<(3*16+16)*kFixed ||
       game.player().x>(3*16+80)*kFixed)return false;
    char row[320]{};
    const int n=std::snprintf(
        row,sizeof(row),
        "VPD_ROMFREE_FOURTH_GUARD_CLEAR_V1 event=guard_clear "
        "frame=%u hero_x=%ld hero_hp=5 guard_hp=0 "
        "previous_guard_hp=1 guard_hits=3 previous_guard_hits=2 "
        "guard_attacks=0 shots=%u sentry_hp=2 wave=0 clear=0 dash=0 "
        "input_fire=1 source=live_guest original_game_proven=no\n",
        game.frame(),static_cast<long>(game.player().x),game.shotsFired());
    return n>0 && static_cast<std::size_t>(n)<sizeof(row) &&
           std::fwrite(row,1,static_cast<std::size_t>(n),f)==
           static_cast<std::size_t>(n) && std::fflush(f)==0;
}
inline void resetFourthGuardClear(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(auto* f=std::fopen(kFourthGuardClearPath,"w"))std::fclose(f);
}
inline bool appendFourthGuardClear(bool sd,const Simulation& game,
                                  uint8_t input,uint8_t before_guard_hp,
                                  uint16_t before_guard_hits){
    if(!sd)return false;
    auto* f=std::fopen(kFourthGuardClearPath,"a");
    if(!f)return false;
    const bool ok=writeFourthGuardClear(
        f,game,input,before_guard_hp,before_guard_hits);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
