// Stand-alone ROM-free validation of the original game's measured transition.
#include "stage_transition.hpp"
#include <stdexcept>
#include <cstdint>
#include <iostream>
using namespace vpd::stage_transition;

void require(bool result) {
    if (!result) throw std::runtime_error("transition timing invariant failed");
}

int main() {
    Timeline sequence;
    for (std::uint32_t f = 0; f <= kOriginalLastDrivingFrame; ++f) {
        require(sequence.present() == Scene::Driving);
    }
    require(sequence.requestExit());
    require(!sequence.requestExit());
    for (std::uint32_t f = kOriginalFirstBlackFrame;
         f <= kOriginalLastBlackFrame; ++f) {
        require(sequence.present() == Scene::Black);
        require(sequence.presentedBlackFrames() == f - kOriginalFirstBlackFrame + 1);
        require(sequence.remainingBlackFrames() == kOriginalLastBlackFrame - f);
        require(!sequence.requestExit());
    }
    require(sequence.presentedBlackFrames() == 41);
    require(sequence.present() == Scene::Platform);
    require(sequence.nextScene() == Scene::Platform);
    require(!sequence.requestExit());
    for (int n = 0; n < 100; ++n) require(sequence.present() == Scene::Platform);

    Timeline replay;
    for (std::uint32_t f = 0; f <= kOriginalLastDrivingFrame; ++f)
        require(replay.present() == Scene::Driving);
    require(replay.requestExit());
    for (std::uint32_t f = kOriginalFirstBlackFrame;
         f <= kOriginalLastBlackFrame; ++f)
        require(replay.present() == Scene::Black);
    require(replay.present() == Scene::Platform);
    require(replay.presentedBlackFrames() == sequence.presentedBlackFrames());

    sequence.reset();
    require(sequence.nextScene() == Scene::Driving);
    require(sequence.presentedBlackFrames() == 0);
    require(sequence.remainingBlackFrames() == 0);
    require(sequence.present() == Scene::Driving);
    require(sequence.requestExit());
    for (std::uint32_t n = 0; n < kBlackFrames; ++n)
        require(sequence.present() == Scene::Black);
    require(sequence.present() == Scene::Platform);

    std::cout << "VPD_ORIGINAL_STAGE_TRANSITION_TIMING_CONTRACT_PASS"
              << " last_driving=3606 first_black=3607 last_black=3647"
              << " first_platform=3648 black_frames=41"
              << " source_pixels_included=no source_fm2_included=no"
              << " gameplay_integration_proven=no\n";
}
