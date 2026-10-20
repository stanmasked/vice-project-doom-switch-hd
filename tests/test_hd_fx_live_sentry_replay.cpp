// ROM-free, source-derived second-wave hostile bullet/HD input regression.
// Only real Simulation::tick spawns shots. No synthetic combat SceneView data.
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
void require(bool ok,const char* why){
    if(!ok)throw std::runtime_error(why);
}
bool solid(void* ctx,int x,int y){
    return static_cast<const vpd::Scene*>(ctx)->solid(x,y);
}
bool liveBullet(const vpd::Simulation& sim){
    for(const auto& p:sim.enemyProjectiles())
        if(p.active)return true;
    return false;
}
vpd::SceneView viewOf(const vpd::Simulation& sim,bool halo){
    using namespace vpd;
    const auto& player=sim.player();
    SceneView v{
        player.x/kFixed,player.y/kFixed,sim.cameraX(),
        sim.frame(),player.grounded,
        const_cast<Scene*>(&sim.scene()),solid
    };
    v.manual_controls=true;
    // Isolate the actual hostile-projectile halo: no haze, footstep dust,
    // hit lighting or HUD ON/OFF label can create this pixel difference.
    v.hd_hit_lighting=false;
    v.hd_atmospheric_haze=false;
    v.hd_footstep_dust=false;
    v.hd_hostile_projectile_halo=halo;
    v.hd_fx_status_visible=false;
    applyCombatOverlay(v,sim);
    return v;
}
bool haloDiff(const vpd::Simulation& sim,
              std::vector<uint32_t>& off,std::vector<uint32_t>& on){
    using namespace vpd;
    const uint64_t state=sim.fingerprint();
    const auto a=viewOf(sim,false);
    const auto b=viewOf(sim,true);
    require(drawScene(off.data(),kSceneWidth,kSceneHeight,kSceneWidth,a) &&
            drawScene(on.data(),kSceneWidth,kSceneHeight,kSceneWidth,b),
            "source-driven sentry halo raster failed");
    const auto x=fingerprintHdFxVisual(
        off.data(),kSceneWidth,kSceneHeight,kSceneWidth);
    const auto y=fingerprintHdFxVisual(
        on.data(),kSceneWidth,kSceneHeight,kSceneWidth);
    require(x.pixels==414000 && y.pixels==414000,
            "HUD-free scene pixel sample size changed");
    require(sim.fingerprint()==state,
            "sentry halo raster changed authoritative simulation");
    return x.hash!=y.hash;
}
void equalGameplay(const vpd::Simulation& a,const vpd::Simulation& b){
    require(a.fingerprint()==b.fingerprint(),
            "cosmetic L+R mode caused second-wave gameplay divergence");
}
void bothTick(vpd::Simulation& a,vpd::Simulation& b,vpd::Input input){
    a.tick(input);
    b.tick(input);
    equalGameplay(a,b);
}
void verify(){
    using namespace vpd;
    Simulation toggled{},baseline{};
    toggled.enableEnemyEncounter();
    baseline.enableEnemyEncounter();
    HdFxRuntimeMode fx{};
    std::vector<uint32_t> off(
        static_cast<std::size_t>(kSceneWidth)*kSceneHeight);
    std::vector<uint32_t> on(off.size());
    // The original authored guard takes exactly three swept shots.
    for(int i=0;i<180 && toggled.guardEnemy().health>0;++i)
        bothTick(toggled,baseline,Input{Fire});
    require(toggled.guardEnemy().health==0 &&
            toggled.guardEnemy().projectile_hits==3 &&
            toggled.playerHealth()>0,
            "real guard defeat missing before turret phase");
    require(!toggled.secondWaveActive() &&
            !liveBullet(toggled) &&
            !haloDiff(toggled,off,on),
            "HD hostile halo appeared before genuine enemy projectile");

    // Activate the original second-wave gate; step closer than the
    // 160-pixel sentry detection range, without fabricating a projectile.
    for(int i=0;i<400 && !toggled.secondWaveActive();++i)
        bothTick(toggled,baseline,Input{Right});
    require(toggled.secondWaveActive() && toggled.sentry().health==2,
            "authentic second-wave activation missing");
    for(int i=0;i<250 && !liveBullet(toggled);++i)
        bothTick(toggled,baseline,Input{Right});
    require(liveBullet(toggled) && toggled.sentry().shots_fired>0 &&
            toggled.playerHealth()>0 && !toggled.stageCleared(),
            "real sentry never fired an active hostile projectile");
    const uint32_t bullet_frame=toggled.frame();
    const uint8_t initial_health=toggled.playerHealth();
    // First actual edge: HD effects are switched off while a projectile
    // remains active. The isolated halo changes only scene pixels.
    require(fx.acceptShoulders(true,true,true,true,true) && !fx.enabled,
            "first live turret-combat L+R edge must disable effects");
    require(haloDiff(toggled,off,on),
            "real hostile bullet yielded no isolated HD halo difference");
    for(int i=0;i<5;++i){
        require(fx.acceptShoulders(true,true,true,false,false) &&
                !fx.enabled,
                "held L+R re-toggled mode during active hostile projectile");
        bothTick(toggled,baseline,Input{});
    }
    require(liveBullet(toggled) && toggled.playerHealth()==initial_health,
            "hostile bullet vanished or collided before second L+R edge");
    require(!fx.acceptShoulders(true,false,false,false,false),
            "releasing shoulders changed cosmetic mode");
    require(fx.acceptShoulders(true,true,true,true,true) && fx.enabled,
            "second live turret-combat L+R edge must restore effects");
    require(haloDiff(toggled,off,on),
            "real hostile bullet halo disappeared after re-enabling HD");
    equalGameplay(toggled,baseline);

    // Actual enemy projectile collision must remain authoritative after
    // cosmetic toggles; this is not a synthetic health subtraction.
    bool hit=false;
    for(int i=0;i<100 && toggled.playerHealth()>0;++i){
        bothTick(toggled,baseline,Input{});
        if(toggled.playerHealth()<initial_health){
            hit=true;
            break;
        }
    }
    require(hit && toggled.sentry().shots_hit>0 &&
            toggled.playerHealth()==baseline.playerHealth() &&
            toggled.sentry().health==2 &&
            !toggled.stageCleared(),
            "real hostile projectile hit diverged after cosmetic toggles");
    std::printf("VPD_HD_FX_LIVE_SENTRY_REPLAY_HOST_PASS "
                "enemy_bullet_frame=%u combat_edges=2 "
                "hostile_projectile_spawns=yes hostile_projectile_hit=yes "
                "hero_health_equal=yes sentry_health=2 "
                "isolated_halo_pixels_change=yes roi_pixels=414000 "
                "simulation_equal_every_tick=yes "
                "original_game_proven=no physical_switch_proven=no\n",
                bullet_frame);
}
}
int main(){
    try{verify();return 0;}
    catch(const std::exception& e){
        std::fprintf(stderr,
                     "VPD_HD_FX_LIVE_SENTRY_REPLAY_HOST_FAIL %s\n",e.what());
        return 1;
    }
}
