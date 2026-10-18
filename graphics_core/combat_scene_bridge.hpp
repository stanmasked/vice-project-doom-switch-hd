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
                game.enemyEncounterEnabled(),guard.alerted,
                guard.hit_flash_ticks};
    view.player_health=game.playerHealth();
    view.player_hit_flash_ticks=game.playerHitFlashTicks();
    static_assert(std::tuple_size<decltype(SceneView{}.enemy_projectiles)>::value
                  ==kMaxEnemyProjectiles,
                  "Sentry projectile capacities must agree");
    const auto& turret=game.sentry();
    view.sentry={turret.x/kFixed,turret.y/kFixed,turret.health,
                 turret.hit_flash_ticks,game.secondWaveActive()};
    view.stage_cleared=game.stageCleared();
    const auto& hostile=game.enemyProjectiles();
    for(std::size_t i=0;i<kMaxEnemyProjectiles;++i)
        view.enemy_projectiles[i]={hostile[i].x/kFixed,
                                  hostile[i].y/kFixed,hostile[i].active};
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
