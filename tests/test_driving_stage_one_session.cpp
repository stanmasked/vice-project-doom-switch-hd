#include "driving_stage_one_session.hpp"
#include <iostream>
#include <stdexcept>

static void check(bool ok,const char* why) {
    if(!ok) throw std::runtime_error(why);
}

int main() {
    using Session=vpd::DrivingStageOneSession;
    Session session;
    check(session.mode()==Session::Mode::Driving,"session did not start in driving mode");
    const auto first=session.state();
    session.tick({false,false,true,false});
    check(session.state().frame==first.frame+1 && session.state().speed==4,
          "driving input did not advance session simulation");
    check(session.presentFrame()==Session::Mode::Driving,
          "session left driving mode without a completion event");

    // A known collision fixture must enter defeat, freeze, and restart cleanly.
    vpd::DrivingState fatal;
    fatal.health=1;
    fatal.obstacle_x=fatal.car_x;
    fatal.obstacle_y=433;
    Session defeated(fatal);
    defeated.tick({});
    check(defeated.mode()==Session::Mode::Defeated,
          "fatal collision did not enter defeated mode");
    const auto deadFrame=defeated.state().frame;
    defeated.tick({false,true,true,false});
    check(defeated.state().frame==deadFrame &&
          defeated.state().health==0,
          "defeated session advanced without restart");
    defeated.tick({},false,true);
    check(defeated.mode()==Session::Mode::Driving &&
          defeated.state().health==5 && defeated.state().frame==0,
          "restart did not restore initial driving state");

    Session finish;
    finish.tick({},true);
    check(finish.mode()==Session::Mode::Transition,
          "explicit finish event did not start transition");
    check(finish.presentFrame()==Session::Mode::Transition,
          "first transition frame was not blackout");
    for(unsigned i=1;i<41;++i)
        check(finish.presentFrame()==Session::Mode::Transition,
              "blackout ended before 41 presented frames");
    check(finish.blackFramesPresented()==41,
          "session did not count 41 blackout frames");
    check(finish.presentFrame()==Session::Mode::Platform,
          "platform mode did not follow blackout");
    const auto frozenFrame=finish.state().frame;
    finish.tick({false,false,true,false},false,true);
    check(finish.mode()==Session::Mode::Platform &&
          finish.state().frame==frozenFrame,
          "platform mode accepted driving input");

    finish.reset();
    check(finish.mode()==Session::Mode::Driving &&
          finish.state().frame==0 &&
          finish.blackFramesPresented()==0,
          "full session reset failed");
    std::cout<<"VPD_STAGE_ONE_SESSION_LIFECYCLE_PASS"
             <<" driving=1 explicit_finish=1 blackout=41 platform=1 reset=1"
             <<" original_finish_trigger_proven=0\n";
}
