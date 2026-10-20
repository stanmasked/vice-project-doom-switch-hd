// Live ROM-free encounter source -> visual HD ON/OFF comparison.
// This test deliberately observes real gameplay changes, never constructs
// a fake alert/impact/projectile SceneView to obtain a visual difference.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include "hd_fx_guest_proof.hpp"
#include "hd_fx_toggle.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
bool solid(void* p,int x,int y){
    return static_cast<const vpd::Scene*>(p)->solid(x,y);
}
vpd::SceneView viewOf(const vpd::Simulation& sim,bool fx){
    const auto& a=sim.player();
    vpd::SceneView v{a.x/vpd::kFixed,a.y/vpd::kFixed,sim.cameraX(),
        sim.frame(),a.grounded,const_cast<vpd::Scene*>(&sim.scene()),solid};
    v.manual_controls=true;
    v.moving=a.vx!=0;
    v.hd_hit_lighting=fx;
    v.hd_atmospheric_haze=fx;
    v.hd_footstep_dust=fx;
    v.hd_hostile_projectile_halo=fx;
    v.hd_fx_status_enabled=fx;
    v.hd_fx_status_visible=true;
    vpd::applyCombatOverlay(v,sim);
    return v;
}
void compareLive(const vpd::Simulation& sim,
                 std::vector<uint32_t>& off,
                 std::vector<uint32_t>& on){
    using namespace vpd;
    // All drawing uses one immutable authoritative Simulation.
    const uint64_t before=sim.fingerprint();
    const auto a=viewOf(sim,false),b=viewOf(sim,true);
    require(drawScene(off.data(),kSceneWidth,kSceneHeight,kSceneWidth,a),
            "active combat HD-OFF render failed");
    require(drawScene(on.data(),kSceneWidth,kSceneHeight,kSceneWidth,b),
            "active combat HD-ON render failed");
    const auto x=fingerprintHdFxVisual(
        off.data(),kSceneWidth,kSceneHeight,kSceneWidth);
    const auto y=fingerprintHdFxVisual(
        on.data(),kSceneWidth,kSceneHeight,kSceneWidth);
    require(x.pixels==414000 && y.pixels==414000 && x.hash!=y.hash,
            "active combat visual delta must originate outside status HUD");
    require(sim.fingerprint()==before,
            "active combat HD differential render mutated gameplay");
}
// A targeted live-guard replay: emulate the two real shoulder edges after
// the first swept impact, while a second copy runs the identical game inputs.
// The cosmetic setting must not leak into AI, HP, projectiles or frame hash.
void verifyGuardShoulderReplay(){
    using namespace vpd;
    Simulation toggled{},untoggled{};
    toggled.enableEnemyEncounter();
    untoggled.enableEnemyEncounter();
    HdFxRuntimeMode fx{};
    std::vector<uint32_t> off(
        static_cast<std::size_t>(kSceneWidth)*kSceneHeight),on(off.size());
    unsigned first_hit_frame=0;
    for(int frame=0;frame<180;++frame){
        toggled.tick(Input{Fire});
        untoggled.tick(Input{Fire});
        require(toggled.fingerprint()==untoggled.fingerprint(),
                "pre-combat shoulder baseline states diverged");
        if(toggled.guardEnemy().projectile_hits==1){
            first_hit_frame=toggled.frame();
            break;
        }
    }
    require(first_hit_frame>0 && toggled.guardEnemy().health==2 &&
            untoggled.guardEnemy().projectile_hits==1,
            "first native swept guard impact missing before L+R");
    require(fx.acceptShoulders(true,true,true,true,true) && !fx.enabled,
            "first in-combat L+R edge did not disable authored effects");
    const uint64_t before_off=toggled.fingerprint();
    compareLive(toggled,off,on);
    require(toggled.fingerprint()==before_off &&
            toggled.fingerprint()==untoggled.fingerprint(),
            "in-combat HD OFF changed authoritative source state");
    for(int frame=0;frame<12;++frame){
        require(fx.acceptShoulders(true,true,true,false,false) &&
                !fx.enabled,
                "held combat L+R incorrectly re-toggled effects");
        toggled.tick(Input{});
        untoggled.tick(Input{});
        require(toggled.fingerprint()==untoggled.fingerprint(),
                "HD OFF mode changed moving guard or player simulation");
    }
    require(toggled.guardEnemy().health==2 &&
            toggled.guardEnemy().projectile_hits==1 &&
            toggled.playerHealth()>0,
            "first hit guard not alive at second HD edge");
    require(!fx.acceptShoulders(true,false,false,false,false),
            "combat shoulder release triggered a mode change");
    require(fx.acceptShoulders(true,true,true,true,true) && fx.enabled,
            "second in-combat L+R edge did not restore authored effects");
    const uint64_t before_on=toggled.fingerprint();
    compareLive(toggled,off,on);
    require(toggled.fingerprint()==before_on &&
            toggled.fingerprint()==untoggled.fingerprint(),
            "in-combat HD ON changed authoritative source state");
    for(int frame=0;frame<180 && toggled.guardEnemy().health>0;++frame){
        toggled.tick(Input{Fire});
        untoggled.tick(Input{Fire});
        require(toggled.fingerprint()==untoggled.fingerprint(),
                "guard fight diverged after live HD OFF/ON");
    }
    require(toggled.guardEnemy().health==0 &&
            toggled.guardEnemy().projectile_hits==3 &&
            toggled.fingerprint()==untoggled.fingerprint(),
            "combat did not continue to authentic guard defeat after toggles");
    std::puts("VPD_HD_FX_LIVE_CHORD_HOST_PASS combat_edges=2 "
              "guard_alive_both=yes guard_first_hits=1 "
              "scene_roi_pixels=414000 simulation_hash_equal_every_tick=yes "
              "guard_defeated_after_chords=yes physical_switch_proven=no "
              "original_game_proven=no");
}
void verify(){
    verifyGuardShoulderReplay();
    using namespace vpd;
    Simulation sim;
    sim.enableEnemyEncounter();
    std::vector<uint32_t> off(
        static_cast<std::size_t>(kSceneWidth)*kSceneHeight),on(off.size());
    // Real guard takes authentic swept projectile hits from repeated Fire.
    unsigned live_impact=0,live_defeat=0,live_hostile=0;
    const unsigned initial_hp=sim.guardEnemy().health;
    for(int i=0;i<180 && sim.guardEnemy().health>0;++i){
        const auto previous=sim.guardEnemy().health;
        sim.tick(Input{Fire});
        if(sim.guardEnemy().health<previous){
            compareLive(sim,off,on);
            ++live_impact;
        }
    }
    require(initial_hp==3 && sim.guardEnemy().health==0 &&
            sim.guardEnemy().projectile_hits==3 && live_impact==3,
            "did not observe three real projectile-driven guard impacts");
    compareLive(sim,off,on);
    ++live_defeat;

    // Walk to real second-wave trigger, then wait for actual turret fire.
    for(int i=0;i<400 && !sim.secondWaveActive();++i)
        sim.tick(Input{Right});
    require(sim.secondWaveActive() && sim.sentry().health==2,
            "guard defeat never unlocked authentic second wave");
    // The wave gate is farther from the turret than its 160px detection
    // range. Advance the real player towards the live threat rather than
    // inventing a projectile or waiting outside its awareness radius.
    for(int i=0;i<250;++i){
        sim.tick(Input{Right});
        bool active=false;
        for(const auto& projectile:sim.enemyProjectiles())
            if(projectile.active)active=true;
        if(active){
            compareLive(sim,off,on);
            ++live_hostile;
            break;
        }
    }
    require(live_hostile==1,
            "real source turret never launched an active hostile projectile");
    std::printf("VPD_HD_FX_LIVE_COMBAT_HOST_PASS "
                "guard_hits=%u guard_defeated=%u hostile_bullet=%u "
                "roi_pixels=414000 same_frame_gameplay_hash=yes "
                "manual_visual_difference=yes original_game_proven=no "
                "physical_switch_proven=no\n",
                live_impact,live_defeat,live_hostile);
}
}
int main(){
    try{verify();return 0;}
    catch(const std::exception& e){
        std::fprintf(stderr,"VPD_HD_FX_LIVE_COMBAT_HOST_FAIL %s\n",e.what());
        return 1;
    }
}
