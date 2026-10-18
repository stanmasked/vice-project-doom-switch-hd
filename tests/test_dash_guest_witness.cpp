// Host-side tests for exact guest serializer used by libnx NRO.
#include "dash_guest_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(){
 try {
    vpd::Simulation game;
    std::FILE* file=std::tmpfile();
    check(file!=nullptr,"temporary stream unavailable");
    check(!vpd::dashGuestProofWrite(file,vpd::DashGuestEvent::Start,game,
                                    6*vpd::kFixed),
          "unpressed dash was accepted");
    const auto x=game.player().x;
    game.tick(vpd::Input{static_cast<uint8_t>(vpd::Right|vpd::Dash)});
    check(!vpd::dashGuestProofWrite(file,vpd::DashGuestEvent::Start,game,
                                   2*vpd::kFixed),
          "ordinary walking delta was accepted");
    check(vpd::dashGuestProofWrite(file,vpd::DashGuestEvent::Start,game,
                                  game.player().x-x),
          "real initial dash step rejected");
    for(int i=0;i<5;++i)game.tick(vpd::Input{vpd::Right});
    check(!vpd::dashGuestProofWrite(file,vpd::DashGuestEvent::Complete,game,
                                   6*vpd::kFixed),
          "incomplete six-tick burst accepted");
    check(vpd::dashGuestProofWrite(file,vpd::DashGuestEvent::Complete,game,
                                  game.player().x-x),
          "completed six-tick dash rejected");
    check(std::fseek(file,0,SEEK_SET)==0,"stream rewind failed");
    char row[240]{};
    check(std::fgets(row,sizeof(row),file)!=nullptr &&
          std::strstr(row,"event=start") &&
          std::strstr(row,"delta_fixed=1536") &&
          std::strstr(row,"cooldown=45"),"start schema changed");
    check(std::fgets(row,sizeof(row),file)!=nullptr &&
          std::strstr(row,"event=complete") &&
          std::strstr(row,"delta_fixed=9216") &&
          std::strstr(row,"cooldown=40"),"completion schema changed");
    check(std::fgets(row,sizeof(row),file)==nullptr,
          "extra guest events");
    std::fclose(file);
    std::puts("VPD_ROMFREE_DASH_GUEST_SERIALIZER_PASS events=2");
    return 0;
 }catch(const std::exception& err) {
    std::fprintf(stderr,"DASH_GUEST_SERIALIZER_REJECT: %s\n",err.what());
    return 1;
 }
}
