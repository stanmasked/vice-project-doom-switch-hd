// Actual turret/projectile pixels are produced by shared Switch renderer.
#include "simulation.hpp"
#include "combat_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>
namespace {
void require(bool okay,const char* reason){if(!okay)throw std::runtime_error(reason);}
bool solid(void* ptr,int x,int y){
    return static_cast<const vpd::Scene*>(ptr)->solid(x,y);
}
vpd::SceneView viewFor(const vpd::Simulation& sim){
    auto& player=sim.player();
    vpd::SceneView view{
        player.x/vpd::kFixed,player.y/vpd::kFixed,sim.cameraX(),
        sim.frame(),player.grounded,
        const_cast<vpd::Scene*>(&sim.scene()),solid
    };
    view.manual_controls=true;
    vpd::applyCombatOverlay(view,sim);
    return view;
}
uint64_t raster(const vpd::SceneView& scene){
    std::vector<uint32_t> pixels(
        static_cast<std::size_t>(vpd::kSceneWidth)*vpd::kSceneHeight);
    require(vpd::drawScene(pixels.data(),vpd::kSceneWidth,
                           vpd::kSceneHeight,vpd::kSceneWidth,scene),
            "Raster rejected sentry scene");
    uint64_t hash=14695981039346656037ULL;
    for(const auto pixel:pixels){hash^=pixel;hash*=1099511628211ULL;}
    return hash;
}
}
int main(){
    try{
        using namespace vpd;
        Simulation world;
        world.enableEnemyEncounter();
        for(int i=0;i<145 && world.guardEnemy().health;++i)
            world.tick(Input{Fire});
        require(world.guardEnemy().health==0,"Failed to defeat first guard");
        while(!world.secondWaveActive() && world.frame()<400)
            world.tick(Input{Right});
        require(world.secondWaveActive(),"Second wave not activated");
        const auto before=viewFor(world);
        require(before.sentry.enabled && before.sentry.health==2 &&
                !before.stage_cleared,"Turret not propagated to SceneView");
        auto hidden=before;
        hidden.sentry.enabled=false;
        require(raster(before)!=raster(hidden),
                "Sentry not visible in real RGBA framebuffer");
        auto wounded=before;
        wounded.sentry.health=1;
        require(raster(before)!=raster(wounded),
                "Sentry health chip unresponsive");
        bool fired=false;
        for(int i=0;i<130;++i){
            world.tick(Input{Right});
            fired|=world.sentry().shots_fired>0;
            if(fired)break;
        }
        require(fired,"Sentry never fired in render test");
        const auto shot=viewFor(world);
        require(shot.sentry.enabled && shot.enemy_projectiles[0].active,
                "Hostile projectile omitted from shared bridge");
        auto erased=shot;
        erased.enemy_projectiles[0].active=false;
        require(raster(shot)!=raster(erased),
                "Enemy projectile missing from actual raster");
        // The existing guard/first wave remains unaffected by the
        // otherwise optional second-wave sprite.
        Simulation demo;
        const auto idle=viewFor(demo);
        require(!idle.sentry.enabled && !idle.enemy_projectiles[0].active,
                "Legacy mode unexpectedly displayed sentry");
        std::puts("VPD_ROMFREE_SECOND_WAVE_RASTER_PASS sentry=yes "
                  "health_chips=yes hostile_bullet=yes "
                  "auto_demo_untouched=yes native_guest_proven=no");
        return 0;
    }catch(const std::exception& ex){
        std::fprintf(stderr,"VPD_SECOND_WAVE_RASTER_REJECT: %s\n",ex.what());
        return 1;
    }
}
