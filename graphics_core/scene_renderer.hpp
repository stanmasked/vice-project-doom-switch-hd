#pragma once
#include <cstdint>
#include "decor_layout.hpp"
namespace vpd {
struct SpriteAtlas;
// ROM-free renderer interface shared by host tests and Nintendo Switch.
struct SceneView {
    int32_t player_x_px=0, player_y_px=0, camera_x_px=0;
    uint32_t frame=0;
    bool grounded=false;
    void* map_context=nullptr;
    bool (*solid_at)(void*,int,int)=nullptr;
    const SpriteAtlas* sprite_atlas=nullptr;
    bool moving=false;
    int sprite_frame=-1; // explicit animation player override; -1 means legacy default
    bool facing_left=false;
    bool external_sprite_asset=false;
    bool asset_reload_failed=false;
    bool external_animation_source=false;
    const SpriteAtlas* terrain_atlas=nullptr;
    bool external_terrain_asset=false;
    bool terrain_reload_failed=false;
    const SpriteAtlas* backdrop_atlas=nullptr;
    bool external_backdrop_asset=false;
    bool backdrop_reload_failed=false;
    const SpriteAtlas* decor_atlas=nullptr;
    bool external_decor_asset=false;
    bool decor_reload_failed=false;
    DecorLayout decor_layout{};
    bool external_decor_layout=false;
    bool decor_layout_reload_failed=false;
};
constexpr int kSceneWidth=1280;
constexpr int kSceneHeight=720;
// Framebuffer is RGBA8888; stride is in 32-bit pixels, not bytes.
// Invalid arguments yield false (safe in libnx's no-exception builds).
bool drawScene(uint32_t* target,int width,int height,
               int stride_pixels,const SceneView& view);
}
