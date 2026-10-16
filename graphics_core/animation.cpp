#include "animation.hpp"
namespace vpd {
bool validAnimationBank(const AnimationBank& bank) {
    if(bank.atlas_frame_count==0 || bank.atlas_frame_count>4096) return false;
    for(const auto& clip : bank.clips){
        if(!clip.frames || clip.count==0 || clip.count>64) return false;
        for(uint16_t i=0;i<clip.count;++i)
            if(clip.frames[i].ticks==0 || clip.frames[i].ticks>600 ||
               clip.frames[i].atlas_frame>=bank.atlas_frame_count) return false;
    }
    return true;
}
AnimationState selectAnimation(const MotionSample& m) {
    if(!m.grounded) return m.vertical_velocity<0?AnimationState::Rise:AnimationState::Fall;
    return m.moving?AnimationState::Run:AnimationState::Idle;
}
void AnimationPlayer::reset(){
    state_=AnimationState::Idle;
    frame_index_=0;
    ticks_on_frame_=0;
    facing_left_=false;
}
bool AnimationPlayer::tick(const AnimationBank& bank,const MotionSample& motion){
    if(!validAnimationBank(bank))return false;
    if(motion.horizontal_velocity<0)facing_left_=true;
    else if(motion.horizontal_velocity>0)facing_left_=false;
    const AnimationState desired=selectAnimation(motion);
    if(desired!=state_){
        state_=desired;
        frame_index_=0;
        ticks_on_frame_=0;
        return true;
    }
    const AnimationClip& clip=bank.clips[static_cast<unsigned>(state_)];
    if(frame_index_>=clip.count){frame_index_=0;ticks_on_frame_=0;}
    if(++ticks_on_frame_>=clip.frames[frame_index_].ticks){
        ticks_on_frame_=0;
        if(frame_index_+1<clip.count)++frame_index_;
        else if(clip.loop)frame_index_=0;
        else{frame_index_=clip.count-1;ticks_on_frame_=0;}
    }
    return true;
}
uint16_t AnimationPlayer::frame(const AnimationBank& bank)const {
    const unsigned s=static_cast<unsigned>(state_);
    if(s>=4)return 0;
    const AnimationClip& clip=bank.clips[s];
    return clip.frames&&frame_index_<clip.count?clip.frames[frame_index_].atlas_frame:0;
}
}
