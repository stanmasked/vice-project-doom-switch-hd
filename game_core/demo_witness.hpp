#pragma once
// Portable, ROM-free execution witness for Switch homebrew smoke tests.
// A witness confirms the *synthetic game-core state* only, not screen output,
// hardware identity, wall-clock frame pacing, or original Vice gameplay.
#include "combat_demo.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace vpd {
constexpr uint64_t kDemoGoldenFingerprint=5947277116621119566ULL;
constexpr unsigned kDemoWitnessMaxRecords=4;

inline bool demoCheckpointReached(const CombatDemo& demo,
                                  const Simulation& game) {
    return demo.enabled() && demo.nextFrame()==kCombatDemoFrames &&
           game.frame()==kCombatDemoFrames;
}
inline bool demoCheckpointMatches(const Simulation& game) {
    return game.frame()==kCombatDemoFrames &&
           game.shotsFired()==11U &&
           game.trainingTarget().hits==3U &&
           game.trainingTarget().health==0U &&
           game.fingerprint()==kDemoGoldenFingerprint;
}
// Result is bounded and entirely derived from the actual live Simulation.
// The caller must invoke this only AFTER successfully submitting the
// application frame, never during initialization or host compilation.
inline bool writeDemoWitness(std::FILE* output,const Simulation& game,
                             unsigned cycle) {
    if(!output || cycle==0 || cycle>kDemoWitnessMaxRecords ||
       game.frame()!=kCombatDemoFrames)
        return false;
    char buffer[256]{};
    const int used=std::snprintf(
        buffer,sizeof(buffer),
        "VPD_ROMFREE_DEMO_WITNESS_V1 cycle=%u frames=%u shots=%u "
        "hits=%u health=%u fnv=%llu state_match=%s "
        "frame_submitted=yes original_game_proven=no\n",
        cycle,game.frame(),game.shotsFired(),
        static_cast<unsigned>(game.trainingTarget().hits),
        static_cast<unsigned>(game.trainingTarget().health),
        static_cast<unsigned long long>(game.fingerprint()),
        demoCheckpointMatches(game)?"yes":"no");
    if(used<=0 || static_cast<std::size_t>(used)>=sizeof(buffer))
        return false;
    const std::size_t count=static_cast<std::size_t>(used);
    return std::fwrite(buffer,1,count,output)==count &&
           std::fflush(output)==0;
}
} // namespace vpd
