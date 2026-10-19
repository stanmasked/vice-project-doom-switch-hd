// Host replay of the exact bounded second-wave guest diagnostic.
#include "second_wave_guest_probe.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace {
void check(bool v,const char* msg){if(!v)throw std::runtime_error(msg);}
void same(const vpd::SentryProofRow& x,const vpd::SentryProofRow& y){
    check(x.frame==y.frame && x.player_x==y.player_x &&
          x.guard_hp==y.guard_hp && x.sentry_hp==y.sentry_hp &&
          x.player_hp==y.player_hp &&
          x.sentry_shots==y.sentry_shots &&
          x.sentry_hits==y.sentry_hits &&
          x.sentry_damage==y.sentry_damage &&
          x.wave==y.wave && x.clear==y.clear,
          "Independent second-wave replays differ");
}
}
int main(){
    try{
        vpd::SentryProofRows first{},second{};
        check(vpd::collectSentryProof(first) &&
              vpd::collectSentryProof(second),
              "Second-wave guest script failed to achieve all five states");
        for(unsigned i=0;i<5;++i)same(first[i],second[i]);
        check(!first[0].wave && first[1].wave &&
              first[1].sentry_hp==2,"Wave gate failed");
        check(first[2].sentry_hits>0 && first[2].player_hp<5,
              "Hostile projectile was not consumed by player");
        check(first[3].sentry_hp==0 && first[3].sentry_damage==2,
              "Real player projectiles failed to defeat turret");
        check(first[4].clear && first[4].player_x>=55*16*256 &&
              first[4].player_hp>0,"No authentic exit transition");
        std::FILE* f=std::tmpfile();
        check(f!=nullptr,"tempfile unavailable");
        check(vpd::writeSentryProof(f,first),
              "Guest writer rejected actual physics events");
        std::rewind(f);
        const char* expected[5]={
            "seq=1 event=guard scenario=stage",
            "seq=2 event=wave scenario=stage",
            "seq=3 event=hostile_hit scenario=stationary",
            "seq=4 event=turret_down scenario=stage",
            "seq=5 event=exit scenario=stage"
        };
        char buffer[330]{};
        for(unsigned i=0;i<5;++i){
            check(std::fgets(buffer,sizeof(buffer),f)!=nullptr &&
                  std::strstr(buffer,expected[i]) &&
                  std::strstr(buffer,"source=guest_script"),
                  "Malformed/reordered guest proof row");
        }
        check(std::fgets(buffer,sizeof(buffer),f)==nullptr,
              "Guest script emitted extra events");
        std::fclose(f);
        std::printf("VPD_ROMFREE_WAVE2_NATIVE_PROBE_HOST_PASS "
                    "spawn_frame=%u hostile_hit_frame=%u "
                    "defeat_frame=%u exit_frame=%u "
                    "duplicate_replay=yes native_guest_proven=no\n",
                    first[1].frame,first[2].frame,
                    first[3].frame,first[4].frame);
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_WAVE2_NATIVE_PROBE_REJECT %s\n",e.what());
        return 1;
    }
}
