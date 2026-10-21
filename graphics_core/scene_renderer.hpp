#pragma once
#include <cstdint>
#include <array>
#include "decor_layout.hpp"
#include "driving_preview.hpp"
namespace vpd {
struct SpriteAtlas;
struct GuardView {
    int32_t x_px=0,y_px=0;
    uint8_t health=0;
    bool enabled=false;
    bool alerted=false;
    uint8_t hit_flash_ticks=0;
    uint8_t attack_cooldown=0; // source guard melee cadence, no new logic
};
struct SentryView {
    int32_t x_px=0,y_px=0;
    uint8_t health=0;
    uint8_t hit_flash_ticks=0;
    bool enabled=false;
};
struct EnemyProjectileView {
    int32_t x_px=0,y_px=0;
    bool active=false;
};
struct ProjectileView {
    int32_t x_px=0,y_px=0;
    bool active=false;
};
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
    std::array<ProjectileView,8> projectiles{};
    int32_t training_target_x_px=0;
    int32_t training_target_y_px=0;
    uint8_t training_target_health=0; // zero means invisible
    bool replay_demo=false; // opt-in ROM-free attract-mode label
    bool demo_checkpoint_ok=false; // frame-200 synthetic state matched
    bool manual_controls=false;
    bool dash_active=false;
    uint8_t dash_cooldown=0;
    bool dash_ever_used=false;
    GuardView guard{};
    uint8_t player_health=5;
    uint8_t player_hit_flash_ticks=0;
    SentryView sentry{};
    std::array<EnemyProjectileView,3> enemy_projectiles{};
    bool stage_cleared=false;
    bool hd_hit_lighting=false; // opt-in localized combat impact light
    bool hd_atmospheric_haze=false; // manual-only world-space atmospheric accents
    bool hd_footstep_dust=false; // optional visual-only grounded movement cue
    bool hd_hostile_projectile_halo=false; // real turret-bullet cue, manual only
    bool hd_low_health_warning=false; // visual-only pulse at HP 1 or 2
    bool hd_guard_threat_tell=false; // opt-in alert and cooldown cue
    bool hd_fx_status_visible=false; // optional L+R mode indicator, off in golden demo
    bool hd_fx_status_enabled=true; // visual setting only, never physics
    // ROM-free stage-two completion gate; explicit source-derived visibility.
    bool exit_visible=false;
    bool exit_open=false;
    int32_t exit_x_px=0;
    int32_t exit_y_px=0;
    bool driving_stage_preview=false; // explicit ROM-free road/HUD preview; never autoplay
    DrivingPreviewView driving{}; // explicit isolated car-state snapshot
};
constexpr int kSceneWidth=1280;
constexpr int kSceneHeight=720;
// Framebuffer is RGBA8888; stride is in 32-bit pixels, not bytes.
// Invalid arguments yield false (safe in libnx's no-exception builds).
bool drawScene(uint32_t* target,int width,int height,
               int stride_pixels,const SceneView& view);
}
