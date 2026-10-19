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
    for(int n=0;n<245 && game.playerHealth();++n)
        game.tick(Input{});
    check(game.playerHealth()==0 && game.guardEnemy().attacks>=5,
          "New run guard did not genuinely kill stationary hero");
    check(writeLiveDefeatRetry(f,DefeatRetryEvent::Death,game,0),
          "Five real melee hits not accepted as death");
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
