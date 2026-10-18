// Host test of the exact live NeXium guard-defeat event serializer.
#include "guard_live_defeat_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void require(bool yes,const char* why){
    if(!yes)throw std::runtime_error(why);
}

int main(){
 try{
    vpd::Simulation sim;
    sim.enableEnemyEncounter();
    std::FILE* stream=std::tmpfile();
    require(stream!=nullptr,"temporary guest serialization stream missing");
    require(!vpd::liveGuardDefeatWrite(
        stream,vpd::LiveGuardDefeatEvent::Fire,1,
        sim,vpd::Fire,sim.guardEnemy().health,
        sim.guardEnemy().projectile_hits,sim.shotsFired()),
        "Fire without an observed shot must be rejected");
    const auto before_shots=sim.shotsFired();
    const auto before_hp=sim.guardEnemy().health;
    const auto before_hits=sim.guardEnemy().projectile_hits;
    sim.tick(vpd::Input{vpd::Fire});
    require(sim.shotsFired()==before_shots+1,"game core did not fire");
    require(!vpd::liveGuardDefeatWrite(
        stream,vpd::LiveGuardDefeatEvent::Fire,1,
        sim,0,before_hp,before_hits,before_shots),
        "host input without actual Fire button accepted");
    require(vpd::liveGuardDefeatWrite(
        stream,vpd::LiveGuardDefeatEvent::Fire,1,
        sim,vpd::Fire,before_hp,before_hits,before_shots),
        "first authentic rightward shot not serialized");
    unsigned seq=1;
    for(int i=0;i<145 && sim.guardEnemy().health;++i){
        const auto hp=sim.guardEnemy().health;
        const auto hits=sim.guardEnemy().projectile_hits;
        const auto shots=sim.shotsFired();
        sim.tick(vpd::Input{vpd::Fire});
        if(sim.guardEnemy().projectile_hits>hits){
            require(!vpd::liveGuardDefeatWrite(
                stream,vpd::LiveGuardDefeatEvent::Impact,seq+1,
                sim,vpd::Fire,hp,hits+1,shots),
                "forged preceding hit count was accepted");
            ++seq;
            require(vpd::liveGuardDefeatWrite(
                stream,vpd::LiveGuardDefeatEvent::Impact,seq,
                sim,vpd::Fire,hp,hits,shots),
                "true swept projectile impact rejected");
        }
    }
    require(sim.guardEnemy().health==0 && seq==4,
            "three genuine swept bullet hits never defeated guard");
    std::rewind(stream);
    char line[320]{};
    for(unsigned index=1;index<=4;++index){
        require(std::fgets(line,sizeof(line),stream)!=nullptr,
                "native writer produced truncated output");
        char expected[50]{};
        std::snprintf(expected,sizeof(expected),"seq=%u ",index);
        require(std::strstr(line,expected)!=nullptr &&
                std::strstr(line,"source=live_guest")!=nullptr,
                "native event provenance or sequence changed");
        if(index==4)
            require(std::strstr(line,"event=defeat") &&
                    std::strstr(line,"hp_after=0"),
                    "last event not an actual enemy defeat");
    }
    require(std::fgets(line,sizeof(line),stream)==nullptr,
            "unexpected extra guest defeat events");
    std::fclose(stream);
    std::puts("VPD_ROMFREE_GUARD_LIVE_DEFEAT_WRITER_PASS "
              "shots_real=yes impact_events=3 guest_only_attestation=yes");
    return 0;
 }catch(const std::exception& exc){
    std::fprintf(stderr,"VPD_LIVE_GUARD_DEFEAT_REJECT %s\n",exc.what());
    return 1;
 }
}
