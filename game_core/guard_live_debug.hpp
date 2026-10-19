#pragma once
// Optional low-volume native-only debug trace; never counts as PASS evidence.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kGuardLiveDebugPath =
    "sdmc:/switch/vice_project_doom/guard_live_debug.txt";
inline void guardLiveDebugReset(bool has_sd){
    if(!has_sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kGuardLiveDebugPath,"w"))std::fclose(f);
}
inline void guardLiveDebugRecord(bool has_sd,const char* event,
                                 const Simulation& game,unsigned input){
    if(!has_sd)return;
    std::FILE* f=std::fopen(kGuardLiveDebugPath,"a");
    if(!f)return;
    const auto& guard=game.guardEnemy();
    std::fprintf(f,
        "VPD_GUARD_LIVE_DEBUG event=%s frame=%u hero_x=%ld "
        "guard_x=%ld guard_hp=%u hero_hp=%u alert=%u attacks=%u "
        "input=%u proof_only=no\n",
        event,game.frame(),static_cast<long>(game.player().x),
        static_cast<long>(guard.x),static_cast<unsigned>(guard.health),
        static_cast<unsigned>(game.playerHealth()),
        guard.alerted?1u:0u,static_cast<unsigned>(guard.attacks),input);
    std::fclose(f);
}
} // namespace vpd
