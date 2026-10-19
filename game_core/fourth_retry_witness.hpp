#pragma once
// The third FULL earned stage victory must permit a fourth independently
// pad-controlled clean retry. This original ROM-free homebrew is not NES parity.
#include "manual_retry_guest_witness.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kFourthRetryPath=
    "sdmc:/switch/vice_project_doom/fourth_retry_witness.txt";
inline bool fourthFresh(const Simulation& game){
    return game.enemyEncounterEnabled() && !game.secondWaveActive() &&
        !game.stageCleared() && game.playerHealth()==5 &&
        game.playerHitFlashTicks()==0 && game.guardEnemy().health==3 &&
        game.guardEnemy().attacks==0 && game.sentry().health==2 &&
        game.shotsFired()==0 && !game.dashEverUsed();
}
inline bool writeFourthRestart(std::FILE* file,
                               ManualRetryOutcome result,
                               const ManualRetryBefore& before,
                               const Simulation& fresh,bool minus){
    if(!file || !minus || result!=ManualRetryOutcome::AfterVictory ||
       !before.stage_clear || before.player_health==0 ||
       before.guard_health!=0 || before.sentry_health!=0 ||
       before.frame<1 || before.frame>1200 ||
       !fourthFresh(fresh) || fresh.frame()!=0 ||
       fresh.player().x!=3*kTileSize*kFixed)return false;
    char line[370]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_FOURTH_RETRY_V1 seq=1 event=restart "
        "old_frame=%u old_hp=%u old_guard_hp=0 old_sentry_hp=0 "
        "old_clear=1 new_frame=0 new_x=%ld hero_hp=5 guard_hp=3 "
        "sentry_hp=2 wave=0 clear=0 input_minus=1 "
        "source=live_guest original_game_proven=no\n",
        before.frame,static_cast<unsigned>(before.player_health),
        static_cast<long>(fresh.player().x));
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),file)==
               static_cast<std::size_t>(n) && std::fflush(file)==0;
}
inline bool writeFourthMove(std::FILE* file,const Simulation& game,
                            uint8_t input,int32_t before_x,
                            uint32_t before_frame){
    const int32_t spawn=3*kTileSize*kFixed;
    if(!file || input!=Right || !fourthFresh(game) ||
       game.frame()<8 || game.frame()>100 ||
       game.frame()!=before_frame+1 ||
       before_x<spawn || game.player().x-before_x!=2*kFixed ||
       game.player().vx!=2*kFixed ||
       game.player().x<spawn+16*kFixed ||
       game.player().x>spawn+120*kFixed)return false;
    char line[340]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_FOURTH_RETRY_V1 seq=2 event=move "
        "frame=%u before_frame=%u before_x=%ld after_x=%ld "
        "delta_fixed=%d hero_hp=5 guard_hp=3 sentry_hp=2 "
        "guard_attacks=0 shots=0 wave=0 clear=0 input_right=1 "
        "source=live_guest original_game_proven=no\n",
        game.frame(),before_frame,static_cast<long>(before_x),
        static_cast<long>(game.player().x),2*kFixed);
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),file)==
               static_cast<std::size_t>(n) && std::fflush(file)==0;
}
inline void resetFourthRetry(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kFourthRetryPath,"w"))std::fclose(f);
}
inline bool appendFourthRestart(bool sd,ManualRetryOutcome result,
                                const ManualRetryBefore& before,
                                const Simulation& fresh,bool minus){
    if(!sd)return false;
    std::FILE* f=std::fopen(kFourthRetryPath,"a");
    if(!f)return false;
    const bool ok=writeFourthRestart(f,result,before,fresh,minus);
    return std::fclose(f)==0 && ok;
}
inline bool appendFourthMove(bool sd,const Simulation& game,
                             uint8_t input,int32_t before_x,
                             uint32_t before_frame){
    if(!sd)return false;
    std::FILE* f=std::fopen(kFourthRetryPath,"a");
    if(!f)return false;
    const bool ok=writeFourthMove(f,game,input,before_x,before_frame);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
