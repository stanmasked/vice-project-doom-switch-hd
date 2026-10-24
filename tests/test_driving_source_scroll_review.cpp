#include "driving_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

// Synthetic-only guest/raster witness. This never loads a NES ROM/movie,
// original source raster or raw CPU/PPU records.
namespace {
void check(bool ok,const char* message) {
    if(!ok)throw std::runtime_error(message);
}
using vpd::SourceScrollTier;
using vpd::SourceScrollPairWitness;
using vpd::SourceScrollReviewStatus;
SourceScrollPairWitness fabricated(std::uint32_t start) {
    SourceScrollPairWitness w{};
    w.original_pair_start=start;
    const unsigned shift=vpd::stage362FiniteShift(start);
    w.observed_rgb_shift_px=static_cast<int>(shift);
    w.first_ppu_y_signed_mod240_step=-static_cast<int>(shift);
    w.tier=(start==519||start==544||start==559)
        ?SourceScrollTier::StrictFour:SourceScrollTier::ArchivedQualifiedUnknown;
    w.source_verified=true;
    w.first_cpu_2005_y_verified=true;
    w.native_ppu_line0_verified=true;
    w.discriminating_rgb=true;
    return w;
}

std::uint64_t hashRows(const std::vector<std::uint32_t>& image,
                       int width,int first,int last) {
    std::uint64_t h=14695981039346656037ull;
    for(int y=first;y<last;++y)
        for(int x=0;x<width;++x) {
            const std::uint32_t pix=image[static_cast<std::size_t>(y)*width+x];
            for(int byte=0;byte<4;++byte) {
                h^=(pix>>(byte*8))&255u;
                h*=1099511628211ull;
            }
        }
    return h;
}
}

int main() {
    using namespace vpd;
    check(stage362FiniteShift(518)==0 && stage362FiniteShift(519)==3 &&
          stage362FiniteShift(526)==3 && stage362FiniteShift(527)==4 &&
          stage362FiniteShift(558)==4 && stage362FiniteShift(559)==5 &&
          stage362FiniteShift(560)==0,
          "finite original-source image mode boundary changed");
    DrivingState guest;
    guest.road_phase=19;
    guest.speed=6;
    guest.car_x=657;
    guest.frame=40;
    const auto snapshot=guest;
    SourceScrollReviewGate gate;
    check(!gate.active() && gate.nextExpectedPair()==519,
          "fresh review must be off");

    const auto disabled=makeDrivingSceneSourceScrollReview(
        guest,gate,false,fabricated(519));
    check(disabled.status==SourceScrollReviewStatus::Off &&
          !disabled.has_observed_shift && !disabled.preview.source_scroll_review_visible &&
          disabled.preview.road_phase==guest.road_phase && !gate.active(),
          "default road scene or source gate mutated by disabled mode");

    auto missing=fabricated(519);
    missing.first_cpu_2005_y_verified=false;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::RegisterMissing && !gate.active(),
          "missing original CPU first write promoted to camera movement");
    missing=fabricated(519);
    missing.native_ppu_line0_verified=false;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::RegisterMissing,
          "missing native PPU line0 evidence promoted");
    missing=fabricated(519);
    missing.source_verified=false;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::UnverifiedSource,
          "unverified original source promoted");
    missing=fabricated(519);
    missing.discriminating_rgb=false;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::NonDiscriminatingImage,
          "flat or identical original source promoted");
    missing=fabricated(519);
    missing.tier=SourceScrollTier::MaskConflict;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::UnqualifiedSource,
          "conflicting RGB regions promoted");
    missing=fabricated(519);
    missing.tier=SourceScrollTier::ImageInconclusive;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::UnqualifiedSource,
          "inconclusive original source promoted");
    missing=fabricated(519);
    missing.first_ppu_y_signed_mod240_step=-4;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::RegisterMismatch,
          "original source first-Y contradiction promoted");
    missing=fabricated(519);
    missing.observed_rgb_shift_px=4;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::UnsupportedMode,
          "unobserved mode invented at original frame 519");
    missing=fabricated(519);
    missing.tier=SourceScrollTier::ArchivedQualifiedUnknown;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,missing).status==
          SourceScrollReviewStatus::UnqualifiedSource,
          "boundary mandatory strict tier replaced by aggregate guess");
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(520)).status==
          SourceScrollReviewStatus::NonContiguous,
          "first observed frame skipped via implicit lookahead");
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(560)).status==
          SourceScrollReviewStatus::WrongFrame,
          "post-559 original frame predicted");

    constexpr int width=kDrivingPreviewWidth;
    constexpr int height=kDrivingPreviewHeight;
    std::vector<std::uint32_t> normal(static_cast<std::size_t>(width)*height);
    std::vector<std::uint32_t> active(normal.size());
    auto base=makeDrivingSceneView(guest);
    check(drawDrivingPreview(normal.data(),width,height,width,base),
          "synthetic default driving preview draw failed");
    const std::uint64_t normalRoad=hashRows(normal,width,0,kDrivingHudTop);
    const std::uint64_t normalHud=hashRows(normal,width,kDrivingHudTop,height);

    unsigned expectedSum=0;
    for(std::uint32_t frame=519;frame<=559;++frame) {
        const auto w=fabricated(frame);
        guest.frame+=1;
        const auto observed=makeDrivingSceneSourceScrollReview(
            guest,gate,true,w);
        expectedSum+=stage362FiniteShift(frame);
        check(observed.status==SourceScrollReviewStatus::Accepted &&
              observed.has_observed_shift &&
              observed.observed_shift_px==stage362FiniteShift(frame) &&
              observed.original_pair_start==frame &&
              observed.cumulative_observed_image_px==expectedSum &&
              observed.preview.source_scroll_review_visible &&
              observed.preview.source_scroll_review_pair==frame &&
              observed.preview.source_scroll_review_shift==stage362FiniteShift(frame) &&
              observed.preview.frame==guest.frame &&
              observed.preview.road_phase==guest.road_phase &&
              observed.preview.speed==guest.speed &&
              observed.preview.car_x==guest.car_x &&
              !observed.physics_proven && !observed.original_source_pixel_art_used,
              "guest bridge did not preserve exact source and game-core separation");
        if(frame==519) {
            check(drawDrivingPreview(active.data(),width,height,width,observed.preview),
                  "opt-in synthetic source numeric overlay not rendered");
            check(hashRows(active,width,0,kDrivingHudTop)!=normalRoad &&
                  hashRows(active,width,kDrivingHudTop,height)!=normalHud ? false :
                  hashRows(active,width,kDrivingHudTop,height)==normalHud,
                  "Stage362 source review mutated speed/health/timer HUD");
            auto equivalent=makeDrivingSceneView(guest);
            check(drawDrivingPreview(normal.data(),width,height,width,equivalent),
                  "baseline review comparison draw failed");
            check(hashRows(active,width,0,kDrivingHudTop)!=
                  hashRows(normal,width,0,kDrivingHudTop) &&
                  hashRows(active,width,kDrivingHudTop,height)==
                  hashRows(normal,width,kDrivingHudTop,height),
                  "review overlay did not remain strictly confined to invented road pixels");
        }
    }
    check(expectedSum==157 && gate.active() && gate.nextExpectedPair()==560,
          "41 finite original-source image observations did not total 157 px");
    const auto prior=guest.road_phase;
    guest.frame+=1;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(560)).status==
          SourceScrollReviewStatus::WrongFrame && !gate.active(),
          "out of bounds original frame accepted or review not reset");
    check(guest.road_phase==prior && guest.speed==snapshot.speed &&
          guest.car_x==snapshot.car_x && guest.health==snapshot.health,
          "observed source-scroll adapter illegally modified simulated car");

    gate.reset();
    guest.frame=100;
    const auto one=makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(519));
    check(one.status==SourceScrollReviewStatus::Accepted,
          "manual review could not restart from first witnessed pair");
    // Same source ID must not be accepted twice.
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(519)).status==
          SourceScrollReviewStatus::NonContiguous && !gate.active(),
          "duplicate source pair silently replayed");
    guest.frame=101;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(519)).status==
          SourceScrollReviewStatus::Accepted,
          "explicit restarted source sequence failed");
    // Guest view frame must progress even though original witness advances.
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(520)).status==
          SourceScrollReviewStatus::NonContiguousGuestTick && !gate.active(),
          "duplicated guest-frame capture allowed as a new observed source state");
    guest.frame=102;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,fabricated(519)).status==
          SourceScrollReviewStatus::Accepted,"manual reviewer failed after rejected tick");
    auto wrong=fabricated(521);
    guest.frame=103;
    check(makeDrivingSceneSourceScrollReview(guest,gate,true,wrong).status==
          SourceScrollReviewStatus::NonContiguous && !gate.active(),
          "skipping original source pair allowed");
    auto off=makeDrivingSceneSourceScrollReview(guest,gate,false,fabricated(519));
    check(off.status==SourceScrollReviewStatus::Off &&
          !off.preview.source_scroll_review_visible && !gate.active(),
          "opt-out did not clear source visual marker");

    std::cout<<"VPD_STAGE362_ROMFREE_GUEST_SCROLL_EVIDENCE_REVIEW_PASS "
             <<"finite_pairs=41 observed_px_sum=157 real_original_game_pixels=0 "
             <<"new_original_capture=0 guest_road_phase_unchanged=1 "
             <<"default_review_off=1 negative_guards=1 hud_unchanged=1 "
             <<"game_vehicle_camera_physics_proven=0\n";
}
