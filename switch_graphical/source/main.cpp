// Independent libnx native raster scene; no NES emulator or proprietary art.
#include <switch.h>
#include "simulation.hpp"
#include "driving_simulation.hpp"
#include "driving_scene_bridge.hpp"
#include "driving_profile_review_mode.hpp"
#include "driving_road_private_bundle.hpp"
#include "driving_private_review_mode.hpp"
#include "driving_private_road_sd_witness.hpp"
#include "driving_private_road_r3_witness.hpp"
#include "driving_private_road_reject_witness.hpp"
#include "driving_road_review_witness.hpp"
#include "driving_guest_witness.hpp"
#include "driving_raster_witness.hpp"
#include "driving_route_witness.hpp"
#include "driving_stage_exit.hpp"
#include "driving_stage_one_config.hpp"
#include "driving_exit_witness.hpp"
#include "driving_transition_black.hpp"
#include "manual_retry.hpp"
#include "manual_retry_guest_witness.hpp"
#include "live_defeat_retry_witness.hpp"
#include "post_defeat_control_witness.hpp"
#include "post_defeat_fire_witness.hpp"
#include "third_guard_clear_witness.hpp"
#include "third_stage_witness.hpp"
#include "fourth_retry_witness.hpp"
#include "hd_footstep_witness.hpp"
#include "hd_hostile_halo_witness.hpp"
#include "fourth_combat_witness.hpp"
#include "hd_hit_light_witness.hpp"
#include "fourth_guard_clear_witness.hpp"
#include "fourth_stage_witness.hpp"
#include "combat_demo.hpp"
#include "demo_witness_sd.hpp"
#include "manual_input_witness.hpp"
#include "dash_guest_witness.hpp"
#include "guard_guest_witness.hpp"
#include "guard_combat_probe.hpp"
#include "second_wave_guest_probe.hpp"
#include "guard_live_debug.hpp"
#include "second_wave_live_witness.hpp"
#include "guard_live_witness.hpp"
#include "guard_live_defeat_witness.hpp"
#include "scene_renderer.hpp"
#include "hd_fx_toggle.hpp"
#include "hd_fx_guest_proof.hpp"
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
#include <cstdio>
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
    vpd::private_road::PrivateRoadBundle private_road_data{};
    if(has_sd)(void)private_road_data.loadFile(
        "sdmc:/switch/vice_project_doom/road_numeric.vprd");
    (void)vpd::writeRoadSdStartup(has_sd,private_road_data);
    // New run, not leftover emulator/SD evidence from a previous NRO.
    (void)vpd::manualProofReset(has_sd);
    (void)vpd::dashGuestProofReset(has_sd);
    vpd::resetDrivingGuestProof(has_sd);
    vpd::resetDrivingRasterProof(has_sd);
    vpd::resetRoadReviewGuest(has_sd);
    vpd::resetPrivateRoadR3Guest(has_sd);
    vpd::resetPrivateRoadRejectGuest(has_sd);
    vpd::resetDrivingExitWitness(has_sd);
    (void)vpd::guardProofReset(has_sd);
    (void)vpd::guardCombatProofReset(has_sd);
    (void)vpd::resetSentryProof(has_sd);
    vpd::guardLiveDebugReset(has_sd);
    (void)vpd::liveGuardProofReset(has_sd);
    (void)vpd::liveGuardDefeatReset(has_sd);
    (void)vpd::liveWaveReset(has_sd);
    vpd::resetManualRetryGuest(has_sd);
    vpd::resetLiveDefeatRetry(has_sd);
    vpd::resetPostDefeatControl(has_sd);
    vpd::resetPostDefeatFire(has_sd);
    // Forensics only: never counted as control/exit PASS evidence.
    if(has_sd){
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/wave_exit_progress.txt","w"))
            std::fclose(report);
    }
    vpd::resetThirdGuardClear(has_sd);
    vpd::resetThirdStage(has_sd);
    vpd::resetFourthRetry(has_sd);
    vpd::resetFootstepProof(has_sd);
    vpd::resetHostileHaloWitness(has_sd);
    vpd::resetFourthCombat(has_sd);
    vpd::resetHitLightEvidence(has_sd);
    vpd::resetFourthGuardClear(has_sd);
    vpd::resetFourthStage(has_sd);
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
    uint32_t manual_session_ticks=0;
    bool plus_seen=false;
    bool dash_probe_started=false;
    bool dash_probe_finished=false;
    bool live_guard_alert_logged=false;
    bool live_guard_strike_logged=false;
    bool live_guard_fire_logged=false;
    bool live_guard_defeated=false;
    unsigned live_guard_defeat_seq=0;
    unsigned live_wave_seq=0;
    bool manual_retry_has_occurred=false;
    bool retry_native_logged=false;
    bool replay_guard_contact_logged=false;
    bool hd_low_hp_logged=false;
    bool hd_low_hp_phase_logged=false;
    uint32_t hd_low_hp_third_frame=0;
    uint32_t hd_low_hp_first_contact_frame=0;
    bool replay_guard_death_logged=false;
    bool replay_guard_restart_logged=false;
    bool third_run_move_logged=false;
    bool third_run_fire_logged=false;
    bool third_run_hit_logged=false;
    bool third_guard_clear_logged=false;
    unsigned third_stage_seq=0;
    bool fourth_restart_logged=false;
    bool fourth_move_logged=false;
    bool native_hd_dust_logged=false;
    bool native_hostile_halo_logged=false;
    vpd::HdFxRuntimeMode hd_fx_mode{};
    bool driving_preview=false; // manual-only ROM-free road/HUD visual preview
    vpd::DrivingState driving_state{}; // separate from platform Simulation
    vpd::RoadProfileReviewMode road_profile_review{};
    vpd::PrivateRoadReviewMode private_road_review{};
    vpd::RoadReviewGuestProof road_review_guest_proof{};
    vpd::PrivateRoadR3GuestProof private_road_r3_proof{};
    vpd::PrivateRoadRejectProof private_road_reject_proof{};
    vpd::DrivingGuestProof driving_proof{};
    vpd::DrivingStageExit driving_stage_exit{};
    vpd::DrivingExitProof driving_exit_proof{};
    vpd::DrivingRouteProof driving_route_proof{};
    unsigned hd_fx_guest_seq=0;
    unsigned hd_fx_combat_seq=0;
    unsigned hd_fx_sentry_seq=0;
    bool hd_fx_sentry_hit_logged=false;
    bool hd_fx_sentry_recovered_logged=false;
    uint32_t hd_fx_sentry_hit_frame=0;
    int32_t hd_fx_sentry_hit_x=0,hd_fx_sentry_hit_y=0;
    int hd_fx_sentry_tracked_slot=-1;
    uint32_t hd_fx_sentry_on_frame=0;
    int32_t hd_fx_sentry_on_x=0,hd_fx_sentry_on_y=0;
    uint16_t hd_fx_sentry_on_age=0;
    uint8_t hd_fx_sentry_on_hero_hp=0;
    uint16_t hd_fx_sentry_on_hits=0;
    if(has_sd){
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_fx_toggle_guest.txt","w"))
            std::fclose(report);
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_fx_combat_guest.txt","w"))
            std::fclose(report);
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_fx_sentry_guest.txt","w"))
            std::fclose(report);
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_fx_sentry_hit_guest.txt","w"))
            std::fclose(report);
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_fx_sentry_recover_guest.txt","w"))
            std::fclose(report);
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_low_health_guest.txt","w"))
            std::fclose(report);
        if(auto* report=std::fopen(
            "sdmc:/switch/vice_project_doom/hd_low_health_phase_guest.txt","w"))
            std::fclose(report);
    }
    bool fourth_fire_logged=false;
    bool fourth_hit_logged=false;
    bool native_hd_hit_logged=false;
    bool fourth_guard_clear_logged=false;
    unsigned fourth_stage_seq=0;
    uint32_t dash_probe_start_frame=0;
    int32_t dash_probe_start_x=0;
    while(appletMainLoop()){
        padUpdate(&pad);
        const u64 buttons=padGetButtons(&pad);
        const u64 pressed=padGetButtonsDown(&pad);
        // Exactly one timeline presentation per native loop. The exit request
        // is intentionally armed only *after* the last drawn road frame.
        const auto driving_present=driving_stage_exit.present();
        if(driving_present==vpd::stage_transition::Scene::Platform &&
           driving_preview) {
            driving_preview=false;
            driving_stage_exit.reset();
        }
        unsigned driving_raster_event_seq=0;
        // Deliberately uncommon debug chord preserves all approved autoplay.
        const bool driving_preview_chord=!demo.enabled() &&
            !driving_stage_exit.active() &&
            (pressed&HidNpadButton_X) &&
            (buttons&HidNpadButton_ZL) &&
            (buttons&HidNpadButton_ZR);
        if(driving_preview_chord) {
            driving_preview=!driving_preview;
            road_profile_review.reset();
            private_road_review.reset();
            if(driving_preview) {
                driving_state.reset();
                driving_stage_exit.reset();
                driving_route_proof.reset();
                vpd::resetDrivingRouteWitness(has_sd);
                (void)vpd::appendDrivingGuestProof(has_sd,
                    driving_proof.enter(!demo.enabled(),true,
                                        driving_state,game.fingerprint()));
            } else {
                (void)vpd::appendDrivingGuestProof(has_sd,
                    driving_proof.leave(!demo.enabled(),true,
                                        driving_state,game.fingerprint()));
            }
        }
        // ZL+ZR+Y cycles through 7 known source-frame numeric swatches
        // then OFF. Does NOT change car/world speed or synthetic road mesh.
        const bool road_review_chord=
            driving_preview && !driving_stage_exit.active() &&
            (pressed&HidNpadButton_Y) &&
            (buttons&HidNpadButton_ZL) &&
            (buttons&HidNpadButton_ZR);
        if(road_review_chord)private_road_review.reset();
        (void)road_profile_review.cycle(
            !demo.enabled(),driving_preview,road_review_chord);
        // ZL+ZR+StickR cycles the locally validated 37 source numeric
        // intervals, then OFF. An absent/invalid SD bundle leaves it inert.
        // No second game tick, road collision update or camera transform.
        const bool private_road_chord=
            driving_preview && !driving_stage_exit.active() &&
            (pressed&HidNpadButton_StickR) &&
            (buttons&HidNpadButton_ZL) &&
            (buttons&HidNpadButton_ZR);
        if(private_road_review.cycle(
            !demo.enabled(),driving_preview,private_road_chord,
            private_road_data))road_profile_review.reset();
        if(buttons&HidNpadButton_Plus){
            if(!demo.enabled())vpd::guardLiveDebugRecord(
                has_sd,"plus",game,0);
            // Must have completed the actual ordered manual control probe.
            if(!demo.enabled() && manual_seq==5){
                if(manual_retry_has_occurred)
                    (void)vpd::manualProofAppendSession(
                        has_sd,vpd::ManualProofEvent::Plus,
                        6,game,1,manual_session_ticks);
                else
                    (void)vpd::manualProofAppend(
                        has_sd,vpd::ManualProofEvent::Plus,6,game,1);
                manual_seq=6;
                plus_seen=true;
            }
            break;
        }
        // L+R toggles only the authored HD effects during manual play.
        // A held chord consumes both individual asset commands, so
        // no backdrop reload/reset is accidentally performed.
        const bool hd_fx_before=hd_fx_mode.enabled;
        const bool hd_fx_chord=hd_fx_mode.acceptShoulders(
            !demo.enabled(),
            (buttons&HidNpadButton_L)!=0,
            (buttons&HidNpadButton_R)!=0,
            (pressed&HidNpadButton_L)!=0,
            (pressed&HidNpadButton_R)!=0);
        // The established guest V2 proof remains POST-CLEAR only.
        // Combat chords use a separate source-owned witness below.
        const bool hd_fx_guest_edge=hd_fx_chord &&
            hd_fx_before!=hd_fx_mode.enabled && hd_fx_guest_seq<2 &&
            fourth_stage_seq==2;
        // Left-stick click switches between 200-frame demo and manual play.
        // StickL+Y still performs the independent development-art reset.
        const bool toggle_manual=!driving_stage_exit.active() &&
            ((pressed&HidNpadButton_StickL) && !(buttons&HidNpadButton_Y)) ||
            ((pressed&HidNpadButton_A) && (buttons&HidNpadButton_R));
        if(toggle_manual) {
            driving_preview=false;
            road_profile_review.reset();
            private_road_review.reset();
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
            live_wave_seq=0;
            if(!demo.enabled()){
                // Preserve ROM-free autoplay hashes: enable encounter only on
                // entry into explicit manual gameplay, never in attract mode.
                game.enableEnemyEncounter();
                manual_seq=1;
                manual_session_ticks=0;
                (void)vpd::manualProofAppend(has_sd,vpd::ManualProofEvent::Enter,
                                             1,game,1);
            } else manual_seq=0;
        }
        if((pressed&HidNpadButton_X) && !driving_preview_chord) {
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
        if((pressed&HidNpadButton_ZL) && !driving_preview_chord) {
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
        if((pressed&HidNpadButton_L) && !hd_fx_chord) {
            backdrop_reload_failed= !has_sd ||
                backdrop.reload(kExternalBackdropPath)!=vpd::BackdropReload::Loaded;
        }
        if((pressed&HidNpadButton_R) && !hd_fx_chord) {
            backdrop.reset();
            backdrop_reload_failed=false;
        }
        if((pressed&HidNpadButton_Up) && !driving_preview) {
            decor_reload_failed= !has_sd ||
                decor.reload(kExternalDecorPath)!=vpd::DecorReload::Loaded;
        }
        if((pressed&HidNpadButton_Down) && !driving_preview) {
            decor.reset();
            decor_reload_failed=false;
        }
        // Minus means RETRY only on a completed or defeated manual
        // encounter. Else retain its existing decorative-layout reload.
        const auto retry_old=vpd::retryBefore(game);
        const bool retry_input=(!demo.enabled() && !driving_preview &&
                                (pressed&HidNpadButton_Minus));
        const auto retry=vpd::retryTerminalEncounter(game,retry_input);
        const bool restarted=retry!=vpd::ManualRetryOutcome::Ignored;
        if(restarted){
            manual_retry_has_occurred=true;
            animation.reset();
            checkpoint_ok=false;
            if(!retry_native_logged)
                retry_native_logged=vpd::appendManualRetryGuest(
                    has_sd,retry,retry_old,game,retry_input);
            // A third *earned* victory can start a fourth attempt, but
            // only the actual pad-Minus and clean core reset can attest it.
            if(third_stage_seq==2 && !fourth_restart_logged &&
               retry==vpd::ManualRetryOutcome::AfterVictory)
                fourth_restart_logged=vpd::appendFourthRestart(
                    has_sd,retry,retry_old,game,retry_input);
            // Independent, second terminal replay: only after the actual
            // same-session victory retry AND source-detected melee death.
            if(retry_native_logged && replay_guard_death_logged &&
               !replay_guard_restart_logged &&
               retry==vpd::ManualRetryOutcome::AfterDefeat)
                replay_guard_restart_logged=vpd::appendLiveDefeatRetry(
                    has_sd,vpd::DefeatRetryEvent::Restart,
                    game,0,retry_input,retry_old,retry);
        }
        if((pressed&HidNpadButton_Minus) && !restarted &&
           !driving_preview){
            decor_layout_reload_failed= !has_sd ||
                layout.reload(kExternalDecorLayoutPath)!=vpd::LayoutLoadResult::Loaded;
        }
        // StickR's old layout reset is still available outside driving,
        // but must not alter platform art when reviewing private road data.
        if((pressed&HidNpadButton_StickR) && !driving_preview){
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
        // Prototype route duration: auto-request the transition after the
        // final completed road frame. This is a tunable placeholder, not a
        // recovered original-game clear condition. Minus remains a manual QA
        // escape hatch for early transition tests.

        const bool driving_retry_pressed=driving_preview &&
            driving_state.health==0 && (pressed&HidNpadButton_X) &&
            !driving_preview_chord;
        if(driving_retry_pressed) {
            driving_state.reset();
            driving_stage_exit.reset();
            driving_route_proof.reset();
            vpd::resetDrivingRouteWitness(has_sd);
            (void)vpd::appendDrivingGuestProof(has_sd,
                driving_proof.enter(!demo.enabled(),true,
                                    driving_state,game.fingerprint()));
        }
        const bool request_driving_exit=
            vpd::DrivingStageOneConfig::shouldRequestExit(
                driving_preview,driving_state.health,
                driving_stage_exit.active(),
                (pressed&HidNpadButton_Minus)!=0,
                driving_state.frame,driving_state.obstacles_passed);
        if(demo.enabled()) {
            if(demo.tick(game)) animation.reset();
        } else {
            ++manual_session_ticks; // independent monotone real pad-loop time
            // Measure actual simulation effects, not merely keyboard events.
            const auto before_x=game.player().x;
            const auto before_frame=game.frame();
            const auto before_shots=game.shotsFired();
            const auto was_alerted=game.guardEnemy().alerted;
            const auto prior_hp=game.playerHealth();
            const auto prior_hero_flash=game.playerHitFlashTicks();
            const auto prior_attacks=game.guardEnemy().attacks;
            const auto prior_guard_hp=game.guardEnemy().health;
            const auto prior_guard_hits=game.guardEnemy().projectile_hits;
            const bool prior_wave_active=game.secondWaveActive();
            const auto prior_turret_hits=game.sentry().projectile_hits;
            const auto prior_shots_hit=game.sentry().shots_hit;
            const auto prior_hero_x=game.player().x;
            const auto prior_hero_y=game.player().y;
            const auto tracked_bullet=(hd_fx_sentry_seq==2 &&
                hd_fx_sentry_tracked_slot>=0)?
                game.enemyProjectiles()[
                    static_cast<unsigned>(hd_fx_sentry_tracked_slot)]:
                vpd::EnemyProjectile{};
            const uint64_t prior_sentry_fingerprint=
                hd_fx_sentry_seq==2 && !hd_fx_sentry_hit_logged ?
                game.fingerprint():0;
            if(driving_preview) {
                // The road prototype updates only its own invented simulation.
                // Keep the established platform game/fingerprint unchanged.
                if(!driving_preview_chord && !driving_retry_pressed &&
                   driving_state.health>0 && !driving_stage_exit.active() &&
                   !request_driving_exit) {
                    const vpd::DriveInput drive_input{
                        (buttons&(HidNpadButton_Left|HidNpadButton_StickLLeft))!=0,
                        (buttons&(HidNpadButton_Right|HidNpadButton_StickLRight))!=0,
                        (buttons&(HidNpadButton_Up|HidNpadButton_StickLUp|HidNpadButton_A))!=0,
                        (buttons&(HidNpadButton_Down|HidNpadButton_StickLDown|HidNpadButton_B))!=0
                    };
                    const vpd::DrivingState car_before=driving_state;
                    driving_state.tick(drive_input);
                    const auto driving_event=driving_proof.tick(
                        drive_input,car_before,driving_state,game.fingerprint());
                    if(driving_event.seq==2 || driving_event.seq==4)
                        driving_raster_event_seq=driving_event.seq;
                    (void)vpd::appendDrivingGuestProof(has_sd,driving_event);
                    (void)vpd::appendDrivingRouteWitness(
                        has_sd,driving_route_proof.sample(
                            drive_input,driving_state,game.fingerprint()));
                }
                input=0;
            } else if(toggle_manual || driving_preview_chord) {
                input=0; // entering/leaving preview never performs a jump/dash
            }
            // First visible platform presentation is a state-identical
            // restoration. Normal platform simulation resumes NEXT frame.
            if(!restarted && !driving_preview &&
               driving_present!=vpd::stage_transition::Scene::Platform)
                game.tick(vpd::Input{input});
            // Verify the actual physics tick consumed the SAME bullet
            // witnessed at native L+R ON, not another hostile projectile.
            // A host keypress, synthetic HP subtraction or raster change
            // cannot create this record. Keep all original wave proofs.
            if(hd_fx_sentry_seq==2 && !hd_fx_sentry_hit_logged &&
               !restarted && input==0 && hd_fx_mode.enabled &&
               fourth_stage_seq==1 && game.guardEnemy().health==0 &&
               game.sentry().health==2 && game.secondWaveActive() &&
               !game.stageCleared() && prior_hp>1 &&
               game.playerHealth()+1==prior_hp &&
               game.sentry().shots_hit==prior_shots_hit+1 &&
               prior_shots_hit==hd_fx_sentry_on_hits &&
               prior_hp==hd_fx_sentry_on_hero_hp &&
               tracked_bullet.active &&
               !game.enemyProjectiles()[
                   static_cast<unsigned>(hd_fx_sentry_tracked_slot)].active &&
               tracked_bullet.vx==-3*vpd::kFixed &&
               tracked_bullet.y==hd_fx_sentry_on_y &&
               before_frame>hd_fx_sentry_on_frame &&
               tracked_bullet.age==hd_fx_sentry_on_age+
                   before_frame-hd_fx_sentry_on_frame &&
               static_cast<int64_t>(tracked_bullet.x)==
                   static_cast<int64_t>(hd_fx_sentry_on_x)-
                   static_cast<int64_t>(3*vpd::kFixed)*
                   (before_frame-hd_fx_sentry_on_frame) &&
               tracked_bullet.x>=prior_hero_x &&
               tracked_bullet.x-3*vpd::kFixed<
                   prior_hero_x+vpd::kPlayerWidth*vpd::kFixed &&
               tracked_bullet.y>=prior_hero_y &&
               tracked_bullet.y<prior_hero_y+
                   vpd::kPlayerHeight*vpd::kFixed &&
               game.fingerprint()!=prior_sentry_fingerprint &&
               has_sd){
                if(auto* report=std::fopen(
                    "sdmc:/switch/vice_project_doom/hd_fx_sentry_hit_guest.txt",
                    "a")){
                    const int printed=std::fprintf(report,
                        "VPD_HD_FX_SENTRY_HIT_V1 frame=%u on_frame=%u "
                        "bullet_slot=%u bullet_age_before=%u "
                        "bullet_x_before=%ld bullet_y=%ld bullet_vx=-768 "
                        "hero_x=%ld hero_y=%ld "
                        "hero_hp_before=%u hero_hp_after=%u "
                        "shots_hit_before=%u shots_hit_after=%u "
                        "input=idle mode=on wave=1 guard_hp=0 "
                        "sentry_hp=2 bullet_consumed=yes "
                        "simulation_before=%016llx simulation_after=%016llx "
                        "source=libnx_tick collision=swept "
                        "original_game_proven=no\n",
                        game.frame(),hd_fx_sentry_on_frame,
                        static_cast<unsigned>(hd_fx_sentry_tracked_slot),
                        static_cast<unsigned>(tracked_bullet.age),
                        static_cast<long>(tracked_bullet.x),
                        static_cast<long>(tracked_bullet.y),
                        static_cast<long>(prior_hero_x),
                        static_cast<long>(prior_hero_y),
                        static_cast<unsigned>(prior_hp),
                        static_cast<unsigned>(game.playerHealth()),
                        static_cast<unsigned>(prior_shots_hit),
                        static_cast<unsigned>(game.sentry().shots_hit),
                        static_cast<unsigned long long>(prior_sentry_fingerprint),
                        static_cast<unsigned long long>(game.fingerprint()));
                    hd_fx_sentry_hit_logged=printed>0 &&
                        std::fclose(report)==0;
                    if(hd_fx_sentry_hit_logged){
                        hd_fx_sentry_hit_frame=game.frame();
                        hd_fx_sentry_hit_x=prior_hero_x;
                        hd_fx_sentry_hit_y=prior_hero_y;
                    }
                    if(!hd_fx_sentry_hit_logged && printed<=0)
                        std::fclose(report);
                }
            }
            // Confirm the authentic hit flash expires after exactly 16 idle
            // source ticks. The hero must remain stationary, alive and at
            // the same HP; no host clock or synthetic damage is accepted.
            if(hd_fx_sentry_hit_logged && !hd_fx_sentry_recovered_logged &&
               !restarted && input==0 && hd_fx_mode.enabled &&
               fourth_stage_seq==1 && game.secondWaveActive() &&
               !game.stageCleared() && game.guardEnemy().health==0 &&
               game.sentry().health==2 &&
               game.frame()==hd_fx_sentry_hit_frame+16 &&
               prior_hero_flash==1 && game.playerHitFlashTicks()==0 &&
               prior_hp==hd_fx_sentry_on_hero_hp-1 &&
               game.playerHealth()==prior_hp &&
               game.player().x==hd_fx_sentry_hit_x &&
               game.player().y==hd_fx_sentry_hit_y &&
               game.sentry().shots_hit==hd_fx_sentry_on_hits+1 &&
               has_sd){
                if(auto* report=std::fopen(
                    "sdmc:/switch/vice_project_doom/hd_fx_sentry_recover_guest.txt",
                    "a")){
                    const int printed=std::fprintf(report,
                        "VPD_HD_FX_SENTRY_RECOVER_V1 hit_frame=%u "
                        "frame=%u flash_before=1 flash_after=0 "
                        "hero_hp_before=%u hero_hp_after=%u "
                        "hero_x=%ld hero_y=%ld shots_hit=%u "
                        "mode=on input=idle wave=1 guard_hp=0 "
                        "sentry_hp=2 source=libnx_tick original_game_proven=no\n",
                        hd_fx_sentry_hit_frame,game.frame(),
                        static_cast<unsigned>(prior_hp),
                        static_cast<unsigned>(game.playerHealth()),
                        static_cast<long>(game.player().x),
                        static_cast<long>(game.player().y),
                        static_cast<unsigned>(game.sentry().shots_hit));
                    hd_fx_sentry_recovered_logged=printed>0 &&
                        std::fclose(report)==0;
                    if(!hd_fx_sentry_recovered_logged && printed<=0)
                        std::fclose(report);
                }
            }
            // Following the *already witnessed* victory Minus, the newly
            // reset visible simulation is played again with actual Right
            // input. The first guard must strike and eventually defeat this
            // hero before a second Minus can be attested.
            if(retry_native_logged && !replay_guard_contact_logged &&
               (input&vpd::Right) && prior_attacks==0 &&
               game.guardEnemy().attacks==1 &&
               prior_hp==5 && game.playerHealth()==4)
                replay_guard_contact_logged=vpd::appendLiveDefeatRetry(
                    has_sd,vpd::DefeatRetryEvent::Contact,game,input);
            if(replay_guard_contact_logged &&
               hd_low_hp_first_contact_frame==0)
                hd_low_hp_first_contact_frame=game.frame();
            // Genuine idle melee strikes from the existing verified
            // second-run encounter. At the third strike HP reaches TWO:
            // this is only a passive observation of Simulation::tick.
            if(replay_guard_contact_logged && !hd_low_hp_logged &&
               !replay_guard_death_logged && !restarted &&
               input==0 && hd_fx_mode.enabled && has_sd &&
               prior_hp==3 && game.playerHealth()==2 &&
               prior_attacks==2 && game.guardEnemy().attacks==3 &&
               game.frame()==hd_low_hp_first_contact_frame+64 &&
               game.guardEnemy().health==3 &&
               !game.secondWaveActive() && !game.stageCleared()){
                if(auto* report=std::fopen(
                    "sdmc:/switch/vice_project_doom/hd_low_health_guest.txt",
                    "a")){
                    const int written=std::fprintf(report,
                        "VPD_HD_LOW_HEALTH_GUEST_V1 contact_frame=%u "
                        "frame=%u hero_hp_before=3 hero_hp_after=2 "
                        "guard_attacks_before=2 guard_attacks_after=3 "
                        "input=idle hd=on guard_hp=3 wave=0 clear=0 "
                        "source=libnx_tick original_game_proven=no\n",
                        hd_low_hp_first_contact_frame,game.frame());
                    hd_low_hp_logged=written>0 &&
                        std::fclose(report)==0;
                    if(hd_low_hp_logged)
                        hd_low_hp_third_frame=game.frame();
                    if(!hd_low_hp_logged && written<=0)
                        std::fclose(report);
                }
            }
            // Issue the native X11 cue only on an actual ON half-cycle
            // (12 source frames visible, 12 absent). The first arbitrary
            // HP2 screenshots could all land in an OFF half-cycle, even
            // with authentic HP and real images. Tie the cue to source
            // frame % 24 == 0 while HP2 remains unchanged in guest.
            if(hd_low_hp_logged && !hd_low_hp_phase_logged &&
               hd_low_hp_third_frame>0 && !restarted &&
               input==0 && hd_fx_mode.enabled && has_sd &&
               game.playerHealth()==2 && prior_hp==2 &&
               game.guardEnemy().attacks==3 &&
               game.frame()>=hd_low_hp_third_frame &&
               game.frame()<hd_low_hp_third_frame+32 &&
               game.frame()%24u==0u &&
               game.guardEnemy().health==3 &&
               !game.secondWaveActive() && !game.stageCleared()){
                if(auto* report=std::fopen(
                    "sdmc:/switch/vice_project_doom/hd_low_health_phase_guest.txt",
                    "a")){
                    const int written=std::fprintf(report,
                        "VPD_HD_LOW_HEALTH_PHASE_V1 third_frame=%u "
                        "frame=%u hero_hp=2 guard_attacks=3 "
                        "input=idle hd=on pulse=on "
                        "source=libnx_tick original_game_proven=no\n",
                        hd_low_hp_third_frame,game.frame());
                    hd_low_hp_phase_logged=written>0 &&
                        std::fclose(report)==0;
                    if(!hd_low_hp_phase_logged && written<=0)
                        std::fclose(report);
                }
            }
            if(replay_guard_contact_logged && !replay_guard_death_logged &&
               prior_hp==1 && game.playerHealth()==0 &&
               game.guardEnemy().attacks>=5)
                replay_guard_death_logged=vpd::appendLiveDefeatRetry(
                    has_sd,vpd::DefeatRetryEvent::Death,game,input);
            // A new third playthrough only becomes attestable after
            // the SAME visible NRO recorded actual defeat and second Minus.
            // Require a fresh Right tick that physically moves a healthy
            // actor. Neither the retry event nor injected host key alone
            // constitutes evidence of resumed playable control.
            if(replay_guard_restart_logged && !third_run_move_logged &&
               !restarted && input==vpd::Right &&
               game.player().x-before_x==2*vpd::kFixed &&
               game.playerHealth()==5)
                third_run_move_logged=vpd::appendPostDefeatControl(
                    has_sd,game,input,before_x,before_frame);
            // After proven post-defeat movement, insist that the native
            // pad-driven third run actually creates one Fire projectile,
            // then the original swept collision subtracts one guard HP.
            if(third_run_move_logged && !third_run_fire_logged &&
               !restarted && input==vpd::Fire &&
               before_shots==0 && game.shotsFired()==1)
                third_run_fire_logged=vpd::appendPostDefeatFire(
                    has_sd,vpd::ThirdFireEvent::Fire,game,input,
                    before_shots,prior_guard_hits,prior_guard_hp);
            if(third_run_fire_logged && !third_run_hit_logged &&
               !restarted && input==0 && prior_guard_hits==0 &&
               game.guardEnemy().projectile_hits==1 &&
               prior_guard_hp==3 && game.guardEnemy().health==2)
                third_run_hit_logged=vpd::appendPostDefeatFire(
                    has_sd,vpd::ThirdFireEvent::Impact,game,input,
                    before_shots,prior_guard_hits,prior_guard_hp);
            // The restored third run must also finish the first guard by
            // two more actual swept impacts under a real held Y/Fire.
            if(third_run_hit_logged && !third_guard_clear_logged &&
               !restarted && input==vpd::Fire &&
               prior_guard_hp==1 && prior_guard_hits==2 &&
               game.guardEnemy().health==0 &&
               game.guardEnemy().projectile_hits==3)
                third_guard_clear_logged=vpd::appendThirdGuardClear(
                    has_sd,game,input,prior_guard_hp,prior_guard_hits);
            // This is the restarted third manual attempt, not the earlier
            // first-playthrough wave witness: genuinely cross the gate
            // after its own guard kill, then earn a fresh stage clear.
            if(third_guard_clear_logged && third_stage_seq==0 &&
               !prior_wave_active && game.secondWaveActive() &&
               (input&vpd::Right) &&
               vpd::appendThirdStage(
                   has_sd,vpd::ThirdStageEvent::Wave,game,input))
                third_stage_seq=1;
            if(third_stage_seq==1 && game.stageCleared() &&
               (input&(vpd::Right|vpd::Fire))==
                   (vpd::Right|vpd::Fire) &&
               vpd::appendThirdStage(
                   has_sd,vpd::ThirdStageEvent::Exit,game,input))
                third_stage_seq=2;
            // After the source-confirmed fourth reset, require real Right
            // to move a freshly restored hero. Merely pressing Minus does
            // not establish that gameplay resumed.
            if(fourth_restart_logged && !fourth_move_logged &&
               !restarted && input==vpd::Right &&
               game.player().x-before_x==2*vpd::kFixed &&
               game.playerHealth()==5)
                fourth_move_logged=vpd::appendFourthMove(
                    has_sd,game,input,before_x,before_frame);
            // A fourth replay is not fully playable until the same
            // guest produces one physical Y/Fire shot AND a real
            // swept guard hit. These cannot originate from the demo.
            if(fourth_move_logged && !fourth_fire_logged &&
               !restarted && input==vpd::Fire &&
               before_shots==0 && game.shotsFired()==1)
                fourth_fire_logged=vpd::appendFourthCombat(
                    has_sd,vpd::FourthCombatEvent::Fire,game,input,
                    before_shots,prior_guard_hits,prior_guard_hp);
            if(fourth_fire_logged && !fourth_hit_logged &&
               !restarted && input==0 && prior_guard_hits==0 &&
               game.guardEnemy().projectile_hits==1 &&
               prior_guard_hp==3 && game.guardEnemy().health==2)
                fourth_hit_logged=vpd::appendFourthCombat(
                    has_sd,vpd::FourthCombatEvent::Impact,game,input,
                    before_shots,prior_guard_hits,prior_guard_hp);
            // Later fourth-round shots are real manual source actions.
            // Count guard defeat only on its exact third swept hit.
            if(fourth_hit_logged && !fourth_guard_clear_logged &&
               !restarted && input==vpd::Fire &&
               prior_guard_hp==1 && prior_guard_hits==2 &&
               game.guardEnemy().health==0 &&
               game.guardEnemy().projectile_hits==3)
                fourth_guard_clear_logged=vpd::appendFourthGuardClear(
                    has_sd,game,input,prior_guard_hp,prior_guard_hits);
            // The actual fourth-run first guard must die before a
            // fresh second-wave gate can be opened by real Right.
            if(fourth_guard_clear_logged && fourth_stage_seq==0 &&
               !prior_wave_active && game.secondWaveActive() &&
               (input&vpd::Right) &&
               vpd::appendFourthStage(
                   has_sd,vpd::FourthStageEvent::Wave,game,input))
                fourth_stage_seq=1;
            // The same rendered fourth simulation must defeat the second
            // sentry and earn stage exit with held manual Right+Fire.
            if(fourth_stage_seq==1 && game.stageCleared() &&
               (input&(vpd::Right|vpd::Fire))==
                   (vpd::Right|vpd::Fire) &&
               vpd::appendFourthStage(
                   has_sd,vpd::FourthStageEvent::Exit,game,input))
                fourth_stage_seq=2;
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
            // Five new milestones from THIS visible manual gameplay, never
            // from the separate native guest-scripted stage-two experiment.
            if(live_guard_defeated && live_wave_seq==0 &&
               !prior_wave_active && game.secondWaveActive() &&
               (input&vpd::Right) &&
               vpd::liveWaveAppend(has_sd,vpd::LiveWaveEvent::Activated,
                                   game,input))
                live_wave_seq=1;
            if(live_wave_seq==1 &&
               (input&(vpd::Right|vpd::Fire))==(vpd::Right|vpd::Fire) &&
               game.shotsFired()>before_shots &&
               vpd::liveWaveAppend(has_sd,vpd::LiveWaveEvent::Fire,
                                   game,input))
                live_wave_seq=2;
            if(live_wave_seq==2 && prior_turret_hits==0 &&
               game.sentry().projectile_hits==1 &&
               vpd::liveWaveAppend(has_sd,vpd::LiveWaveEvent::FirstImpact,
                                   game,input))
                live_wave_seq=3;
            if(live_wave_seq==3 && prior_turret_hits==1 &&
               game.sentry().projectile_hits==2 &&
               vpd::liveWaveAppend(has_sd,vpd::LiveWaveEvent::Defeat,
                                   game,input))
                live_wave_seq=4;
            // Sparse source-side position samples let a failed NeXium
            // run distinguish slow guest frames from blocked movement or
            // an unexpected terminal hero state. Never substitute for
            // the five strict real-pad live-wave witness events.
            if(has_sd && live_wave_seq==4 &&
               game.frame()!=0 && game.frame()%64==0){
                if(auto* report=std::fopen(
                    "sdmc:/switch/vice_project_doom/wave_exit_progress.txt",
                    "a")){
                    (void)std::fprintf(
                        report,
                        "VPD_WAVE_EXIT_PROGRESS_V1 frame=%u hero_x=%ld "
                        "hero_hp=%u sentry_hp=%u wave=%u clear=%u "
                        "right=%u fire=%u source=live_guest "
                        "diagnostic_only=yes\n",
                        game.frame(),static_cast<long>(game.player().x),
                        static_cast<unsigned>(game.playerHealth()),
                        static_cast<unsigned>(game.sentry().health),
                        game.secondWaveActive()?1u:0u,
                        game.stageCleared()?1u:0u,
                        (input&vpd::Right)?1u:0u,
                        (input&vpd::Fire)?1u:0u);
                    (void)std::fclose(report);
                }
            }
            if(live_wave_seq==4 && game.stageCleared() &&
               vpd::liveWaveAppend(has_sd,vpd::LiveWaveEvent::Exit,
                                   game,input))
                live_wave_seq=5;
            // Two guest-written milestones require a real first and
            // eighth tick from the opt-in enemy AI, not a host fixture.
            if(!manual_retry_has_occurred && game.frame()==1)
                (void)vpd::guardProofAppend(
                    has_sd,vpd::GuardProofEvent::FirstStep,game);
            if(!manual_retry_has_occurred && game.frame()==8){
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
        view.driving_stage_preview=driving_preview && view.manual_controls;
        if(view.driving_stage_preview) {
            view.driving=vpd::makeDrivingSceneView(driving_state);
            view.driving.observed_road_frame=
                road_profile_review.originalFrame();
            if(const auto* selected=
                private_road_review.selected(private_road_data)) {
                view.driving.private_road_enabled=true;
                view.driving.private_original_frame=selected->frame;
                view.driving.private_left=selected->left;
                view.driving.private_right=selected->right;
            }
        }
        const bool hd_effects=hd_fx_mode.activeForGameplay(
            view.manual_controls);
        view.hd_hit_lighting=hd_effects;
        view.hd_atmospheric_haze=hd_effects;
        view.hd_footstep_dust=hd_effects;
        view.hd_hostile_projectile_halo=hd_effects;
        view.hd_low_health_warning=hd_effects;
        view.hd_guard_threat_tell=hd_effects;
        view.hd_fx_status_visible=view.manual_controls;
        view.hd_fx_status_enabled=hd_effects;
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
        // Proof from the actual fourth-run sentry projectile: one source
        // frame, two native draws, zero extra physics or pad steps. Use only
        // the first ACTIVE hostile bullet after the authenticated wave gate.
        bool hostile_sample_frame=false;
        unsigned hostile_slot=0;
        int hostile_x=0,hostile_y=0;
        if(!native_hostile_halo_logged && fourth_stage_seq==1 &&
           view.manual_controls && view.hd_hostile_projectile_halo &&
           game.secondWaveActive() && !game.stageCleared() &&
           game.sentry().health>0 && game.sentry().shots_fired>0){
            const auto& enemies=game.enemyProjectiles();
            for(unsigned i=0;i<enemies.size();++i){
                if(!enemies[i].active)continue;
                const int sx=(enemies[i].x/vpd::kFixed-game.cameraX())*2+2;
                const int sy=(enemies[i].y/vpd::kFixed+80)*2;
                if(sx<16 || sx>vpd::kSceneWidth-16 ||
                   sy<16 || sy>vpd::kSceneHeight-16)continue;
                hostile_sample_frame=true;
                hostile_slot=i;hostile_x=sx;hostile_y=sy;
                break;
            }
        }
        vpd::HostileHaloSample hostile_dark{},hostile_lit{};
        const int hostile_stride=static_cast<int>(stride/sizeof(uint32_t));
        if(hostile_sample_frame){
            view.hd_hostile_projectile_halo=false;
            const bool unlit=vpd::drawScene(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,
                hostile_stride,view);
            if(!unlit){framebufferEnd(&fb);break;}
            hostile_dark=vpd::sampleHostileHalo(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,
                hostile_stride,hostile_x,hostile_y);
            view.hd_hostile_projectile_halo=true;
        }
        // Fourth physically injected Right input already earned its native
        // source movement record. Measure one same-frame native framebuffer
        // pair around the hero's grounded trailing heel, no extra game tick.
        const bool dust_sample_frame=!native_hd_dust_logged &&
            fourth_move_logged && view.manual_controls &&
            view.hd_footstep_dust && actor.grounded &&
            actor.vx==2*vpd::kFixed && game.shotsFired()==0 &&
            vpd::fourthFresh(game);
        vpd::DustFrameSample no_dust{},with_dust{};
        const int dust_stride=static_cast<int>(stride/sizeof(uint32_t));
        const int heel=(actor.x/vpd::kFixed-game.cameraX())*2+3;
        const int ground=(actor.y/vpd::kFixed+80)*2+30;
        if(dust_sample_frame){
            view.hd_footstep_dust=false;
            const bool plain=vpd::drawScene(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,dust_stride,view);
            if(!plain){framebufferEnd(&fb);break;}
            no_dust=vpd::sampleFootstep(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,
                dust_stride,heel,ground);
            view.hd_footstep_dust=true;
        }
        // Differential proof in a single *actual* guard-impact frame.
        // The first pass is unlit and sampled only; the second pass is
        // the real illuminated framebuffer that goes to NeXium.
        // Neither pass ticks the game, alters the camera, nor replays inputs.
        const bool hd_sample_frame=!native_hd_hit_logged &&
            fourth_hit_logged && view.manual_controls &&
            view.hd_hit_lighting && game.enemyEncounterEnabled() &&
            game.guardEnemy().health==2 &&
            game.guardEnemy().projectile_hits==1 &&
            game.guardEnemy().hit_flash_ticks>0 &&
            game.shotsFired()==1;
        vpd::ImpactSample unlit{},lit{};
        const int pixels_per_row=static_cast<int>(stride/sizeof(uint32_t));
        const int center_x=(game.guardEnemy().x/vpd::kFixed-game.cameraX())*2+13;
        const int center_y=(game.guardEnemy().y/vpd::kFixed+80)*2+13;
        if(hd_sample_frame){
            view.hd_hit_lighting=false;
            const bool without=vpd::drawScene(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row,view);
            if(!without){framebufferEnd(&fb);break;}
            unlit=vpd::sampleGuardImpact(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row,
                center_x,center_y);
            view.hd_hit_lighting=true;
        }
        // Real libnx L+R input must change source-owned HD pixels on the
        // SAME guest frame. Render the opposite setting first, fingerprint
        // a HUD-free region, then render the actual state for presentation.
        // No additional input, game tick, camera step or allocated buffer.
        // Snapshot the authoritative game state after the one legitimate
        // simulation tick, before either HD-effect raster pass. This proves
        // both comparison draws are render-only inside the actual NRO.
        const bool hd_fx_combat_edge=hd_fx_chord &&
            hd_fx_before!=hd_fx_mode.enabled && hd_fx_combat_seq<2 &&
            fourth_hit_logged && !fourth_guard_clear_logged &&
            view.manual_controls && game.enemyEncounterEnabled() &&
            game.guardEnemy().health==2 &&
            game.guardEnemy().projectile_hits==1 &&
            game.playerHealth()>0 && !game.stageCleared();
        // Separate guest-only witness while a genuine second-wave bullet
        // remains active after the previously audited live halo sample.
        // A host key event alone cannot create this source-owned record.
        int hd_fx_sentry_slot=-1;
        const auto& hostile_bullets=game.enemyProjectiles();
        for(unsigned i=0;i<hostile_bullets.size();++i){
            if(hostile_bullets[i].active){hd_fx_sentry_slot=static_cast<int>(i);break;}
        }
        const bool hd_fx_sentry_edge=hd_fx_chord &&
            hd_fx_before!=hd_fx_mode.enabled && hd_fx_sentry_seq<2 &&
            native_hostile_halo_logged && fourth_stage_seq==1 &&
            view.manual_controls && game.enemyEncounterEnabled() &&
            game.guardEnemy().health==0 && game.secondWaveActive() &&
            game.sentry().health==2 && game.playerHealth()>0 &&
            !game.stageCleared() && hd_fx_sentry_slot>=0;
        const bool hd_fx_probe_edge=hd_fx_guest_edge ||
            hd_fx_combat_edge || hd_fx_sentry_edge;
        // One shared edge gate drives both raster passes and both source
        // fingerprints. No duplicated, potentially divergent predicates.
        const uint64_t fx_sim_before=hd_fx_probe_edge &&
            view.manual_controls ? game.fingerprint() : 0;
        vpd::HdFxGuestFingerprint fx_other{},fx_presented{};
        if(hd_fx_probe_edge && view.manual_controls){
            auto alternate=view;
            const bool alt=!hd_effects;
            alternate.hd_hit_lighting=alt;
            alternate.hd_atmospheric_haze=alt;
            alternate.hd_footstep_dust=alt;
            alternate.hd_hostile_projectile_halo=alt;
            alternate.hd_low_health_warning=alt;
            alternate.hd_guard_threat_tell=alt;
            alternate.hd_fx_status_enabled=alt;
            if(!vpd::drawScene(pixels,vpd::kSceneWidth,
                               vpd::kSceneHeight,pixels_per_row,alternate)){
                framebufferEnd(&fb);break;
            }
            fx_other=vpd::fingerprintHdFxVisual(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row);
        }
        const bool drawn=driving_present==vpd::stage_transition::Scene::Black
            ? vpd::drawDrivingBlackout(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row)
            : vpd::drawScene(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row,view);
        if(drawn && driving_present==vpd::stage_transition::Scene::Black) {
            const bool black_pixel=
                pixels[0]==0xff000000u &&
                pixels[360*pixels_per_row+640]==0xff000000u &&
                pixels[719*pixels_per_row+1279]==0xff000000u;
            (void)vpd::appendDrivingExitWitness(
                has_sd,driving_exit_proof.black(
                    driving_stage_exit.blackFramesPresented(),
                    game.fingerprint(),black_pixel));
        }
        if(drawn && driving_present==vpd::stage_transition::Scene::Platform) {
            (void)vpd::appendDrivingExitWitness(
                has_sd,driving_exit_proof.platform(game.fingerprint()));
        }
        if(drawn && view.driving_stage_preview && private_road_chord)
            (void)vpd::appendPrivateRoadRejectGuest(
                has_sd,private_road_reject_proof.observe(
                    view.manual_controls,view.driving_stage_preview,
                    private_road_chord,private_road_data,
                    private_road_review,view.driving,
                    pixels,pixels_per_row,game.fingerprint()));
        if(drawn && view.driving_stage_preview && private_road_chord)
            (void)vpd::appendPrivateRoadR3Guest(
                has_sd,private_road_r3_proof.observe(
                    view.manual_controls,view.driving_stage_preview,
                    private_road_chord,private_road_data,
                    private_road_review,view.driving,
                    pixels,pixels_per_row,game.fingerprint()));
        if(drawn && view.driving_stage_preview && road_review_chord)
            (void)vpd::appendRoadReviewGuest(
                has_sd,road_review_guest_proof.observe(
                    view.manual_controls,view.driving_stage_preview,
                    road_review_chord,road_profile_review,view.driving,
                    pixels,pixels_per_row,game.fingerprint()));
        if(drawn && view.driving_stage_preview &&
           driving_raster_event_seq!=0) {
            (void)vpd::appendDrivingRasterProof(
                has_sd,driving_raster_event_seq,view.driving,
                pixels,pixels_per_row);
        }
        if(drawn && hd_fx_probe_edge && view.manual_controls)
            fx_presented=vpd::fingerprintHdFxVisual(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row);
        const uint64_t fx_sim_after=hd_fx_probe_edge &&
            view.manual_controls && drawn ? game.fingerprint() : 0;
        if(drawn && hd_sample_frame)
            lit=vpd::sampleGuardImpact(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,pixels_per_row,
                center_x,center_y);
        if(drawn && dust_sample_frame)
            with_dust=vpd::sampleFootstep(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,
                pixels_per_row,heel,ground);
        if(drawn && hostile_sample_frame)
            hostile_lit=vpd::sampleHostileHalo(
                pixels,vpd::kSceneWidth,vpd::kSceneHeight,
                pixels_per_row,hostile_x,hostile_y);
        framebufferEnd(&fb);
        if(!drawn)break;
        if(request_driving_exit && view.driving_stage_preview &&
           driving_stage_exit.requestAfterDrivingFrame(true,true)) {
            const bool manual_exit=(pressed&HidNpadButton_Minus)!=0;
            const bool route_complete=
                vpd::DrivingStageOneConfig::routeProgressComplete(
                    driving_state.frame,driving_state.obstacles_passed);
            (void)vpd::appendDrivingRouteWitness(
                has_sd,driving_route_proof.exitRequest(
                    driving_state,game.fingerprint(),manual_exit,route_complete));
            (void)vpd::appendDrivingExitWitness(
                has_sd,driving_exit_proof.begin(
                    true,driving_state.frame,game.fingerprint()));
        }
        if(hd_fx_sentry_edge && drawn && has_sd &&
           fx_other.pixels==414000 && fx_presented.pixels==414000 &&
           fx_other.hash!=fx_presented.hash &&
           fx_sim_before==fx_sim_after){
            const auto& bullet=hostile_bullets[
                static_cast<unsigned>(hd_fx_sentry_slot)];
            if(auto* report=std::fopen(
                "sdmc:/switch/vice_project_doom/hd_fx_sentry_guest.txt","a")){
                ++hd_fx_sentry_seq;
                if(hd_fx_sentry_seq==2){
                    hd_fx_sentry_tracked_slot=hd_fx_sentry_slot;
                    hd_fx_sentry_on_frame=game.frame();
                    hd_fx_sentry_on_x=bullet.x;
                    hd_fx_sentry_on_y=bullet.y;
                    hd_fx_sentry_on_age=bullet.age;
                    hd_fx_sentry_on_hero_hp=game.playerHealth();
                    hd_fx_sentry_on_hits=game.sentry().shots_hit;
                }
                (void)std::fprintf(report,
                    "VPD_HD_FX_SENTRY_V1 seq=%u mode=%s frame=%u "
                    "manual=1 l=1 r=1 edge=1 "
                    "guard_hp=0 wave=1 sentry_hp=%u hero_hp=%u "
                    "bullet_slot=%u bullet_age=%u bullet_x=%ld bullet_y=%ld "
                    "bullet_vx=%ld sentry_shots=%u stage_clear=0 "
                    "scene_other=%016llx scene_displayed=%016llx "
                    "roi_pixels=%u simulation_before=%016llx "
                    "simulation_after=%016llx "
                    "source=libnx_pad same_frame=yes\n",
                    hd_fx_sentry_seq,hd_effects?"on":"off",game.frame(),
                    static_cast<unsigned>(game.sentry().health),
                    static_cast<unsigned>(game.playerHealth()),
                    static_cast<unsigned>(hd_fx_sentry_slot),
                    static_cast<unsigned>(bullet.age),
                    static_cast<long>(bullet.x),
                    static_cast<long>(bullet.y),
                    static_cast<long>(bullet.vx),
                    static_cast<unsigned>(game.sentry().shots_fired),
                    static_cast<unsigned long long>(fx_other.hash),
                    static_cast<unsigned long long>(fx_presented.hash),
                    fx_presented.pixels,
                    static_cast<unsigned long long>(fx_sim_before),
                    static_cast<unsigned long long>(fx_sim_after));
                std::fclose(report);
            }
        }
        if(hd_fx_combat_edge && view.manual_controls && has_sd &&
           fx_other.pixels==414000 && fx_presented.pixels==414000 &&
           fx_other.hash!=fx_presented.hash &&
           fx_sim_before==fx_sim_after){
            if(auto* report=std::fopen(
                "sdmc:/switch/vice_project_doom/hd_fx_combat_guest.txt","a")){
                ++hd_fx_combat_seq;
                (void)std::fprintf(report,
                    "VPD_HD_FX_COMBAT_V1 seq=%u mode=%s frame=%u "
                    "manual=1 l=1 r=1 edge=1 "
                    "guard_health=%u guard_hits=%u hero_health=%u "
                    "wave_active=0 stage_clear=0 "
                    "scene_other=%016llx scene_displayed=%016llx "
                    "roi_pixels=%u simulation_before=%016llx "
                    "simulation_after=%016llx "
                    "source=libnx_pad same_frame=yes\n",
                    hd_fx_combat_seq,hd_effects?"on":"off",game.frame(),
                    static_cast<unsigned>(game.guardEnemy().health),
                    static_cast<unsigned>(game.guardEnemy().projectile_hits),
                    static_cast<unsigned>(game.playerHealth()),
                    static_cast<unsigned long long>(fx_other.hash),
                    static_cast<unsigned long long>(fx_presented.hash),
                    fx_presented.pixels,
                    static_cast<unsigned long long>(fx_sim_before),
                    static_cast<unsigned long long>(fx_sim_after));
                std::fclose(report);
            }
        }
        if(hd_fx_guest_edge && view.manual_controls && has_sd &&
           fx_other.pixels==414000 && fx_presented.pixels==414000 &&
           fx_other.hash!=fx_presented.hash &&
           fx_sim_before==fx_sim_after){
            if(auto* report=std::fopen(
                "sdmc:/switch/vice_project_doom/hd_fx_toggle_guest.txt","a")){
                ++hd_fx_guest_seq;
                (void)std::fprintf(report,
                    "VPD_HD_FX_GUEST_V2 seq=%u mode=%s frame=%u "
                    "manual=1 l=1 r=1 edge=1 "
                    "scene_other=%016llx scene_displayed=%016llx "
                    "roi_pixels=%u simulation_before=%016llx "
                    "simulation_after=%016llx "
                    "source=libnx_pad same_frame=yes\n",
                    hd_fx_guest_seq,hd_effects?"on":"off",game.frame(),
                    static_cast<unsigned long long>(fx_other.hash),
                    static_cast<unsigned long long>(fx_presented.hash),
                    fx_presented.pixels,
                    static_cast<unsigned long long>(fx_sim_before),
                    static_cast<unsigned long long>(fx_sim_after));
                std::fclose(report);
            }
        }
        if(hostile_sample_frame){
            const unsigned changed=vpd::countHostileHaloChanges(
                hostile_dark,hostile_lit);
            native_hostile_halo_logged=vpd::appendHostileHaloWitness(
                has_sd,game,hostile_slot,hostile_dark,hostile_lit,changed);
        }
        if(dust_sample_frame){
            const unsigned difference=vpd::changedFootstepPixels(
                no_dust,with_dust);
            native_hd_dust_logged=vpd::appendFootstepProof(
                has_sd,game,no_dust,with_dust,difference);
        }
        if(hd_sample_frame){
            const unsigned diff=vpd::diffGuardImpactSamples(unlit,lit);
            native_hd_hit_logged=vpd::appendHitLightEvidence(
                has_sd,game,unlit,lit,diff);
        }
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
        if(manual_retry_has_occurred)
            (void)vpd::manualProofAppendSession(
                has_sd,vpd::ManualProofEvent::Exit,
                7,game,1,manual_session_ticks);
        else
            (void)vpd::manualProofAppend(
                has_sd,vpd::ManualProofEvent::Exit,7,game,1);
    }
    if(we_mounted_sd)fsdevUnmountDevice("sdmc");
    return 0;
}
