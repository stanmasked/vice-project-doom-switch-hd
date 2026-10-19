// Deterministic manual retry after genuine loss and earned stage victory.
// No ROM or controller framework: this is the portable core used by libnx.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "combat_demo.hpp"
#include <cstdio>
#include <stdexcept>
namespace {
void require(bool good,const char* why){if(!good)throw std::runtime_error(why);}
void pristine(const vpd::Simulation& game,uint64_t reference){
    using namespace vpd;
    require(game.enemyEncounterEnabled() && game.frame()==0 &&
            game.playerHealth()==5 &&
            game.guardEnemy().health==3 && !game.guardEnemy().alerted &&
            game.guardEnemy().attacks==0 &&
            game.sentry().health==2 && game.sentry().shots_fired==0 &&
            game.sentry().shots_hit==0 &&
            !game.secondWaveActive() && !game.stageCleared() &&
            !game.dashEverUsed() && game.shotsFired()==0 &&
            game.fingerprint()==reference,
            "Retry retained old health, hits, enemies, physics or progression");
    for(const auto& shot:game.projectiles())
        require(!shot.active,"Old player projectile survived retry");
    for(const auto& shot:game.enemyProjectiles())
        require(!shot.active,"Hostile projectile survived retry");
}
void clearLevel(vpd::Simulation& game){
    using namespace vpd;
    game.enableEnemyEncounter();
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    require(game.guardEnemy().health==0,"First guard never defeated");
    for(int n=0;n<270 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    require(game.secondWaveActive(),"Wave-two gate failed");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    require(game.stageCleared() && game.playerHealth()>0,
            "Could not earn stage clear with regular source gameplay");
}
}
int main(){
    try{
        using namespace vpd;
        Simulation baseline;
        baseline.enableEnemyEncounter();
        const auto fresh_fingerprint=baseline.fingerprint();
        require(retryTerminalEncounter(baseline,true)==ManualRetryOutcome::Ignored,
                "Retry accepted before a terminal state");
        require(retryTerminalEncounter(baseline,false)==ManualRetryOutcome::Ignored,
                "Retry occurred without physical Minus button");
        pristine(baseline,fresh_fingerprint);

        Simulation lost;
        lost.enableEnemyEncounter();
        bool died=false;
        for(int n=0;n<410;++n){
            lost.tick(Input{Right});
            if(lost.playerHealth()==0){died=true;break;}
        }
        require(died && !lost.stageCleared() &&
                lost.guardEnemy().attacks>=5,
                "Real first-guard melee never caused terminal defeat");
        const auto dead_x=lost.player().x;
        const auto dead_health=lost.playerHealth();
        const auto dead_frame=lost.frame();
        for(int n=0;n<6;++n)lost.tick(Input{static_cast<uint8_t>(Right|Fire)});
        require(lost.player().x==dead_x &&
                lost.playerHealth()==dead_health &&
                lost.frame()==dead_frame+6,
                "Defeated hero kept moving, attacking or modifying HP");
        require(retryTerminalEncounter(lost,false)==ManualRetryOutcome::Ignored &&
                lost.playerHealth()==0,
                "Dead hero auto-restarted without a retry button");
        require(retryTerminalEncounter(lost,true)==ManualRetryOutcome::AfterDefeat,
                "Minus did not restart terminal loss");
        pristine(lost,fresh_fingerprint);
        require(retryTerminalEncounter(lost,true)==ManualRetryOutcome::Ignored,
                "Held or repeated Minus retriggered a healthy run");
        for(int n=0;n<12;++n)lost.tick(Input{Right});
        require(lost.player().x>3*kTileSize*kFixed &&
                lost.playerHealth()==5,
                "New run is not playable after a real loss");

        Simulation won;
        clearLevel(won);
        const auto winner_x=won.player().x;
        const auto winner_hp=won.playerHealth();
        const auto win_frame=won.frame();
        for(int n=0;n<6;++n)
            won.tick(Input{static_cast<uint8_t>(Left|Fire|Dash)});
        require(won.stageCleared() && won.player().x==winner_x &&
                won.playerHealth()==winner_hp &&
                won.frame()==win_frame+6,
                "Won level kept advancing gameplay before explicit replay");
        require(retryTerminalEncounter(won,false)==ManualRetryOutcome::Ignored,
                "Victory auto-replayed without Minus");
        require(retryTerminalEncounter(won,true)==ManualRetryOutcome::AfterVictory,
                "Minus failed to restart legitimately completed stage");
        pristine(won,fresh_fingerprint);
        require(!won.stageCleared(),"Level clear leaked across retries");

        // The pinned ROM-free autoplay contains no encounter and may never
        // be reset accidentally by the new manual-only retry action.
        Simulation demo;
        for(unsigned n=0;n<kCombatDemoFrames;++n)
            demo.tick(combatDemoInput(n));
        const auto old_hash=demo.fingerprint();
        require(old_hash==5947277116621119566ULL,
                "Pinned autoplay fingerprint changed");
        require(retryTerminalEncounter(demo,true)==ManualRetryOutcome::Ignored &&
                demo.fingerprint()==old_hash,
                "Minus unexpectedly reset the autoplay demonstration");
        std::puts("VPD_ROMFREE_MANUAL_RETRY_PASS "
                  "genuine_guard_death=yes genuine_stage_clear=yes "
                  "no_automatic_retry=yes terminal_physics_frozen=yes "
                  "both_reset_clean=yes demo_hash_preserved=yes");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_MANUAL_RETRY_REJECT %s\n",e.what());
        return 1;
    }
}
