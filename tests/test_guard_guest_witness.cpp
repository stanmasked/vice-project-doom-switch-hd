// Portable copy of exact native guard witness serializer behavior.
#include "guard_guest_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void check(bool ok,const char* reason) {
    if(!ok)throw std::runtime_error(reason);
}
int main(){
 try{
    vpd::Simulation game;
    std::FILE* file=std::tmpfile();
    check(file!=nullptr,"temporary witness stream unavailable");
    check(!vpd::guardProofWrite(file,vpd::GuardProofEvent::FirstStep,game),
          "disabled encounter forged first-step proof");
    game.enableEnemyEncounter();
    check(!vpd::guardProofWrite(file,vpd::GuardProofEvent::FirstStep,game),
          "unadvanced simulation forged guard movement");
    game.tick(vpd::Input{});
    check(vpd::guardProofWrite(file,vpd::GuardProofEvent::FirstStep,game),
          "actual guard first step rejected");
    check(!vpd::guardProofWrite(file,vpd::GuardProofEvent::Patrol,game),
          "early guard patrol completion accepted");
    for(int i=0;i<7;++i)game.tick(vpd::Input{});
    check(vpd::guardProofWrite(file,vpd::GuardProofEvent::Patrol,game),
          "actual eighth tick rejected");
    std::rewind(file);
    char line[256]{};
    check(std::fgets(line,sizeof(line),file)!=nullptr &&
          std::strstr(line,"seq=1 event=first frame=1") &&
          std::strstr(line,"x_fixed=65792"),
          "first movement record changed");
    check(std::fgets(line,sizeof(line),file)!=nullptr &&
          std::strstr(line,"seq=2 event=patrol frame=8") &&
          std::strstr(line,"x_fixed=67584"),
          "eighth movement record changed");
    check(std::fgets(line,sizeof(line),file)==nullptr,
          "extra guest output");
    std::fclose(file);
    std::puts("VPD_ROMFREE_GUARD_GUEST_SERIALIZER_PASS events=2");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_ROMFREE_GUARD_GUEST_REJECT: %s\n",e.what());
    return 1;
 }
}
