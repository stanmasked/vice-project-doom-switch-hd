#pragma once
// Real libnx terminal Minus action, preserved as an independent SD witness.
// The input/transition must have actually occurred in the visible Simulation.
#include "manual_retry.hpp"
#include <cstdio>
#include <cstdint>
#include <cstddef>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kManualRetryGuestPath=
    "sdmc:/switch/vice_project_doom/manual_retry_witness.txt";
struct ManualRetryBefore {
    uint32_t frame=0;
    uint8_t player_health=0;
    uint8_t guard_health=0;
    uint8_t sentry_health=0;
    bool stage_clear=false;
};
inline ManualRetryBefore retryBefore(const Simulation& sim){
    return {sim.frame(),sim.playerHealth(),sim.guardEnemy().health,
            sim.sentry().health,sim.stageCleared()};
}
inline bool writeManualRetryGuest(std::FILE* file,
                                  ManualRetryOutcome outcome,
                                  const ManualRetryBefore& old,
                                  const Simulation& fresh,
                                  bool native_minus_down){
    if(!file || !native_minus_down ||
       outcome==ManualRetryOutcome::Ignored ||
       !fresh.enemyEncounterEnabled() ||
       fresh.frame()!=0 || fresh.playerHealth()!=5 ||
       fresh.guardEnemy().health!=3 || fresh.sentry().health!=2 ||
       fresh.secondWaveActive() || fresh.stageCleared() ||
       fresh.player().x!=3*kTileSize*kFixed ||
       fresh.shotsFired()!=0 || fresh.dashEverUsed() ||
       old.frame<1 || old.frame>2000) return false;
    const char* reason=outcome==ManualRetryOutcome::AfterVictory?
        "victory":"defeat";
    if(outcome==ManualRetryOutcome::AfterVictory &&
       (!old.stage_clear || old.player_health==0 ||
        old.guard_health!=0 || old.sentry_health!=0))return false;
    if(outcome==ManualRetryOutcome::AfterDefeat &&
       (old.stage_clear || old.player_health!=0))return false;
    char line[350]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_MANUAL_RETRY_V1 event=restart reason=%s "
        "old_frame=%u old_hp=%u old_guard_hp=%u old_sentry_hp=%u "
        "old_clear=%u new_frame=%u new_x=%ld new_hp=%u "
        "new_guard_hp=%u new_sentry_hp=%u wave=0 clear=0 "
        "input_minus=1 source=live_guest original_game_proven=no\n",
        reason,old.frame,static_cast<unsigned>(old.player_health),
        static_cast<unsigned>(old.guard_health),
        static_cast<unsigned>(old.sentry_health),
        old.stage_clear?1u:0u,fresh.frame(),
        static_cast<long>(fresh.player().x),
        static_cast<unsigned>(fresh.playerHealth()),
        static_cast<unsigned>(fresh.guardEnemy().health),
        static_cast<unsigned>(fresh.sentry().health));
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),file)==
               static_cast<std::size_t>(n) && std::fflush(file)==0;
}
inline void resetManualRetryGuest(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kManualRetryGuestPath,"w"))
        std::fclose(f);
}
inline bool appendManualRetryGuest(bool sd,ManualRetryOutcome outcome,
                                   const ManualRetryBefore& old,
                                   const Simulation& game,bool minus){
    if(!sd)return false;
    std::FILE* f=std::fopen(kManualRetryGuestPath,"a");
    if(!f)return false;
    const bool ok=writeManualRetryGuest(f,outcome,old,game,minus);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
