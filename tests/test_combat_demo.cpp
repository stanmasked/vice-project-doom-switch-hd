// Host-only ROM-free replay-at-boot and manual-toggle regression.
#include "combat_demo.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>

static void require(bool ok,const char* what){
    if(!ok)throw std::runtime_error(what);
}
int main(){
    try {
        vpd::Simulation game,reference;
        vpd::CombatDemo demo;
        require(demo.enabled() && demo.nextFrame()==0,
                "autoplay must begin without controller input");
        unsigned fresh=0;
        uint64_t one=0,two=0;
        for(unsigned tick=0;tick<400;++tick){
            if(demo.tick(game))++fresh;
            if(tick==199 || tick==399){
                require(game.frame()==200 && game.shotsFired()==11 &&
                        game.trainingTarget().hits==3 &&
                        game.trainingTarget().health==0,
                        "script loop did not reproduce the practice target");
                const uint64_t fingerprint=game.fingerprint();
                require(fingerprint==5947277116621119566ULL,
                        "200-frame ROM-free golden replay mismatch");
                if(tick==199)one=fingerprint;
                else two=fingerprint;
            }
            if(tick==200){
                reference.tick(vpd::combatDemoInput(0));
                require(game.frame()==1 &&
                        game.fingerprint()==reference.fingerprint() &&
                        game.shotsFired()==1 &&
                        game.trainingTarget().health==3,
                        "loop boundary retained stale gameplay state");
            }
        }
        require(fresh==2 && one==two && demo.nextFrame()==200,
                "demo did not repeat the exact 200-frame scenario twice");
        demo.toggle(game);
        require(!demo.enabled() && demo.nextFrame()==0 &&
                game.frame()==0 && game.shotsFired()==0 &&
                game.trainingTarget().health==3,
                "disabling demo failed to reset into manual play");
        require(!demo.tick(game) && game.frame()==0,
                "disabled demo still advanced the game");
        game.tick(vpd::Input{vpd::Right});
        require(game.frame()==1,"manual controls cannot advance");
        demo.toggle(game);
        require(demo.enabled() && demo.nextFrame()==0 && game.frame()==0,
                "enabling demo failed to reset manual inputs");
        require(demo.tick(game) && game.frame()==1 &&
                game.shotsFired()==1,
                "re-enabling demo did not replay its initial shot");
        require(vpd::combatDemoInput(200).buttons==0 &&
                vpd::combatDemoInput(110).buttons==0 &&
                vpd::combatDemoInput(115).buttons==vpd::Right &&
                vpd::combatDemoInput(145).buttons==(vpd::Left|vpd::Jump) &&
                vpd::combatDemoInput(150).buttons==vpd::Left,
                "source-shared input script changed at transition");
        std::printf("VPD_ROMFREE_AUTOPLAY_DEMO_PASS loops=2 "
                    "frames=400 shots_per_loop=11 hits_per_loop=3 "
                    "golden_fingerprint=%llu reset_at_boundary=yes "
                    "manual_toggle=yes native_switch_runtime_proven=no\n",
                    static_cast<unsigned long long>(one));
        return 0;
    } catch(const std::exception& ex){
        std::fprintf(stderr,"ROMFREE_AUTOPLAY_DEMO_REJECT: %s\n",ex.what());
        return 1;
    }
}
