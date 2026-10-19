// Full source-level replay: victory -> Minus -> five-hit guard loss ->
// Minus -> third manual movement -> one physical Fire-equivalent tick ->
// one actual swept-projectile collision. Live X11 control is separate.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "post_defeat_fire_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace {
void require(bool truth,const char* why){
    if(!truth)throw std::runtime_error(why);
}
}
int main(){
 try{
    using namespace vpd;
    Simulation game;
    game.enableEnemyEncounter();
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    require(game.guardEnemy().health==0,"Initial guard did not fall");
    for(int n=0;n<270 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    require(game.secondWaveActive(),"First wave gate unavailable");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    require(game.stageCleared() && game.playerHealth()>0,
            "Initial victory was not earned by the real game core");
    require(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterVictory,
            "First terminal Minus did not restart victory");
    for(int n=0;n<260 && !game.guardEnemy().attacks;++n)
        game.tick(Input{Right});
    require(game.playerHealth()==4 && game.guardEnemy().attacks==1,
            "Post-win guard failed its initial melee");
    for(int n=0;n<245 && game.playerHealth();++n)game.tick(Input{});
    require(game.playerHealth()==0 && game.guardEnemy().attacks==5,
            "Post-win guard did not cause genuine terminal defeat");
    require(retryTerminalEncounter(game,true)==ManualRetryOutcome::AfterDefeat,
            "Second Minus did not restart after defeat");
    for(int n=0;n<8;++n)game.tick(Input{Right});
    require(game.playerHealth()==5 && game.shotsFired()==0 &&
            game.player().x==(3*16+16)*kFixed,
            "Third run did not move an undamaged hero to firing position");
    std::FILE* f=std::tmpfile();
    require(f!=nullptr,"Failed to open in-memory source witness");
    require(!writePostDefeatFire(f,ThirdFireEvent::Fire,
                                 game,Fire,0,0,3),
            "Claimed Fire before the simulation consumed an input");
    const auto before_fire=game.shotsFired();
    const auto before_hits=game.guardEnemy().projectile_hits;
    const auto before_hp=game.guardEnemy().health;
    game.tick(Input{Fire});
    require(game.shotsFired()==1 && game.guardEnemy().health==3,
            "Real third-run shot did not spawn at full guard health");
    require(!writePostDefeatFire(f,ThirdFireEvent::Fire,
                                 game,0,before_fire,before_hits,before_hp),
            "Guest accepted Fire evidence without physical Fire input");
    require(writePostDefeatFire(f,ThirdFireEvent::Fire,
                                game,Fire,before_fire,before_hits,before_hp),
            "Guest failed to record a real source-created third-run shot");
    bool impact=false;
    for(int n=0;n<120 && !impact;++n){
        const auto prior_hits=game.guardEnemy().projectile_hits;
        const auto prior_hp=game.guardEnemy().health;
        const auto prior_shots=game.shotsFired();
        game.tick(Input{});
        if(game.guardEnemy().projectile_hits==1){
            require(prior_hits==0 && prior_hp==3 &&
                    game.guardEnemy().health==2 && prior_shots==1,
                    "Swept first impact did not subtract exactly one HP");
            require(!writePostDefeatFire(f,ThirdFireEvent::Impact,
                                         game,Fire,prior_shots,prior_hits,prior_hp),
                    "Impact falsely accepted while Fire remains pressed");
            impact=writePostDefeatFire(f,ThirdFireEvent::Impact,
                                       game,0,prior_shots,prior_hits,prior_hp);
        }
    }
    require(impact && game.playerHealth()==5,
            "Third-run shot failed to hit living guard without injuring hero");
    std::rewind(f);
    char line[350]{};
    require(std::fgets(line,sizeof(line),f) &&
            std::strstr(line,"seq=1 event=fire") &&
            std::strstr(line,"guard_hp=3 guard_hits=0") &&
            std::strstr(line,"input_fire=1 source=live_guest"),
            "Third-run Fire source event is malformed");
    require(std::fgets(line,sizeof(line),f) &&
            std::strstr(line,"seq=2 event=impact") &&
            std::strstr(line,"guard_hp=2 guard_hits=1") &&
            std::strstr(line,"input_fire=0 source=live_guest"),
            "Third-run swept impact source event is malformed");
    require(std::fgets(line,sizeof(line),f)==nullptr,
            "Unexpected extra third-run combat witness");
    std::fclose(f);
    std::puts("VPD_THIRD_RUN_FIRE_HOST_PASS victory=yes defeat=yes "
              "two_native_retries=yes third_movement=yes "
              "one_real_shot=yes one_swept_impact=yes "
              "live_neXium_proven=no");
    return 0;
 }catch(const std::exception& exc){
    std::fprintf(stderr,"VPD_THIRD_RUN_FIRE_HOST_FAIL %s\n",exc.what());
    return 1;
 }
}
