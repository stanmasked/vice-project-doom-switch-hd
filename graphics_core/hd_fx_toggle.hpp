#pragma once
// Lightweight visual-only runtime switch for self-authored HD effects.
// No simulation state, wall clock, original NES assets or libnx dependency.
namespace vpd {
struct HdFxRuntimeMode {
    bool enabled=true; // existing manual-mode appearance remains default
    // Return true while the L+R chord belongs to the visual-effects
    // switch, suppressing independent L reload/R backdrop reset.
    bool acceptShoulders(bool manual,bool l_down,bool r_down,
                         bool l_pressed,bool r_pressed){
        if(!manual || !l_down || !r_down)return false;
        if(l_pressed || r_pressed)enabled=!enabled;
        return true;
    }
    bool activeForGameplay(bool manual) const {
        return manual && enabled;
    }
};
} // namespace vpd
