#pragma once
#include "driving_source_scroll_review.hpp"
#include <cstdint>

// Stage363: ROM-free MANUAL DEMO, intentionally separate from the verified
// Stage362 SourceScrollReviewGate. This replays *published aggregate numbers*
// only; it NEVER sets source_verified or claims a fresh NES capture.
namespace vpd {
enum class ScrollDemoState : std::uint8_t {
    Off, Preview, LastFrame, GuestTickGap
};
class SourceScrollManualDemo {
public:
    void reset() noexcept {
        enabled_=false; next_=519u; previous_guest_=0u; had_frame_=false;
    }
    bool enabled() const noexcept {return enabled_;}
    std::uint32_t nextPairStart() const noexcept {return next_;}
    bool toggle(bool manual_driving,bool fresh_chord) noexcept {
        if (!manual_driving) { reset();return false; }
        if (!fresh_chord)return false;
        if (enabled_) {reset();return true;}
        reset();enabled_=true;return true;
    }
    ScrollDemoState present(bool manual_driving,std::uint32_t guest_frame,
                            DrivingPreviewView& view) noexcept {
        // Standalone view annotation: NEVER touches speed, road_phase,
        // obstacles, player, HUD, collision or SourceScrollReviewGate.
        view.source_scroll_review_visible=false;
        view.source_scroll_review_demo=false;
        view.source_scroll_review_pair=0;
        view.source_scroll_review_shift=0;
        if (!manual_driving || !enabled_) {
            reset();return ScrollDemoState::Off;
        }
        if (had_frame_ &&
            (previous_guest_==UINT32_MAX || guest_frame!=previous_guest_+1u)) {
            reset();return ScrollDemoState::GuestTickGap;
        }
        const unsigned shift=stage362FiniteShift(next_);
        if(shift==0u) {reset();return ScrollDemoState::Off;}
        view.source_scroll_review_visible=true;
        view.source_scroll_review_demo=true;
        view.source_scroll_review_pair=static_cast<std::uint16_t>(next_);
        view.source_scroll_review_shift=static_cast<std::uint8_t>(shift);
        previous_guest_=guest_frame;had_frame_=true;
        if(next_==559u) {
            // Last observed pair appears for exactly one presentation.
            // Restart requires another explicit real input edge.
            reset();return ScrollDemoState::LastFrame;
        }
        ++next_;
        return ScrollDemoState::Preview;
    }
private:
    bool enabled_=false;
    std::uint32_t next_=519u;
    std::uint32_t previous_guest_=0u;
    bool had_frame_=false;
};
} // namespace vpd
