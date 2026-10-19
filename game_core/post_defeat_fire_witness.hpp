#pragma once
// Live third-attempt combat proof. Must be driven by the SAME visible NRO
// after victory, defeat and the second source-confirmed Minus replay.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kPostDefeatFirePath=
    "sdmc:/switch/vice_project_doom/post_defeat_fire_witness.txt";
enum class ThirdFireEvent : unsigned { Fire=1, Impact=2 };
inline bool writePostDefeatFire(std::FILE* f,ThirdFireEvent event,
                               const Simulation& game,uint8_t input,
                               uint32_t prior_shots,uint16_t prior_hits,
                               uint8_t prior_guard_hp){
    if(!f || !game.enemyEncounterEnabled() || game.frame()<1 ||
       game.frame()>240 || game.playerHealth()!=5 ||
       game.guardEnemy().attacks!=0 ||
       game.sentry().health!=2 || game.secondWaveActive() ||
       game.stageCleared() || game.dashEverUsed() ||
       game.player().x < (3*16+16)*kFixed ||
       game.player().x > (3*16+80)*kFixed ||
       game.shotsFired()!=1) return false;
    const unsigned seq=static_cast<unsigned>(event);
    const char* name=nullptr;
    if(event==ThirdFireEvent::Fire){
        if(input!=Fire || prior_shots!=0 || prior_hits!=0 ||
           prior_guard_hp!=3 || game.guardEnemy().health!=3 ||
           game.guardEnemy().projectile_hits!=0)return false;
        bool found=false;
        for(const auto& shot:game.projectiles())
            if(shot.active)found=true;
        if(!found)return false;
        name="fire";
    }else if(event==ThirdFireEvent::Impact){
        if(input!=0 || prior_shots!=1 || prior_hits!=0 ||
           prior_guard_hp!=3 || game.guardEnemy().health!=2 ||
           game.guardEnemy().projectile_hits!=1 ||
           game.guardEnemy().hit_flash_ticks==0)return false;
        name="impact";
    }else return false;
    char line[320]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_THIRD_FIRE_V1 seq=%u event=%s frame=%u "
        "hero_x=%ld hero_hp=5 guard_hp=%u guard_hits=%u guard_attacks=0 "
        "shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
        "input_fire=%u source=live_guest original_game_proven=no\n",
        seq,name,game.frame(),static_cast<long>(game.player().x),
        static_cast<unsigned>(game.guardEnemy().health),
        static_cast<unsigned>(game.guardEnemy().projectile_hits),
        event==ThirdFireEvent::Fire?1u:0u);
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),f)==
               static_cast<std::size_t>(n) && std::fflush(f)==0;
}
inline void resetPostDefeatFire(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kPostDefeatFirePath,"w"))
        std::fclose(f);
}
inline bool appendPostDefeatFire(bool sd,ThirdFireEvent event,
                                const Simulation& game,uint8_t input,
                                uint32_t prior_shots,uint16_t prior_hits,
                                uint8_t prior_guard_hp){
    if(!sd)return false;
    std::FILE* f=std::fopen(kPostDefeatFirePath,"a");
    if(!f)return false;
    const bool ok=writePostDefeatFire(f,event,game,input,
                                       prior_shots,prior_hits,prior_guard_hp);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
