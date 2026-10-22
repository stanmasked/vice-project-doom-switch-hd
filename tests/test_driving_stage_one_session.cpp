#include "driving_stage_one_session.hpp"
#include <iostream>
#include <stdexcept>

static void check(bool ok,const char* why) {
    if(!ok) throw std::runtime_error(why);
}

int main() {
    using Session=vpd::DrivingStageOneSession;
    static_assert(vpd::DrivingStageOneConfig::shouldRequestExit(
                      true,5,false,false,1800,8),
                  "complete healthy preview should request route exit");
    static_assert(!vpd::DrivingStageOneConfig::shouldRequestExit(
                      true,0,false,true,1800,8),
                  "dead vehicle must not request route exit");
    static_assert(!vpd::DrivingStageOneConfig::shouldRequestExit(
                      true,5,true,true,1800,8),
                  "active transition must not be requested twice");
    static_assert(!vpd::DrivingStageOneConfig::shouldRequestExit(
                      false,5,false,true,1800,8),
                  "route preview exit must be disabled outside preview");
    static_assert(vpd::DrivingStageOneConfig::shouldRequestExit(
                      true,5,false,true,0,0),
                  "manual QA escape hatch should work before route completion");
    static_assert(vpd::DrivingStageOneConfig::routeProgressComplete(1800,8),
                  "default route completion predicate should accept complete progress");
    static_assert(!vpd::DrivingStageOneConfig::routeProgressComplete(1800,7),
                  "route completion must require obstacle progress");
    static_assert(!vpd::DrivingStageOneConfig::routeProgressComplete(1799,8),
                  "route completion must require duration");
    static_assert(vpd::DrivingStageOneConfig::routeProgressComplete(3,1,3,1),
                  "custom route thresholds must be supported");
    static_assert(!vpd::DrivingStageOneConfig::shouldRequestExit(
                      true,5,false,false,1800,8,5000,20),
                  "custom longer route must not exit at default thresholds");
    static_assert(vpd::DrivingStageOneConfig::shouldRequestExit(
                      true,5,false,false,5000,20,5000,20),
                  "custom route must exit at its own configured thresholds");
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
          defeated.state().health==5 && defeated.state().frame==0 &&
          defeated.state().obstacles_passed==0 &&
          defeated.state().obstacle_serial==0 &&
          defeated.state().impacts==0 &&
          defeated.state().hit_cooldown==0 &&
          !defeated.state().last_impact,
          "restart did not restore canonical driving state and clear stale progress");

    // A fatal collision takes precedence over an explicit finish request.
    vpd::DrivingState fatalFinish;
    fatalFinish.health=1;
    fatalFinish.obstacle_x=fatalFinish.car_x;
    fatalFinish.obstacle_y=433;
    Session fatalFinishSession(fatalFinish,1,0);
    fatalFinishSession.tick({},true);
    check(fatalFinishSession.mode()==Session::Mode::Defeated &&
          fatalFinishSession.blackFramesPresented()==0,
          "fatal collision incorrectly entered stage transition");

    // A complete route ends from gameplay progress without a debug/host event.
    Session route(3,0);
    route.tick({});
    check(route.mode()==Session::Mode::Driving,
          "route ended before its configured prototype duration");
    route.tick({});
    check(route.mode()==Session::Mode::Driving,
          "route ended one frame before its configured prototype duration");
    route.tick({});
    check(route.mode()==Session::Mode::Transition,
          "route did not transition at its configured completion frame");
    check(route.state().frame==3,
          "route completion advanced the simulation beyond its final frame");

    // Time alone must not complete a route when required obstacle progress is missing.
    Session progressGate(1,1);
    progressGate.tick({});
    check(progressGate.mode()==Session::Mode::Driving &&
          progressGate.state().obstacles_passed==0,
          "route completed without required obstacle progress");
    vpd::DrivingState nearPass;
    nearPass.obstacle_y=649;
    // Seed the obstacle near the exit via the supported initial-state fixture.
    Session progressFixture(nearPass,1,1);
    progressFixture.tick({});
    check(progressFixture.state().obstacles_passed==1 &&
          progressFixture.mode()==Session::Mode::Transition,
          "route did not complete after duration and obstacle progress");

    Session finish;
    finish.tick({},true);
    check(finish.mode()==Session::Mode::Transition,
          "explicit finish event did not start transition");
    check(finish.presentFrame()==Session::Mode::Transition,
          "first transition frame was not blackout");
    const auto frameAtTransition=finish.state().frame;
    for(unsigned i=1;i<41;++i) {
        finish.tick({false,false,true,false},false,true);
        check(finish.state().frame==frameAtTransition,
              "driving simulation advanced during blackout");
        check(finish.presentFrame()==Session::Mode::Transition,
              "blackout ended before 41 presented frames");
    }
    check(finish.blackFramesPresented()==41,
          "session did not count 41 blackout frames");
    check(finish.presentFrame()==Session::Mode::Platform,
          "platform mode did not follow blackout");
    const auto terminalBlackFrames=finish.blackFramesPresented();
    for(unsigned i=0;i<3;++i)
        check(finish.presentFrame()==Session::Mode::Platform,
              "platform mode regressed after transition completion");
    check(finish.blackFramesPresented()==terminalBlackFrames,
          "blackout counter changed after platform mode began");
    const auto frozenFrame=finish.state().frame;
    finish.tick({false,false,true,false},false,true);
    check(finish.mode()==Session::Mode::Platform &&
          finish.state().frame==frozenFrame,
          "platform mode accepted driving input");

    finish.reset();
    check(finish.mode()==Session::Mode::Driving &&
          finish.state().frame==0 && finish.state().health==5 &&
          finish.state().obstacles_passed==0 &&
          finish.state().obstacle_serial==0 && finish.state().impacts==0 &&
          finish.state().hit_cooldown==0 && !finish.state().last_impact &&
          finish.blackFramesPresented()==0,
          "full session reset retained stale driving or transition state");
    vpd::DrivingState restartInitial;
    restartInitial.health=1;
    restartInitial.obstacle_x=restartInitial.car_x;
    restartInitial.obstacle_y=433;
    Session configuredRestart(restartInitial,3,0);
    configuredRestart.tick({});
    check(configuredRestart.mode()==Session::Mode::Defeated,
          "configured session did not enter defeated mode");
    configuredRestart.tick({},false,true);
    configuredRestart.tick({});
    configuredRestart.tick({});
    check(configuredRestart.mode()==Session::Mode::Driving,
          "restart lost custom route duration before its threshold");
    configuredRestart.tick({});
    check(configuredRestart.mode()==Session::Mode::Transition,
          "restart lost custom route thresholds");

    // Reset the integrated session midway through blackout, then prove a fresh
    // explicit finish request receives its own complete 41 presented frames.
    Session interrupted;
    interrupted.tick({},true);
    for(unsigned i=0;i<10;++i)
        check(interrupted.presentFrame()==Session::Mode::Transition,
              "integrated transition ended before interrupted reset fixture");
    check(interrupted.blackFramesPresented()==10,
          "integrated transition did not count pre-reset blackout frames");
    interrupted.reset();
    interrupted.reset();
    check(interrupted.mode()==Session::Mode::Driving &&
          interrupted.blackFramesPresented()==0 &&
          interrupted.state().frame==0 && interrupted.state().health==5,
          "repeated integrated reset retained partial transition or driving state");
    check(interrupted.presentFrame()==Session::Mode::Driving,
          "repeated reset resumed a stale transition before a new request");
    interrupted.tick({},true);
    for(unsigned i=0;i<41;++i) {
        check(interrupted.presentFrame()==Session::Mode::Transition,
              "restarted integrated transition ended before 41 frames");
        check(interrupted.blackFramesPresented()==i+1,
              "restarted integrated transition counter skipped a frame");
    }
    check(interrupted.presentFrame()==Session::Mode::Platform &&
          interrupted.blackFramesPresented()==41,
          "restarted integrated transition failed to hand off after 41 frames");

    Session configured(3,0);
    configured.reset();
    configured.tick({});
    configured.tick({});
    check(configured.mode()==Session::Mode::Driving,
          "reset discarded custom route duration");
    configured.tick({});
    check(configured.mode()==Session::Mode::Transition,
          "reset discarded custom obstacle threshold");
    configured.reset();
    configured.reset();
    configured.tick({});
    configured.tick({});
    check(configured.mode()==Session::Mode::Driving,
          "repeated reset after transition discarded custom route duration");
    configured.tick({});
    check(configured.mode()==Session::Mode::Transition,
          "repeated reset after transition discarded custom route thresholds");

    std::cout<<"VPD_STAGE_ONE_SESSION_LIFECYCLE_PASS"
             <<" driving=1 explicit_finish=1 blackout=41 platform=1 reset=1"
             <<" original_finish_trigger_proven=0\n";
}
