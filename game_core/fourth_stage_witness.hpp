#pragma once
// Native fourth-playthrough stage-two milestone, only after the same manual
// gameplay has earned victory, suffered defeat, restarted and killed guard.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kFourthStagePath=
    "sdmc:/switch/vice_project_doom/fourth_stage_witness.txt";
enum class FourthStageEvent: unsigned { Wave=1, Exit=2 };
inline bool writeFourthStage(std::FILE* f,FourthStageEvent event,
                            const Simulation& game,uint8_t input){
    if(!f || !game.enemyEncounterEnabled() ||
       game.frame()==0 || game.frame()>1200 ||
       game.playerHealth()==0 || game.guardEnemy().health!=0 ||
       game.guardEnemy().projectile_hits!=3 ||
       !game.secondWaveActive() || game.dashEverUsed())return false;
    const unsigned seq=static_cast<unsigned>(event);
    const char* name=nullptr;
    if(event==FourthStageEvent::Wave){
        if(!(input&Right) || game.stageCleared() ||
           game.sentry().health!=2 ||
           game.player().x<26*kTileSize*kFixed)return false;
        name="wave";
    }else if(event==FourthStageEvent::Exit){
        if((input&(Right|Fire))!=(Right|Fire) ||
           !game.stageCleared() || game.sentry().health!=0 ||
           game.sentry().projectile_hits!=2 ||
           game.player().x<55*kTileSize*kFixed)return false;
        name="exit";
    }else return false;
    char line[340]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_FOURTH_STAGE_V1 seq=%u event=%s frame=%u "
        "hero_x=%ld hero_hp=%u guard_hp=0 guard_hits=3 "
        "sentry_hp=%u sentry_hits=%u wave=1 clear=%u "
        "input_right=%u input_fire=%u source=live_guest "
        "original_game_proven=no\n",
        seq,name,game.frame(),static_cast<long>(game.player().x),
        static_cast<unsigned>(game.playerHealth()),
        static_cast<unsigned>(game.sentry().health),
        static_cast<unsigned>(game.sentry().projectile_hits),
        game.stageCleared()?1u:0u,
        (input&Right)?1u:0u,(input&Fire)?1u:0u);
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),f)==
               static_cast<std::size_t>(n) && std::fflush(f)==0;
}
inline void resetFourthStage(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kFourthStagePath,"w"))std::fclose(f);
}
inline bool appendFourthStage(bool sd,FourthStageEvent event,
                             const Simulation& game,uint8_t input){
    if(!sd)return false;
    std::FILE* f=std::fopen(kFourthStagePath,"a");
    if(!f)return false;
    const bool ok=writeFourthStage(f,event,game,input);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
