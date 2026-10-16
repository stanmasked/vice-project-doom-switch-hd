#pragma once
#include <cstddef>
#include <cstdint>
namespace vpd {
// Animator is independent of gameplay/renderer, uses ticks not wall-clock time.
// Values in demo manifest are author-selected placeholders, not original timings.
enum class AnimationState : uint8_t { Idle=0, Run=1, Rise=2, Fall=3 };
struct AnimationFrame { uint16_t atlas_frame; uint16_t ticks; };
struct AnimationClip { const AnimationFrame* frames; uint16_t count; bool loop; };
struct AnimationBank { AnimationClip clips[4]; uint16_t atlas_frame_count; };
struct MotionSample {
    bool grounded=true;
    bool moving=false;
    int32_t vertical_velocity=0;
    int32_t horizontal_velocity=0;
};
class AnimationPlayer {
public:
    bool tick(const AnimationBank& bank, const MotionSample& motion);
    void reset();
    AnimationState state() const { return state_; }
    uint16_t frame(const AnimationBank& bank) const;
    bool facingLeft() const { return facing_left_; }
    uint16_t frameIndex() const { return frame_index_; }
    uint16_t ticksOnFrame() const { return ticks_on_frame_; }
private:
    AnimationState state_=AnimationState::Idle;
    uint16_t frame_index_=0;
    uint16_t ticks_on_frame_=0;
    bool facing_left_=false;
};
bool validAnimationBank(const AnimationBank& bank);
AnimationState selectAnimation(const MotionSample& motion);
}
