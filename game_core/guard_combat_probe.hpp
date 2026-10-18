#pragma once
// Native AArch64 gameplay-core smoke diagnostic. This is a *separate scripted*
// ROM-free simulation, NOT the live manual encounter or original NES behavior.
#include "simulation.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kGuardCombatProofPath =
    "sdmc:/switch/vice_project_doom/guard_combat_witness.txt";

struct GuardCombatSample {
    uint32_t frame=0;
    int32_t guard_x=0;
    uint8_t guard_health=0;
    uint8_t player_health=0;
    uint16_t hits=0;
    uint16_t attacks=0;
    uint8_t cooldown=0;
    bool alerted=false;
};
using GuardCombatSamples=std::array<GuardCombatSample,5>;

inline GuardCombatSample guardCombatSnapshot(const Simulation& game) {
    const auto& guard=game.guardEnemy();
    return {game.frame(),guard.x,guard.health,game.playerHealth(),
            guard.projectile_hits,guard.attacks,guard.attack_cooldown,
            guard.alerted};
}

inline bool collectGuardCombatSamples(GuardCombatSamples& result) {
    // Scenario 1: the actual manual-mode AI detects an approaching player
    // and ultimately damages the player, respecting its cooldown.
    Simulation approach;
    approach.enableEnemyEncounter();
    bool detected=false;
    bool struck=false;
    for(unsigned i=0;i<210;++i){
        const bool previously_alerted=approach.guardEnemy().alerted;
        const uint16_t attacks_before=approach.guardEnemy().attacks;
        approach.tick(Input{Right});
        if(!detected && !previously_alerted && approach.guardEnemy().alerted){
            result[0]=guardCombatSnapshot(approach);
            detected=true;
        }
        if(!struck && approach.guardEnemy().attacks>attacks_before){
            result[1]=guardCombatSnapshot(approach);
            struck=true;
            break;
        }
    }
    if(!detected || !struck ||
       result[0].guard_health!=3 || result[0].player_health!=5 ||
       result[0].hits || result[0].attacks || !result[0].alerted ||
       result[1].frame<=result[0].frame ||
       result[1].guard_health!=3 || result[1].player_health!=4 ||
       result[1].attacks!=1 || result[1].hits!=0 ||
       result[1].cooldown!=32 || !result[1].alerted)return false;

    // Scenario 2: real swept bullets from the existing Fire action remove
    // three health points; not a direct setter of guard health.
    Simulation shooter;
    shooter.enableEnemyEncounter();
    unsigned next=2;
    for(unsigned i=0;i<150 && next<result.size();++i){
        const uint16_t before=shooter.guardEnemy().projectile_hits;
        shooter.tick(Input{Fire});
        if(shooter.guardEnemy().projectile_hits>before){
            if(shooter.guardEnemy().projectile_hits!=next-1 ||
               shooter.guardEnemy().health!=4-next)return false;
            result[next]=guardCombatSnapshot(shooter);
            ++next;
        }
    }
    if(next!=result.size())return false;
    for(unsigned i=2;i<result.size();++i){
        const auto& row=result[i];
        if(row.guard_health!=4-i || row.hits!=i-1 ||
           row.player_health!=5 || row.attacks!=0 ||
           (i>2 && row.frame<=result[i-1].frame))return false;
    }
    return result[4].guard_health==0 && !result[4].alerted;
}

inline bool writeGuardCombatProof(std::FILE* file,
                                  const GuardCombatSamples& samples) {
    if(!file)return false;
    static constexpr const char* kNames[5]={
        "alert","attack","hit1","hit2","defeat"
    };
    for(std::size_t i=0;i<samples.size();++i){
        const auto& row=samples[i];
        const char* scenario=i<2?"approach":"shoot";
        char line[232]{};
        const int size=std::snprintf(line,sizeof(line),
            "VPD_ROMFREE_GUARD_COMBAT_V1 seq=%u event=%s scenario=%s "
            "frame=%u guard_x=%ld guard_hp=%u player_hp=%u hits=%u "
            "attacks=%u cooldown=%u alerted=%u "
            "source=guest_script original_game_proven=no\n",
            static_cast<unsigned>(i+1),kNames[i],scenario,row.frame,
            static_cast<long>(row.guard_x),
            static_cast<unsigned>(row.guard_health),
            static_cast<unsigned>(row.player_health),
            static_cast<unsigned>(row.hits),
            static_cast<unsigned>(row.attacks),
            static_cast<unsigned>(row.cooldown),
            row.alerted?1u:0u);
        if(size<=0 || static_cast<std::size_t>(size)>=sizeof(line) ||
           std::fwrite(line,1,static_cast<std::size_t>(size),file)!=
           static_cast<std::size_t>(size))return false;
    }
    return std::fflush(file)==0;
}

inline bool guardCombatProofReset(bool has_sd) {
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* file=std::fopen(kGuardCombatProofPath,"w");
    return file && std::fclose(file)==0;
}

inline bool persistGuardCombatProof(bool has_sd) {
    if(!has_sd)return false;
    GuardCombatSamples samples{};
    if(!collectGuardCombatSamples(samples))return false;
    std::FILE* file=std::fopen(kGuardCombatProofPath,"w");
    if(!file)return false;
    const bool written=writeGuardCombatProof(file,samples);
    return std::fclose(file)==0 && written;
}
} // namespace vpd
