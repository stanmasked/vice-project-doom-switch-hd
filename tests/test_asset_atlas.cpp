#include "asset_atlas.hpp"
#include "scene_renderer.hpp"
#include "demo_atlas.hpp"
#include <stdexcept>
#define CHECK(expr) do { if (!(expr)) throw std::runtime_error(#expr); } while (0)
#include <cstdint>
#include <cstdio>
#include <vector>
#include <cstring>

static uint64_t hash(const std::vector<uint32_t>& b) {
    uint64_t h=14695981039346656037ull;
    for(uint32_t p:b)for(unsigned k=0;k<4;++k){h^=(p>>(k*8))&255;h*=1099511628211ull;}
    return h;
}
int main(){
    vpd::SpriteAtlas a;
    CHECK(vpd::openAtlas(a,vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes));
    CHECK(a.width==96&&a.height==32&&a.frame_width==24&&a.frame_height==32&&a.frame_count==4);
    std::vector<uint8_t> broken(vpd_demo::kAtlasBlob,vpd_demo::kAtlasBlob+vpd_demo::kAtlasBytes);
    auto bad=[&] {vpd::SpriteAtlas invalid; CHECK(!vpd::openAtlas(invalid,broken.data(),broken.size())); CHECK(invalid.pixels==nullptr);};
    broken.back()^=1;bad();broken.back()^=1;
    broken[0]='X';bad();broken[0]='V';
    broken[6]=0;broken[7]=0;bad();broken[6]=96;
    broken[14]=99;bad();broken[14]=4;
    vpd::SpriteAtlas empty;
    CHECK(!vpd::openAtlas(empty,nullptr,0));
    CHECK(!vpd::openAtlas(empty,broken.data(),broken.size()-1));
    constexpr int w=100,h=100,stride=103;
    std::vector<uint32_t> image(stride*h,0xff202030u);
    CHECK(vpd::blitAtlasFrame(image.data(),w,h,stride,a,0,25,16,2));
    const auto still=hash(image);
    bool found_hero=false;
    for(int y=16;y<80;++y)for(int x=25;x<73;++x)
      if(image[y*stride+x]!=0xff202030u)found_hero=true;
    CHECK(found_hero);
    for(int y=0;y<h;++y)for(int x=w;x<stride;++x)
      CHECK(image[y*stride+x]==0xff202030u);
    std::fill(image.begin(),image.end(),0xff202030u);
    CHECK(vpd::blitAtlasFrame(image.data(),w,h,stride,a,1,25,16,2));
    CHECK(hash(image)!=still);
    CHECK(vpd::blitAtlasFrame(image.data(),w,h,stride,a,3,-40,84,3));
    CHECK(!vpd::blitAtlasFrame(image.data(),w,h,stride,a,4,0,0,1));
    CHECK(!vpd::blitAtlasFrame(image.data(),w,h,stride,a,0,0,0,0));
    CHECK(!vpd::blitAtlasFrame(nullptr,w,h,stride,a,0,0,0,1));
    puts("PASS: VPAT v1 header validation, CRC, blitting, frame differences, clipping and guards");
}
