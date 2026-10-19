// Source-derived exit-gate UI must match real staged gameplay and remain
// invisible to the unchanged ROM-free auto-demo/single-guard intro.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "combat_scene_bridge.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void check(bool yes,const char* reason){
    if(!yes)throw std::runtime_error(reason);
}
bool solid(void* opaque,int tx,int ty){
    return static_cast<const vpd::Scene*>(opaque)->solid(tx,ty);
}
vpd::SceneView viewFor(const vpd::Simulation& game){
    const auto& actor=game.player();
    vpd::SceneView view{actor.x/vpd::kFixed,actor.y/vpd::kFixed,
                        game.cameraX(),game.frame(),actor.grounded,
                        const_cast<vpd::Scene*>(&game.scene()),solid};
    view.manual_controls=true;
    vpd::applyCombatOverlay(view,game);
    // Inspect the same visible portal viewport for all game states;
    // do not manufacture opening/clearing flags or hand-paint any pixels.
    view.camera_x_px=24*vpd::kTileSize;
    return view;
}
using Pixels=std::vector<uint32_t>;
Pixels draw(const vpd::SceneView& view){
    Pixels pixels(static_cast<std::size_t>(vpd::kSceneWidth)
                  *vpd::kSceneHeight);
    check(vpd::drawScene(pixels.data(),vpd::kSceneWidth,
                         vpd::kSceneHeight,vpd::kSceneWidth,view),
          "Shared RGBA scene draw failed");
    return pixels;
}
uint32_t at(const Pixels& p,int x,int y){
    return p[static_cast<std::size_t>(y)*vpd::kSceneWidth+x];
}
}
int main(){
    try{
        using namespace vpd;
        Simulation world;
        world.enableEnemyEncounter();
        auto first=viewFor(world);
        check(!first.exit_visible && !first.exit_open && !first.stage_cleared,
              "Exit gate visible before first guard defeated");
        auto first_pixels=draw(first);

        for(int i=0;i<150 && world.guardEnemy().health;++i)
            world.tick(Input{Fire});
        check(world.guardEnemy().health==0,"First guard not defeated");
        for(int i=0;i<275 && !world.secondWaveActive();++i)
            world.tick(Input{Right});
        check(world.secondWaveActive() && world.sentry().health==2,
              "Real game did not enter locked second wave");
        auto locked=viewFor(world);
        check(locked.exit_visible && !locked.exit_open &&
              !locked.stage_cleared &&
              locked.exit_x_px==55*kTileSize,
              "Locked gate is not tied to real second-wave progression");
        auto lock_pixels=draw(locked);
        const int gx=(locked.exit_x_px-locked.camera_x_px)*2;
        const int gy=(locked.exit_y_px+80)*2;
        check(gx>0 && gx<kSceneWidth-70 &&
              gy>400 && gy<kSceneHeight-85,
              "Exit gate test world position unexpectedly offscreen");
        check(at(first_pixels,gx+12,gy+12)!=
              at(lock_pixels,gx+12,gy+12),
              "Locked exit absent from host/libnx shared RGBA renderer");
        auto hidden=locked;
        hidden.manual_controls=false;
        check(at(draw(hidden),gx+12,gy+12)!=
              at(lock_pixels,gx+12,gy+12),
              "Autoplay incorrectly rendered manual-only exit gate");

        for(int i=0;i<470 && world.sentry().health;++i)
            world.tick(Input{static_cast<uint8_t>(Right|Fire)});
        check(world.sentry().health==0 &&
              world.sentry().projectile_hits==2 &&
              !world.stageCleared(),
              "Turret did not open exit before player arrival");
        auto opened=viewFor(world);
        check(opened.exit_visible && opened.exit_open && !opened.stage_cleared,
              "Real sentry defeat did not unlock exit");
        auto open_pixels=draw(opened);
        check(at(open_pixels,gx+12,gy+12)!=
              at(lock_pixels,gx+12,gy+12),
              "Gate indicator does not change when sentry is defeated");

        for(int i=0;i<350 && !world.stageCleared();++i)
            world.tick(Input{Right});
        check(world.stageCleared() && world.playerHealth()>0 &&
              world.player().x>=55*kTileSize*kFixed,
              "Living hero did not trigger original stage-clear condition");
        auto clear=viewFor(world);
        check(clear.exit_visible && clear.exit_open && clear.stage_cleared,
              "Shared scene bridge lost source-based stage-clear state");
        auto cleared_pixels=draw(clear);
        auto before=clear;
        before.stage_cleared=false;
        const auto before_pixels=draw(before);
        check(at(cleared_pixels,600,300)!=at(before_pixels,600,300),
              "Earned stage-completion banner not visible");
        check(at(cleared_pixels,gx+12,gy+12)!=
              at(lock_pixels,gx+12,gy+12),
              "Exit remains visibly locked after completing stage");

        world.reset();
        const auto reset=viewFor(world);
        check(!reset.exit_visible && !reset.exit_open && !reset.stage_cleared,
              "Reset leaked a gate-unlocked flag into the new run");
        std::puts("VPD_ROMFREE_EXIT_PORTAL_RASTER_PASS "
                  "guard_gate=yes locked_red=yes sentry_unlock=yes "
                  "stage_banner=yes demo_hidden=yes reset=yes "
                  "original_game_proven=no");
        return 0;
    }catch(const std::exception& ex){
        std::fprintf(stderr,"VPD_EXIT_PORTAL_RASTER_REJECT %s\n",ex.what());
        return 1;
    }
}
