#include "driving_source_scroll_demo.hpp"
#include "driving_source_scroll_demo_guest.hpp"
#include "driving_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

static void require(bool x,const char* msg) {
    if(!x)throw std::runtime_error(msg);
}
static std::uint64_t regionFingerprint(const std::vector<std::uint32_t>& p,
                                       int y0,int y1) {
    std::uint64_t h=14695981039346656037ull;
    for(int y=y0;y<y1;++y)
        for(int x=0;x<vpd::kDrivingPreviewWidth;++x) {
            const auto value=p[static_cast<std::size_t>(y)*
                vpd::kDrivingPreviewWidth+x];
            for(unsigned b=0;b<4;++b) {
                h^=(value>>(b*8u))&255u;
                h*=1099511628211ull;
            }
        }
    return h;
}
int main() {
    using namespace vpd;
    constexpr int w=kDrivingPreviewWidth,h=kDrivingPreviewHeight;
    const std::size_t len=static_cast<std::size_t>(w)*h;
    std::vector<std::uint32_t> baseline(len),demoPixels(len);
    DrivingState state{};
    SourceScrollManualDemo ctrl{};
    require(!ctrl.enabled() && ctrl.nextPairStart()==519,
            "numeric source replay DEMO must default OFF");
    auto disabled=makeDrivingSceneView(state);
    require(ctrl.present(false,state.frame,disabled)==ScrollDemoState::Off &&
            !disabled.source_scroll_review_visible && !disabled.source_scroll_review_demo,
            "unrequested scroll witness erroneously enabled");
    require(!ctrl.toggle(false,true) && !ctrl.enabled(),
            "autoplay or platform view enabled manual review");
    require(!ctrl.toggle(true,false),"held buttons without fresh edge enabled review");
    require(ctrl.toggle(true,true) && ctrl.enabled(),"manual DEMO edge was ignored");
    std::uint32_t firstGuest=0;
    unsigned total=0;
    for(unsigned i=0;i<41;++i) {
        ++state.frame;
        auto actual=makeDrivingSceneView(state);
        auto normal=makeDrivingSceneView(state);
        const auto status=ctrl.present(true,state.frame,actual);
        require(status==(i==40?ScrollDemoState::LastFrame:ScrollDemoState::Preview),
                "missing or duplicate numerical pair in ROM-free manual DEMO");
        const unsigned sourceFrame=519u+i;
        require(actual.source_scroll_review_demo &&
                actual.source_scroll_review_visible &&
                actual.source_scroll_review_pair==sourceFrame &&
                actual.source_scroll_review_shift==stage362FiniteShift(sourceFrame),
                "fabricated DEMO has wrong previously published original aggregate number");
        total+=stage362FiniteShift(sourceFrame);
        require(actual.frame==normal.frame &&
                actual.speed==normal.speed && actual.health==normal.health &&
                actual.road_phase==normal.road_phase &&
                actual.car_x==normal.car_x &&
                actual.obstacle_y==normal.obstacle_y,
                "manual view affected invented vehicle state or road-phase");
        require(drawDrivingPreview(baseline.data(),w,h,w,normal) &&
                drawDrivingPreview(demoPixels.data(),w,h,w,actual),
                "ROM-free HDR/GPU host road frame did not draw");
        require(regionFingerprint(baseline,kDrivingHudTop,h)==
                regionFingerprint(demoPixels,kDrivingHudTop,h),
                "manual source numerical DEMO changed original synthetic HUD");
        require(regionFingerprint(baseline,0,kDrivingHudTop)!=
                regionFingerprint(demoPixels,0,kDrivingHudTop),
                "manual DEMO did not paint bounded numeric road-area panel");
        const auto proof=inspectScrollDemoRaster(
            true,true,i==0,status,actual,demoPixels.data(),w,12345);
        require(proof.valid && proof.last==(i==40) &&
                proof.original_pair_start==sourceFrame &&
                proof.guest_frame==state.frame &&
                proof.image_shift==stage362FiniteShift(sourceFrame) &&
                proof.simulation_fingerprint==12345,
                "synthetic host framebuffer failed per-frame Stage365 raster witness");
        if(i==0)firstGuest=proof.guest_frame;
        auto bad=demoPixels;
        bad[270*w+1040]^=1u;
        require(!inspectScrollDemoRaster(true,true,i==0,status,actual,
                                         bad.data(),w,12345).valid,
                "incorrect framebuffer pixel manufactured a verified demo event");
    }
    require(total==157 && !ctrl.enabled() && ctrl.nextPairStart()==519 &&
            firstGuest==1,
            "source numeric demo did not end after exactly 41 finite observed pairs");
    auto last=makeDrivingSceneView(state);
    require(ctrl.present(true,state.frame,last)==ScrollDemoState::Off &&
            !last.source_scroll_review_demo,
            "DEM0 overlay persisted beyond supported original numerical interval");
    // If the NRO drops a render tick, the demo must not interpolate original
    // pairs to paper over missing frames; only a new explicit chord can restart.
    require(ctrl.toggle(true,true),"could not restart manual demo");
    state.frame=51;
    auto restart=makeDrivingSceneView(state);
    require(ctrl.present(true,51,restart)==ScrollDemoState::Preview,"restart failed");
    state.frame=53;
    auto dropped=makeDrivingSceneView(state);
    require(ctrl.present(true,53,dropped)==ScrollDemoState::GuestTickGap &&
            !ctrl.enabled() && !dropped.source_scroll_review_visible,
            "guest dropped tick was extrapolated");
    require(ctrl.toggle(true,true),"cannot manually enable after guest skip");
    state.frame=90;
    restart=makeDrivingSceneView(state);
    require(ctrl.present(true,90,restart)==ScrollDemoState::Preview,"reset restart failed");
    dropped=makeDrivingSceneView(state);
    require(ctrl.present(true,90,dropped)==ScrollDemoState::GuestTickGap &&
            !ctrl.enabled(),"repeat guest frame replayed fake source transition");
    require(ctrl.toggle(true,true),"unable to restart demo after rejection");
    state.frame=99;
    restart=makeDrivingSceneView(state);
    require(ctrl.present(true,99,restart)==ScrollDemoState::Preview,"restart after repeat failed");
    require(ctrl.toggle(true,true) && !ctrl.enabled(),
            "fresh chord cannot disable diagnostic mode");
    dropped=makeDrivingSceneView(state);
    require(ctrl.present(true,99,dropped)==ScrollDemoState::Off &&
            !dropped.source_scroll_review_demo,
            "OFF chord leaked synthetic graphic marker");
    require(ctrl.toggle(true,true),"manual input missed");
    ctrl.reset();
    require(!ctrl.enabled() && ctrl.nextPairStart()==519,"exit did not reset");
    // Stage366: leaving the manual driving view pauses/exits the DEMO.
    // Resuming without a fresh chord must not replay an old sequence edge.
    ctrl.reset();
    require(ctrl.toggle(true,true),"manual-exit lifecycle DEMO did not start");
    state.frame=200;
    auto lifecycleStart=makeDrivingSceneView(state);
    require(ctrl.present(true,200,lifecycleStart)==ScrollDemoState::Preview &&
            lifecycleStart.source_scroll_review_pair==519,
            "lifecycle start did not begin at the first supported pair");
    state.frame=201;
    auto manualExit=makeDrivingSceneView(state);
    require(ctrl.present(false,201,manualExit)==ScrollDemoState::Off &&
            !ctrl.enabled() && ctrl.nextPairStart()==519 &&
            !manualExit.source_scroll_review_visible,
            "leaving manual driving did not clear the paused DEMO");
    require(!ctrl.toggle(true,false) && !ctrl.enabled(),
            "DEMO resumed without a fresh controller edge");
    require(ctrl.toggle(true,true) && ctrl.enabled(),
            "fresh controller edge did not re-arm DEMO after manual exit");
    state.frame=202;
    auto lifecycleRestart=makeDrivingSceneView(state);
    require(ctrl.present(true,202,lifecycleRestart)==ScrollDemoState::Preview &&
            lifecycleRestart.source_scroll_review_pair==519,
            "fresh re-arm did not restart at pair 519");
    state.frame=203;
    auto lifecycleNext=makeDrivingSceneView(state);
    require(ctrl.present(true,203,lifecycleNext)==ScrollDemoState::Preview &&
            lifecycleNext.source_scroll_review_pair==520,
            "restarted sequence did not advance contiguously");
    require(ctrl.toggle(true,true) && !ctrl.enabled(),
            "fresh chord did not cancel an active restarted DEMO");
    state.frame=204;
    auto lifecycleStopped=makeDrivingSceneView(state);
    require(ctrl.present(true,204,lifecycleStopped)==ScrollDemoState::Off &&
            !lifecycleStopped.source_scroll_review_visible,
            "cancelled DEMO leaked its overlay into a later frame");

    // Default scene renderer remains identical when no manual review.
    SceneView scene{};
    scene.driving_stage_preview=true;
    scene.driving=makeDrivingSceneView(state);
    require(drawScene(baseline.data(),w,h,w,scene),"normal shared scene failed");
    require(!scene.driving.source_scroll_review_demo &&
            !scene.driving.source_scroll_review_visible,
            "default NRO scene enabled opt-in diagnostic without chord");
    require(!inspectScrollDemoRaster(
            true,true,true,ScrollDemoState::Preview,scene.driving,
            baseline.data(),w,12345).valid,
            "normal game frame incorrectly attested a DEMO pixel");
    std::cout<<"VPD_STAGE366_ROMFREE_MANUAL_SCROLL_DEMO_LIFECYCLE_PASS "
             <<"observed_numeric_pairs=41 sum=157 "
             <<"panel_and_demo_glyph=1 disabled_by_default=1 "
             <<"guest_skip_rejected=1 guest_duplicate_rejected=1 pause_exit_restart=1 fresh_edge_required=1 "
             <<"HUD_and_driving_road_phase_unchanged=1 "
             <<"actual_NeXium_full_guest_sequence_proven=0 "
             <<"original_ROM_FM2_PPU_source_replayed=0\n";
}
