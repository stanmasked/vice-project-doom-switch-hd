// Original ROM-free gameplay test driver. Does not load NES game assets.
// Output is a deterministic host-side witness, not Switch runtime evidence.
#include "simulation.hpp"
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <iostream>
#include <stdexcept>

namespace {
vpd::Input inputAt(unsigned frame) {
    using namespace vpd;
    if(frame<110U)return Input{Fire};        // target practice
    if(frame>=115U && frame<145U)return Input{Right}; // camera motion
    if(frame>=145U && frame<175U)
        return Input{static_cast<uint8_t>(Left | (frame<150U ? Jump : 0))};
    return Input{};
}
unsigned activeShots(const vpd::Simulation& state){
    unsigned active=0;
    for(const auto& shot:state.projectiles())
        if(shot.active)++active;
    return active;
}
unsigned parseFrames(const char* text){
    if(!text || !*text || *text=='-')throw std::invalid_argument("Invalid frame count");
    errno=0;
    char* end=nullptr;
    const unsigned long count=std::strtoul(text,&end,10);
    if(errno || !end || *end || count<1UL || count>3600UL)
        throw std::invalid_argument("Frames must be between 1 and 3600");
    return static_cast<unsigned>(count);
}
void verify(){
    using namespace vpd;
    Simulation a,b;
    for(unsigned frame=0;frame<200U;++frame){
        const Input input=inputAt(frame);
        a.tick(input);
        b.tick(input);
        if(a.fingerprint()!=b.fingerprint())
            throw std::runtime_error("Independent replay runs diverged");
        if(a.frame()!=frame+1U || a.trainingTarget().hits>3U)
            throw std::runtime_error("Invalid frame counter or repeated target damage");
    }
    if(a.trainingTarget().health!=0U || a.trainingTarget().hits!=3U ||
       a.shotsFired()!=11U || a.frame()!=200U)
        throw std::runtime_error("Shooting practice did not reach expected state");
    // Negative control: world geometry is gameplay state even if player and
    // active projectiles have otherwise identical coordinates.
    Simulation altered=a;
    altered.scene().setSolid(57,3,true);
    if(altered.fingerprint()==a.fingerprint())
        throw std::runtime_error("Changed geometry did not invalidate replay");
    altered.scene().setSolid(57,3,false);
    if(altered.fingerprint()!=a.fingerprint())
        throw std::runtime_error("Restored geometry failed exact replay identity");
    std::cout<<"VPD_ROMFREE_COMBAT_REPLAY_PASS"
             <<" frames=200 shots="<<a.shotsFired()
             <<" target_hits="<<a.trainingTarget().hits
             <<" target_health="<<static_cast<unsigned>(a.trainingTarget().health)
             <<" active_shots="<<activeShots(a)
             <<" final_fingerprint="<<a.fingerprint()
             <<" identical_independent_runs=yes"
             <<" modified_map_control=rejected"
             <<" restored_map_control=clean"
             <<" synthetic_only=yes original_game_proven=no"
             <<" switch_runtime_proven=no\n";
}
void csv(unsigned frames){
    using namespace vpd;
    Simulation game;
    std::cout<<"frame,buttons,x_fixed,y_fixed,camera,shots,target_health,"
                "target_hits,active_projectiles,fingerprint\n";
    for(unsigned frame=0;frame<frames;++frame){
        const Input input=inputAt(frame);
        game.tick(input);
        const auto& p=game.player();
        const auto& t=game.trainingTarget();
        std::cout<<game.frame()<<','
                 <<static_cast<unsigned>(input.buttons)<<','
                 <<p.x<<','<<p.y<<','<<game.cameraX()<<','
                 <<game.shotsFired()<<','
                 <<static_cast<unsigned>(t.health)<<','
                 <<t.hits<<','<<activeShots(game)<<','
                 <<game.fingerprint()<<'\n';
    }
}
} // namespace

int main(int argc,char** argv){
    try{
        if(argc==2 && std::strcmp(argv[1],"--verify")==0){
            verify();
            return 0;
        }
        if(argc==3 && std::strcmp(argv[1],"--frames")==0){
            csv(parseFrames(argv[2]));
            return 0;
        }
        std::cerr<<"Usage: vpd_combat_replay --verify | --frames <1..3600>\n";
        return 2;
    }catch(const std::exception& exc){
        std::cerr<<"Replay rejected: "<<exc.what()<<'\n';
        return 1;
    }
}
