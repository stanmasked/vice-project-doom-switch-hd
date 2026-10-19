// End-state UI rendering from real source hero death / stage victory.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>
namespace {
void check(bool value,const char* message){
    if(!value)throw std::runtime_error(message);
}
bool solid(void* ptr,int x,int y){
    return static_cast<const vpd::Scene*>(ptr)->solid(x,y);
}
vpd::SceneView scene(const vpd::Simulation& sim,bool manual=true){
    const auto& actor=sim.player();
    vpd::SceneView view{actor.x/vpd::kFixed,actor.y/vpd::kFixed,
                        sim.cameraX(),sim.frame(),actor.grounded,
                        const_cast<vpd::Scene*>(&sim.scene()),solid};
    view.manual_controls=manual;
    vpd::applyCombatOverlay(view,sim);
    return view;
}
using Raster=std::vector<uint32_t>;
Raster rasterize(const vpd::SceneView& view){
    Raster p(static_cast<std::size_t>(vpd::kSceneWidth)
             *vpd::kSceneHeight);
    check(vpd::drawScene(p.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                         vpd::kSceneWidth,view),"Portable RGBA draw failed");
    return p;
}
unsigned deltaWithin(const Raster& a,const Raster& b){
    unsigned diff=0;
    for(int y=225;y<420;++y)
        for(int x=355;x<925;++x){
            const auto ix=static_cast<std::size_t>(y)*vpd::kSceneWidth+x;
            if(a[ix]!=b[ix])++diff;
        }
    return diff;
}
}
int main(){
    try{
        using namespace vpd;
        Simulation dead;
        dead.enableEnemyEncounter();
        for(int n=0;n<420 && dead.playerHealth();++n)
            dead.tick(Input{Right});
        check(dead.playerHealth()==0 && !dead.stageCleared(),
              "Damage source never killed hero");
        const auto real_dead=scene(dead);
        auto invalid_alive=real_dead;
        invalid_alive.player_health=1; // only comparison: no fabricated pixels
        check(deltaWithin(rasterize(real_dead),
                          rasterize(invalid_alive))>1200,
              "Real defeat did not create central failure panel");
        check(retryTerminalEncounter(dead,true)==ManualRetryOutcome::AfterDefeat,
              "Victory/defeat retry input unavailable");
        const auto revived=scene(dead);
        check(revived.player_health==5 && !revived.stage_cleared &&
              !revived.exit_visible,
              "Loss retry leaked health or wave UI");
        check(deltaWithin(rasterize(real_dead),
                          rasterize(revived))>1200,
              "Defeat panel did not disappear after real replay");

        Simulation won;
        won.enableEnemyEncounter();
        for(int n=0;n<160 && won.guardEnemy().health;++n)
            won.tick(Input{Fire});
        for(int n=0;n<280 && !won.secondWaveActive();++n)
            won.tick(Input{Right});
        for(int n=0;n<460 && !won.stageCleared();++n)
            won.tick(Input{static_cast<uint8_t>(Right|Fire)});
        check(won.stageCleared() && won.playerHealth()>0,
              "Actual source progress did not clear wave two");
        const auto real_won=scene(won);
        auto missing_clear=real_won;
        missing_clear.stage_cleared=false; // isolate *earned* overlay pixels
        check(deltaWithin(rasterize(real_won),
                          rasterize(missing_clear))>1200,
              "Victory did not draw earned replay prompt");
        check(retryTerminalEncounter(won,true)==ManualRetryOutcome::AfterVictory,
              "Victory replay control not bound to source logic");
        const auto reset=scene(won);
        check(!reset.stage_cleared && !reset.exit_visible &&
              reset.player_health==5 &&
              deltaWithin(rasterize(real_won),
                          rasterize(reset))>1200,
              "Victory/exit panel leaked into fresh run");

        const auto attract=scene(Simulation{},false);
        check(!attract.manual_controls && !attract.stage_cleared,
              "Auto-demo was unexpectedly converted to terminal screen");
        std::puts("VPD_ROMFREE_RETRY_RASTER_PASS "
                  "death_panel=yes victory_prompt=yes no_leak=yes "
                  "source_derived=yes auto_demo_intact=yes");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_RETRY_RASTER_REJECT %s\n",e.what());
        return 1;
    }
}
