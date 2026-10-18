#pragma once
// Guest-generated proof of actual ROM-free guard physics, not host injection.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kGuardProofPath =
    "sdmc:/switch/vice_project_doom/guard_witness.txt";
enum class GuardProofEvent : unsigned { FirstStep=1, Patrol=2 };
inline bool guardProofWrite(std::FILE* stream, GuardProofEvent event,
                            const Simulation& game) {
    const unsigned sequence=static_cast<unsigned>(event);
    if(!stream || !game.enemyEncounterEnabled())return false;
    const GuardEnemy& enemy=game.guardEnemy();
    const unsigned expected_frame=event==GuardProofEvent::FirstStep?1u:8u;
    const int32_t expected_x=(16*kTileSize+static_cast<int>(expected_frame))*kFixed;
    if(game.frame()!=expected_frame || enemy.x!=expected_x ||
       enemy.health!=3 || enemy.alerted || enemy.attacks!=0 ||
       enemy.projectile_hits!=0 || game.playerHealth()!=5)return false;
    const char* name=event==GuardProofEvent::FirstStep?"first":"patrol";
    char line[200]{};
    const int size=std::snprintf(line,sizeof(line),
        "VPD_ROMFREE_GUARD_V1 seq=%u event=%s frame=%u "
        "x_fixed=%ld hp=3 alerted=0 source=guest "
        "original_game_proven=no\n",
        sequence,name,game.frame(),static_cast<long>(enemy.x));
    if(size<=0 || static_cast<std::size_t>(size)>=sizeof(line))return false;
    return std::fwrite(line,1,static_cast<std::size_t>(size),stream)==
           static_cast<std::size_t>(size) && std::fflush(stream)==0;
}
inline bool guardProofReset(bool has_sd) {
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* f=std::fopen(kGuardProofPath,"w");
    return f && std::fclose(f)==0;
}
inline bool guardProofAppend(bool has_sd,GuardProofEvent e,
                             const Simulation& game) {
    if(!has_sd)return false;
    std::FILE* f=std::fopen(kGuardProofPath,"a");
    if(!f)return false;
    const bool ok=guardProofWrite(f,e,game);
    return std::fclose(f)==0 && ok;
}
}
