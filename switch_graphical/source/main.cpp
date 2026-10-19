// Independent libnx native raster scene; no NES emulator or proprietary art.
#include <switch.h>
#include "simulation.hpp"
#include "combat_demo.hpp"
#include "demo_witness_sd.hpp"
#include "manual_input_witness.hpp"
#include "dash_guest_witness.hpp"
#include "guard_guest_witness.hpp"
#include "guard_combat_probe.hpp"
#include "second_wave_guest_probe.hpp"
#include "guard_live_debug.hpp"
#include "guard_live_witness.hpp"
#include "guard_live_defeat_witness.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include "asset_atlas.hpp"
#include "asset_bundle.hpp"
#include "animation.hpp"
#include "demo_animation.hpp"
#include "demo_atlas.hpp"
#include "demo_terrain.hpp"
#include "terrain_source.hpp"
#include "backdrop_source.hpp"
#include "demo_backdrop.hpp"
#include "decor_source.hpp"
#include "demo_decor.hpp"
#include "decor_layout.hpp"
#include "demo_decor_layout.hpp"
#include <cstdint>
namespace {
bool solidAt(void* context,int x,int y) {
    return static_cast<const vpd::Scene*>(context)->solid(x,y);
}
}
int main(int,char**) {
    padConfigureInput(1,HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    Framebuffer fb{};
    Result rc=framebufferCreate(&fb,nwindowGetDefault(),vpd::kSceneWidth,
                                vpd::kSceneHeight,PIXEL_FORMAT_RGBA_8888,2);
    if(R_FAILED(rc))return 2;
    rc=framebufferMakeLinear(&fb);
    if(R_FAILED(rc)){framebufferClose(&fb);return 3;}
    // Optional development asset. Missing or damaged SD data never blocks launch.
    constexpr const char* kExternalAtlasPath=
        "sdmc:/switch/vice_project_doom/hero.vpat";
    constexpr const char* kExternalAnimationPath=
        "sdmc:/switch/vice_project_doom/hero.vanm";
    vpd::AssetBundle assets;
    if(!assets.initialize(vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes,
                          vpd_demo::kAnimationBank)) {
        framebufferClose(&fb);return 4;
    }
    const Result sd_mount=fsdevMountSdmc();
    const bool we_mounted_sd=R_SUCCEEDED(sd_mount);
    const bool has_sd=we_mounted_sd || fsdevGetDeviceFileSystem("sdmc")!=nullptr;
    // New run, not leftover emulator/SD evidence from a previous NRO.
    (void)vpd::manualProofReset(has_sd);
    (void)vpd::dashGuestProofReset(has_sd);
    (void)vpd::guardProofReset(has_sd);
    (void)vpd::guardCombatProofReset(has_sd);
    (void)vpd::resetSentryProof(has_sd);
    vpd::guardLiveDebugReset(has_sd);
    (void)vpd::liveGuardProofReset(has_sd);
    (void)vpd::liveGuardDefeatReset(has_sd);
    if(has_sd)assets.reload(kExternalAtlasPath,kExternalAnimationPath);
    bool reload_failed=false;
    constexpr const char* kExternalTerrainPath=
        "sdmc:/switch/vice_project_doom/terrain.vpat";
    vpd::TerrainSource terrain;
    if(!terrain.initialize(vpd_terrain::kAtlasBlob,vpd_terrain::kAtlasBytes)) {
        framebufferClose(&fb);
        if(we_mounted_sd)fsdevUnmountDevice("sdmc");
        return 5;
    }
    if(has_sd)terrain.reload(kExternalTerrainPath);
    bool terrain_reload_failed=false;
    constexpr const char* kExternalBackdropPath=
        "sdmc:/switch/vice_project_doom/backdrop.vpat";
    vpd::BackdropSource backdrop;
    if(!backdrop.initialize(vpd_backdrop::kAtlasBlob,
                            vpd_backdrop::kAtlasBytes)) {
        framebufferClose(&fb);
        if(we_mounted_sd)fsdevUnmountDevice("sdmc");
        return 6;
    }
    if(has_sd)backdrop.reload(kExternalBackdropPath);
    bool backdrop_reload_failed=false;
    constexpr const char* kExternalDecorPath=
        "sdmc:/switch/vice_project_doom/decor.vpat";
    vpd::DecorSource decor;
    if(!decor.initialize(vpd_decor::kAtlasBlob,vpd_decor::kAtlasBytes)) {
        framebufferClose(&fb);
        if(we_mounted_sd)fsdevUnmountDevice("sdmc");
        return 7;
    }
    if(has_sd)decor.reload(kExternalDecorPath);
    bool decor_reload_failed=false;
    constexpr const char* kExternalDecorLayoutPath=
        "sdmc:/switch/vice_project_doom/decor_layout.vlay";
    vpd::DecorLayoutSource layout;
    if(!layout.initialize(vpd_layout::kLayout)){
        framebufferClose(&fb);
        if(we_mounted_sd)fsdevUnmountDevice("sdmc");
        return 8;
    }
    if(has_sd)layout.reload(kExternalDecorLayoutPath);
    bool decor_layout_reload_failed=false;
    vpd::AnimationPlayer animation;
    vpd::Simulation game;
    vpd::CombatDemo demo; // auto-starts for reproducible emulator smoke tests
    unsigned witness_cycles=0; // hard cap: four records per launch
    bool checkpoint_ok=false;
    unsigned manual_seq=0;
    bool plus_seen=false;
    bool dash_probe_started=false;
    bool dash_probe_finished=false;
    bool live_guard_alert_logged=false;
    bool live_guard_strike_logged=false;
    bool live_guard_fire_logged=false;
    bool live_guard_defeated=false;
    unsigned live_guard_defeat_seq=0;
    uint32_t dash_probe_start_frame=0;
    int32_t dash_probe_start_x=0;
    while(appletMainLoop()){
        padUpdate(&pad);
        const u64 buttons=padGetButtons(&pad);
        const u64 pressed=padGetButtonsDown(&pad);
        if(buttons&HidNpadButton_Plus){
            if(!demo.enabled())vpd::guardLiveDebugRecord(
                has_sd,"plus",game,0);
            // Must have completed the actual ordered manual control probe.
            if(!demo.enabled() && manual_seq==5){
                (void)vpd::manualProofAppend(has_sd,vpd::ManualProofEvent::Plus,
                                             6,game,1);
                manual_seq=6;
                plus_seen=true;
            }
            break;
        }
        // Left-stick click switches between 200-frame demo and manual play.
        // StickL+Y still performs the independent development-art reset.
        const bool toggle_manual=
            ((pressed&HidNpadButton_StickL) && !(buttons&HidNpadButton_Y)) ||
            ((pressed&HidNpadButton_A) && (buttons&HidNpadButton_R));
        if(toggle_manual) {
            demo.toggle(game);
            animation.reset();
            checkpoint_ok=false;
            dash_probe_started=false;
            dash_probe_finished=false;
            live_guard_alert_logged=false;
            live_guard_strike_logged=false;
            live_guard_fire_logged=false;
            live_guard_defeated=false;
            live_guard_defeat_seq=0;
            if(!demo.enabled()){
                // Preserve ROM-free autoplay hashes: enable encounter only on
                // entry into explicit manual gameplay, never in attract mode.
                game.enableEnemyEncounter();
                manual_seq=1;
                (void)vpd::manualProofAppend(has_sd,vpd::ManualProofEvent::Enter,
                                             1,game,1);
            } else manual_seq=0;
        }
        if(pressed&HidNpadButton_X) {
            const vpd::BundleReload result=has_sd ?
                assets.reload(kExternalAtlasPath,kExternalAnimationPath) :
                vpd::BundleReload::MissingAtlas;
            reload_failed=result!=vpd::BundleReload::LoadedPair &&
                          result!=vpd::BundleReload::LoadedAtlasOnly;
            if(!reload_failed)animation.reset(); // clip counts/ticks may change
        }
        // Y is now Fire; hold left-stick click + Y for developer reset.
        if((pressed&HidNpadButton_Y) && (buttons&HidNpadButton_StickL)) {
            assets.reset();
            animation.reset();
            reload_failed=false;
        }
        if(pressed&HidNpadButton_ZL) {
            terrain_reload_failed= !has_sd ||
                terrain.reload(kExternalTerrainPath)!=vpd::TerrainReload::Loaded;
        }
        // ZR now dashes in manual play. StickL+ZR retains the developer
        // terrain reset; autoplay still supports the original ZR reset.
        if((pressed&HidNpadButton_ZR) &&
           (demo.enabled() || (buttons&HidNpadButton_StickL))) {
            terrain.reset();
            terrain_reload_failed=false;
        }
        if(pressed&HidNpadButton_L) {
            backdrop_reload_failed= !has_sd ||
                backdrop.reload(kExternalBackdropPath)!=vpd::BackdropReload::Loaded;
        }
        if(pressed&HidNpadButton_R) {
            backdrop.reset();
            backdrop_reload_failed=false;
        }
        if(pressed&HidNpadButton_Up) {
            decor_reload_failed= !has_sd ||
                decor.reload(kExternalDecorPath)!=vpd::DecorReload::Loaded;
        }
        if(pressed&HidNpadButton_Down) {
            decor.reset();
            decor_reload_failed=false;
        }
        if(pressed&HidNpadButton_Minus){
            decor_layout_reload_failed= !has_sd ||
                layout.reload(kExternalDecorLayoutPath)!=vpd::LayoutLoadResult::Loaded;
        }
        if(pressed&HidNpadButton_StickR){
            layout.reset();
            decor_layout_reload_failed=false;
        }
        uint8_t input=0;
        if(buttons&(HidNpadButton_Left|HidNpadButton_StickLLeft))input|=vpd::Left;
        if(buttons&(HidNpadButton_Right|HidNpadButton_StickLRight))input|=vpd::Right;
        if(buttons&(HidNpadButton_A|HidNpadButton_B))input|=vpd::Jump;
        if((buttons&HidNpadButton_Y) && !(buttons&HidNpadButton_StickL))
            input|=vpd::Fire;
        if(!demo.enabled() && (buttons&HidNpadButton_ZR) &&
           !(buttons&HidNpadButton_StickL))
            input|=vpd::Dash;
        if(demo.enabled()) {
            if(demo.tick(game)) animation.reset();
        } else {
            // Measure actual simulation effects, not merely keyboard events.
            const auto before_x=game.player().x;
            const auto before_shots=game.shotsFired();
            const auto was_alerted=game.guardEnemy().alerted;
            const auto prior_hp=game.playerHealth();
            const auto prior_attacks=game.guardEnemy().attacks;
            const auto prior_guard_hp=game.guardEnemy().health;
            const auto prior_guard_hits=game.guardEnemy().projectile_hits;
            if(toggle_manual)input=0; // R+A is a mode switch, not a jump
            game.tick(vpd::Input{input});
            // These events are from the *visible*, pad-driven gameplay
            // instance, unlike the isolated guard-combat script. A host
            // keystroke by itself cannot satisfy the observed transitions.
            if(!was_alerted && game.guardEnemy().alerted)
                vpd::guardLiveDebugRecord(has_sd,"alert_transition",game,input);
            if(!live_guard_alert_logged && !was_alerted &&
               game.guardEnemy().alerted &&
               (input&vpd::Right) && prior_hp==5)
                live_guard_alert_logged=vpd::liveGuardProofAppend(
                    has_sd,vpd::LiveGuardEvent::Alert,game,input);
            if(live_guard_alert_logged && !live_guard_strike_logged &&
               (input&vpd::Right) && prior_hp==5 &&
               game.playerHealth()==4 && prior_attacks==0 &&
               game.guardEnemy().attacks==1)
                live_guard_strike_logged=vpd::liveGuardProofAppend(
                    has_sd,vpd::LiveGuardEvent::FirstStrike,game,input);
            // A separate attestation of the real player-controlled Fire
            // sequence after the first melee strike. Only count actual
            // swept collision changes in this same rendered simulation.
            if(live_guard_strike_logged && !live_guard_fire_logged &&
               (input&vpd::Fire) && game.shotsFired()>before_shots &&
               game.guardEnemy().health>0){
                live_guard_fire_logged=vpd::liveGuardDefeatAppend(
                    has_sd,vpd::LiveGuardDefeatEvent::Fire,1,game,input,
                    prior_guard_hp,prior_guard_hits,before_shots);
                if(live_guard_fire_logged)live_guard_defeat_seq=1;
            }
            if(live_guard_fire_logged && !live_guard_defeated &&
               game.guardEnemy().projectile_hits==prior_guard_hits+1 &&
               game.guardEnemy().health+1==prior_guard_hp &&
               live_guard_defeat_seq<4){
                const unsigned next_seq=live_guard_defeat_seq+1;
                if(vpd::liveGuardDefeatAppend(
                    has_sd,vpd::LiveGuardDefeatEvent::Impact,
                    next_seq,game,input,prior_guard_hp,prior_guard_hits,
                    before_shots)){
                    live_guard_defeat_seq=next_seq;
                    if(game.guardEnemy().health==0)live_guard_defeated=true;
                }
            }
            // Two guest-written milestones require a real first and
            // eighth tick from the opt-in enemy AI, not a host fixture.
            if(game.frame()==1)
                (void)vpd::guardProofAppend(
                    has_sd,vpd::GuardProofEvent::FirstStep,game);
            if(game.frame()==8){
                (void)vpd::guardProofAppend(
                    has_sd,vpd::GuardProofEvent::Patrol,game);
                // Separate scripted guard combat test executed by this very
                // guest NRO. Does not modify the visible/manual simulation.
                (void)vpd::persistGuardCombatProof(has_sd);
                // Native-only scripted wave-two test; never mutates the
                // manual encounter or inherited guest-input witness.
                (void)vpd::persistSentryProof(has_sd);
            }
            // Independent dash proof: record only after the live Switch
            // gameplay core has consumed ZR + Right and moved six pixels.
            if(manual_seq==5 && !dash_probe_started &&
               (input&(vpd::Dash|vpd::Right))==(vpd::Dash|vpd::Right) &&
               game.player().x-before_x==6*vpd::kFixed &&
               game.dashing() && game.dashCooldown()==45){
                dash_probe_started=vpd::dashGuestProofAppend(
                    has_sd,vpd::DashGuestEvent::Start,game,
                    game.player().x-before_x);
                if(dash_probe_started){
                    dash_probe_start_frame=game.frame();
                    dash_probe_start_x=before_x;
                }
            }
            if(dash_probe_started && !dash_probe_finished &&
               game.frame()==dash_probe_start_frame+5 &&
               !game.dashing() && game.dashCooldown()==40 &&
               game.player().x-dash_probe_start_x==36*vpd::kFixed){
                dash_probe_finished=vpd::dashGuestProofAppend(
                    has_sd,vpd::DashGuestEvent::Complete,game,
                    game.player().x-dash_probe_start_x);
            }
            vpd::ManualProofEvent event=vpd::ManualProofEvent::Enter;
            int32_t metric=0;
            if(manual_seq==1 && (input&vpd::Right) &&
               game.player().x>before_x){
                event=vpd::ManualProofEvent::Right;
                metric=game.player().x-before_x;
            } else if(manual_seq==2 && (input&vpd::Fire) &&
                      game.shotsFired()>before_shots){
                event=vpd::ManualProofEvent::Fire;
                metric=static_cast<int32_t>(game.shotsFired()-before_shots);
            } else if(manual_seq==3 && (input&vpd::Jump) &&
                      game.player().vy<0){
                event=vpd::ManualProofEvent::Jump;
                metric=-game.player().vy;
            } else if(manual_seq==4 && (input&vpd::Left) &&
                      game.player().x<before_x){
                event=vpd::ManualProofEvent::Left;
                metric=before_x-game.player().x;
            }
            if(metric>0){
                ++manual_seq;
                (void)vpd::manualProofAppend(has_sd,event,manual_seq,game,metric);
            }
        }
        u32 stride=0;
        auto* pixels=static_cast<uint32_t*>(framebufferBegin(&fb,&stride));
        const auto& actor=game.player();
        vpd::SceneView view{
            actor.x/vpd::kFixed,actor.y/vpd::kFixed,game.cameraX(),
            game.frame(),actor.grounded,
            const_cast<vpd::Scene*>(&game.scene()),solidAt
        };
        view.sprite_atlas=&assets.atlas();
        view.external_sprite_asset=assets.externalAtlas();
        view.external_animation_source=assets.externalAnimation();
        view.asset_reload_failed=reload_failed;
        view.moving=actor.vx!=0;
        view.replay_demo=demo.enabled();
        view.manual_controls=!demo.enabled();
        view.demo_checkpoint_ok=checkpoint_ok && demo.enabled();
        // Same adapter is exercised by native host combat/raster CTest.
        vpd::applyCombatOverlay(view,game);
        if(!animation.tick(assets.animation(),
                vpd::MotionSample{actor.grounded,actor.vx!=0,actor.vy,actor.vx}))break;
        view.sprite_frame=animation.frame(assets.animation());
        view.facing_left=animation.facingLeft();
        view.terrain_atlas=&terrain.atlas();
        view.external_terrain_asset=terrain.external();
        view.terrain_reload_failed=terrain_reload_failed;
        view.backdrop_atlas=&backdrop.atlas();
        view.external_backdrop_asset=backdrop.external();
        view.backdrop_reload_failed=backdrop_reload_failed;
        view.decor_atlas=&decor.atlas();
        view.external_decor_asset=decor.external();
        view.decor_reload_failed=decor_reload_failed;
        view.decor_layout=layout.layout();
        view.external_decor_layout=layout.external();
        view.decor_layout_reload_failed=decor_layout_reload_failed;
        const bool drawn=vpd::drawScene(pixels,vpd::kSceneWidth,
                vpd::kSceneHeight,static_cast<int>(stride/sizeof(uint32_t)),view);
        framebufferEnd(&fb);
        if(!drawn)break;
        // The checkpoint is written only after a successful framebuffer
        // submission, not merely because a host test compiled this binary.
        if(vpd::demoCheckpointReached(demo,game)){
            checkpoint_ok=vpd::demoCheckpointMatches(game);
            if(witness_cycles<vpd::kDemoWitnessMaxRecords){
                ++witness_cycles;
                (void)vpd::persistDemoWitness(game,witness_cycles,has_sd);
            }
        }
        // Diagnostic pacing only, actual Switch frame timing unmeasured.
        svcSleepThread(16666667);
    }
    framebufferClose(&fb);
    if(plus_seen && manual_seq==6){
        (void)vpd::manualProofAppend(has_sd,vpd::ManualProofEvent::Exit,
                                     7,game,1);
    }
    if(we_mounted_sd)fsdevUnmountDevice("sdmc");
    return 0;
}
