#pragma once
// Guest-side ROM-free dash witness. Serialized only after simulation effects.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kDashGuestProofPath =
    "sdmc:/switch/vice_project_doom/dash_witness.txt";
enum class DashGuestEvent : unsigned { Start=1, Complete=2 };

inline bool dashGuestProofWrite(std::FILE* out,DashGuestEvent event,
                                const Simulation& game,int32_t delta_fixed) {
    if(!out || !game.dashEverUsed() || game.frame()==0)return false;
    unsigned seq=static_cast<unsigned>(event);
    const bool correct=(event==DashGuestEvent::Start &&
                        delta_fixed==6*kFixed && game.dashing() &&
                        game.dashCooldown()==45) ||
                       (event==DashGuestEvent::Complete &&
                        delta_fixed==36*kFixed && !game.dashing() &&
                        game.dashCooldown()==40);
    if(!correct)return false;
    const char* name=event==DashGuestEvent::Start?"start":"complete";
    char text[200]{};
    int len=std::snprintf(
        text,sizeof(text),
        "VPD_ROMFREE_DASH_V1 seq=%u event=%s frame=%u "
        "delta_fixed=%ld cooldown=%u source=ZR+Right "
        "mode=manual original_game_proven=no\n",
        seq,name,game.frame(),static_cast<long>(delta_fixed),
        static_cast<unsigned>(game.dashCooldown()));
    if(len<=0 || static_cast<std::size_t>(len)>=sizeof(text))return false;
    return std::fwrite(text,1,static_cast<std::size_t>(len),out)==
           static_cast<std::size_t>(len) && std::fflush(out)==0;
}
inline bool dashGuestProofReset(bool has_sd){
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* out=std::fopen(kDashGuestProofPath,"w");
    return out && std::fclose(out)==0;
}
inline bool dashGuestProofAppend(bool has_sd,DashGuestEvent event,
                                 const Simulation& game,int32_t delta_fixed){
    if(!has_sd)return false;
    std::FILE* out=std::fopen(kDashGuestProofPath,"a");
    if(!out)return false;
    const bool ok=dashGuestProofWrite(out,event,game,delta_fixed);
    return std::fclose(out)==0 && ok;
}
} // namespace vpd
