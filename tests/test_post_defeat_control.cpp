// Portable control-path regression; NeXium must separately prove real keys.
// This exercises the same Simulation and serializer compiled into libnx.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "post_defeat_control_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace {
void check(bool good,const char* why){
    if(!good)throw std::runtime_error(why);
}
}
int main(){
 try{
    using namespace vpd;
    Simulation game;
    game.enableEnemyEncounter();
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    check(game.guardEnemy().health==0,"Guard survived initial victory script");
    for(int n=0;n<270 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    check(game.secondWaveActive(),"Second wave did not activate");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    check(game.stageCleared() && game.playerHealth()>0,
          "First attempt failed to earn legitimate victory");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterVictory,
          "First replay must come from victory");
    for(int n=0;n<260 && game.guardEnemy().attacks==0;++n)
        game.tick(Input{Right});
    check(game.guardEnemy().attacks==1 && game.playerHealth()==4,
          "Second attempt guard failed to land genuine damage");
    for(int n=0;n<245 && game.playerHealth()>0;++n)
        game.tick(Input{});
    check(game.playerHealth()==0 && game.guardEnemy().attacks==5,
          "Second attempt was not defeated by five true guard strikes");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterDefeat,
          "Second Minus must restart from an actual defeat");
    std::FILE* f=std::tmpfile();
    check(f!=nullptr,"Could not create source serializer test stream");
    const auto spawn=game.player().x;
    check(game.frame()==0 && spawn==3*kTileSize*kFixed,
          "Third attempt did not reset to spawn");
    check(!writePostDefeatControl(f,game,Right,spawn,0),
          "Writer accepted an unplayed third attempt");
    for(int n=0;n<8;++n)game.tick(Input{Right});
    const auto prior_x=game.player().x;
    const auto prior_frame=game.frame();
    game.tick(Input{Right});
    check(game.player().x-prior_x==2*kFixed && game.playerHealth()==5,
          "Third attempt failed to move as a healthy controlled hero");
    check(!writePostDefeatControl(f,game,0,prior_x,prior_frame),
          "Writer accepted movement without a Right key");
    check(!writePostDefeatControl(f,game,Right,prior_x-1,prior_frame),
          "Writer accepted a forged prior actor position");
    check(!writePostDefeatControl(f,game,Right,prior_x,prior_frame+1),
          "Writer accepted skipped or reordered source frames");
    check(writePostDefeatControl(f,game,Right,prior_x,prior_frame),
          "Native third-attempt control event rejected");
    std::rewind(f);
    char line[400]{};
    check(std::fgets(line,sizeof(line),f)!=nullptr &&
          std::strstr(line,"VPD_ROMFREE_THIRD_RUN_V1 event=move") &&
          std::strstr(line,"delta_fixed=512 hero_hp=5") &&
          std::strstr(line,"input_right=1 source=live_guest"),
          "Serialized proof not sourced from correct movement state");
    check(std::fgets(line,sizeof(line),f)==nullptr,
          "Third-attempt witness contains unexpected extra records");
    std::fclose(f);
    check(game.guardEnemy().health==3 &&
          game.guardEnemy().attacks==0 &&
          game.sentry().health==2 && !game.stageCleared(),
          "Third run did not restore enemy and progression state");
    std::puts("VPD_POST_DEFEAT_CONTROL_HOST_PASS "
              "earned_victory=yes genuine_loss=yes second_minus=yes "
              "third_manual_movement=yes guest_runtime_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_POST_DEFEAT_CONTROL_HOST_FAIL %s\n",e.what());
    return 1;
 }
}
