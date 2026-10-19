// Long-run replay invariant: repeated legitimate wins and defeats must
// restore the same independently authored ROM-free encounter every time.
// Not NES game emulation and not proof of physical Switch performance.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include <cstdint>
#include <cstdio>
#include <exception>
#include <stdexcept>
#include <string>

namespace {
void require(bool yes,const char* why){
    if(!yes)throw std::runtime_error(why);
}
uint64_t freshHash(){
    vpd::Simulation fresh;
    fresh.enableEnemyEncounter();
    return fresh.fingerprint();
}
void freshCheck(const vpd::Simulation& game,uint64_t baseline){
    using namespace vpd;
    require(game.enemyEncounterEnabled(),"Enemy encounter was not enabled");
    require(game.frame()==0,"Game frame not zero after restart");
    require(game.fingerprint()==baseline,"Stale internal physics/replay state survived restart");
    require(game.playerHealth()==5 && game.playerHitFlashTicks()==0,
            "Hero health/flash not restored");
    require(game.player().x==3*kTileSize*kFixed,
            "Hero did not return to exact original spawn");
    require(game.guardEnemy().health==3 &&
            game.guardEnemy().attacks==0 &&
            game.guardEnemy().projectile_hits==0,
            "Guard retained prior combat state");
    require(game.sentry().health==2 &&
            game.sentry().projectile_hits==0 &&
            game.sentry().shots_fired==0 &&
            game.sentry().shots_hit==0,
            "Sentry retained prior projectile/damage state");
    require(!game.secondWaveActive() && !game.stageCleared(),
            "Old stage victory/wave survived restart");
    require(game.shotsFired()==0 && !game.dashEverUsed(),
            "Hero retained old firearm/dash state");
    for(const auto& p:game.projectiles())
        require(!p.active,"Player projectile leaked into next game");
    for(const auto& p:game.enemyProjectiles())
        require(!p.active,"Enemy projectile leaked into next game");
}
uint64_t win(vpd::Simulation& game){
    using namespace vpd;
    // The first guard is defeated by the same deterministic source shots.
    for(int n=0;n<180 && game.guardEnemy().health>0;++n)
        game.tick(Input{Fire});
    require(game.guardEnemy().health==0 &&
            game.guardEnemy().projectile_hits==3,
            "Guard failed to lose its exact third HP");
    require(game.playerHealth()==5,
            "A clean initial volley unexpectedly damaged the hero");
    for(int n=0;n<350 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    require(game.secondWaveActive() && game.sentry().health==2,
            "Sentry was not rearmed after restart");
    for(int n=0;n<550 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    require(game.stageCleared() && game.playerHealth()>0 &&
            game.sentry().health==0 &&
            game.sentry().projectile_hits==2,
            "Stage victory was not earned by two sentry hits");
    require(game.frame()<1200,"Victory route stalled beyond test frame cap");
    return game.fingerprint();
}
uint64_t lose(vpd::Simulation& game){
    using namespace vpd;
    // Explicitly earn one real guard contact under Right, then let the
    // same source AI finish its five-attack melee sequence.
    for(int n=0;n<300 && game.guardEnemy().attacks==0;++n)
        game.tick(Input{Right});
    require(game.guardEnemy().attacks==1 && game.playerHealth()==4,
            "Fresh guard did not deliver the first real melee attack");
    for(int n=0;n<300 && game.playerHealth()>0;++n)
        game.tick(Input{});
    require(game.playerHealth()==0 && game.guardEnemy().attacks==5,
            "Guard failed to deliver exactly five real attacks");
    require(!game.stageCleared() && !game.secondWaveActive() &&
            game.guardEnemy().health==3,
            "Game falsely awarded clear during defeat");
    require(game.frame()<1200,"Melee death route stalled beyond test frame cap");
    return game.fingerprint();
}
}
int main(){
    try {
        using namespace vpd;
        Simulation game;
        game.enableEnemyEncounter();
        const uint64_t baseline=freshHash();
        constexpr unsigned kRuns=32; // 16 earned wins + 16 source deaths
        uint64_t victory_hash=0;
        uint64_t defeat_hash=0;
        uint64_t cumulative=14695981039346656037ull;
        freshCheck(game,baseline);
        for(unsigned run=0;run<kRuns;++run){
            const bool earned_win=(run%2)==0;
            // Healthy manual play must ignore an attempted Minus.
            const uint64_t prior=game.fingerprint();
            require(retryTerminalEncounter(game,true)==ManualRetryOutcome::Ignored,
                    "Healthy encounter incorrectly permitted terminal retry");
            require(game.fingerprint()==prior,
                    "Ignored healthy Minus changed actual gameplay state");

            const uint64_t finished=earned_win?win(game):lose(game);
            if(earned_win){
                if(run==0)victory_hash=finished;
                require(victory_hash==finished,
                        "Replay drift across separate earned victories");
            }else{
                if(run==1)defeat_hash=finished;
                require(defeat_hash==finished,
                        "Replay drift across separate authentic melee deaths");
            }
            require(finished!=baseline && victory_hash!=defeat_hash,
                    "Terminal state unexpectedly equals reset/other outcome");
            // Replay fingerprint is independent of the number of *previous*
            // encounters, and reset returns to the same pristine hash.
            cumulative^=finished;
            cumulative*=1099511628211ull;
            const auto requested=earned_win?
                ManualRetryOutcome::AfterVictory:ManualRetryOutcome::AfterDefeat;
            require(retryTerminalEncounter(game,false)==ManualRetryOutcome::Ignored,
                    "False Minus did not leave terminal state in place");
            require(game.fingerprint()==finished,
                    "Ignored terminal replay unexpectedly changed state");
            require(retryTerminalEncounter(game,true)==requested,
                    "Actual terminal Minus failed to restart the run");
            freshCheck(game,baseline);
            cumulative^=game.fingerprint();
            cumulative*=1099511628211ull;
        }
        // Validate restored input after 32 terminal transitions.
        for(int step=0;step<8;++step)game.tick(Input{Right});
        require(game.player().x==(3*16+16)*kFixed &&
                game.guardEnemy().health==3,
                "32nd terminal retry lost responsive manual Right input");
        game.tick(Input{Fire});
        require(game.shotsFired()==1 && game.playerHealth()==5,
                "32nd terminal retry lost manual Fire input");
        std::printf(
            "VPD_RESTART_STRESS_HOST_PASS runs=%u wins=%u deaths=%u "
            "restarted=%u manual_right_after_stress=yes "
            "manual_fire_after_stress=yes "
            "initial_hash=%llu victory_hash=%llu defeat_hash=%llu "
            "chain_hash=%llu guest_nexium_proven=no original_game_proven=no\n",
            kRuns,kRuns/2,kRuns/2,kRuns,
            static_cast<unsigned long long>(baseline),
            static_cast<unsigned long long>(victory_hash),
            static_cast<unsigned long long>(defeat_hash),
            static_cast<unsigned long long>(cumulative));
        return 0;
    }catch(const std::exception& err){
        std::fprintf(stderr,"VPD_RESTART_STRESS_HOST_FAIL %s\n",err.what());
        return 1;
    }
}
