#include "scene_renderer.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <fstream>

static void check(bool ok,const char* what) {
    if(!ok)throw std::runtime_error(what);
}
static bool solid(void*,int x,int y) {
    return y==14 || (y==11 && x>=12 && x<=21) ||
           (y==9 && x>=28 && x<=35) ||
           (y==12 && x>=43 && x<=52);
}
static uint64_t checksum(const std::vector<uint32_t>& pixels,int stride) {
    uint64_t h=14695981039346656037ull;
    for(int y=0;y<vpd::kSceneHeight;++y)
        for(int x=0;x<vpd::kSceneWidth;++x) {
            uint32_t v=pixels[static_cast<size_t>(y)*stride+x];
            for(int i=0;i<4;++i) {h^=(v>>(8*i))&255;h*=1099511628211ull;}
        }
    return h;
}
int main(int argc,char** argv) {
    try {
        constexpr int stride=vpd::kSceneWidth+32;
        const uint32_t guard=0x6f99c0ffu;
        std::vector<uint32_t> image(static_cast<size_t>(stride)*vpd::kSceneHeight,guard);
        vpd::SceneView view;
        view.map_context=nullptr;
        view.solid_at=solid;
        view.player_x_px=48;
        view.player_y_px=210;
        view.grounded=true;
        check(vpd::drawScene(image.data(),vpd::kSceneWidth,vpd::kSceneHeight,stride,view),"draw failed");
        const uint64_t original=checksum(image,stride);
        // Pinned ROM-free reference includes the embedded-asset HUD indicator.
        check(original==11599697196412129738ull,
              "rendered screenshot does not match approved synthetic golden frame");
        for(int y=0;y<vpd::kSceneHeight;++y)
            for(int x=vpd::kSceneWidth;x<stride;++x)
                check(image[static_cast<size_t>(y)*stride+x]==guard,"row-padding corruption");
        std::vector<uint32_t> repeat(image.size(),guard);
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,vpd::kSceneHeight,stride,view),"repeat draw failed");
        check(checksum(repeat,stride)==original,"nondeterministic pixels");
        // Live projectiles alter only the optional asset-free shot layer.
        view.projectiles[0]={100,210,true};
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,
                             vpd::kSceneHeight,stride,view),
              "fired projectile raster failed");
        const uint64_t shot_hash=checksum(repeat,stride);
        check(shot_hash!=original,"visible shot did not change framebuffer");
        check(vpd::drawScene(image.data(),vpd::kSceneWidth,
                             vpd::kSceneHeight,stride,view),
              "repeated projectile raster failed");
        check(checksum(image,stride)==shot_hash,
              "projectile raster is not deterministic");
        view.projectiles[0].active=false;
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,
                             vpd::kSceneHeight,stride,view),
              "inactive projectile raster failed");
        check(checksum(repeat,stride)==original,
              "inactive projectile changed approved legacy frame");
        view.training_target_x_px=400;
        view.training_target_y_px=208;
        view.training_target_health=3;
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,
                             vpd::kSceneHeight,stride,view),
              "combat target raster failed");
        const uint64_t full_target_hash=checksum(repeat,stride);
        check(full_target_hash!=original,
              "live target not visible in synthetic scene");
        view.training_target_health=1;
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,
                             vpd::kSceneHeight,stride,view),
              "damaged target raster failed");
        check(checksum(repeat,stride)!=full_target_hash,
              "changing target health did not update visual indicator");
        view.training_target_health=0;
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,
                             vpd::kSceneHeight,stride,view),
              "removed target raster failed");
        check(checksum(repeat,stride)==original,
              "destroyed target left pixels in old golden frame");
        view.camera_x_px=160;
        view.player_x_px=350;
        view.frame=6;
        view.grounded=false;
        check(vpd::drawScene(repeat.data(),vpd::kSceneWidth,vpd::kSceneHeight,stride,view),"scrolled draw failed");
        check(checksum(repeat,stride)!=original,"scroll/player must change output");
        check(!vpd::drawScene(nullptr,vpd::kSceneWidth,vpd::kSceneHeight,stride,view),"null pointer allowed");
        check(!vpd::drawScene(image.data(),100,200,stride,view),"invalid dimensions allowed");
        check(!vpd::drawScene(image.data(),vpd::kSceneWidth,vpd::kSceneHeight,1,view),"bad stride allowed");
        if(argc==2) {
            std::ofstream file(argv[1],std::ios::binary);
            check(bool(file),"cannot create screenshot");
            file<<"P6\n"<<vpd::kSceneWidth<<' '<<vpd::kSceneHeight<<"\n255\n";
            for(int y=0;y<vpd::kSceneHeight;++y)
                for(int x=0;x<vpd::kSceneWidth;++x){
                    uint32_t p=image[static_cast<size_t>(y)*stride+x];
                    file.put(static_cast<char>(p&255));
                    file.put(static_cast<char>((p>>8)&255));
                    file.put(static_cast<char>((p>>16)&255));
                }
            check(bool(file),"screenshot save failed");
        }
        std::cout<<"PASS: scene raster, row padding, deterministic output, scroll, invalid arguments; FNV="<<original<<'\n';
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
