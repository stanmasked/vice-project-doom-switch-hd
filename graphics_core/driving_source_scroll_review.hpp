#pragma once
#include "driving_preview.hpp"
#include <cstdint>

// Stage362: ROM-free finite source-scroll review bridge only.
// These 41 numeric source witness edges are an observational lookup, never
// inferred NES camera/vehicle mechanics. Default preview remains untouched.
// Real original-source provenance belongs to owner-private analysis; a
// source_verified flag alone cannot authenticate a ROM capture.
namespace vpd {

enum class SourceScrollTier : std::uint8_t {
    StrictFour, QualifiedThree, ArchivedQualifiedUnknown,
    ImageInconclusive, MaskConflict
};
enum class SourceScrollReviewStatus : std::uint8_t {
    Off, Accepted, DisabledSource, WrongFrame, UnsupportedMode,
    RegisterMissing, RegisterMismatch, NonDiscriminatingImage,
    UnqualifiedSource, UnverifiedSource, NonContiguous
};

struct SourceScrollPairWitness {
    std::uint32_t original_pair_start=0;
    int observed_rgb_shift_px=0;
    int first_ppu_y_signed_mod240_step=0;
    SourceScrollTier tier=SourceScrollTier::ImageInconclusive;
    bool source_verified=false;
    bool first_cpu_2005_y_verified=false;
    bool native_ppu_line0_verified=false;
    bool discriminating_rgb=true;
};

struct SourceScrollReviewResult {
    DrivingPreviewView preview{}; // cloned, never mutates Road/DrivingState.
    SourceScrollReviewStatus status=SourceScrollReviewStatus::Off;
    bool original_source_pixel_art_used=false;
    bool physics_proven=false;
    bool has_observed_shift=false;
    std::uint32_t original_pair_start=0;
    unsigned cumulative_observed_image_px=0;
    std::uint8_t observed_shift_px=0;
};

// Only the three finite observed numeric modes from Stage361, never
// extrapolated past pair start 559. Not a new source authenticator.
constexpr unsigned stage362FiniteShift(std::uint32_t start) noexcept {
    return start>=519u && start<=526u ? 3u :
           start>=527u && start<=558u ? 4u :
           start==559u ? 5u : 0u;
}

class SourceScrollReviewGate {
public:
    void reset() noexcept {next_=519u;cumulative_=0u;active_=false;}
    SourceScrollReviewGate() noexcept {reset();}
    bool active() const noexcept {return active_;}
    std::uint32_t nextExpectedPair() const noexcept {return next_;}
    unsigned cumulativeObservedImagePx() const noexcept {return cumulative_;}
    SourceScrollReviewResult observe(
            bool manual_review_enabled,
            const DrivingPreviewView& live_preview,
            const SourceScrollPairWitness& source) noexcept {
        SourceScrollReviewResult out{};
        out.preview=live_preview;
        if(!manual_review_enabled) {
            reset();
            return out; // OFF never draws or changes guest road/HUD.
        }
        auto fail=[&](SourceScrollReviewStatus status) noexcept {
            reset();
            out.status=status;
            return out;
        };
        // "Manual only" here means explicitly opt-in by caller. Merely
        // constructing the adapter cannot switch the runtime's source.
        if(source.original_pair_start<519u || source.original_pair_start>559u)
            return fail(SourceScrollReviewStatus::WrongFrame);
        if(source.original_pair_start!=next_)
            return fail(SourceScrollReviewStatus::NonContiguous);
        if(!source.source_verified)
            return fail(SourceScrollReviewStatus::UnverifiedSource);
        if(!source.first_cpu_2005_y_verified ||
           !source.native_ppu_line0_verified)
            return fail(SourceScrollReviewStatus::RegisterMissing);
        if(source.tier==SourceScrollTier::ImageInconclusive ||
           source.tier==SourceScrollTier::MaskConflict)
            return fail(SourceScrollReviewStatus::UnqualifiedSource);
        if(!source.discriminating_rgb)
            return fail(SourceScrollReviewStatus::NonDiscriminatingImage);
        const unsigned expected=stage362FiniteShift(source.original_pair_start);
        if(expected==0u || source.observed_rgb_shift_px!=static_cast<int>(expected))
            return fail(SourceScrollReviewStatus::UnsupportedMode);
        if(source.first_ppu_y_signed_mod240_step !=
           -source.observed_rgb_shift_px)
            return fail(SourceScrollReviewStatus::RegisterMismatch);
        const bool archive_summary_only=
            (source.original_pair_start>=520u &&
             source.original_pair_start<=543u) ||
            (source.original_pair_start>=545u &&
             source.original_pair_start<=558u);
        if(source.tier==SourceScrollTier::ArchivedQualifiedUnknown &&
           !archive_summary_only)
            return fail(SourceScrollReviewStatus::UnqualifiedSource);
        // Historical source summary does not expose per-pair 4/4/3/4.
        // The unknown tier is permitted only for those archived intervals.
        // Strict/3/4 can be passed for fabricated standalone tests, but does
        // not turn a test into an independently verified original event.
        cumulative_+=expected;
        ++next_;
        active_=true;
        out.status=SourceScrollReviewStatus::Accepted;
        out.has_observed_shift=true;
        out.original_pair_start=source.original_pair_start;
        out.observed_shift_px=static_cast<std::uint8_t>(expected);
        out.cumulative_observed_image_px=cumulative_;
        // Separate, visually bounded ROM-free overlay, never road_phase.
        out.preview.source_scroll_review_visible=true;
        out.preview.source_scroll_review_pair=
            static_cast<std::uint16_t>(source.original_pair_start);
        out.preview.source_scroll_review_shift=
            static_cast<std::uint8_t>(expected);
        return out;
    }
private:
    std::uint32_t next_=519u;
    unsigned cumulative_=0u;
    bool active_=false;
};

} // namespace vpd
