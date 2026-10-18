#include "manual_input_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
static void check(bool yes,const char* error){if(!yes)throw std::runtime_error(error);}
int main(){
 try{
  vpd::Simulation game;
  using vpd::ManualProofEvent;
  std::FILE* file=std::tmpfile();
  check(file!=nullptr,"temp file unavailable");
  check(vpd::manualProofWrite(file,ManualProofEvent::Enter,1,game,1),
        "initial manual mode witness rejected");
  check(!vpd::manualProofWrite(file,ManualProofEvent::Right,3,game,100),
        "incorrect event sequence accepted");
  check(!vpd::manualProofWrite(file,ManualProofEvent::Right,2,game,0),
        "movement without effect accepted");
  const auto x=game.player().x;
  game.tick(vpd::Input{vpd::Right});
  check(game.player().x>x,"test did not move right");
  check(vpd::manualProofWrite(file,ManualProofEvent::Right,2,game,
                              game.player().x-x),"right movement missing");
  const auto shots=game.shotsFired();
  game.tick(vpd::Input{vpd::Fire});
  check(game.shotsFired()>shots,"test did not fire");
  check(vpd::manualProofWrite(file,ManualProofEvent::Fire,3,game,1),
        "fire witness missing");
  game.tick(vpd::Input{vpd::Jump});
  check(game.player().vy<0,"test did not jump");
  check(vpd::manualProofWrite(file,ManualProofEvent::Jump,4,game,
                              -game.player().vy),"jump witness missing");
  const auto last=game.player().x;
  game.tick(vpd::Input{vpd::Left});
  check(game.player().x<last,"test did not move left");
  check(vpd::manualProofWrite(file,ManualProofEvent::Left,5,game,
                              last-game.player().x),"left witness missing");
  check(vpd::manualProofWrite(file,ManualProofEvent::Plus,6,game,1),
        "plus receipt not serialized");
  check(vpd::manualProofWrite(file,ManualProofEvent::Exit,7,game,1),
        "cleanup not serialized");
  check(std::fseek(file,0,SEEK_SET)==0,"rewind failed");
  char buffer[256]{};
  for(unsigned i=1;i<=7;++i){
   check(std::fgets(buffer,sizeof(buffer),file)!=nullptr,"missing row");
   char expected[48]{};
   std::snprintf(expected,sizeof(expected),"seq=%u",i);
   check(std::strstr(buffer,expected)!=nullptr &&
         std::strstr(buffer,"mode=manual")!=nullptr,
         "malformed witnessed manual event");
  }
  check(std::fgets(buffer,sizeof(buffer),file)==nullptr,"excess rows");
  std::fclose(file);
  game.reset();
  check(!vpd::manualProofValid(ManualProofEvent::Plus,game,1),
        "plus before manual gameplay falsely accepted");
  std::puts("VPD_ROMFREE_MANUAL_HOST_PASS events=7 effects=right,fire,jump,left plus_and_cleanup=yes");
  return 0;
 }catch(const std::exception& exc){
  std::fprintf(stderr,"MANUAL_HOST_REJECT: %s\n",exc.what());
  return 1;
 }
}
