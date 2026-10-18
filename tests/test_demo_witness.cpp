// Host-only test for the exact state-only witness used by both libnx NROs.
#include "demo_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>

static void require(bool good,const char* error) {
    if(!good)throw std::runtime_error(error);
}
int main(){
    try{
        vpd::Simulation game;
        vpd::CombatDemo demo;
        require(!vpd::demoCheckpointReached(demo,game),
                "initialization forged completed playback");
        std::FILE* file=std::tmpfile();
        require(file!=nullptr,"portable temporary file unavailable");
        for(unsigned loop=1;loop<=4;++loop){
            for(unsigned frame=0;frame<200;++frame){
                demo.tick(game);
                if(frame<199)
                    require(!vpd::demoCheckpointReached(demo,game),
                            "premature witness before 200th tick");
            }
            require(vpd::demoCheckpointReached(demo,game),
                    "completed run not recognized");
            require(vpd::demoCheckpointMatches(game),
                    "completed run failed synthetic state comparison");
            require(vpd::writeDemoWitness(file,game,loop),
                    "failed to serialize valid witness record");
        }
        require(!vpd::writeDemoWitness(file,game,5),
                "unbounded run count was accepted");
        require(!vpd::writeDemoWitness(nullptr,game,1),
                "null stream was accepted");
        require(std::fseek(file,0,SEEK_SET)==0,"witness file rewind failed");
        char line[256]{};
        for(unsigned loop=1;loop<=4;++loop){
            require(std::fgets(line,sizeof(line),file)!=nullptr,
                    "missing exact demo report line");
            char expected[64]{};
            std::snprintf(expected,sizeof(expected),"cycle=%u frames=200",loop);
            require(std::strstr(line,"VPD_ROMFREE_DEMO_WITNESS_V1 cycle=")==line &&
                    std::strstr(line,expected)!=nullptr &&
                    std::strstr(line,"shots=11 hits=3 health=0")!=nullptr &&
                    std::strstr(line,"fnv=5947277116621119566")!=nullptr &&
                    std::strstr(line,"state_match=yes")!=nullptr &&
                    std::strstr(line,"frame_submitted=yes")!=nullptr &&
                    std::strstr(line,"original_game_proven=no")!=nullptr,
                    "valid report failed exact content check");
        }
        require(std::fgets(line,sizeof(line),file)==nullptr,
                "unbounded extra witness data observed");
        std::fclose(file);
        // Changed game state must be reported as a mismatch, never PASS.
        vpd::Simulation altered=game;
        altered.scene().setSolid(57,3,true);
        require(!vpd::demoCheckpointMatches(altered),
                "map mutation did not invalidate runtime witness");
        file=std::tmpfile();
        require(file && vpd::writeDemoWitness(file,altered,1),
                "mismatched state was silently discarded");
        std::rewind(file);
        require(std::fgets(line,sizeof(line),file)!=nullptr &&
                std::strstr(line,"state_match=no")!=nullptr,
                "failure-state record falsely claimed success");
        std::fclose(file);
        demo.toggle(game);
        require(!vpd::demoCheckpointReached(demo,game),
                "manual mode forged a completed demo witness");
        file=std::tmpfile();
        require(file!=nullptr,"temporary file unavailable");
        require(!vpd::writeDemoWitness(file,game,1),
                "zero-frame manual play forged report");
        std::fclose(file);
        std::puts("VPD_ROMFREE_SWITCH_WITNESS_HOST_PASS "
                  "cycles=4 frames_each=200 state_match=yes "
                  "invalid_state=reported_not_hidden "
                  "manual_mode=rejected no_emulator_execution_claim=yes");
        return 0;
    }catch(const std::exception& exc){
        std::fprintf(stderr,"WITNESS_HOST_REJECT: %s\n",exc.what());
        return 1;
    }
}
