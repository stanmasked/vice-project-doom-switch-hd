#pragma once
// Synthetic homebrew guest input witness. Not an authenticated attestation.
#include "simulation.hpp"
#include <cstdio>
#include <cstdint>
#include <sys/stat.h>

namespace vpd {
enum class ManualProofEvent : unsigned {
    Enter=1, Right=2, Fire=3, Jump=4, Left=5, Plus=6, Exit=7
};
constexpr const char* kManualProofPath=
    "sdmc:/switch/vice_project_doom/manual_witness.txt";
inline const char* manualProofEventName(ManualProofEvent event) {
    switch(event) {
        case ManualProofEvent::Enter: return "enter";
        case ManualProofEvent::Right: return "right";
        case ManualProofEvent::Fire: return "fire";
        case ManualProofEvent::Jump: return "jump";
        case ManualProofEvent::Left: return "left";
        case ManualProofEvent::Plus: return "plus";
        case ManualProofEvent::Exit: return "exit";
    }
    return "invalid";
}
inline bool manualProofValid(ManualProofEvent event,
                             const Simulation& game,int32_t metric) {
    if(metric<=0 || game.trainingTarget().health>3) return false;
    switch(event) {
        case ManualProofEvent::Enter: return game.frame()==0 &&
               game.shotsFired()==0 && game.trainingTarget().health==3;
        case ManualProofEvent::Right:
        case ManualProofEvent::Fire:
        case ManualProofEvent::Jump:
        case ManualProofEvent::Left: return game.frame()>0;
        case ManualProofEvent::Plus:
        case ManualProofEvent::Exit: return game.frame()>0;
    }
    return false;
}
// The caller supplies real before/after deltas observed after game.tick().
// A line must never claim a key caused movement when no change occurred.
inline bool manualProofWrite(std::FILE* stream,ManualProofEvent event,
                             unsigned seq,const Simulation& game,
                             int32_t metric) {
    if(!stream || seq!=static_cast<unsigned>(event) ||
       !manualProofValid(event,game,metric))
        return false;
    char buf[192]{};
    const int length=std::snprintf(
        buf,sizeof(buf),
        "VPD_ROMFREE_MANUAL_V1 seq=%u event=%s frame=%u metric=%ld "
        "mode=manual original_game_proven=no\n",
        seq,manualProofEventName(event),game.frame(),
        static_cast<long>(metric));
    if(length<=0 || static_cast<std::size_t>(length)>=sizeof(buf))
        return false;
    return std::fwrite(buf,1,static_cast<std::size_t>(length),stream)==
           static_cast<std::size_t>(length) && std::fflush(stream)==0;
}
inline bool manualProofAppend(bool has_sd,ManualProofEvent event,
                              unsigned seq,const Simulation& game,
                              int32_t metric) {
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* file=std::fopen(kManualProofPath,"a");
    if(!file)return false;
    const bool ok=manualProofWrite(file,event,seq,game,metric);
    return std::fclose(file)==0 && ok;
}
inline bool manualProofReset(bool has_sd) {
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* file=std::fopen(kManualProofPath,"w");
    return file && std::fclose(file)==0;
}
} // namespace vpd
