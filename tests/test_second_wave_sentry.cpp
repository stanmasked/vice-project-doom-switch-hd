// ROM-free two-stage prototype: guarded corridor then a ranged turret.
#include "simulation.hpp"
#include "combat_demo.hpp"
#include <cstdio>
#include <stdexcept>

static void check(bool yes,const char* message){if(!yes)throw std::runtime_error(message);}

static vpd::Simulation clearFirstGuard(){
    using namespace vpd;
    Simulation world;
    world.enableEnemyEncounter();
    check(!world.secondWaveActive() && !world.stageCleared(),
          "Wave two was enabled at stage start");
    for(int i=0;i<140 && world.guardEnemy().health;++i)
        world.tick(Input{Fire});
    check(world.guardEnemy().health==0 &&
          world.guardEnemy().projectile_hits==3,
          "Existing first guard was not defeated using real bullets");
    check(!world.secondWaveActive(),
          "Second wave activated before the player crossed corridor boundary");
    for(int i=0;i<260 && !world.secondWaveActive();++i)
        world.tick(Input{Right});
    check(world.secondWaveActive() && world.sentry().health==2 &&
          world.player().x>=26*kTileSize*kFixed,
          "Wave two failed to activate after guard defeat and corridor travel");
    return world;
}
int main(){
    using namespace vpd;
    try{
        // No changed output from the established 200-frame autonomous demo.
        Simulation demo;
        for(unsigned i=0;i<kCombatDemoFrames;++i)
            demo.tick(combatDemoInput(i));
        check(!demo.enemyEncounterEnabled() &&
              !demo.secondWaveActive() &&
              demo.fingerprint()==5947277116621119566ULL,
              "Second wave altered frozen autoplay witness");
        // An alive guard keeps wave two locked even if the player runs ahead.
        Simulation gate;
        gate.enableEnemyEncounter();
        for(int i=0;i<230;++i)gate.tick(Input{Right});
        check(gate.guardEnemy().health>0 && !gate.secondWaveActive(),
              "Guard progression gate can be bypassed");

        Simulation standoff=clearFirstGuard();
        while(standoff.player().x<29*kTileSize*kFixed)
            standoff.tick(Input{Right});
        const uint8_t start_hp=standoff.playerHealth();
        check(start_hp>0,"Hero unexpectedly died in empty corridor");
        bool saw_bullet=false,hit=false;
        for(int i=0;i<200;++i){
            const auto before=standoff.playerHealth();
            standoff.tick(Input{});
            saw_bullet|=standoff.sentry().shots_fired>0;
            hit|=standoff.playerHealth()<before;
        }
        check(saw_bullet && hit && standoff.sentry().shots_hit>0 &&
              standoff.sentry().health==2,
              "Stationary sentry failed to fire a real swept hostile shot");
        // Independent identical simulations must replay the complete
        // progression, hostile projectiles and exit checkpoint exactly.
        Simulation a=clearFirstGuard(),b=clearFirstGuard();
        check(a.fingerprint()==b.fingerprint(),"Stage activation not deterministic");
        bool saw_turret_hit=false;
        bool saw_exit=false;
        for(int i=0;i<450;++i){
            const auto previous=a.sentry().projectile_hits;
            a.tick(Input{static_cast<uint8_t>(Right|Fire)});
            b.tick(Input{static_cast<uint8_t>(Right|Fire)});
            check(a.fingerprint()==b.fingerprint(),
                  "Duplicate wave-two simulation diverged");
            saw_turret_hit|=a.sentry().projectile_hits>previous;
            if(a.stageCleared()){saw_exit=true;break;}
        }
        check(saw_turret_hit && a.sentry().health==0 &&
              a.sentry().projectile_hits==2,
              "Player shots never disabled the second-wave turret");
        check(saw_exit && a.player().x>=55*kTileSize*kFixed &&
              a.playerHealth()>0,
              "Stage clear did not require defeating sentry and reaching exit");
        check(a.stageCleared() && a.enemyEncounterEnabled(),
              "Cleared stage lost its combat progression state");
        a.reset();
        check(!a.enemyEncounterEnabled() && !a.secondWaveActive() &&
              !a.stageCleared() && a.sentry().health==2 &&
              a.fingerprint()==Simulation{}.fingerprint(),
              "Reset retained private turret or stage-completion state");
        std::puts("VPD_ROMFREE_SECOND_WAVE_PASS "
                  "guard_gate=yes sentry_activation=yes "
                  "hostile_swept_hits=yes turret_defeat=2 "
                  "stage_exit=yes replay_repeatable=yes "
                  "golden_autoplay_intact=yes original_game_proven=no");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_SECOND_WAVE_REJECT %s\n",e.what());
        return 1;
    }
}
