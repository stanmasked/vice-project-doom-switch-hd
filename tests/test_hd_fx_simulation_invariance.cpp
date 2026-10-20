// Independent ROM-free HD setting versus gameplay-state replay invariance.
// Runs the same combat input stream against two *real* simulation instances;
// effects may change pixels, never actor, projectile, health, AI or replay hash.
#include "simulation.hpp"
#include "manual_retry.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include "hd_fx_toggle.hpp"
#include "hd_fx_guest_proof.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void require(bool value,const char* message){
    if(!value)throw std::runtime_error(message);
}
bool solidAt(void* context,int x,int y){
    return static_cast<const vpd::Scene*>(context)->solid(x,y);
}
vpd::SceneView viewOf(const vpd::Simulation& game,bool enabled,bool manual){
    const auto& actor=game.player();
    vpd::SceneView view{
        actor.x/vpd::kFixed,actor.y/vpd::kFixed,game.cameraX(),
        game.frame(),actor.grounded,
        const_cast<vpd::Scene*>(&game.scene()),solidAt
    };
    view.moving=actor.vx!=0;
    view.manual_controls=manual;
    view.hd_hit_lighting=manual && enabled;
    view.hd_atmospheric_haze=manual && enabled;
    view.hd_footstep_dust=manual && enabled;
    view.hd_hostile_projectile_halo=manual && enabled;
    view.hd_fx_status_visible=manual;
    view.hd_fx_status_enabled=enabled;
    vpd::applyCombatOverlay(view,game);
    return view;
}
vpd::Input gameplayInput(int frame){
    // Authored combat and movement. This is not an NES trace.
    uint8_t bits=0;
    if(frame<45 || frame>=80)bits|=vpd::Right;
    if((frame>=30 && frame<170) || (frame>=185 && frame<330))
        bits|=vpd::Fire;
    if(frame>=56 && frame<59)bits|=vpd::Jump;
    if(frame>=108 && frame<114)bits|=vpd::Dash;
    return vpd::Input{bits};
}
void takeSnapshot(const vpd::Simulation& reference,
                  const vpd::Simulation& variant,
                  bool fx_enabled,
                  std::vector<uint32_t>& a,std::vector<uint32_t>& b,
                  unsigned& changed,unsigned& identical){
    using namespace vpd;
    const uint64_t before_a=reference.fingerprint();
    const uint64_t before_b=variant.fingerprint();
    require(before_a==before_b,"states differed before raster comparison");
    const auto va=viewOf(reference,true,true);
    const auto vb=viewOf(variant,fx_enabled,true);
    require(drawScene(a.data(),kSceneWidth,kSceneHeight,kSceneWidth,va),
            "reference render failed");
    require(drawScene(b.data(),kSceneWidth,kSceneHeight,kSceneWidth,vb),
            "toggle render failed");
    const auto ha=fingerprintHdFxVisual(
        a.data(),kSceneWidth,kSceneHeight,kSceneWidth);
    const auto hb=fingerprintHdFxVisual(
        b.data(),kSceneWidth,kSceneHeight,kSceneWidth);
    require(ha.pixels==414000 && hb.pixels==414000,
            "invalid guest-compatible HUD-free ROI");
    if(fx_enabled){
        require(ha.hash==hb.hash,
                "identical HD states rendered different scene pixels");
        ++identical;
    }else{
        require(ha.hash!=hb.hash,
                "disabled HD effects did not change scene pixels");
        ++changed;
    }
    require(reference.fingerprint()==before_a &&
            variant.fingerprint()==before_b,
            "render-only HD effects mutated authoritative game state");
}
void runCombatReplay(){
    using namespace vpd;
    Simulation reference{},variant{};
    reference.enableEnemyEncounter();
    variant.enableEnemyEncounter();
    HdFxRuntimeMode fx{};
    std::vector<uint32_t> reference_pixels(
        static_cast<std::size_t>(kSceneWidth)*kSceneHeight,0);
    std::vector<uint32_t> variant_pixels(reference_pixels.size(),0);
    unsigned changed=0,identical=0;
    constexpr int kFrames=350;
    for(int frame=0;frame<kFrames;++frame){
        // Each input pattern is applied to the exact same scene sources.
        if(frame==12 || frame==92 || frame==180 || frame==270)
            require(fx.acceptShoulders(true,true,true,true,true),
                    "real shoulder chord must be consumed by visual mode");
        if(frame==13 || frame==93 || frame==181 || frame==271)
            require(!fx.acceptShoulders(true,false,false,false,false),
                    "chord release consumed unrelated input");
        const Input input=gameplayInput(frame);
        reference.tick(input);
        variant.tick(input);
        require(reference.fingerprint()==variant.fingerprint(),
                "HD mode changed deterministic simulation state");
        // Exercise both states on scene snapshots, including after a
        // damage/death/terminal state if reached during this run.
        if(frame==12 || frame==52 || frame==92 || frame==140 ||
           frame==180 || frame==230 || frame==270 || frame==340)
            takeSnapshot(reference,variant,fx.enabled,
                         reference_pixels,variant_pixels,changed,identical);
    }
    require(changed==4 && identical==4,
            "wrong number of HD-on/off scene snapshots");
    require(reference.fingerprint()==variant.fingerprint(),
            "combat state diverged after full replay");

    // Renderer and autoplay never write to HD mode. A transition out of
    // manual gameplay disables HD effects without forgetting player choice.
    require(fx.acceptShoulders(true,true,true,true,true) && !fx.enabled,
            "pre-retry HD mode OFF was not selected");
    const auto manual_selected=fx.enabled;
    require(!fx.acceptShoulders(false,true,true,true,true) &&
            fx.enabled==manual_selected &&
            !fx.activeForGameplay(false),
            "autoplay must ignore shoulder chords and visual setting");
    auto auto_on=viewOf(reference,true,false);
    auto auto_off=viewOf(variant,false,false);
    require(drawScene(reference_pixels.data(),kSceneWidth,kSceneHeight,
                      kSceneWidth,auto_on) &&
            drawScene(variant_pixels.data(),kSceneWidth,kSceneHeight,
                      kSceneWidth,auto_off),
            "autoplay render failed");
    require(fingerprintHdFxVisual(reference_pixels.data(),
                                 kSceneWidth,kSceneHeight,kSceneWidth).hash==
            fingerprintHdFxVisual(variant_pixels.data(),
                                 kSceneWidth,kSceneHeight,kSceneWidth).hash,
            "HD visuals leaked into existing autoplay");
    require(!fx.enabled && !fx.activeForGameplay(true),
            "manual choice not retained across attract-mode transition");

    // Defeat and manual Minus retry must reinitialize gameplay only:
    // visual preference belongs to the frontend, not Simulation.
    Simulation a{},b{};
    a.enableEnemyEncounter();
    b.enableEnemyEncounter();
    bool defeated=false;
    // Match the proven native guard-defeat scenario: approach until the
    // first actual melee attack, then stop and receive subsequent blows.
    // Holding Right forever escapes the guard and cannot cause defeat.
    bool first_contact=false;
    for(int frame=0;frame<500;++frame){
        const Input actual=first_contact?Input{}:Input{Right};
        a.tick(actual);b.tick(actual);
        require(a.fingerprint()==b.fingerprint(),
                "defeat replay diverged with HD preference disabled");
        if(a.guardEnemy().attacks>0)first_contact=true;
        if(a.playerHealth()==0){
            defeated=true;
            break;
        }
    }
    require(first_contact,"synthetic guard never reached real melee contact");
    require(defeated,"synthetic guard contact did not reach defeat");
    require(retryTerminalEncounter(a,true)==ManualRetryOutcome::AfterDefeat &&
            retryTerminalEncounter(b,true)==ManualRetryOutcome::AfterDefeat,
            "explicit Minus retry from defeat rejected");
    require(a.fingerprint()==b.fingerprint() &&
            a.frame()==0 && a.playerHealth()==5 &&
            a.guardEnemy().health==3 &&
            !fx.enabled,
            "retry reset gameplay but incorrectly reset HD visual preference");
    a.tick(Input{Right});b.tick(Input{Right});
    require(a.fingerprint()==b.fingerprint(),
            "HD preference affected first post-retry movement");
    std::puts("VPD_HD_FX_GAMEPLAY_INVARIANCE_PASS "
              "combat_frames=350 scene_samples=8 "
              "off_samples=4 on_samples=4 "
              "simulation_hash_equal_every_tick=yes "
              "render_does_not_mutate_state=yes "
              "autoplay_unchanged=yes preference_retained_across_retry=yes "
              "physical_switch_proven=no original_game_proven=no");
}
} // namespace

int main(){
    try{
        runCombatReplay();
        return 0;
    }catch(const std::exception& error){
        std::fprintf(stderr,"VPD_HD_FX_GAMEPLAY_INVARIANCE_FAIL %s\n",
                     error.what());
        return 1;
    }
}
