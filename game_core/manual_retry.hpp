#pragma once
// One deliberate restart action for the two terminal manual-play outcomes.
// The exact same clean initialization path is used for both reasons.
// No original ROM, game resources or Switch SDK dependencies.
#include "simulation.hpp"
#include <cstdint>
namespace vpd {
enum class ManualRetryOutcome : uint8_t {
    Ignored=0, AfterDefeat=1, AfterVictory=2
};
inline ManualRetryOutcome retryTerminalEncounter(Simulation& game,
                                                 bool minus_pressed) {
    if(!minus_pressed || !game.enemyEncounterEnabled())
        return ManualRetryOutcome::Ignored;
    ManualRetryOutcome result=ManualRetryOutcome::Ignored;
    if(game.stageCleared())result=ManualRetryOutcome::AfterVictory;
    else if(game.playerHealth()==0)
        result=ManualRetryOutcome::AfterDefeat;
    if(result==ManualRetryOutcome::Ignored)
        return result;
    game.reset();
    game.enableEnemyEncounter();
    return result;
}
} // namespace vpd
