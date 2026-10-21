// Stand-alone ROM-free validation of the original game's measured transition.
#include "stage_transition.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace vpd::stage_transition;

int main() {
    Timeline sequence;
    for (std::uint32_t f = 0; f <= kOriginalLastDrivingFrame; ++f) {
        assert(sequence.present() == Scene::Driving);
    }
    assert(sequence.requestExit());
    assert(!sequence.requestExit());
    for (std::uint32_t f = kOriginalFirstBlackFrame;
         f <= kOriginalLastBlackFrame; ++f) {
        assert(sequence.present() == Scene::Black);
        assert(sequence.presentedBlackFrames() == f - kOriginalFirstBlackFrame + 1);
        assert(sequence.remainingBlackFrames() == kOriginalLastBlackFrame - f);
        assert(!sequence.requestExit());
    }
    assert(sequence.presentedBlackFrames() == 41);
    assert(sequence.present() == Scene::Platform);
    assert(sequence.nextScene() == Scene::Platform);
    assert(!sequence.requestExit());
    for (int n = 0; n < 100; ++n) assert(sequence.present() == Scene::Platform);

    Timeline replay;
    for (std::uint32_t f = 0; f <= kOriginalLastDrivingFrame; ++f)
        assert(replay.present() == Scene::Driving);
    assert(replay.requestExit());
    for (std::uint32_t f = kOriginalFirstBlackFrame;
         f <= kOriginalLastBlackFrame; ++f)
        assert(replay.present() == Scene::Black);
    assert(replay.present() == Scene::Platform);
    assert(replay.presentedBlackFrames() == sequence.presentedBlackFrames());

    sequence.reset();
    assert(sequence.nextScene() == Scene::Driving);
    assert(sequence.presentedBlackFrames() == 0);
    assert(sequence.remainingBlackFrames() == 0);
    assert(sequence.present() == Scene::Driving);
    assert(sequence.requestExit());
    for (std::uint32_t n = 0; n < kBlackFrames; ++n)
        assert(sequence.present() == Scene::Black);
    assert(sequence.present() == Scene::Platform);

    std::cout << "VPD_ORIGINAL_STAGE_TRANSITION_TIMING_CONTRACT_PASS"
              << " last_driving=3606 first_black=3607 last_black=3647"
              << " first_platform=3648 black_frames=41"
              << " source_pixels_included=no source_fm2_included=no"
              << " gameplay_integration_proven=no\n";
}
