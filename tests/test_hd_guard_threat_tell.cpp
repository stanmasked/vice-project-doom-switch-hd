// Stage91: a genuinely alert source guard drives an optional visual tell.
// Renderer never owns melee timers, motion, collision or player health.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void check(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
bool solid(void* p,int x,int y){
    return static_cast<const vpd::Scene*>(p)->solid(x,y);
}
constexpr int W=vpd::kSceneWidth,H=vpd::kSceneHeight;
uint32_t ink(unsigned r,unsigned g,unsigned b){
    return 0xff000000u | r | (g<<8) | (b<<16);
}
vpd::SceneView bridge(const vpd::Simulation& sim){
    const auto& p=sim.player();
    vpd::SceneView view{
        p.x/vpd::kFixed,p.y/vpd::kFixed,sim.cameraX(),
        sim.frame(),p.grounded,
        const_cast<vpd::Scene*>(&sim.scene()),solid
    };
    view.manual_controls=true;
    vpd::applyCombatOverlay(view,sim);
    return view;
}
std::vector<uint32_t> raster(const vpd::SceneView& view){
    std::vector<uint32_t> im(static_cast<std::size_t>(W)*H);
    check(vpd::drawScene(im.data(),W,H,W,view),"native scene rejected");
    return im;
}
uint32_t pixel(const std::vector<uint32_t>& im,int x,int y){
    check(x>=0 && x<W && y>=0 && y<H,"source alert ROI offscreen");
    return im[static_cast<std::size_t>(y)*W+x];
}
void testDifferenceOnlyInCue(const vpd::SceneView& view){
    auto off=view;
    off.hd_guard_threat_tell=false;
    auto on=off;
    on.hd_guard_threat_tell=true;
    const auto plain=raster(off),cue=raster(on);
    const int gx=(view.guard.x_px-view.camera_x_px)*2;
    const int gy=(view.guard.y_px+80)*2;
    unsigned changed=0;
    for(int y=0;y<H;++y)
        for(int x=0;x<W;++x){
            if(pixel(plain,x,y)==pixel(cue,x,y))continue;
            check(x>=gx+3 && x<gx+30 && y>=gy-27 && y<gy-9,
                  "guard warning altered terrain, actor, HP HUD or backdrop");
            ++changed;
        }
    check(changed>=45,"guard source cue not visible in real RGBA");
}
void invisible(const vpd::SceneView& src,const char* why){
    auto a=src,b=src;
    a.hd_guard_threat_tell=false;
    b.hd_guard_threat_tell=true;
    check(raster(a)==raster(b),why);
}
}
int main(){
 try{
    using namespace vpd;
    Simulation sim;
    sim.enableEnemyEncounter();
    auto quiet=bridge(sim);
    check(quiet.guard.enabled && !quiet.guard.alerted,
          "guard must begin outside detection range");
    invisible(quiet,"indicator appeared before genuine guard detection");
    const uint64_t pristine=sim.fingerprint();
    bool alerted=false;
    for(int i=0;i<110;++i){
        sim.tick(Input{Right});
        if(sim.guardEnemy().alerted && sim.guardEnemy().attacks==0){
            alerted=true;break;
        }
    }
    check(alerted,"live guard never detected moving player before strike");
    auto ready=bridge(sim);
    check(ready.guard.attack_cooldown==0 && ready.guard.alerted &&
          ready.player_health==5,"real game bridge dropped ready attack state");
    const int rx=(ready.guard.x_px-ready.camera_x_px)*2;
    const int ry=(ready.guard.y_px+80)*2;
    ready.hd_guard_threat_tell=true;
    const auto readypixels=raster(ready);
    check(pixel(readypixels,rx+10,ry-27)==ink(248,198,104) &&
          pixel(readypixels,rx+10,ry-13)==ink(248,198,104),
          "ready-to-strike exclamation not visible above real enemy");
    testDifferenceOnlyInCue(ready);
    auto optout=ready;
    optout.manual_controls=false;
    invisible(optout,"new HD guard icon leaked into old auto-demo");

    // Keep pressing Right only to first authentic melee contact. Further
    // movement would outrun the guard between its 32-tick real cooldowns.
    bool hit=false;
    for(int i=0;i<200;++i){
        sim.tick(Input{Right});
        if(sim.guardEnemy().attacks==1){hit=true;break;}
    }
    check(hit && sim.playerHealth()==4 &&
          sim.guardEnemy().attack_cooldown==32,
          "guard did not land its real initial 32-tick cooldown strike");
    auto cooling=bridge(sim);
    check(cooling.guard.attack_cooldown==32 &&
          cooling.player_hit_flash_ticks==16,
          "combat bridge misrepresented melee cooldown or hit feedback");
    cooling.hd_guard_threat_tell=true;
    const int cx=(cooling.guard.x_px-cooling.camera_x_px)*2;
    const int cy=(cooling.guard.y_px+80)*2;
    const auto cold=raster(cooling);
    check(pixel(cold,cx+5,cy-22)==ink(92,101,118) &&
          pixel(cold,cx+13,cy-22)==ink(92,101,118) &&
          pixel(cold,cx+21,cy-22)==ink(92,101,118),
          "fresh attack cooldown should leave all three pips dim");
    testDifferenceOnlyInCue(cooling);
    const uint64_t before=sim.fingerprint();
    auto without=cooling;
    without.hd_guard_threat_tell=false;
    (void)raster(without);
    (void)raster(cooling);
    check(sim.fingerprint()==before,"rendering warning changed gameplay state");
    for(int i=0;i<12;++i)sim.tick(Input{});
    check(sim.guardEnemy().attack_cooldown==20 &&
          sim.playerHealth()==4,"cooldown or HP changed unexpectedly while idle");
    auto warmed=bridge(sim);
    warmed.hd_guard_threat_tell=true;
    const int wx=(warmed.guard.x_px-warmed.camera_x_px)*2;
    const int wy=(warmed.guard.y_px+80)*2;
    const auto warming=raster(warmed);
    check(pixel(warming,wx+5,wy-22)==ink(237,170,101) &&
          pixel(warming,wx+13,wy-22)==ink(92,101,118),
          "actual cooldown did not refill exactly one of three threat pips");
    testDifferenceOnlyInCue(warmed);
    auto dead=warmed;
    dead.guard.health=0;
    invisible(dead,"dead guard incorrectly displayed threat indicator");
    auto healthy=warmed;
    healthy.guard.alerted=false;
    invisible(healthy,"unaware guard displayed an attack readiness cue");
    auto defeated=warmed;
    defeated.player_health=0;
    invisible(defeated,"guard warning leaked onto terminal defeat screen");
    auto victory=warmed;
    victory.stage_cleared=true;
    invisible(victory,"guard warning leaked into cleared stage");

    Simulation demo;
    auto old=bridge(demo);
    old.manual_controls=false;
    check(!old.guard.enabled && demo.fingerprint()!=pristine,
          "control fixture accidentally used altered first encounter");
    invisible(old,"ROM-free legacy demo changed through new visual switch");

    std::puts("VPD_HD_GUARD_THREAT_TELL_PASS "
              "genuine_detection=yes actual_contact=yes "
              "melee_cooldown_32_to_20=yes refill_pips=yes "
              "native_rgba_only_cue=yes runtime_hd_toggle=yes "
              "source_simulation_unchanged=yes old_demo_unchanged=yes "
              "original_game_proven=no physical_switch_proven=no");
    return 0;
 }catch(const std::exception& error){
    std::fprintf(stderr,"VPD_HD_GUARD_THREAT_TELL_FAIL %s\n",error.what());
    return 1;
 }
}
