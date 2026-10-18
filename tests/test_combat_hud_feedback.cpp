// Verify real gameplay-derived damage pulses and collision-free manual HUD.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void check(bool yes,const char* reason){if(!yes)throw std::runtime_error(reason);}
bool solid(void* p,int x,int y){
    return static_cast<const vpd::Scene*>(p)->solid(x,y);
}
vpd::SceneView scene(const vpd::Simulation& sim){
    const auto& hero=sim.player();
    vpd::SceneView view{hero.x/vpd::kFixed,hero.y/vpd::kFixed,
                        sim.cameraX(),sim.frame(),hero.grounded,
                        const_cast<vpd::Scene*>(&sim.scene()),solid};
    view.manual_controls=true;
    vpd::applyCombatOverlay(view,sim);
    return view;
}
std::vector<uint32_t> render(const vpd::SceneView& view){
    std::vector<uint32_t> pixels(static_cast<size_t>(vpd::kSceneWidth)
                                *vpd::kSceneHeight);
    check(vpd::drawScene(pixels.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                         vpd::kSceneWidth,view),"Raster failed");
    return pixels;
}
uint32_t pixel(const std::vector<uint32_t>& img,int x,int y){
    return img[static_cast<size_t>(y)*vpd::kSceneWidth+x];
}
void unchangedZone(const std::vector<uint32_t>& a,
                   const std::vector<uint32_t>& b,
                   int x0,int x1,int y0,int y1){
    for(int y=y0;y<y1;++y)
        for(int x=x0;x<x1;++x)
            check(pixel(a,x,y)==pixel(b,x,y),
                  "Manual combat HUD overwrote title or disclaimer");
}
}

int main(){
 try{
    vpd::Simulation sim;
    sim.enableEnemyEncounter();
    const auto base=scene(sim);
    check(base.guard.enabled && base.guard.health==3 &&
          !base.guard.hit_flash_ticks && base.player_health==5,
          "Expected fresh manual combat state");
    const auto fresh=render(base);
    auto injured=base;
    injured.guard.health=2;
    injured.player_health=4;
    const auto damaged=render(injured);
    // Title extends only to x462; disclaimer ends at x548.
    unchangedZone(fresh,damaged,0,476,7,43);
    unchangedZone(fresh,damaged,0,552,47,72);
    check(pixel(fresh,611,18)!=pixel(damaged,611,18),
          "Guard third HP chip failed to respond");
    check(pixel(fresh,821,18)!=pixel(damaged,821,18),
          "Hero fifth HP chip failed to respond");

    // Actual swept bullets trigger 12-tick guard feedback; it must be
    // sourced from Simulation, not injected into the renderer by tests.
    vpd::Simulation firing;
    firing.enableEnemyEncounter();
    bool hit=false;
    for(int i=0;i<125;++i){
        const auto before=firing.guardEnemy().projectile_hits;
        firing.tick(vpd::Input{vpd::Fire});
        if(firing.guardEnemy().projectile_hits>before){hit=true;break;}
    }
    check(hit && firing.guardEnemy().health==2 &&
          firing.guardEnemy().hit_flash_ticks==12,
          "Swept bullet did not start damage feedback");
    const auto active=scene(firing);
    check(active.guard.hit_flash_ticks==12,"Combat adapter lost enemy flash");
    auto faded=active;
    faded.guard.hit_flash_ticks=0;
    check(render(active)!=render(faded),
          "Guard hit pulse did not alter procedural body pixels");
    for(int i=0;i<12;++i)firing.tick(vpd::Input{});
    check(firing.guardEnemy().hit_flash_ticks==0,
          "Guard flash failed to decay without new hits");

    // Real guard contact lights up the live hero/HUD; compare equivalent
    // frames, varying only the *view* flash to isolate presentation.
    vpd::Simulation encounter;
    encounter.enableEnemyEncounter();
    bool struck=false;
    for(int i=0;i<220;++i){
        const auto old=encounter.guardEnemy().attacks;
        encounter.tick(vpd::Input{vpd::Right});
        if(encounter.guardEnemy().attacks>old){struck=true;break;}
    }
    check(struck && encounter.playerHealth()==4 &&
          encounter.playerHitFlashTicks()==16,
          "Actual contact attack did not trigger hero flash");
    auto hurt=scene(encounter);
    check(hurt.player_hit_flash_ticks==16 && hurt.player_health==4,
          "Combat bridge lost live damage event");
    auto recovered=hurt;
    recovered.player_hit_flash_ticks=0;
    check(render(hurt)!=render(recovered),
          "Player damage flash not present in real RGBA pixels");
    for(int i=0;i<16;++i)encounter.tick(vpd::Input{});
    check(encounter.playerHitFlashTicks()==0,
          "Hero damage highlight failed to decay");

    // Disabled auto-demo must not produce any combat-only HUD or feedback.
    vpd::Simulation demo;
    const auto legacy=scene(demo);
    check(!legacy.guard.enabled && !legacy.guard.hit_flash_ticks &&
          !legacy.player_hit_flash_ticks,
          "Default synthetic replay activated guard damage feedback");
    std::puts("VPD_ROMFREE_COMBAT_HUD_FEEDBACK_PASS "
              "title_clear=yes subtitle_clear=yes health_chips=yes "
              "swept_guard_pulse=yes contact_hero_pulse=yes "
              "cooldown_bounded=yes native_guest_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_COMBAT_HUD_FEEDBACK_REJECT %s\n",e.what());
    return 1;
 }
}
