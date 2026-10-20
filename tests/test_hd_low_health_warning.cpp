// ROM-free native regression for the opt-in source-health HD warning.
// The warning is a renderer overlay, not a physics or HP transition.
#include "combat_scene_bridge.hpp"
#include "scene_renderer.hpp"
#include "simulation.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace {
void require(bool v,const char* why){if(!v)throw std::runtime_error(why);}
constexpr int W=vpd::kSceneWidth, H=vpd::kSceneHeight;
uint32_t rgba(unsigned r,unsigned g,unsigned b){
    return 0xff000000u | r | (g<<8) | (b<<16);
}
bool solid(void* p,int x,int y){
    return static_cast<const vpd::Scene*>(p)->solid(x,y);
}
std::vector<uint32_t> render(const vpd::SceneView& view){
    std::vector<uint32_t> img(static_cast<std::size_t>(W)*H);
    require(vpd::drawScene(img.data(),W,H,W,view),"native scene drawing failed");
    return img;
}
uint32_t px(const std::vector<uint32_t>& img,int x,int y){
    return img[static_cast<std::size_t>(y)*W+x];
}
bool warningPixel(int x,int y){
    return (x>=757 && x<836 && y>=34 && y<37) ||
           (x>=846 && x<919 && y>=17 && y<31);
}
void sameOutsideWarning(const std::vector<uint32_t>& off,
                        const std::vector<uint32_t>& on){
    for(int y=0;y<H;++y)
        for(int x=0;x<W;++x)
            if(!warningPixel(x,y))
                require(px(off,x,y)==px(on,x,y),
                        "low-health HD warning changed actor/world/HP pixels");
}
}
int main(){
    try {
        vpd::Simulation sim;
        sim.enableEnemyEncounter();
        // Actual guard strikes must lower the authoritative Simulation HP.
        bool low=false;
        for(int n=0;n<600;++n){
            sim.tick(vpd::Input{vpd::Right});
            if(sim.playerHealth()==2){low=true;break;}
        }
        require(low && sim.guardEnemy().attacks>=3,
                "real guard contact failed to reach two health");
        const auto stable=sim.fingerprint();
        const auto& player=sim.player();
        vpd::SceneView lowView{
            player.x/vpd::kFixed,player.y/vpd::kFixed,
            sim.cameraX(),sim.frame(),player.grounded,
            const_cast<vpd::Scene*>(&sim.scene()),solid
        };
        lowView.manual_controls=true;
        vpd::applyCombatOverlay(lowView,sim);
        require(lowView.player_health==2 && lowView.guard.enabled,
                "real combat bridge did not propagate low HP");
        lowView.frame=(lowView.frame/24u)*24u;
        const auto off=render(lowView);
        lowView.hd_low_health_warning=true;
        const auto on=render(lowView);
        require(px(on,760,34)==rgba(237,115,112) &&
                px(on,846,17)!=px(off,846,17),
                "visual low HP cue or label absent");
        sameOutsideWarning(off,on);
        // The source-authoritative five HP cells must stay bit-for-bit
        // identical, including source-owned yellow flash and empties.
        for(int y=18;y<30;++y)
            for(int x=761;x<833;++x)
                require(px(off,x,y)==px(on,x,y),
                        "HD warning modified genuine heart cell pixels");
        require(sim.fingerprint()==stable,
                "renderer changed gameplay state after low-health cue");
        lowView.frame+=12;
        const auto phaseOff=render(lowView);
        auto expectedQuiet=lowView;
        expectedQuiet.hd_low_health_warning=false;
        require(phaseOff==render(expectedQuiet),
                "source frame phase should extinguish all warning pixels");
        // Ineligible conditions: 3+ HP, 0 HP, earned stage clear, demo.
        for(unsigned hp: {0u,3u,5u}){
            auto other=lowView;
            other.player_health=static_cast<uint8_t>(hp);
            other.frame=24;
            other.hd_low_health_warning=false;
            const auto a=render(other);
            other.hd_low_health_warning=true;
            require(render(other)==a,
                    "HD warning leaked outside one/two HP");
        }
        auto cleared=lowView;
        cleared.frame=24;
        cleared.stage_cleared=true;
        cleared.hd_low_health_warning=false;
        const auto clean=render(cleared);
        cleared.hd_low_health_warning=true;
        require(render(cleared)==clean,"HD warning leaked to stage clear");
        auto demo=lowView;
        demo.frame=24;
        demo.manual_controls=false;
        demo.hd_low_health_warning=false;
        const auto legacy=render(demo);
        demo.hd_low_health_warning=true;
        require(render(demo)==legacy,
                "HD warning leaked into untouched attract-mode pixels");
        require(sim.fingerprint()==stable,
                "HD status checks changed source-derived combat fingerprint");
        std::puts("VPD_HD_LOW_HEALTH_WARNING_PASS "
                  "real_guard_damage_to_hp2=yes pulse_12_on_12_off=yes "
                  "four_real_heart_cells_unchanged=yes "
                  "hd_toggle_visual_only=yes legacy_demo_unchanged=yes "
                  "source_simulation_unchanged=yes original_game_proven=no");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_HD_LOW_HEALTH_WARNING_FAIL %s\n",e.what());
        return 1;
    }
}
