#include "simulation.hpp"
#include "scene_renderer.hpp"
#include "asset_atlas.hpp"
#include "animation.hpp"
#include "demo_atlas.hpp"
#include "demo_animation.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <vector>
#define CHECK(x) do { if(!(x)) throw std::runtime_error(#x); } while(0)
static bool solidAt(void* p,int x,int y){
    return static_cast<const vpd::Scene*>(p)->solid(x,y);
}
static uint64_t hashPixels(const std::vector<uint32_t>& pixels){
    uint64_t hash=14695981039346656037ull;
    for(uint32_t p:pixels)for(int b=0;b<4;++b){
        hash^=(p>>(8*b))&255u;
        hash*=1099511628211ull;
    }
    return hash;
}
struct Result {
    uint64_t fingerprint=0;
    uint32_t visited=0;
    uint64_t rendered_hash=0;
};
static Result playback(){
    vpd::Simulation game;
    vpd::SpriteAtlas atlas{};
    CHECK(vpd::openAtlas(atlas,vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes));
    CHECK(vpd::validAnimationBank(vpd_demo::kAnimationBank));
    CHECK(vpd_demo::kAnimationBank.atlas_frame_count==atlas.frame_count);
    vpd::AnimationPlayer animator;
    std::vector<uint32_t> pixels(vpd::kSceneWidth*vpd::kSceneHeight);
    Result result;
    const int samples[]={0,12,24,39,79,129,199};
    for(int tick=0;tick<200;++tick){
        uint8_t buttons=tick<180?vpd::Right:0;
        if(tick>=12&&tick<17)buttons|=vpd::Jump;
        game.tick(vpd::Input{buttons});
        const auto& actor=game.player();
        CHECK(animator.tick(vpd_demo::kAnimationBank,
                            {actor.grounded,actor.vx!=0,actor.vy,actor.vx}));
        result.visited|=1u<<static_cast<unsigned>(animator.state());
        bool render=false;
        for(int index:samples)if(index==tick)render=true;
        if(render){
            vpd::SceneView v{
                actor.x/vpd::kFixed,actor.y/vpd::kFixed,game.cameraX(),
                game.frame(),actor.grounded,
                const_cast<vpd::Scene*>(&game.scene()),solidAt,
                &atlas,actor.vx!=0
            };
            v.sprite_frame=animator.frame(vpd_demo::kAnimationBank);
            v.facing_left=animator.facingLeft();
            CHECK(vpd::drawScene(pixels.data(),vpd::kSceneWidth,
                                 vpd::kSceneHeight,vpd::kSceneWidth,v));
            result.rendered_hash^=hashPixels(pixels)+(result.rendered_hash<<6)
                                           +(result.rendered_hash>>2);
        }
    }
    result.fingerprint=game.fingerprint();
    return result;
}
int main(){
    try{
        auto a=playback(),b=playback();
        CHECK(a.rendered_hash==b.rendered_hash);
        CHECK(a.fingerprint==b.fingerprint);
        CHECK(a.rendered_hash!=0);
        CHECK((a.visited & 0x7u)==0x7u); // idle, run, rise
        CHECK((a.visited & 0x8u)!=0u);    // fall
        puts("PASS: simulation, JSON animation manifest, VPAT atlas and native raster are deterministic");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"FAIL: %s\n",e.what());
        return 1;
    }
}
