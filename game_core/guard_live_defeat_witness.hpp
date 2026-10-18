#pragma once
// ROM-free proof of actual on-screen manual Fire->guard swept hit transitions.
// Records only the authoritative pad-driven Simulation; no offscreen scripts.
#include "simulation.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kLiveGuardDefeatPath =
    "sdmc:/switch/vice_project_doom/guard_live_defeat_witness.txt";
enum class LiveGuardDefeatEvent : unsigned { Fire=1, Impact=2 };

inline bool liveGuardDefeatWrite(
        std::FILE* file,LiveGuardDefeatEvent event,unsigned seq,
        const Simulation& game,uint8_t input,uint8_t health_before,
        uint16_t hits_before,uint32_t shots_before) {
    if(!file || !game.enemyEncounterEnabled() || seq<1 || seq>4 ||
       game.frame()==0 || game.frame()>1200)return false;
    const auto& guard=game.guardEnemy();
    const bool fire=event==LiveGuardDefeatEvent::Fire;
    const unsigned input_fire=(input&Fire)?1u:0u;
    if(fire){
        if(seq!=1 || !input_fire || game.shotsFired()<=shots_before ||
           guard.health==0 || guard.health!=health_before ||
           guard.projectile_hits!=hits_before ||
           guard.x<=game.player().x)return false;
    } else {
        if(seq<2 || health_before==0 ||
           guard.health+1!=health_before ||
           guard.projectile_hits!=hits_before+1 ||
           game.shotsFired()==0)return false;
    }
    if(guard.health>3 || guard.projectile_hits>3)return false;
    const char* name=fire?"fire":(guard.health==0?"defeat":"impact");
    char line[300]{};
    const int len=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=%u event=%s "
        "frame=%u player_x=%ld guard_x=%ld "
        "hp_before=%u hp_after=%u hits_before=%u hits_after=%u "
        "shots=%u input_fire=%u source=live_guest "
        "original_game_proven=no\n",
        seq,name,game.frame(),
        static_cast<long>(game.player().x),static_cast<long>(guard.x),
        static_cast<unsigned>(health_before),
        static_cast<unsigned>(guard.health),
        static_cast<unsigned>(hits_before),
        static_cast<unsigned>(guard.projectile_hits),
        game.shotsFired(),input_fire);
    if(len<=0 || static_cast<std::size_t>(len)>=sizeof(line))return false;
    return std::fwrite(line,1,static_cast<std::size_t>(len),file)==
        static_cast<std::size_t>(len) && std::fflush(file)==0;
}
inline bool liveGuardDefeatReset(bool has_sd){
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* file=std::fopen(kLiveGuardDefeatPath,"w");
    return file && std::fclose(file)==0;
}
inline bool liveGuardDefeatAppend(
        bool has_sd,LiveGuardDefeatEvent event,unsigned seq,
        const Simulation& game,uint8_t input,uint8_t health_before,
        uint16_t hits_before,uint32_t shots_before) {
    if(!has_sd)return false;
    std::FILE* file=std::fopen(kLiveGuardDefeatPath,"a");
    if(!file)return false;
    const bool wrote=liveGuardDefeatWrite(
        file,event,seq,game,input,health_before,hits_before,shots_before);
    return std::fclose(file)==0 && wrote;
}
} // namespace vpd
