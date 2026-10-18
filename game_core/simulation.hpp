#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Independent ROM-free gameplay scaffold. Physics/map values are placeholders,
// NOT measurements or recovered Vice: Project Doom gameplay.
namespace vpd {
constexpr int kFixed=256;
constexpr int kTileSize=16;
constexpr int kMapWidth=64;
constexpr int kMapHeight=15;
constexpr int kPlayerWidth=12;
constexpr int kPlayerHeight=14;
enum Buttons : uint8_t { Left=1, Right=2, Jump=4, Fire=8, Dash=16 };
struct Input { uint8_t buttons=0; };
struct Actor {
    int32_t x=0;
    int32_t y=0;
    int32_t vx=0;
    int32_t vy=0;
    bool grounded=false;
};
// Original, placeholder run-and-gun projectile, NOT recovered game behavior.
constexpr std::size_t kMaxProjectiles=8;
struct Projectile {
    int32_t x=0,y=0,vx=0;
    uint16_t age=0;
    bool active=false;
};
// Opt-in ROM-free guard prototype. Absent from the existing auto-demo.
struct GuardEnemy {
    int32_t x=16*kTileSize*kFixed;
    int32_t y=((kMapHeight-1)*kTileSize-kPlayerHeight)*kFixed;
    uint8_t health=3;
    bool alerted=false;
    int8_t direction=1;
    uint8_t attack_cooldown=0;
    uint16_t attacks=0;
    uint16_t projectile_hits=0;
    uint8_t hit_flash_ticks=0; // cosmetic feedback after authentic swept damage
};
// Separate second-wave fixed turret, activated only after the first guard is
// defeated and the player reaches the next section of this synthetic map.
struct SentryEnemy {
    int32_t x=39*kTileSize*kFixed;
    int32_t y=((kMapHeight-1)*kTileSize-kPlayerHeight)*kFixed;
    uint8_t health=2;
    uint8_t fire_cooldown=0;
    uint8_t hit_flash_ticks=0;
    uint16_t shots_fired=0;
    uint16_t shots_hit=0;
    uint16_t projectile_hits=0;
};
struct EnemyProjectile {
    int32_t x=0,y=0,vx=0;
    uint16_t age=0;
    bool active=false;
};
constexpr std::size_t kMaxEnemyProjectiles=3;
// Self-authored stationary training target in a synthetic arena.
struct TrainingTarget {
    int32_t x=25*kTileSize*kFixed;
    int32_t y=13*kTileSize*kFixed;
    uint8_t health=3;
    uint16_t hits=0;
};
class Scene {
public:
    Scene();
    bool solid(int tile_x,int tile_y) const;
    void setSolid(int tile_x,int tile_y,bool value);
    char cell(int tile_x,int tile_y) const;
    // Read-only map bytes, serialized in fixed tile order for replay identity.
    const std::array<uint8_t,kMapWidth*kMapHeight>& cells() const { return tiles_; }
private:
    std::array<uint8_t,kMapWidth*kMapHeight> tiles_{};
};
class Simulation {
public:
    Simulation();
    void tick(Input input);
    void reset();
    const Actor& player() const { return player_; }
    const Scene& scene() const { return scene_; }
    Scene& scene() { return scene_; }
    uint32_t frame() const { return frame_; }
    int32_t cameraX() const { return camera_x_; }
    uint64_t fingerprint() const;
    const std::array<Projectile,kMaxProjectiles>& projectiles() const { return projectiles_; }
    uint32_t shotsFired() const { return shots_fired_; }
    bool dashing() const { return dash_ticks_>0; }
    uint8_t dashCooldown() const { return dash_cooldown_; }
    bool dashEverUsed() const { return dash_ever_used_; }
    const TrainingTarget& trainingTarget() const { return target_; }
    // Manual mode opts into active enemy logic; autoplay remains unchanged.
    void enableEnemyEncounter();
    bool enemyEncounterEnabled() const { return encounter_enabled_; }
    const GuardEnemy& guardEnemy() const { return guard_; }
    uint8_t playerHealth() const { return player_health_; }
    uint8_t playerHitFlashTicks() const { return player_hit_flash_ticks_; }
    bool secondWaveActive() const { return second_wave_active_; }
    bool stageCleared() const { return stage_cleared_; }
    const SentryEnemy& sentry() const { return sentry_; }
    const std::array<EnemyProjectile,kMaxEnemyProjectiles>&
        enemyProjectiles() const { return enemy_projectiles_; }
private:
    Scene scene_;
    Actor player_{};
    uint32_t frame_=0;
    int32_t camera_x_=0;
    bool jump_was_down_=false;
    bool facing_left_=false;
    uint8_t fire_cooldown_=0;
    uint32_t shots_fired_=0;
    uint8_t dash_ticks_=0;
    uint8_t dash_cooldown_=0;
    int8_t dash_direction_=0;
    bool dash_was_down_=false;
    bool dash_ever_used_=false;
    std::array<Projectile,kMaxProjectiles> projectiles_{};
    TrainingTarget target_{};
    bool encounter_enabled_=false;
    GuardEnemy guard_{};
    uint8_t player_health_=5;
    uint8_t player_hit_flash_ticks_=0;
    bool second_wave_active_=false;
    bool stage_cleared_=false;
    SentryEnemy sentry_{};
    std::array<EnemyProjectile,kMaxEnemyProjectiles> enemy_projectiles_{};
    void advanceSentry();
    void advanceEnemyProjectiles();
    void advanceGuard();
    void advanceProjectiles();
    void fireProjectile();
    bool collideAt(int32_t x,int32_t y) const;
    void moveHorizontal(int32_t delta);
    void moveVertical(int32_t delta);
};
}
