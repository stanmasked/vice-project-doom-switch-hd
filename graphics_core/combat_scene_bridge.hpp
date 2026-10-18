#pragma once
// ROM-free bridge shared *without modification* by libnx frontend and
// native host raster integration tests. No commercial game assets.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include <tuple>

namespace vpd {
inline void applyCombatOverlay(SceneView& view,const Simulation& game) {
    static_assert(
        std::tuple_size<decltype(SceneView{}.projectiles)>::value==
        kMaxProjectiles,
        "SceneView projectile capacity must match game_core exactly");
    const auto& target=game.trainingTarget();
    view.training_target_x_px=target.x/kFixed;
    view.training_target_y_px=target.y/kFixed;
    view.training_target_health=target.health;
    view.dash_active=game.dashing();
    view.dash_cooldown=game.dashCooldown();
    view.dash_ever_used=game.dashEverUsed();
    const auto& guard=game.guardEnemy();
    view.guard={guard.x/kFixed,guard.y/kFixed,guard.health,
                game.enemyEncounterEnabled(),guard.alerted};
    view.player_health=game.playerHealth();
    const auto& shots=game.projectiles();
    for(std::size_t i=0;i<kMaxProjectiles;++i){
        view.projectiles[i]={
            shots[i].x/kFixed,
            shots[i].y/kFixed,
            shots[i].active
        };
    }
}
} // namespace vpd
