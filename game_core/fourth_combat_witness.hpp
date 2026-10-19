#pragma once
// Source-only fourth-attempt firearm proof. Requires a genuine third-victory
// Minus and physical fourth-run movement in the visible NRO.
#include "simulation.hpp"
#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kFourthCombatPath=
    "sdmc:/switch/vice_project_doom/fourth_combat_witness.txt";
enum class FourthCombatEvent : unsigned { Fire=1, Impact=2 };
inline bool writeFourthCombat(std::FILE* f,FourthCombatEvent event,
                              const Simulation& game,uint8_t input,
                              uint32_t previous_shots,
                              uint16_t previous_hits,
                              uint8_t previous_guard_hp){
    if(!f || !game.enemyEncounterEnabled() || game.frame()<1 ||
       game.frame()>240 || game.playerHealth()!=5 ||
       game.guardEnemy().attacks!=0 || game.sentry().health!=2 ||
       game.secondWaveActive() || game.stageCleared() ||
       game.dashEverUsed() ||
       game.player().x < (3*16+16)*kFixed ||
       game.player().x > (3*16+80)*kFixed ||
       game.shotsFired()!=1)return false;
    const unsigned seq=static_cast<unsigned>(event);
    const char* label=nullptr;
    if(event==FourthCombatEvent::Fire){
        if(input!=Fire || previous_shots!=0 || previous_hits!=0 ||
           previous_guard_hp!=3 || game.guardEnemy().health!=3 ||
           game.guardEnemy().projectile_hits!=0)return false;
        bool active=false;
        for(const auto& shot:game.projectiles())
            if(shot.active)active=true;
        if(!active)return false;
        label="fire";
    }else if(event==FourthCombatEvent::Impact){
        if(input!=0 || previous_shots!=1 || previous_hits!=0 ||
           previous_guard_hp!=3 || game.guardEnemy().health!=2 ||
           game.guardEnemy().projectile_hits!=1 ||
           game.guardEnemy().hit_flash_ticks==0)return false;
        label="impact";
    }else return false;
    char line[340]{};
    const int len=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_FOURTH_COMBAT_V1 seq=%u event=%s frame=%u "
        "hero_x=%ld hero_hp=5 guard_hp=%u guard_hits=%u guard_attacks=0 "
        "shots=1 sentry_hp=2 wave=0 clear=0 dash=0 "
        "input_fire=%u source=live_guest original_game_proven=no\n",
        seq,label,game.frame(),static_cast<long>(game.player().x),
        static_cast<unsigned>(game.guardEnemy().health),
        static_cast<unsigned>(game.guardEnemy().projectile_hits),
        event==FourthCombatEvent::Fire?1u:0u);
    return len>0 && static_cast<std::size_t>(len)<sizeof(line) &&
        std::fwrite(line,1,static_cast<std::size_t>(len),f)==
            static_cast<std::size_t>(len) && std::fflush(f)==0;
}
inline void resetFourthCombat(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kFourthCombatPath,"w"))
        std::fclose(f);
}
inline bool appendFourthCombat(bool sd,FourthCombatEvent event,
                               const Simulation& game,uint8_t input,
                               uint32_t previous_shots,uint16_t previous_hits,
                               uint8_t previous_guard_hp){
    if(!sd)return false;
    std::FILE* f=std::fopen(kFourthCombatPath,"a");
    if(!f)return false;
    const bool ok=writeFourthCombat(f,event,game,input,
                                     previous_shots,previous_hits,
                                     previous_guard_hp);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
