#include "driving_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include "simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

static void require(bool condition,const char* message) {
    if(!condition)throw std::runtime_error(message);
}
static uint64_t hashRows(const std::vector<uint32_t>& data,
                         int stride,int from,int to) {
    uint64_t hash=14695981039346656037ull;
    for(int y=from;y<to;++y)
        for(int x=0;x<vpd::kDrivingPreviewWidth;++x) {
            const uint32_t pixel=data[static_cast<std::size_t>(y)*stride+x];
            for(int byte=0;byte<4;++byte) {
                hash^=(pixel>>(byte*8))&255u;
                hash*=1099511628211ull;
            }
        }
    return hash;
}
static void checkBridge(const vpd::DrivingState& state) {
    const auto view=vpd::makeDrivingSceneView(state);
    require(view.frame==state.frame && view.ticks==state.frame,
            "driving frame/timer bridge drift");
    require(view.road_phase==state.road_phase &&
            view.health==state.health && view.speed==state.speed,
            "driving scroll/status bridge drift");
    require(view.car_x==state.car_x &&
            view.obstacle_x==state.obstacle_x &&
            view.obstacle_y==state.obstacle_y,
            "vehicle/obstacle geometry bridge drift");
    require(view.show_car && view.show_obstacle,
            "fixture visibility unexpectedly changed");
    require(view.impact_flash==(state.hit_cooldown>0 &&
            (state.frame/4u)%2u==0u),
            "damage flash bridge drift");
}

int main() {
    constexpr int w=vpd::kDrivingPreviewWidth;
    constexpr int h=vpd::kDrivingPreviewHeight;
    constexpr int stride=w+13;
    constexpr int split=vpd::kDrivingHudTop;
    vpd::Simulation platform;
    const auto platformBefore=platform.fingerprint();
    vpd::DrivingState drive;
    checkBridge(drive);

    // A single state powers both actual SceneView and the standalone
    // renderer, not two individually hand-authored visual snapshots.
    vpd::SceneView scene{};
    scene.frame=39;
    scene.player_health=3;
    std::vector<uint32_t> framebuffer(static_cast<std::size_t>(stride)*h);
    std::vector<uint32_t> direct(framebuffer.size());
    require(vpd::drawScene(framebuffer.data(),w,h,stride,scene),
            "original scene draw failed");
    const auto oldRoad=hashRows(framebuffer,stride,0,split);
    const auto oldHud=hashRows(framebuffer,stride,split,h);
    scene.driving_stage_preview=true;
    scene.driving=vpd::makeDrivingSceneView(drive);
    require(vpd::drawScene(framebuffer.data(),w,h,stride,scene) &&
            vpd::drawDrivingPreview(direct.data(),w,h,stride,scene.driving),
            "driving render failed");
    require(hashRows(framebuffer,stride,0,split)==
                hashRows(direct,stride,0,split) &&
            hashRows(framebuffer,stride,split,h)==
                hashRows(direct,stride,split,h),
            "SceneView and isolated drawing paths diverged");
    const auto initialRoad=hashRows(framebuffer,stride,0,split);
    const auto initialHud=hashRows(framebuffer,stride,split,h);

    for(int i=0;i<20;++i) {
        drive.tick({false,true,true,false});
        checkBridge(drive);
    }
    scene.driving=vpd::makeDrivingSceneView(drive);
    require(vpd::drawScene(framebuffer.data(),w,h,stride,scene),
            "steered/accelerated render failed");
    require(hashRows(framebuffer,stride,0,split)!=initialRoad &&
            hashRows(framebuffer,stride,split,h)!=initialHud,
            "steering or acceleration was not displayed");

    // Damage changes only the HUD counters for an identical road
    // snapshot, not the framebuffer portion reserved for traffic.
    drive.reset();
    bool foundImpact=false;
    for(int i=0;i<120;++i) {
        drive.tick({});
        checkBridge(drive);
        if(drive.last_impact)foundImpact=true;
    }
    require(foundImpact && drive.health==4 && drive.impacts==1,
            "synthetic obstacle impact not reproduced");
    auto damaged=vpd::makeDrivingSceneView(drive);
    require(vpd::drawDrivingPreview(direct.data(),w,h,stride,damaged),
            "collision snapshot could not render");
    const auto damagedRoad=hashRows(direct,stride,0,split);
    const auto damagedHud=hashRows(direct,stride,split,h);
    damaged.health=3;
    require(vpd::drawDrivingPreview(direct.data(),w,h,stride,damaged),
            "modified HUD snapshot could not render");
    require(hashRows(direct,stride,0,split)==damagedRoad &&
            hashRows(direct,stride,split,h)!=damagedHud,
            "HUD health update leaked into road layer");

    scene.driving_stage_preview=false;
    require(vpd::drawScene(framebuffer.data(),w,h,stride,scene),
            "return to platform scene failed");
    require(hashRows(framebuffer,stride,0,split)==oldRoad &&
            hashRows(framebuffer,stride,split,h)==oldHud,
            "platform framebuffer changed after driving toggle");
    require(platform.fingerprint()==platformBefore,
            "vehicle bridge modified legacy platform simulation");
    std::cout<<"VPD_ROMFREE_DRIVING_STATE_BRIDGE_PASS"
             <<" shared_nro_host_mapping=1 collision_hud=1"
             <<" legacy_platform_unchanged=1"
             <<" real_nexium_vehicle_controls_proven=0"
             <<" original_rom_assets_used=0\n";
}
