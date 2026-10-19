// Full source-shared three-run test: earned win, real death, two Minus,
// a third guard kill and a fresh second-wave stage completion.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "third_stage_witness.hpp"
#include "fourth_retry_witness.hpp"
#include "fourth_combat_witness.hpp"
#include "fourth_guard_clear_witness.hpp"
#include "fourth_stage_witness.hpp"
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
    const auto third_fire_fingerprint=game.fingerprint();
    for(int n=0;n<120 && game.guardEnemy().projectile_hits==0;++n)
        game.tick(Input{});
    check(game.guardEnemy().projectile_hits==1 &&
          game.guardEnemy().health==2,"Third first collision absent");
    const auto third_impact_fingerprint=game.fingerprint();
    for(int n=0;n<160 && game.guardEnemy().health;++n)
        game.tick(Input{Fire});
    check(game.guardEnemy().projectile_hits==3 &&
          game.guardEnemy().health==0 && game.playerHealth()==5,
          "Third source guard was not defeated with true bullets");
    const auto third_guard_fingerprint=game.fingerprint();
    std::FILE* f=std::tmpfile();
    check(f!=nullptr,"Native third stage witness tempfile unavailable");
    check(!writeThirdStage(f,ThirdStageEvent::Wave,game,Right),
          "Pre-wave guest event accepted");
    for(int n=0;n<280 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    check(game.secondWaveActive() && !game.stageCleared() &&
          game.sentry().health==2,"Third-run wave gate unavailable");
    const auto third_wave_fingerprint=game.fingerprint();
    check(!writeThirdStage(f,ThirdStageEvent::Wave,game,0),
          "Guest wave accepted absent Right");
    check(writeThirdStage(f,ThirdStageEvent::Wave,game,Right),
          "Third-run native wave event rejected");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    check(game.stageCleared() && game.sentry().health==0 &&
          game.sentry().projectile_hits==2 && game.playerHealth()>0,
          "Third-run stage-two combat did not actually clear exit");
    const auto third_exit_fingerprint=game.fingerprint();
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
    // A third *earned* stage clear must support the same real terminal
    // Minus reset path a fourth time, not an implicit auto-restart.
    std::FILE* fourth=std::tmpfile();
    check(fourth!=nullptr,"Fourth-run guest witness stream unavailable");
    const auto previous=retryBefore(game);
    check(!writeFourthRestart(fourth,ManualRetryOutcome::Ignored,
                              previous,game,true),
          "Fourth restart accepted absent terminal retry");
    const auto fourth_outcome=retryTerminalEncounter(game,true);
    check(fourth_outcome==ManualRetryOutcome::AfterVictory &&
          fourthFresh(game) && game.frame()==0 &&
          game.player().x==3*kTileSize*kFixed,
          "Fourth attempt was not cleanly restored after third win");
    Simulation freshly_constructed;
    freshly_constructed.enableEnemyEncounter();
    check(game.fingerprint()==freshly_constructed.fingerprint(),
          "Fourth-run restored state differs from pristine encounter");
    check(writeFourthRestart(fourth,fourth_outcome,previous,game,true),
          "Fourth source restart rejected genuine prior stage victory");
    check(!writeFourthMove(fourth,game,Right,game.player().x,0),
          "Fourth-run movement accepted before any real input");
    check(retryTerminalEncounter(game,true)==ManualRetryOutcome::Ignored,
          "Healthy fourth attempt accepted another Minus");
    for(int i=0;i<7;++i)game.tick(Input{Right});
    const auto before_x=game.player().x;
    const auto before_frame=game.frame();
    game.tick(Input{Right});
    check(!writeFourthMove(fourth,game,0,before_x,before_frame),
          "Fourth-run movement witness accepted absent Right");
    check(!writeFourthMove(fourth,game,Right,before_x-1,before_frame),
          "Fourth-run movement accepted forged actor prior x");
    check(writeFourthMove(fourth,game,Right,before_x,before_frame),
          "Source fourth-run movement rejected actual healthy Right tick");
    std::rewind(fourth);
    check(std::fgets(line,sizeof(line),fourth)!=nullptr &&
          std::strstr(line,"seq=1 event=restart") &&
          std::strstr(line,"old_clear=1 new_frame=0") &&
          std::strstr(line,"input_minus=1 source=live_guest"),
          "Fourth-run genuine Minus reset witness malformed");
    check(std::fgets(line,sizeof(line),fourth)!=nullptr &&
          std::strstr(line,"seq=2 event=move") &&
          std::strstr(line,"delta_fixed=512 hero_hp=5") &&
          std::strstr(line,"input_right=1 source=live_guest"),
          "Fourth-run genuine Right witness malformed");
    check(std::fgets(line,sizeof(line),fourth)==nullptr,
          "Fourth-run witness contained extra guest records");
    std::fclose(fourth);
    // Actual physical Fire equivalent on the pristine fourth attempt,
    // then exactly one first swept guard damage event.
    std::FILE* combat=std::tmpfile();
    check(combat!=nullptr,"Fourth-run combat witness stream unavailable");
    check(!writeFourthCombat(combat,FourthCombatEvent::Fire,
                             game,Fire,0,0,3),
          "Fourth-run Fire witness accepted an unspawned shot");
    const auto shots_before=game.shotsFired();
    const auto hits_before=game.guardEnemy().projectile_hits;
    const auto hp_before=game.guardEnemy().health;
    game.tick(Input{Fire});
    check(game.shotsFired()==1 && game.guardEnemy().health==3,
          "Fourth run failed to spawn original source projectile");
    check(game.fingerprint()==third_fire_fingerprint,
          "Fourth replay leaked state before its first shot");
    check(!writeFourthCombat(combat,FourthCombatEvent::Fire,
                             game,0,shots_before,hits_before,hp_before),
          "Fourth Fire witness accepted absent physical Y/Fire");
    check(writeFourthCombat(combat,FourthCombatEvent::Fire,
                            game,Fire,shots_before,hits_before,hp_before),
          "Fourth native source Fire event rejected");
    bool fourth_hit=false;
    for(int i=0;i<120 && !fourth_hit;++i){
        const auto old_hits=game.guardEnemy().projectile_hits;
        const auto old_hp=game.guardEnemy().health;
        const auto old_shots=game.shotsFired();
        game.tick(Input{});
        if(game.guardEnemy().projectile_hits==1){
            check(old_hits==0 && old_hp==3 &&
                  game.guardEnemy().health==2 && old_shots==1,
                  "Fourth projectile hit did not subtract exactly one HP");
            check(!writeFourthCombat(combat,FourthCombatEvent::Impact,
                                     game,Fire,old_shots,old_hits,old_hp),
                  "Fourth hit witness accepted held Fire");
            fourth_hit=writeFourthCombat(
                combat,FourthCombatEvent::Impact,game,0,
                old_shots,old_hits,old_hp);
        }
    }
    check(fourth_hit && game.playerHealth()==5 &&
          game.guardEnemy().health==2 && game.guardEnemy().attacks==0,
          "Fourth run failed to hurt the new guard with genuine projectile");
    check(game.fingerprint()==third_impact_fingerprint,
          "Fourth replay diverged during identical first swept impact");
    std::rewind(combat);
    check(std::fgets(line,sizeof(line),combat)!=nullptr &&
          std::strstr(line,"seq=1 event=fire") &&
          std::strstr(line,"guard_hp=3 guard_hits=0") &&
          std::strstr(line,"input_fire=1 source=live_guest"),
          "Fourth Fire native guest event malformed");
    check(std::fgets(line,sizeof(line),combat)!=nullptr &&
          std::strstr(line,"seq=2 event=impact") &&
          std::strstr(line,"guard_hp=2 guard_hits=1") &&
          std::strstr(line,"input_fire=0 source=live_guest"),
          "Fourth impact native guest event malformed");
    check(std::fgets(line,sizeof(line),combat)==nullptr,
          "Fourth combat writer emitted extra events");
    std::fclose(combat);
    // Complete fourth-run first guard fight after witnessed first hit.
    auto* final_hit=std::tmpfile();
    check(final_hit!=nullptr,"Fourth guard test stream unavailable");
    check(!writeFourthGuardClear(final_hit,game,Fire,3,0),
          "Fourth guard clear falsely accepted prior first-hit state");
    bool guard_dead=false;
    for(int n=0;n<160 && !guard_dead;++n){
        const auto old_guard_hp=game.guardEnemy().health;
        const auto old_hits=game.guardEnemy().projectile_hits;
        game.tick(Input{Fire});
        if(game.guardEnemy().health==0){
            check(old_guard_hp==1 && old_hits==2 &&
                  game.guardEnemy().projectile_hits==3,
                  "Fourth guard final hit was not third swept projectile collision");
            check(!writeFourthGuardClear(final_hit,game,0,
                                         old_guard_hp,old_hits),
                  "Fourth guard kill accepted absent physical Y/Fire");
            guard_dead=writeFourthGuardClear(
                final_hit,game,Fire,old_guard_hp,old_hits);
        }
    }
    check(guard_dead && game.playerHealth()==5 &&
          game.guardEnemy().attacks==0 && !game.secondWaveActive() &&
          game.sentry().health==2,
          "Fourth hero failed to eliminate restored guard without melee");
    check(game.fingerprint()==third_guard_fingerprint,
          "Fourth replay diverged during identical third guard collision");
    std::rewind(final_hit);
    check(std::fgets(line,sizeof(line),final_hit)!=nullptr &&
          std::strstr(line,"event=guard_clear") &&
          std::strstr(line,"guard_hp=0 previous_guard_hp=1") &&
          std::strstr(line,"guard_hits=3 previous_guard_hits=2") &&
          std::strstr(line,"input_fire=1 source=live_guest"),
          "Fourth native guard clear row malformed");
    check(std::fgets(line,sizeof(line),final_hit)==nullptr,
          "Fourth guard kill emitted unexpected extra records");
    std::fclose(final_hit);
    // Fourth run must ALSO beat the actual stage-two sentry and reach exit.
    auto* stage_four=std::tmpfile();
    check(stage_four!=nullptr,"Fourth stage witness stream unavailable");
    check(!writeFourthStage(stage_four,FourthStageEvent::Wave,game,Right),
          "Fourth stage gate accepted before encounter activation");
    for(int n=0;n<280 && !game.secondWaveActive();++n)
        game.tick(Input{Right});
    check(game.secondWaveActive() && !game.stageCleared() &&
          game.guardEnemy().health==0 && game.sentry().health==2,
          "Fourth run never activated its own second wave");
    check(game.fingerprint()==third_wave_fingerprint,
          "Fourth replay leaked state when the second wave activated");
    check(!writeFourthStage(stage_four,FourthStageEvent::Wave,game,0),
          "Fourth wave writer accepted missing Right input");
    check(writeFourthStage(stage_four,FourthStageEvent::Wave,game,Right),
          "Fourth wave source event not accepted");
    for(int n=0;n<470 && !game.stageCleared();++n)
        game.tick(Input{static_cast<uint8_t>(Right|Fire)});
    check(game.stageCleared() && game.sentry().health==0 &&
          game.sentry().projectile_hits==2 && game.playerHealth()>0,
          "Fourth attempt never completed its real second wave");
    check(game.fingerprint()==third_exit_fingerprint,
          "Fourth replay stage exit differs from identical third input route");
    check(!writeFourthStage(stage_four,FourthStageEvent::Exit,game,Right),
          "Fourth stage exit erroneously accepted missing Fire");
    check(writeFourthStage(stage_four,FourthStageEvent::Exit,
                           game,static_cast<uint8_t>(Right|Fire)),
          "Fourth stage source exit rejected earned victory");
    std::rewind(stage_four);
    check(std::fgets(line,sizeof(line),stage_four)!=nullptr &&
          std::strstr(line,"VPD_ROMFREE_FOURTH_STAGE_V1") &&
          std::strstr(line,"seq=1 event=wave") &&
          std::strstr(line,"sentry_hp=2 sentry_hits=0 wave=1 clear=0"),
          "Fourth stage new wave event malformed");
    check(std::fgets(line,sizeof(line),stage_four)!=nullptr &&
          std::strstr(line,"seq=2 event=exit") &&
          std::strstr(line,"sentry_hp=0 sentry_hits=2 wave=1 clear=1"),
          "Fourth stage native earned victory record malformed");
    check(std::fgets(line,sizeof(line),stage_four)==nullptr,
          "Fourth stage witness emitted additional records");
    std::fclose(stage_four);
    std::puts("VPD_THIRD_STAGE_HOST_PASS initial_victory=yes "
              "second_loss=yes third_guard_kill=yes "
              "third_wave=yes third_stage_clear=yes "
              "fourth_retry_and_move=yes fourth_fire_hit=yes "
              "fourth_guard_kill=yes fourth_stage_clear=yes "
              "live_nexium_proven=no original_game_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_THIRD_STAGE_HOST_FAIL %s\n",e.what());
    return 1;
 }
}
