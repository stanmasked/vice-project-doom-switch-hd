// Verify the exact live manual combat event serializer used by libnx.
#include "guard_live_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void require(bool ok,const char* message){
    if(!ok)throw std::runtime_error(message);
}
int main(){
    try{
        vpd::Simulation sim;
        std::FILE* proof=std::tmpfile();
        require(proof!=nullptr,"No temporary evidence stream");
        require(!vpd::liveGuardProofWrite(proof,vpd::LiveGuardEvent::Alert,
                                          sim,vpd::Right),
                "Inactive guard was accepted as live encounter");
        sim.enableEnemyEncounter();
        require(!vpd::liveGuardProofWrite(proof,vpd::LiveGuardEvent::Alert,
                                          sim,vpd::Right),
                "Unalerted guard was accepted");
        unsigned n_alert=0,n_strike=0;
        for(unsigned i=0;i<210;++i){
            const auto before_alerted=sim.guardEnemy().alerted;
            const auto before_hp=sim.playerHealth();
            const auto before_attacks=sim.guardEnemy().attacks;
            sim.tick(vpd::Input{vpd::Right});
            if(!n_alert && !before_alerted && sim.guardEnemy().alerted){
                require(!vpd::liveGuardProofWrite(proof,vpd::LiveGuardEvent::Alert,
                                                  sim,0),
                        "Missing real right input accepted");
                require(vpd::liveGuardProofWrite(proof,vpd::LiveGuardEvent::Alert,
                                                 sim,vpd::Right),
                        "Real right-input guard alert rejected");
                n_alert=sim.frame();
            }
            if(n_alert && !n_strike && before_hp==5 &&
               before_attacks==0 && sim.guardEnemy().attacks==1 &&
               sim.playerHealth()==4){
                require(!vpd::liveGuardProofWrite(proof,vpd::LiveGuardEvent::FirstStrike,
                                                  sim,vpd::Left),
                        "Opposite direction falsely attested strike");
                require(vpd::liveGuardProofWrite(proof,vpd::LiveGuardEvent::FirstStrike,
                                                 sim,vpd::Right),
                        "Real first melee HP loss rejected");
                n_strike=sim.frame();
                break;
            }
        }
        require(n_alert>0 && n_strike>n_alert,"No live manual alert/contact reached");
        require(std::fseek(proof,0,SEEK_SET)==0,"Seek failed");
        char buf[256]{};
        require(std::fgets(buf,sizeof(buf),proof)!=nullptr &&
                std::strstr(buf,"seq=1 event=alert") &&
                std::strstr(buf,"player_hp=5") &&
                std::strstr(buf,"source=live_guest"),
                "Incorrect alert witness format");
        require(std::fgets(buf,sizeof(buf),proof)!=nullptr &&
                std::strstr(buf,"seq=2 event=strike") &&
                std::strstr(buf,"player_hp=4") &&
                std::strstr(buf,"cooldown=32"),
                "Incorrect first strike proof");
        require(std::fgets(buf,sizeof(buf),proof)==nullptr,
                "Live manual witness must have exactly two events");
        std::fclose(proof);
        std::printf("VPD_ROMFREE_GUARD_LIVE_SERIALIZER_PASS "
                    "alert_frame=%u strike_frame=%u "
                    "observed_right=yes hp_lost=1 script_guest=no\n",
                    n_alert,n_strike);
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_GUARD_LIVE_REJECT %s\n",e.what());
        return 1;
    }
}
