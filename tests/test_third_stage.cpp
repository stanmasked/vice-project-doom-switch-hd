// Full source-shared three-run test: earned win, real death, two Minus,
// a third guard kill and a fresh second-wave stage completion.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "third_stage_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace {
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
}
int main(){
 try{
    using namespace vpd;
    Simulation game;
    game.enableEnemyEncounter();
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    check(game.guardEnemy().health==0,"Initial guard did not fall");
    for(int n=0;n<270 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    check(game.secondWaveActive(),"Initial second wave missing");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    check(game.stageCleared() && game.playerHealth()>0,
          "Initial stage victory not earned");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterVictory,
          "First Minus did not reset earned win");
    for(int n=0;n<260 && !game.guardEnemy().attacks;++n)
        game.tick(Input{Right});
    check(game.guardEnemy().attacks==1 && game.playerHealth()==4,
          "Second run did not suffer native first contact");
    for(int n=0;n<245 && game.playerHealth();++n)
        game.tick(Input{});
    check(game.guardEnemy().attacks==5 && game.playerHealth()==0,
          "Second run did not suffer genuine source death");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterDefeat,
          "Second Minus did not restart defeated run");
    for(int n=0;n<8;++n)game.tick(Input{Right});
    check(game.player().x==(3*16+16)*kFixed,"Third movement missing");
    game.tick(Input{Fire});
    check(game.shotsFired()==1,"Third shot not fired");
    for(int n=0;n<120 && game.guardEnemy().projectile_hits==0;++n)
        game.tick(Input{});
    check(game.guardEnemy().projectile_hits==1 &&
          game.guardEnemy().health==2,"Third first collision absent");
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    check(game.guardEnemy().projectile_hits==3 &&
          game.guardEnemy().health==0 && game.playerHealth()==5,
          "Third source guard was not defeated with true bullets");
    std::FILE* f=std::tmpfile();
    check(f!=nullptr,"Native third stage witness tempfile unavailable");
    check(!writeThirdStage(f,ThirdStageEvent::Wave,game,Right),
          "Pre-wave guest event accepted");
    for(int n=0;n<280 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    check(game.secondWaveActive() && !game.stageCleared() &&
          game.sentry().health==2,"Third-run wave gate unavailable");
    check(!writeThirdStage(f,ThirdStageEvent::Wave,game,0),
          "Guest wave accepted absent Right");
    check(writeThirdStage(f,ThirdStageEvent::Wave,game,Right),
          "Third-run native wave event rejected");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    check(game.stageCleared() && game.sentry().health==0 &&
          game.sentry().projectile_hits==2 && game.playerHealth()>0,
          "Third-run stage-two combat did not actually clear exit");
    check(!writeThirdStage(f,ThirdStageEvent::Exit,game,Right),
          "Third exit accepted without actual Fire");
    check(writeThirdStage(f,ThirdStageEvent::Exit,game,
                          static_cast<uint8_t>(Right|Fire)),
          "Third-run earned stage exit rejected");
    std::rewind(f);
    char line[370]{};
    check(std::fgets(line,sizeof(line),f) &&
          std::strstr(line,"seq=1 event=wave ") &&
          std::strstr(line,"sentry_hp=2 sentry_hits=0 wave=1 clear=0") &&
          std::strstr(line,"source=live_guest"),
          "Third stage wave witness malformed");
    check(std::fgets(line,sizeof(line),f) &&
          std::strstr(line,"seq=2 event=exit ") &&
          std::strstr(line,"sentry_hp=0 sentry_hits=2 wave=1 clear=1") &&
          std::strstr(line,"source=live_guest"),
          "Third stage completed exit witness malformed");
    check(std::fgets(line,sizeof(line),f)==nullptr,
          "Extra third-stage guest event recorded");
    std::fclose(f);
    std::puts("VPD_THIRD_STAGE_HOST_PASS initial_victory=yes "
              "second_loss=yes third_guard_kill=yes "
              "third_wave=yes third_stage_clear=yes "
              "live_nexium_proven=no original_game_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_THIRD_STAGE_HOST_FAIL %s\n",e.what());
    return 1;
 }
}
