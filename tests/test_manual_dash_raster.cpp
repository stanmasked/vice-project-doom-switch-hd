// Host-side raster contract: actual dash physics reach shared SceneView.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

static void require(bool test,const char* why){
    if(!test)throw std::runtime_error(why);
}
static bool solid(void* context,int x,int y){
    return static_cast<const vpd::Scene*>(context)->solid(x,y);
}
static vpd::SceneView viewFor(const vpd::Simulation& sim){
    const auto& actor=sim.player();
    vpd::SceneView view{
        actor.x/vpd::kFixed,actor.y/vpd::kFixed,sim.cameraX(),
        sim.frame(),actor.grounded,
        const_cast<vpd::Scene*>(&sim.scene()),solid
    };
    view.manual_controls=true;
    vpd::applyCombatOverlay(view,sim);
    return view;
}
static uint64_t render(const vpd::SceneView& view){
    std::vector<uint32_t> pixels(
        static_cast<std::size_t>(vpd::kSceneWidth)*vpd::kSceneHeight);
    require(vpd::drawScene(pixels.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                           vpd::kSceneWidth,view),
            "Renderer rejected live dash scene");
    uint64_t h=14695981039346656037ULL;
    for(uint32_t px:pixels){
        h^=px;h*=1099511628211ULL;
    }
    return h;
}
int main(){
    try {
        vpd::Simulation game;
        auto idle=viewFor(game);
        require(!idle.dash_active && idle.dash_cooldown==0,
                "Initial manual scene contains forged dash");
        game.tick(vpd::Input{static_cast<uint8_t>(vpd::Right|vpd::Dash)});
        const auto active=viewFor(game);
        require(active.dash_active && active.dash_cooldown==45 &&
                active.dash_ever_used,
                "Bridge omitted live grounded dash state");
        auto no_trail=active;
        no_trail.dash_active=false;
        require(render(active)!=render(no_trail),
                "Active dash did not alter actual raster pixels");
        auto no_cooldown=active;
        no_cooldown.dash_cooldown=0;
        require(render(active)!=render(no_cooldown),
                "Manual cooldown bar not driven by gameplay state");
        for(int i=0;i<50;++i)game.tick(vpd::Input{});
        auto recovered=viewFor(game);
        require(!recovered.dash_active && recovered.dash_cooldown==0 &&
                recovered.dash_ever_used,
                "Cooldown failed to recover in source simulation");
        require(render(recovered)==render(recovered),
                "Raster result not deterministic for recovered dash state");
        std::puts("VPD_ROMFREE_DASH_RASTER_PASS source_dash=yes "
                  "trail_pixels=yes cooldown_pixels=yes recovered=yes "
                  "original_game_proven=no");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_ROMFREE_DASH_RASTER_REJECT %s\n",e.what());
        return 1;
    }
}
