#include "simulation.hpp"
#include "scene_renderer.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

static void verify(bool ok,const char* message) {
    if(!ok) throw std::runtime_error(message);
}
static bool tileSolid(void* context,int x,int y) {
    return static_cast<const vpd::Scene*>(context)->solid(x,y);
}
static vpd::SceneView viewOf(const vpd::Simulation& sim) {
    const auto& actor=sim.player();
    return {actor.x/vpd::kFixed,actor.y/vpd::kFixed,sim.cameraX(),
            sim.frame(),actor.grounded,
            const_cast<vpd::Scene*>(&sim.scene()),tileSolid};
}
static uint64_t imageFingerprint(const std::vector<uint32_t>& pixels) {
    uint64_t h=14695981039346656037ull;
    for(uint32_t pixel:pixels){
        for(unsigned byte=0;byte<4;++byte){
            h^=(pixel>>(byte*8))&255u;
            h*=1099511628211ull;
        }
    }
    return h;
}
int main(){
    try {
        vpd::Simulation sim;
        std::vector<uint32_t> image(vpd::kSceneWidth*vpd::kSceneHeight);
        verify(vpd::drawScene(image.data(),vpd::kSceneWidth,
                vpd::kSceneHeight,vpd::kSceneWidth,viewOf(sim)),"initial scene fails");
        const auto first=imageFingerprint(image);
        const int start=sim.player().x;
        for(int tick=0;tick<200;++tick){
            uint8_t buttons=tick<180?vpd::Right:0;
            if(tick>=15 && tick<21)buttons|=vpd::Jump;
            sim.tick(vpd::Input{buttons});
        }
        verify(sim.player().x>start,"native player never moved");
        verify(sim.cameraX()>0,"native camera did not scroll");
        verify(vpd::drawScene(image.data(),vpd::kSceneWidth,
                vpd::kSceneHeight,vpd::kSceneWidth,viewOf(sim)),"updated scene fails");
        const auto second=imageFingerprint(image);
        verify(first!=second,"native renderer ignored camera/player movement");
        std::vector<uint32_t> copy(image.size());
        verify(vpd::drawScene(copy.data(),vpd::kSceneWidth,
                vpd::kSceneHeight,vpd::kSceneWidth,viewOf(sim)),"repeat scene fails");
        verify(imageFingerprint(copy)==second,"combined game+renderer not deterministic");
        std::cout<<"PASS: native gameplay and raster renderer integrate deterministically\n";
        return 0;
    } catch(const std::exception& ex) {
        std::cerr<<"FAIL: "<<ex.what()<<'\n';
        return 1;
    }
}
