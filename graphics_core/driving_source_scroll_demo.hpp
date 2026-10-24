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

// Stage367: reason labels are diagnostic state only. They never feed the
// vehicle, road-phase, renderer selection or original-source confidence gate.
enum class ScrollDemoTransitionReason : std::uint8_t {
    Off, Started, FramePresented, ManualExit, ChordCancelled,
    GuestTickGap, UnsupportedPair, SequenceComplete, ExplicitReset
};

class SourceScrollManualDemo {
public:
    void reset(ScrollDemoTransitionReason reason=
                   ScrollDemoTransitionReason::ExplicitReset) noexcept {
        enabled_=false; next_=519u; previous_guest_=0u; had_frame_=false;
        last_reason_=reason;
    }
    bool enabled() const noexcept {return enabled_;}
    std::uint32_t nextPairStart() const noexcept {return next_;}
    ScrollDemoTransitionReason lastTransitionReason() const noexcept {
        return last_reason_;
    }
    bool toggle(bool manual_driving,bool fresh_chord) noexcept {
        if (!manual_driving) {
            reset(ScrollDemoTransitionReason::ManualExit);return false;
        }
        if (!fresh_chord)return false;
        if (enabled_) {
            reset(ScrollDemoTransitionReason::ChordCancelled);return true;
        }
        reset(ScrollDemoTransitionReason::ExplicitReset);
        enabled_=true;
        last_reason_=ScrollDemoTransitionReason::Started;
        return true;
    }
    ScrollDemoState present(bool manual_driving,std::uint32_t guest_frame,
                            DrivingPreviewView& view) noexcept {
        // Standalone view annotation: NEVER touches speed, road_phase,
        // obstacles, player, HUD, collision or SourceScrollReviewGate.
        view.source_scroll_review_visible=false;
        view.source_scroll_review_demo=false;
        view.source_scroll_review_pair=0;
        view.source_scroll_review_shift=0;
        if (!manual_driving) {
            reset(ScrollDemoTransitionReason::ManualExit);
            return ScrollDemoState::Off;
        }
        if (!enabled_) {
            reset(ScrollDemoTransitionReason::Off);
            return ScrollDemoState::Off;
        }
        if (had_frame_ &&
            (previous_guest_==UINT32_MAX || guest_frame!=previous_guest_+1u)) {
            reset(ScrollDemoTransitionReason::GuestTickGap);
            return ScrollDemoState::GuestTickGap;
        }
        const unsigned shift=stage362FiniteShift(next_);
        if(shift==0u) {
            reset(ScrollDemoTransitionReason::UnsupportedPair);
            return ScrollDemoState::Off;
        }
        view.source_scroll_review_visible=true;
        view.source_scroll_review_demo=true;
        view.source_scroll_review_pair=static_cast<std::uint16_t>(next_);
        view.source_scroll_review_shift=static_cast<std::uint8_t>(shift);
        previous_guest_=guest_frame;had_frame_=true;
        if(next_==559u) {
            // Last observed pair appears for exactly one presentation.
            // Restart requires another explicit real input edge.
            reset(ScrollDemoTransitionReason::SequenceComplete);
            return ScrollDemoState::LastFrame;
        }
        ++next_;
        last_reason_=ScrollDemoTransitionReason::FramePresented;
        return ScrollDemoState::Preview;
    }
private:
    bool enabled_=false;
    std::uint32_t next_=519u;
    std::uint32_t previous_guest_=0u;
    bool had_frame_=false;
    ScrollDemoTransitionReason last_reason_=ScrollDemoTransitionReason::Off;
};
} // namespace vpd
