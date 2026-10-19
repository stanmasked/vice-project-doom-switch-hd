// Source-level replica of the actual second-playthrough NeXium input path.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "live_defeat_retry_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void check(bool good,const char* why) {
    if(!good)throw std::runtime_error(why);
}
int main(){
 try{
    using namespace vpd;
    Simulation game;
    game.enableEnemyEncounter();
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    check(game.guardEnemy().health==0,"First guard defeat missing");
    for(int n=0;n<270 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    check(game.secondWaveActive(),"Original wave-two gate absent");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    check(game.stageCleared() && game.playerHealth()>0,
          "Could not earn preceding victory to unlock replay scenario");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterVictory,
          "First native-equivalent Minus replay failed");

    std::FILE* f=std::tmpfile();
    check(f!=nullptr,"Native debug stream not open");
    check(!writeLiveDefeatRetry(f,DefeatRetryEvent::Contact,game,Right),
          "Pre-contact event incorrectly accepted");

    unsigned previous=game.guardEnemy().attacks;
    for(int n=0;n<260 && previous==0;++n){
        game.tick(Input{Right});
        previous=game.guardEnemy().attacks;
    }
    check(previous==1 && game.playerHealth()==4,
          "New playthrough guard never landed first actual hit");
    check(!writeLiveDefeatRetry(f,DefeatRetryEvent::Contact,game,0),
          "No real Right input accepted for contact event");
    check(writeLiveDefeatRetry(f,DefeatRetryEvent::Contact,game,Right),
          "Live source contact incorrectly rejected");
    check(!writeLiveDefeatRetry(f,DefeatRetryEvent::Death,game,0),
          "Guest falsely recorded death while the hero still had HP");
    // This arena's genuine first-guard attack cycle is 32 simulation
    // ticks. Each additional melee strike must consume one complete
    // cooldown and exactly one health point before MISSION FAILED.
    uint32_t last_strike_frame=game.frame();
    unsigned observed_attacks=game.guardEnemy().attacks;
    for(int n=0;n<245 && game.playerHealth();++n){
        game.tick(Input{});
        if(game.guardEnemy().attacks!=observed_attacks){
            check(game.guardEnemy().attacks==observed_attacks+1 &&
                  game.frame()==last_strike_frame+32 &&
                  game.playerHealth()==5-game.guardEnemy().attacks,
                  "Melee cadence or one-hit damage differs from auditor");
            last_strike_frame=game.frame();
            observed_attacks=game.guardEnemy().attacks;
        }
    }
    check(game.playerHealth()==0 && game.guardEnemy().attacks==5,
          "New run guard did not land exactly five lethal melee blows");
    check(writeLiveDefeatRetry(f,DefeatRetryEvent::Death,game,0),
          "Five real melee hits not accepted as death");
    // Terminal-state regression: the same source Simulation must ignore a
    // full burst of inputs. Frame time may advance to present MISSION FAILED,
    // but neither the hero nor hostile/projectile state may advance.
    const auto dead_frame=game.frame();
    const auto dead_x=game.player().x;
    const auto dead_y=game.player().y;
    const auto dead_camera=game.cameraX();
    const auto dead_guard_x=game.guardEnemy().x;
    const auto dead_guard_attacks=game.guardEnemy().attacks;
    const auto dead_guard_cooldown=game.guardEnemy().attack_cooldown;
    const auto dead_guard_alert=game.guardEnemy().alerted;
    const auto dead_guard_hits=game.guardEnemy().projectile_hits;
    const auto dead_sentry_fired=game.sentry().shots_fired;
    const auto dead_shots=game.shotsFired();
    const auto dead_flash=game.playerHitFlashTicks();
    for(unsigned n=0;n<64;++n){
        const uint8_t input=(n%3==0)?
            static_cast<uint8_t>(Right|Fire|Jump|Dash):
            (n%3==1?static_cast<uint8_t>(Left|Fire):uint8_t{0});
        game.tick(Input{input});
        check(game.frame()==dead_frame+n+1 &&
              game.playerHealth()==0 && !game.stageCleared() &&
              !game.secondWaveActive() &&
              game.player().x==dead_x && game.player().y==dead_y &&
              game.cameraX()==dead_camera && game.shotsFired()==dead_shots &&
              game.playerHitFlashTicks()==dead_flash &&
              game.guardEnemy().health==3 &&
              game.guardEnemy().x==dead_guard_x &&
              game.guardEnemy().attacks==dead_guard_attacks &&
              game.guardEnemy().attack_cooldown==dead_guard_cooldown &&
              game.guardEnemy().alerted==dead_guard_alert &&
              game.guardEnemy().projectile_hits==dead_guard_hits &&
              game.sentry().shots_fired==dead_sentry_fired,
              "Defeated hero, guard, or camera advanced without Minus");
        for(const auto& projectile:game.projectiles())
            check(!projectile.active,
                  "Terminal fire input spawned a phantom projectile");
        for(const auto& projectile:game.enemyProjectiles())
            check(!projectile.active,
                  "Terminal frame spawned a hostile projectile");
    }
    check(retryTerminalEncounter(game,false)==ManualRetryOutcome::Ignored &&
          game.playerHealth()==0 && game.frame()==dead_frame+64,
          "Defeat auto-restarted without a fresh Minus key");
    const auto before=retryBefore(game);
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterDefeat,
          "Native Minus failed to restart dead new playthrough");
    check(!writeLiveDefeatRetry(f,DefeatRetryEvent::Restart,game,0,false,
                               before,ManualRetryOutcome::AfterDefeat),
          "Guest writer accepted a missing Minus key");
    check(writeLiveDefeatRetry(f,DefeatRetryEvent::Restart,game,0,true,
                               before,ManualRetryOutcome::AfterDefeat),
          "Second native Minus reset rejected");
    check(game.frame()==0 && game.playerHealth()==5 &&
          game.guardEnemy().health==3 && game.guardEnemy().attacks==0 &&
          game.sentry().health==2 && !game.secondWaveActive(),
          "Second loss left health, enemy AI or progression state behind");
    Simulation pristine;
    pristine.enableEnemyEncounter();
    check(game.fingerprint()==pristine.fingerprint(),
          "Second retry does not match a newly initialized manual arena");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::Ignored &&
          game.frame()==0 && game.playerHealth()==5,
          "Repeated Minus restarted a nonterminal fresh encounter");
    for(int n=0;n<260 && game.guardEnemy().attacks==0;++n)
        game.tick(Input{Right});
    check(game.guardEnemy().attacks==1 && game.playerHealth()==4 &&
          game.shotsFired()==0,
          "The second restored encounter is not immediately playable");
    std::rewind(f);
    char line[360]{};
    const char* events[]={"seq=1 event=contact ",
                          "seq=2 event=death ",
                          "seq=3 event=restart "};
    for(unsigned i=0;i<3;++i)
        check(std::fgets(line,sizeof(line),f)!=nullptr &&
              std::strstr(line,events[i])!=nullptr &&
              std::strstr(line,"source=live_guest")!=nullptr,
              "Ordered real-source defeat proof is malformed");
    check(std::fgets(line,sizeof(line),f)==nullptr,
          "Live source writer emitted extra defeat events");
    std::fclose(f);
    std::puts("VPD_ROMFREE_DEFEAT_RETRY_HOST_PASS "
              "first_win=yes first_retry=yes real_guard_death=yes "
              "five_contact_attacks=yes real_minus_reset=yes "
              "fresh_two_wave_state=yes physical_switch_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_DEFEAT_RETRY_HOST_REJECT %s\n",e.what());
    return 1;
 }
}
