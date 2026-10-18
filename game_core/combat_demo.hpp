#pragma once
// ROM-free authored input script shared by native and host tests.
#include "simulation.hpp"
#include <cstdint>
namespace vpd {
constexpr unsigned kCombatDemoFrames=200;
inline Input combatDemoInput(unsigned frame) {
    if(frame<110U)return Input{Fire};
    if(frame>=115U && frame<145U)return Input{Right};
    if(frame>=145U && frame<175U)
        return Input{static_cast<uint8_t>(Left | (frame<150U ? Jump : 0))};
    return Input{};
}
class CombatDemo {
public:
    bool enabled() const { return enabled_; }
    unsigned nextFrame() const { return next_frame_; }
    void toggle(Simulation& game) {
        enabled_=!enabled_;
        next_frame_=0;
        game.reset();
    }
    bool tick(Simulation& game) {
        if(!enabled_)return false;
        bool restarted=next_frame_==0;
        if(next_frame_==kCombatDemoFrames) {
            game.reset();
            next_frame_=0;
            restarted=true;
        }
        game.tick(combatDemoInput(next_frame_++));
        return restarted;
    }
private:
    bool enabled_=true;
    unsigned next_frame_=0;
};
}
