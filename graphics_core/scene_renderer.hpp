#pragma once
#include <cstdint>
namespace vpd {
// ROM-free renderer interface shared by host tests and Nintendo Switch.
struct SceneView {
    int32_t player_x_px=0, player_y_px=0, camera_x_px=0;
    uint32_t frame=0;
    bool grounded=false;
    void* map_context=nullptr;
    bool (*solid_at)(void*,int,int)=nullptr;
};
constexpr int kSceneWidth=1280;
constexpr int kSceneHeight=720;
// Framebuffer is RGBA8888; stride is in 32-bit pixels, not bytes.
// Invalid arguments yield false (safe in libnx's no-exception builds).
bool drawScene(uint32_t* target,int width,int height,
               int stride_pixels,const SceneView& view);
}
