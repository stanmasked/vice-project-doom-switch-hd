#include "driving_stage_exit.hpp"
#include "driving_transition_black.hpp"
#include "driving_preview.hpp"
#include "scene_renderer.hpp"
#include "simulation.hpp"
#include <vector>
#include <cstdint>
#include <iostream>
#include <stdexcept>
static void check(bool ok, const char* why){if(!ok)throw std::runtime_error(why);}
int main(){
    constexpr int w=1280,h=720,stride=w+17;
    constexpr std::uint32_t sentinel=0x12345678u;
    vpd::DrivingStageExit driveExit;
    vpd::Simulation platform;
    const auto original=platform.fingerprint();
    std::vector<std::uint32_t> frame(static_cast<std::size_t>(stride)*h,sentinel);
    std::vector<std::uint32_t> expected(frame.size(),sentinel);
    vpd::DrivingPreviewView driving{};
    check(vpd::drawDrivingPreview(frame.data(),w,h,stride,driving),
          "initial synthetic road render failed");
    check(!driveExit.requestAfterDrivingFrame(false,true),
          "completion outside driving mode accepted");
    check(!driveExit.requestAfterDrivingFrame(true,false),
          "transition activated without a completion request");
    check(driveExit.present()==vpd::DrivingStageExit::Scene::Driving,
          "unrequested blackout started");
    // A validated completion request is applied only after the last successfully presented car frame.
    check(driveExit.requestAfterDrivingFrame(true,true),
          "validated completion request did not arm the timeline");
    check(!driveExit.requestAfterDrivingFrame(true,true),
          "duplicate completion request was accepted");
    check(!vpd::drawDrivingBlackout(nullptr,w,h,stride),
          "null framebuffer accepted");
    check(!vpd::drawDrivingBlackout(frame.data(),w,h,stride-1-17),
          "short stride accepted");
    check(!vpd::drawDrivingBlackout(frame.data(),w-1,h,stride),
          "incorrect width accepted");
    check(!vpd::drawDrivingBlackout(frame.data(),w,h-1,stride),
          "incorrect height accepted");
    for(unsigned frameIndex=0;frameIndex<41;++frameIndex){
        check(driveExit.present()==vpd::DrivingStageExit::Scene::Black,
              "blackout duration not 41 presented frames");
        check(vpd::drawDrivingBlackout(frame.data(),w,h,stride),
              "native black raster rejected frame");
        check(driveExit.blackFramesPresented()==frameIndex+1,
              "black frame counter skipped or repeated");
        for(int y=0;y<h;++y){
            for(int x=0;x<w;++x)
                check(frame[static_cast<std::size_t>(y)*stride+x]==0xff000000u,
                      "nonblack pixel during blackout");
            for(int x=w;x<stride;++x)
                check(frame[static_cast<std::size_t>(y)*stride+x]==sentinel,
                      "blackout wrote into padded memory");
        }
        check(platform.fingerprint()==original,
              "platform simulation advanced during car/blackout");
    }
    check(driveExit.present()==vpd::DrivingStageExit::Scene::Platform,
          "platform scene did not follow exactly 41 black frames");
    vpd::SceneView platformScene{};
    check(vpd::drawScene(frame.data(),w,h,stride,platformScene),
          "platform scene could not resume");
    check(vpd::drawScene(expected.data(),w,h,stride,platformScene),
          "baseline platform scene could not render");
    check(frame==expected,"platform raster after blackout differs from baseline");
    check(platform.fingerprint()==original,
          "platform state changed during transition");
    check(driveExit.present()==vpd::DrivingStageExit::Scene::Platform,
          "transition unexpectedly restarted");
    check(!driveExit.requestAfterDrivingFrame(true,true),
          "second platform-to-blackout trigger accepted");
    driveExit.reset();
    check(driveExit.present()==vpd::DrivingStageExit::Scene::Driving,
          "reset did not restore driving selection");
    check(driveExit.blackFramesPresented()==0,
          "reset retained old blackout count");
    check(driveExit.requestAfterDrivingFrame(true,true),
          "fresh transition request rejected after completed reset");
    for(unsigned i=0;i<10;++i) {
        check(driveExit.present()==vpd::DrivingStageExit::Scene::Black,
              "fresh transition did not begin with blackout");
    }
    check(driveExit.blackFramesPresented()==10,
          "fresh transition did not count ten presented frames");
    driveExit.reset();
    check(driveExit.present()==vpd::DrivingStageExit::Scene::Driving &&
          driveExit.blackFramesPresented()==0,
          "mid-transition reset retained stale gate or frame count");
    check(driveExit.requestAfterDrivingFrame(true,true),
          "transition could not restart after mid-blackout reset");
    for(unsigned i=0;i<41;++i) {
        check(driveExit.present()==vpd::DrivingStageExit::Scene::Black,
              "restarted gate ended before all 41 frames");
        check(driveExit.blackFramesPresented()==i+1,
              "restarted gate skipped or repeated a black frame");
    }
    check(driveExit.present()==vpd::DrivingStageExit::Scene::Platform,
          "restarted gate failed to reach platform after 41 frames");
    std::cout<<"VPD_DRIVING_TO_PLATFORM_BLACKOUT_PASS black_frames=41"
             <<" real_original_frame_alignment_proven=no"
             <<" platform_state_unchanged=yes source_assets=none\n";
}
