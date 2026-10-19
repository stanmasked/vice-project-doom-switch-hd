#pragma once
// Native guest-only witness: actual loss and Minus restart in the same
// visible, live pad-controlled Simulation after an already proven victory.
#include "manual_retry_guest_witness.hpp"
#include <cstdio>
#include <cstdint>
#include <cstddef>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kLiveDefeatRetryPath=
    "sdmc:/switch/vice_project_doom/live_defeat_retry_witness.txt";
enum class DefeatRetryEvent : unsigned { Contact=1, Death=2, Restart=3 };
inline bool writeLiveDefeatRetry(std::FILE* f,DefeatRetryEvent event,
                                const Simulation& game,uint8_t input,
                                bool minus_pressed=false,
                                const ManualRetryBefore& before={},
                                ManualRetryOutcome outcome=
                                    ManualRetryOutcome::Ignored){
    if(!f || !game.enemyEncounterEnabled() ||
       game.guardEnemy().health!=3 || game.secondWaveActive() ||
       game.stageCleared() || game.frame()>1200)return false;
    if(event==DefeatRetryEvent::Contact){
        if(!(input&Right) || game.frame()==0 ||
           game.guardEnemy().attacks!=1 ||
           game.playerHealth()!=4 ||
           outcome!=ManualRetryOutcome::Ignored)return false;
    }else if(event==DefeatRetryEvent::Death){
        if(game.frame()==0 || game.playerHealth()!=0 ||
           // Exactly five melee blows exhaust the five-point HP pool.
           // A count greater than five is not reachable after terminal
           // freeze, and must never be accepted as native evidence.
           game.guardEnemy().attacks!=5 ||
           outcome!=ManualRetryOutcome::Ignored)return false;
    }else if(event==DefeatRetryEvent::Restart){
        if(!minus_pressed || outcome!=ManualRetryOutcome::AfterDefeat ||
           before.player_health!=0 || before.guard_health!=3 ||
           before.stage_clear || before.frame==0 ||
           game.frame()!=0 || game.playerHealth()!=5 ||
           game.guardEnemy().attacks!=0 ||
           game.player().x!=3*kTileSize*kFixed ||
           game.sentry().health!=2 || game.shotsFired()!=0 ||
           game.dashEverUsed())return false;
    }else return false;
    static constexpr const char* names[]={"contact","death","restart"};
    const unsigned seq=static_cast<unsigned>(event);
    char line[340]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_DEFEAT_RETRY_V1 seq=%u event=%s frame=%u "
        "hero_x=%ld hero_hp=%u guard_hp=%u guard_attacks=%u "
        "sentry_hp=%u wave=0 clear=0 input_right=%u input_minus=%u "
        "old_frame=%u old_hp=%u source=live_guest "
        "original_game_proven=no\n",
        seq,names[seq-1],game.frame(),
        static_cast<long>(game.player().x),
        static_cast<unsigned>(game.playerHealth()),
        static_cast<unsigned>(game.guardEnemy().health),
        static_cast<unsigned>(game.guardEnemy().attacks),
        static_cast<unsigned>(game.sentry().health),
        (input&Right)?1u:0u,minus_pressed?1u:0u,
        event==DefeatRetryEvent::Restart?before.frame:0,
        event==DefeatRetryEvent::Restart?before.player_health:0);
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),f)==
               static_cast<std::size_t>(n) && std::fflush(f)==0;
}
inline void resetLiveDefeatRetry(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kLiveDefeatRetryPath,"w"))std::fclose(f);
}
inline bool appendLiveDefeatRetry(bool sd,DefeatRetryEvent event,
                                 const Simulation& game,uint8_t input,
                                 bool minus_pressed=false,
                                 const ManualRetryBefore& before={},
                                 ManualRetryOutcome outcome=
                                     ManualRetryOutcome::Ignored){
    if(!sd)return false;
    std::FILE* f=std::fopen(kLiveDefeatRetryPath,"a");
    if(!f)return false;
    const bool ok=writeLiveDefeatRetry(f,event,game,input,
                                       minus_pressed,before,outcome);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
