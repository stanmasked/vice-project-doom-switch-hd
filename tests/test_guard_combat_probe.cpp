// The same deterministic guard-combat probe used by the native libnx NRO.
#include "guard_combat_probe.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void check(bool condition, const char* message){
    if(!condition)throw std::runtime_error(message);
}

int main() {
    try {
        vpd::GuardCombatSamples a{}, b{};
        check(vpd::collectGuardCombatSamples(a) &&
              vpd::collectGuardCombatSamples(b),
              "Scripted guard combat never reached all five milestones");
        for(unsigned i=0;i<a.size();++i){
            const auto& x=a[i];
            const auto& y=b[i];
            check(x.frame==y.frame && x.guard_x==y.guard_x &&
                  x.guard_health==y.guard_health &&
                  x.player_health==y.player_health && x.hits==y.hits &&
                  x.attacks==y.attacks && x.cooldown==y.cooldown &&
                  x.alerted==y.alerted,
                  "Repeated independent guard scenarios differ");
        }
        check(a[0].alerted && a[0].attacks==0 && a[0].player_health==5,
              "Guard proximity alert missing");
        check(a[1].attacks==1 && a[1].cooldown==32 &&
              a[1].player_health==4 && a[1].frame>a[0].frame,
              "Native-scripted contact attack did not apply damage");
        for(unsigned i=2;i<5;++i){
            check(a[i].hits==i-1 && a[i].guard_health==4-i,
                  "Native projectile impacts did not reduce guard HP");
            if(i>2)check(a[i].frame>a[i-1].frame,
                         "Projectile hit frames nonmonotonic");
        }
        check(a[4].guard_health==0 && !a[4].alerted,
              "Defeated enemy remains active");

        std::FILE* out=std::tmpfile();
        check(out!=nullptr,"Temporary witness stream unavailable");
        check(vpd::writeGuardCombatProof(out,a),
              "Guest-source record serializer rejected valid combat");
        check(std::fseek(out,0,SEEK_SET)==0,"Stream rewind failed");
        static constexpr const char* expected[5]={
            "seq=1 event=alert scenario=approach ",
            "seq=2 event=attack scenario=approach ",
            "seq=3 event=hit1 scenario=shoot ",
            "seq=4 event=hit2 scenario=shoot ",
            "seq=5 event=defeat scenario=shoot "
        };
        char line[256]{};
        for(unsigned i=0;i<5;++i){
            check(std::fgets(line,sizeof(line),out)!=nullptr,
                  "Serialized combat event truncated");
            check(std::strstr(line,expected[i])!=nullptr &&
                  std::strstr(line,"source=guest_script")!=nullptr,
                  "Unexpected native combat row schema/order");
        }
        check(std::fgets(line,sizeof(line),out)==nullptr,
              "Native guest probe created extra combat rows");
        std::fclose(out);
        std::printf("VPD_ROMFREE_GUARD_COMBAT_SCRIPT_HOST_PASS "
                    "alert_frame=%u attack_frame=%u "
                    "hit_frames=%u,%u,%u "
                    "independent_runs=2 deterministic=yes native_guest=no\n",
                    a[0].frame,a[1].frame,
                    a[2].frame,a[3].frame,a[4].frame);
        return 0;
    } catch(const std::exception& e){
        std::fprintf(stderr,"VPD_GUARD_COMBAT_SCRIPT_REJECT %s\n",e.what());
        return 1;
    }
}
