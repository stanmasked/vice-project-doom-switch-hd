// Portable equivalent of live right/fire controller physics witness.
#include "second_wave_live_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace {
void check(bool valid,const char* why){if(!valid)throw std::runtime_error(why);}
}
int main(){
 try{
    using namespace vpd;
    Simulation world;
    world.enableEnemyEncounter();
    std::FILE* records=std::tmpfile();
    check(records!=nullptr,"No temporary guest-evidence stream");
    check(!liveWaveWrite(records,LiveWaveEvent::Activated,world,Right),
          "Second wave certified before first-guard defeat");
    for(int n=0;n<155 && world.guardEnemy().health;++n)
        world.tick(Input{Fire});
    check(world.guardEnemy().health==0 && !world.secondWaveActive(),
          "First-guard prerequisite absent");
    unsigned sequence=0;
    // First reach the new section using actual Right input (not a scripted
    // internal world teleport), then aim/fire only after the gate opens.
    for(int n=0;n<260 && !world.secondWaveActive();++n){
        const bool old=world.secondWaveActive();
        world.tick(Input{Right});
        if(!old && world.secondWaveActive()){
            check(liveWaveWrite(records,LiveWaveEvent::Activated,world,Right),
                  "Actual wave gate rejected");sequence=1;
        }
    }
    check(sequence==1 && world.secondWaveActive(),"Real Right never reached sentry wave");
    for(int n=0;n<460 && !world.stageCleared();++n){
        const auto hp_before=world.sentry().health;
        const uint32_t shots_before=world.shotsFired();
        const uint8_t keys=static_cast<uint8_t>(Right|Fire);
        world.tick(Input{keys});
        if(sequence==1 && world.shotsFired()>shots_before &&
           world.sentry().health==2){
            check(!liveWaveWrite(records,LiveWaveEvent::Fire,world,Right),
                  "Missing Fire key accepted");
            check(liveWaveWrite(records,LiveWaveEvent::Fire,world,keys),
                  "True pad Fire event rejected");sequence=2;
        }
        if(sequence==2 && hp_before==2 && world.sentry().health==1){
            check(liveWaveWrite(records,LiveWaveEvent::FirstImpact,world,keys),
                  "First legitimate impact rejected");sequence=3;
        }
        if(sequence==3 && hp_before==1 && world.sentry().health==0){
            check(liveWaveWrite(records,LiveWaveEvent::Defeat,world,keys),
                  "Second legitimate impact rejected");sequence=4;
        }
        if(sequence==4 && world.stageCleared()){
            check(liveWaveWrite(records,LiveWaveEvent::Exit,world,keys),
                  "Native gated exit rejected");sequence=5;
        }
    }
    check(sequence==5 && world.stageCleared() &&
          world.sentry().projectile_hits==2 &&
          world.playerHealth()>0,
          "Normal pad Right+Fire did not complete stage");
    std::rewind(records);
    const char* markers[5]={
        "seq=1 event=wave ","seq=2 event=fire ",
        "seq=3 event=hit1 ","seq=4 event=defeat ",
        "seq=5 event=exit "
    };
    char row[350]{};
    for(unsigned i=0;i<5;++i){
        check(std::fgets(row,sizeof(row),records)!=nullptr &&
              std::strstr(row,markers[i])!=nullptr &&
              std::strstr(row,"source=live_guest")!=nullptr,
              "Wrong live guest event sequence");
    }
    check(std::fgets(row,sizeof(row),records)==nullptr,
          "Unexpected extra live stage event");
    std::fclose(records);
    std::puts("VPD_ROMFREE_WAVE2_LIVE_HOST_PASS "
              "pad_right_fire=yes wave_gate=yes two_swept_hits=yes "
              "exit=yes native_guest_proven=no");
    return 0;
 }catch(const std::exception& ex){
    std::fprintf(stderr,"VPD_ROMFREE_WAVE2_LIVE_REJECT %s\n",ex.what());
    return 1;
 }
}
