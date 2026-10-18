// Opt-in ROM-free guard encounter: deterministic patrol, aggro and hit logic.
#include "simulation.hpp"
#include "combat_demo.hpp"
#include <cstdio>
#include <cstdint>
#include <stdexcept>

static void check(bool condition,const char* message) {
    if(!condition)throw std::runtime_error(message);
}
int main(){
    using namespace vpd;
    try {
        Simulation plain,mirror;
        check(!plain.enemyEncounterEnabled() && plain.playerHealth()==5,
              "Legacy default must have no active guard");
        plain.enableEnemyEncounter();
        mirror.enableEnemyEncounter();
        check(plain.enemyEncounterEnabled() && plain.guardEnemy().health==3 &&
              plain.fingerprint()==mirror.fingerprint(),
              "Encounter initialization is not deterministic");
        check(plain.fingerprint()!=Simulation{}.fingerprint(),
              "Opt-in enemy world omitted from replay hash");
        const int32_t starting_x=plain.guardEnemy().x;
        for(int f=0;f<100;++f){
            plain.tick(Input{});
            mirror.tick(Input{});
            check(plain.fingerprint()==mirror.fingerprint(),
                  "Two guard patrol replays diverged");
            check(plain.guardEnemy().x>=14*kTileSize*kFixed &&
                  plain.guardEnemy().x<=20*kTileSize*kFixed,
                  "Enemy patrol escaped its bounded territory");
        }
        check(plain.guardEnemy().x!=starting_x &&
              !plain.guardEnemy().alerted && plain.guardEnemy().attacks==0,
              "Distant player wrongly activated the guard");
        // The guard notices an approaching hero, then attacks at close range.
        Simulation attacker,attacker_mirror;
        attacker.enableEnemyEncounter();
        attacker_mirror.enableEnemyEncounter();
        bool alerted=false;
        bool attacked=false;
        for(int f=0;f<210;++f){
            const Input move{Right};
            attacker.tick(move);
            attacker_mirror.tick(move);
            check(attacker.fingerprint()==attacker_mirror.fingerprint(),
                  "Enemy attack replay diverged");
            alerted|=attacker.guardEnemy().alerted;
            attacked|=attacker.guardEnemy().attacks>0;
            check(attacker.playerHealth()<=5,
                  "Guard attack overflowed player health");
            if(attacked)break;
        }
        check(alerted && attacked && attacker.playerHealth()<5,
              "Guard failed to pursue and attack approaching hero");
        check(attacker.guardEnemy().attack_cooldown>0,
              "Contact damage has no bounded cooldown");
        const uint8_t prior_hp=attacker.playerHealth();
        attacker.tick(Input{});
        check(attacker.playerHealth()==prior_hp,
              "Contact damage repeated before cooldown elapsed");
        // Swept bullet collision must affect the guard before the target.
        Simulation shooting,shooting_mirror;
        shooting.enableEnemyEncounter();
        shooting_mirror.enableEnemyEncounter();
        for(int f=0;f<125;++f){
            shooting.tick(Input{Fire});
            shooting_mirror.tick(Input{Fire});
            check(shooting.fingerprint()==shooting_mirror.fingerprint(),
                  "Projectile/enemy interaction broke exact replay");
        }
        check(shooting.guardEnemy().health==0 &&
              shooting.guardEnemy().projectile_hits==3 &&
              !shooting.guardEnemy().alerted,
              "Three projectile impacts did not defeat guard exactly once");
        const uint16_t previous_hits=shooting.guardEnemy().projectile_hits;
        for(int f=0;f<60;++f)shooting.tick(Input{Fire});
        check(shooting.guardEnemy().projectile_hits==previous_hits,
              "Defeated enemy incorrectly received additional hits");
        Simulation covered;
        covered.enableEnemyEncounter();
        covered.scene().setSolid(10,kMapHeight-2,true);
        for(int f=0;f<125;++f)covered.tick(Input{Fire});
        check(covered.guardEnemy().health==3 &&
              covered.guardEnemy().projectile_hits==0,
              "Wall failed to shield guard from projectiles");
        check(covered.fingerprint()!=shooting.fingerprint(),
              "Guard health/map changes disappeared from simulation identity");
        // The original deterministic attract-mode is intentionally unchanged.
        Simulation attract;
        for(unsigned i=0;i<kCombatDemoFrames;++i)
            attract.tick(combatDemoInput(i));
        check(!attract.enemyEncounterEnabled() &&
              attract.fingerprint()==5947277116621119566ULL &&
              attract.trainingTarget().hits==3,
              "Opt-in guard contaminated the golden autoplay");
        shooting.reset();
        check(!shooting.enemyEncounterEnabled() &&
              shooting.playerHealth()==5 &&
              shooting.fingerprint()==Simulation{}.fingerprint(),
              "Gameplay reset retained guard encounter state");
        std::puts("VPD_ROMFREE_GUARD_ENCOUNTER_PASS patrol=yes aggro=yes "
                  "contact_attack=yes cooldown=yes projectile_hits=3 "
                  "solid_cover=yes repeatable=yes legacy_autoplay_intact=yes "
                  "native_switch_runtime_proven=no");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_ROMFREE_GUARD_ENCOUNTER_REJECT: %s\n",e.what());
        return 1;
    }
}
