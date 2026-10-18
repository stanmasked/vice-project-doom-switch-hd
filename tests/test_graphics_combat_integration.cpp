// Native HOST integration regression for the ROM-free training scene.
// Exercise actual simulation -> SceneView -> RGBA renderer with no NES assets.
#include "simulation.hpp"
#include "scene_renderer.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void require(bool condition, const char* message) {
    if(!condition)throw std::runtime_error(message);
}
bool solid(void* pointer,int x,int y){
    return static_cast<const vpd::Scene*>(pointer)->solid(x,y);
}
vpd::Input inputAt(unsigned frame){
    using namespace vpd;
    if(frame<110U)return Input{Fire};
    if(frame>=115U && frame<145U)return Input{Right};
    if(frame>=145U && frame<175U)
        return Input{static_cast<uint8_t>(Left | (frame<150U ? Jump : 0))};
    return Input{};
}
vpd::SceneView combatView(const vpd::Simulation& sim){
    const auto& actor=sim.player();
    vpd::SceneView v{
        actor.x/vpd::kFixed,actor.y/vpd::kFixed,sim.cameraX(),
        sim.frame(),actor.grounded,
        const_cast<vpd::Scene*>(&sim.scene()),solid
    };
    const auto& target=sim.trainingTarget();
    v.training_target_x_px=target.x/vpd::kFixed;
    v.training_target_y_px=target.y/vpd::kFixed;
    v.training_target_health=target.health;
    const auto& shots=sim.projectiles();
    static_assert(vpd::kMaxProjectiles==8,
                  "SceneView must carry all simulation projectile slots");
    require(v.projectiles.size()==shots.size(),
            "Projectile slots were lost across the graphics bridge");
    for(std::size_t i=0;i<shots.size();++i){
        v.projectiles[i]={
            shots[i].x/vpd::kFixed,shots[i].y/vpd::kFixed,
            shots[i].active
        };
    }
    return v;
}
uint64_t hashPixels(const std::vector<uint32_t>& pixels){
    uint64_t hash=14695981039346656037ULL;
    for(uint32_t pixel:pixels)
        for(unsigned shift=0;shift<32;shift+=8){
            hash^=(pixel>>shift)&255U;
            hash*=1099511628211ULL;
        }
    return hash;
}
uint64_t render(std::vector<uint32_t>& pixels,const vpd::SceneView& v){
    require(vpd::drawScene(pixels.data(),vpd::kSceneWidth,
             vpd::kSceneHeight,vpd::kSceneWidth,v),
            "Host raster rejected the combined gameplay scene");
    return hashPixels(pixels);
}
struct Report{
    uint64_t sim=0,rendered=0;
    unsigned samples=0,shots=0,hits=0;
    bool shot_visible=false, target_visible=false;
    bool damage_visible=false, destroyed_visible=false;
};
Report exercise(){
    vpd::Simulation game;
    std::vector<uint32_t> pixels(
        static_cast<std::size_t>(vpd::kSceneWidth)*vpd::kSceneHeight);
    static constexpr std::array<unsigned,7> chosen{{0,17,57,77,109,159,199}};
    Report report;
    for(unsigned frame=0;frame<200U;++frame){
        game.tick(inputAt(frame));
        bool selected=false;
        for(unsigned wanted:chosen)if(wanted==frame)selected=true;
        if(!selected)continue;
        const auto scene=combatView(game);
        const auto actual=render(pixels,scene);
        report.rendered^=actual+0x9e3779b97f4a7c15ULL+
                         (report.rendered<<6)+(report.rendered>>2);
        ++report.samples;
        if(frame==0U){
            // Both visible layers must originate in the live simulation.
            require(game.shotsFired()==1U &&
                    game.trainingTarget().health==3U,
                    "Initial shot/target state missing");
            auto no_shot=scene;
            for(auto& shot:no_shot.projectiles)shot.active=false;
            report.shot_visible=render(pixels,no_shot)!=actual;
            auto no_target=scene;
            no_target.training_target_health=0;
            report.target_visible=render(pixels,no_target)!=actual;
        }
        if(frame==57U){
            require(game.trainingTarget().health==2U,
                    "No source-observed damage by frame 58");
            auto undamaged=scene;
            undamaged.training_target_health=3U;
            report.damage_visible=render(pixels,undamaged)!=actual;
        }
        if(frame==77U){
            require(game.trainingTarget().health==0U &&
                    game.trainingTarget().hits==3U,
                    "Source target did not vanish after three actual hits");
            auto restored=scene;
            restored.training_target_health=3U;
            report.destroyed_visible=render(pixels,restored)!=actual;
        }
    }
    report.sim=game.fingerprint();
    report.shots=game.shotsFired();
    report.hits=game.trainingTarget().hits;
    return report;
}
} // namespace
int main(){
    try{
        const Report a=exercise(), b=exercise();
        require(a.samples==7U && b.samples==7U,
                "Unexpected number of gameplay-to-raster checkpoints");
        require(a.sim==5947277116621119566ULL && b.sim==a.sim,
                "Native C++ gameplay hash differs from golden replay");
        require(a.rendered!=0 && a.rendered==b.rendered,
                "GPU-independent host raster checkpoints differ");
        require(a.shots==11U && a.hits==3U &&
                b.shots==a.shots && b.hits==a.hits,
                "Gameplay-to-raster run changed damage/shot counters");
        require(a.shot_visible && b.shot_visible &&
                a.target_visible && b.target_visible &&
                a.damage_visible && b.damage_visible &&
                a.destroyed_visible && b.destroyed_visible,
                "Live combat state was not bound into actual rendered pixels");
        std::printf("VPD_ROMFREE_COMBAT_RASTER_BRIDGE_PASS "
                    "frames=200 samples=%u shots=%u hits=%u "
                    "final_sim_fingerprint=%llu "
                    "rendered_fingerprint=%llu identical_runs=yes "
                    "live_projectile=yes target_health_indicator=yes "
                    "target_damage=yes target_destruction=yes "
                    "synthetic_only=yes original_game_proven=no "
                    "switch_runtime_proven=no\n",
                    a.samples,a.shots,a.hits,
                    static_cast<unsigned long long>(a.sim),
                    static_cast<unsigned long long>(a.rendered));
        return 0;
    }catch(const std::exception& error){
        std::fprintf(stderr,"COMBAT_RASTER_BRIDGE_REJECT: %s\n",error.what());
        return 1;
    }
}
