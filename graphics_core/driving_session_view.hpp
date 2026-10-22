#pragma once
#include "driving_stage_one_session.hpp"
#include "driving_scene_bridge.hpp"

// One-way presentation adapter: the vehicle/session state is authoritative;
// the renderer receives a view derived from that exact state each frame.
namespace vpd {
inline DrivingPreviewView makeDrivingSessionView(
    const DrivingStageOneSession& session) {
    auto view=makeDrivingSceneView(session.state());
    view.show_car=session.mode()==DrivingStageOneSession::Mode::Driving ||
                  session.mode()==DrivingStageOneSession::Mode::Transition;
    view.show_obstacle=session.mode()==DrivingStageOneSession::Mode::Driving &&
                       session.state().health>0;
    return view;
}
} // namespace vpd
