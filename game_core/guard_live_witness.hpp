#pragma once
// Strict observation of the visible/manual ROM-free guard encounter.
// Unlike guard_combat_probe.hpp this reads the real pad-driven Simulation,
// not a separate scripted test instance.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kLiveGuardProofPath =
    "sdmc:/switch/vice_project_doom/guard_live_witness.txt";
enum class LiveGuardEvent : unsigned { Alert=1, FirstStrike=2 };

inline bool liveGuardProofWrite(std::FILE* file,LiveGuardEvent event,
                                const Simulation& game,uint8_t input) {
    if(!file || !game.enemyEncounterEnabled() || !(input&Right))
        return false;
    const auto& enemy=game.guardEnemy();
    const bool is_alert=event==LiveGuardEvent::Alert;
    if(game.frame()==0 || game.frame()>1200 || !enemy.alerted ||
       enemy.health!=3 || enemy.projectile_hits!=0 ||
       game.player().x<0 || game.player().x>kMapWidth*kTileSize*kFixed ||
       enemy.x<14*kTileSize*kFixed || enemy.x>20*kTileSize*kFixed ||
       (is_alert &&
        (game.playerHealth()!=5 || enemy.attacks!=0 ||
         enemy.attack_cooldown!=0)) ||
       (!is_alert &&
        (game.playerHealth()!=4 || enemy.attacks!=1 ||
         enemy.attack_cooldown!=32)))return false;
    const unsigned seq=static_cast<unsigned>(event);
    const char* name=is_alert?"alert":"strike";
    char line[248]{};
    const int len=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_GUARD_LIVE_V1 seq=%u event=%s frame=%u "
        "player_x=%ld guard_x=%ld player_hp=%u guard_hp=3 "
        "attacks=%u cooldown=%u alerted=1 input_right=1 "
        "source=live_guest original_game_proven=no\n",
        seq,name,game.frame(),
        static_cast<long>(game.player().x),
        static_cast<long>(enemy.x),
        static_cast<unsigned>(game.playerHealth()),
        static_cast<unsigned>(enemy.attacks),
        static_cast<unsigned>(enemy.attack_cooldown));
    if(len<=0 || static_cast<std::size_t>(len)>=sizeof(line))return false;
    return std::fwrite(line,1,static_cast<std::size_t>(len),file)==
           static_cast<std::size_t>(len) && std::fflush(file)==0;
}
inline bool liveGuardProofReset(bool has_sd){
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* f=std::fopen(kLiveGuardProofPath,"w");
    return f && std::fclose(f)==0;
}
inline bool liveGuardProofAppend(bool has_sd,LiveGuardEvent event,
                                 const Simulation& game,uint8_t input){
    if(!has_sd)return false;
    std::FILE* f=std::fopen(kLiveGuardProofPath,"a");
    if(!f)return false;
    const bool ok=liveGuardProofWrite(f,event,game,input);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
