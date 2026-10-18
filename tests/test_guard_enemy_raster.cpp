// Guard sprite pixels come from the same gameplay adapter as the Switch NRO.
#include "simulation.hpp"
#include "combat_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void check(bool test,const char* why){if(!test)throw std::runtime_error(why);}
bool solid(void* p,int x,int y){
    return static_cast<const vpd::Scene*>(p)->solid(x,y);
}
vpd::SceneView makeView(const vpd::Simulation& game){
    const auto& player=game.player();
    vpd::SceneView view{
        player.x/vpd::kFixed,player.y/vpd::kFixed,game.cameraX(),
        game.frame(),player.grounded,
        const_cast<vpd::Scene*>(&game.scene()),solid
    };
    view.manual_controls=true;
    vpd::applyCombatOverlay(view,game);
    return view;
}
uint64_t pixels(const vpd::SceneView& view){
    std::vector<uint32_t> image(
        static_cast<std::size_t>(vpd::kSceneWidth)*vpd::kSceneHeight);
    check(vpd::drawScene(image.data(),vpd::kSceneWidth,
                         vpd::kSceneHeight,vpd::kSceneWidth,view),
          "Renderer rejected the guard scene");
    uint64_t hash=14695981039346656037ULL;
    for(uint32_t pixel:image){hash^=pixel;hash*=1099511628211ULL;}
    return hash;
}
}
int main(){
 try{
    vpd::Simulation game;
    auto empty=makeView(game);
    check(!empty.guard.enabled,"Guard unexpectedly active in legacy demo");
    game.enableEnemyEncounter();
    game.tick(vpd::Input{});
    const auto guard=makeView(game);
    check(guard.guard.enabled && guard.guard.health==3 &&
          guard.player_health==5, "Combat bridge did not expose live enemy state");
    auto hidden=guard;
    hidden.guard.enabled=false;
    check(pixels(guard)!=pixels(hidden),
          "Guard is not present in actual raster pixels");
    // Attacking changes the player-health HUD and must not be an invented
    // renderer-only effect.
    bool has_attacked=false;
    for(int i=0;i<200;++i){
        game.tick(vpd::Input{vpd::Right});
        if(game.guardEnemy().attacks){has_attacked=true;break;}
    }
    check(has_attacked,"Fixture did not reach a real guard attack");
    const auto hit=makeView(game);
    check(hit.player_health<5,"Player HUD did not receive health loss");
    auto restored=hit;
    restored.player_health=5;
    check(pixels(hit)!=pixels(restored),
          "Actual contact damage left health HUD unchanged");
    auto unaware=hit;
    unaware.guard.alerted=false;
    check(hit.guard.alerted && pixels(hit)!=pixels(unaware),
          "Detection state not rendered on guard character");
    vpd::Simulation shooter;
    shooter.enableEnemyEncounter();
    for(int i=0;i<125;++i)shooter.tick(vpd::Input{vpd::Fire});
    const auto dead=makeView(shooter);
    check(dead.guard.health==0 && dead.guard.enabled,
          "Real bullets did not produce defeated enemy sprite state");
    auto resurrected=dead;
    resurrected.guard.health=3;
    check(pixels(dead)!=pixels(resurrected),
          "Defeated enemy remains visible in the raster");
    std::puts("VPD_ROMFREE_GUARD_RASTER_PASS movement=yes alert=yes "
              "health_pixels=yes projectile_defeat_pixels=yes "
              "original_game_proven=no native_switch_runtime_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_ROMFREE_GUARD_RASTER_REJECT %s\n",e.what());
    return 1;
 }
}
