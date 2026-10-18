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
enum Buttons : uint8_t { Left=1, Right=2, Jump=4, Fire=8 };
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
class Scene {
public:
    Scene();
    bool solid(int tile_x,int tile_y) const;
    void setSolid(int tile_x,int tile_y,bool value);
    char cell(int tile_x,int tile_y) const;
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
private:
    Scene scene_;
    Actor player_{};
    uint32_t frame_=0;
    int32_t camera_x_=0;
    bool jump_was_down_=false;
    bool facing_left_=false;
    uint8_t fire_cooldown_=0;
    uint32_t shots_fired_=0;
    std::array<Projectile,kMaxProjectiles> projectiles_{};
    void advanceProjectiles();
    void fireProjectile();
    bool collideAt(int32_t x,int32_t y) const;
    void moveHorizontal(int32_t delta);
    void moveVertical(int32_t delta);
};
}
