#include "driving_session_view.hpp"
#include <iostream>
#include <stdexcept>

static void check(bool ok,const char* why) {
    if(!ok) throw std::runtime_error(why);
}

int main() {
    using Session=vpd::DrivingStageOneSession;
    Session session;
    vpd::DrivingState progressState;
    progressState.obstacles_passed=7;
    Session progressSession(progressState,100,1);
    const auto progressView=vpd::makeDrivingSessionView(progressSession);
    check(progressView.obstacles_passed==7,
          "HUD progress did not reflect seeded session counter");

    auto view=vpd::makeDrivingSessionView(session);
    check(view.frame==session.state().frame &&
          view.car_x==session.state().car_x &&
          view.road_phase==session.state().road_phase &&
          view.health==session.state().health &&
          view.obstacles_passed==session.state().obstacles_passed && view.show_car &&
          view.show_obstacle,
          "initial renderer view diverged from driving session");

    session.tick({false,false,true,false});
    view=vpd::makeDrivingSessionView(session);
    check(view.frame==1 && view.ticks==1 && view.speed==4 &&
          view.car_x==session.state().car_x,
          "renderer view did not reflect the latest simulation tick");

    session.tick({},true);
    view=vpd::makeDrivingSessionView(session);
    check(session.mode()==Session::Mode::Transition && view.show_car &&
          !view.show_obstacle,
          "transition presentation did not suppress obstacle while retaining car");

    for(unsigned i=0;i<41;++i) session.presentFrame();
    check(session.presentFrame()==Session::Mode::Platform,
          "session did not hand off to platform scene after blackout");
    view=vpd::makeDrivingSessionView(session);
    check(!view.show_car && !view.show_obstacle,
          "platform session still exposed driving sprites");

    vpd::DrivingState fragile;
    fragile.health=1;
    fragile.obstacle_x=fragile.car_x;
    fragile.obstacle_y=433;
    Session retrySession(fragile,100,1);
    retrySession.tick({});
    check(retrySession.mode()==Session::Mode::Defeated,
          "session view fixture did not reach defeated state");
    view=vpd::makeDrivingSessionView(retrySession);
    check(!view.show_obstacle && view.health==0,
          "HUD/renderer view exposed a live obstacle after defeat");
    retrySession.tick({},false,true);
    view=vpd::makeDrivingSessionView(retrySession);
    check(retrySession.mode()==Session::Mode::Driving && view.show_car &&
          view.show_obstacle && view.health==5 && view.frame==0 &&
          view.obstacles_passed==0,
          "renderer view retained stale state after retry");

    std::cout<<"VPD_STAGE_ONE_RENDER_VIEW_PASS shared_state=1 transition=1 platform_handoff=1\n";
}
