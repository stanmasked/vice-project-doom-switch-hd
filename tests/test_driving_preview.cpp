#include "driving_preview.hpp"
#include "scene_renderer.hpp"
#include "driving_simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

static void require(bool cond,const char* message) {
    if(!cond)throw std::runtime_error(message);
}
static uint64_t hashRows(const std::vector<uint32_t>& data,int stride,
                         int y0,int y1) {
    uint64_t h=14695981039346656037ull;
    for(int y=y0;y<y1;++y)
        for(int x=0;x<vpd::kDrivingPreviewWidth;++x) {
            const auto p=data[static_cast<std::size_t>(y)*stride+x];
            for(unsigned byte=0;byte<4;++byte) {
                h^=(p>>(byte*8))&255u;
                h*=1099511628211ull;
            }
        }
    return h;
}

int main() {
    constexpr int w=vpd::kDrivingPreviewWidth;
    constexpr int h=vpd::kDrivingPreviewHeight;
    constexpr int split=vpd::kDrivingHudTop;
    constexpr int stride=w+23;
    constexpr uint32_t sentinel=0x13579bdfu;
    require(split==588,"stage-1 HUD source boundary not preserved");
    std::vector<uint32_t> data(static_cast<std::size_t>(stride)*h,sentinel);
    vpd::DrivingPreviewView view;
    view.frame=120;
    view.road_phase=11;
    view.ticks=12345;
    view.health=4;
    require(!vpd::drawDrivingPreview(nullptr,w,h,stride,view),
            "null canvas incorrectly accepted");
    require(!vpd::drawDrivingPreview(data.data(),w,h,stride-40,view),
            "short pitch incorrectly accepted");
    require(!vpd::drawDrivingPreview(data.data(),w-1,h,stride,view),
            "bad width incorrectly accepted");
    require(!vpd::drawDrivingPreview(data.data(),w,h-1,stride,view),
            "bad height incorrectly accepted");
    require(vpd::drawDrivingPreview(data.data(),w,h,stride,view),
            "road/HUD draw failed");
    for(int y=0;y<h;++y) {
        for(int x=w;x<stride;++x)
            require(data[static_cast<std::size_t>(y)*stride+x]==sentinel,
                    "raster wrote to padded columns");
        for(int x=0;x<w;++x)
            require((data[static_cast<std::size_t>(y)*stride+x]>>24)==255u,
                    "raster left an uninitialized/transparent pixel");
    }
    const uint64_t originalRoad=hashRows(data,stride,0,split);
    const uint64_t originalHud=hashRows(data,stride,split,h);
    const uint32_t topEdge=data[(split-1)*stride+640];
    const uint32_t bottomEdge=data[split*stride+640];
    require(topEdge!=bottomEdge,"road/HUD layer boundary not visible");
    std::vector<uint32_t> same(data.size(),sentinel);
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,view),
            "second identical draw failed");
    require(hashRows(same,stride,0,split)==originalRoad &&
            hashRows(same,stride,split,h)==originalHud,
            "driving stage preview not deterministic");

    // Timing variables affect ONLY the driving region. The numeric HUD
    // remains identical even at extreme positive and negative offsets.
    view.road_phase=-10007;
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,view),
            "negative-phase driving preview failed");
    require(hashRows(same,stride,0,split)!=originalRoad,
            "road markers did not change after phase update");
    require(hashRows(same,stride,split,h)==originalHud,
            "road scroll leaked into separate lower HUD");

    // Score/health HUD counters can change independently of the road.
    view.road_phase=11;
    view.ticks+=1000;
    view.health=2;
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,view),
            "status counter preview failed");
    require(hashRows(same,stride,0,split)==originalRoad,
            "HUD counter changed road pixels");
    require(hashRows(same,stride,split,h)!=originalHud,
            "HUD status change drew no pixels");

    // Car sprite is clipped above the HUD and never changes the bottom panel.
    view.ticks=12345;
    view.health=4;
    view.show_car=false;
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,view),
            "no-car frame failed");
    require(hashRows(same,stride,0,split)!=originalRoad,
            "car placeholder absent from road preview");
    require(hashRows(same,stride,split,h)==originalHud,
            "car sprite wrote into HUD layer");

    // Renderer fully clears the same address on each frame.
    view.show_car=true;
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,view),
            "restore car preview failed");
    require(hashRows(same,stride,0,split)==originalRoad &&
            hashRows(same,stride,split,h)==originalHud,
            "previous frame state leaked into driving preview");

    // The shared Switch/host SceneView bridge must render the same
    // isolated preview only on explicit opt-in, and preserve the old scene.
    vpd::SceneView scene{};
    scene.frame=view.frame;
    scene.player_health=view.health;
    std::vector<uint32_t> legacy(data.size(),sentinel);
    require(vpd::drawScene(legacy.data(),w,h,stride,scene),
            "legacy SceneView draw failed");
    const auto legacyRoad=hashRows(legacy,stride,0,split);
    const auto legacyHud=hashRows(legacy,stride,split,h);
    scene.driving_stage_preview=true;
    scene.driving.frame=scene.frame;
    scene.driving.road_phase=static_cast<int>(scene.frame%72u);
    scene.driving.ticks=scene.frame;
    scene.driving.health=scene.player_health;
    require(vpd::drawScene(legacy.data(),w,h,stride,scene),
            "opt-in shared SceneView driving draw failed");
    vpd::DrivingPreviewView reference=scene.driving;
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,reference),
            "direct driving preview reference failed");
    require(hashRows(legacy,stride,0,split)==hashRows(same,stride,0,split) &&
            hashRows(legacy,stride,split,h)==hashRows(same,stride,split,h),
            "shared SceneView did not select isolated driving renderer");
    // A real (invented) input-driven model must change only the road pixels
    // under steering and speed, while scene status stays HUD-only.
    vpd::DrivingState drivingState{};
    const vpd::DrivingPreviewView originalDriving=view;
    vpd::DrivingPreviewView moving=originalDriving;
    moving.show_obstacle=true;
    moving.obstacle_x=drivingState.obstacle_x;
    moving.obstacle_y=drivingState.obstacle_y;
    moving.car_x=drivingState.car_x;
    moving.speed=static_cast<uint8_t>(drivingState.speed);
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,moving),
            "input-driven baseline preview failed");
    const auto movementHud=hashRows(same,stride,split,h);
    const auto movementRoad=hashRows(same,stride,0,split);
    for(int n=0;n<15;++n)drivingState.tick({false,true,true,false});
    moving.frame=drivingState.frame;
    moving.road_phase=drivingState.road_phase;
    moving.ticks=originalDriving.ticks; // fixed HUD timer source
    moving.car_x=drivingState.car_x;
    moving.obstacle_x=drivingState.obstacle_x;
    moving.obstacle_y=drivingState.obstacle_y;
    moving.speed=static_cast<uint8_t>(drivingState.speed);
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,moving),
            "steered car and obstacle raster failed");
    require(hashRows(same,stride,0,split)!=movementRoad,
            "steering/speed/traffic did not affect road");
    require(hashRows(same,stride,split,h)!=movementHud,
            "speed HUD did not reflect acceleration");
    const auto acceleratedRoad=hashRows(same,stride,0,split);
    moving.health=2;
    require(vpd::drawDrivingPreview(same.data(),w,h,stride,moving),
            "independent damage-HUD redraw failed");
    require(hashRows(same,stride,0,split)==acceleratedRoad,
            "vehicle HUD health altered roadway pixels");

    scene.driving_stage_preview=false;
    require(vpd::drawScene(legacy.data(),w,h,stride,scene),
            "legacy rendering after toggle failed");
    require(hashRows(legacy,stride,0,split)==legacyRoad &&
            hashRows(legacy,stride,split,h)==legacyHud,
            "driving preview changed the legacy rendering after exit");

    std::cout<<"VPD_ROMFREE_DRIVING_HUD_LAYER_PASS"
             <<" source_split_y=196 output_split_y=588"
             <<" road_and_hud_independent=yes"
             <<" legacy_renderer_changed=no"
             <<" original_camera_speed_proven=no"
             <<" original_rom_or_tiles_used=no\n";
}
