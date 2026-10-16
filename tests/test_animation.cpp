#include "animation.hpp"
#include "demo_animation.hpp"
#include <cstdio>
#include <stdexcept>
#define CHECK(x) do { if(!(x))throw std::runtime_error(#x); } while(0)
int main(){
    const auto& bank=vpd_demo::kAnimationBank;
    CHECK(vpd::validAnimationBank(bank));
    vpd::AnimationPlayer actor;
    CHECK(actor.frame(bank)==0);
    CHECK(actor.state()==vpd::AnimationState::Idle);
    CHECK(vpd::selectAnimation({true,true,0,2})==vpd::AnimationState::Run);
    CHECK(vpd::selectAnimation({false,true,-1,2})==vpd::AnimationState::Rise);
    CHECK(vpd::selectAnimation({false,true,1,0})==vpd::AnimationState::Fall);
    CHECK(actor.tick(bank,{true,true,0,2}));
    CHECK(actor.frame(bank)==1);
    for(int i=0;i<6;++i)CHECK(actor.tick(bank,{true,true,0,2}));
    CHECK(actor.frame(bank)==2);
    for(int i=0;i<8;++i)CHECK(actor.tick(bank,{true,true,0,-2}));
    CHECK(actor.frame(bank)==1);
    CHECK(actor.facingLeft());
    CHECK(actor.tick(bank,{false,true,-5,-2}));
    CHECK(actor.state()==vpd::AnimationState::Rise && actor.frame(bank)==3);
    CHECK(actor.tick(bank,{false,true,0,0}));
    CHECK(actor.state()==vpd::AnimationState::Fall && actor.frame(bank)==3);
    for(int i=0;i<20;++i)CHECK(actor.tick(bank,{false,false,3,0}));
    CHECK(actor.frameIndex()==0); // non-looping fall holds last pose
    CHECK(actor.facingLeft());   // retained facing while airborne
    CHECK(actor.tick(bank,{true,false,0,0}));
    CHECK(actor.state()==vpd::AnimationState::Idle&&actor.frame(bank)==0);
    CHECK(actor.tick(bank,{true,true,0,2}));
    CHECK(!actor.facingLeft()&&actor.frame(bank)==1);
    actor.reset();
    CHECK(!actor.facingLeft()&&actor.frameIndex()==0);
    auto invalid=bank;
    invalid.clips[1].frames=nullptr;
    CHECK(!vpd::validAnimationBank(invalid));
    CHECK(!actor.tick(invalid,{true,true,0,2}));
    vpd::AnimationFrame invalid_frame[]={{99,0}};
    invalid=bank;
    invalid.clips[2]={invalid_frame,1,false};
    CHECK(!vpd::validAnimationBank(invalid));
    invalid_frame[0]={3,0};
    CHECK(!vpd::validAnimationBank(invalid));
    puts("PASS: data-driven animation, authored durations, state resets, facing and guards");
}
