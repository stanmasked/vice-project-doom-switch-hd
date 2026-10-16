#include "decor_layout.hpp"
#include "decor_source.hpp"
#include "scene_renderer.hpp"
#include "demo_decor_layout.hpp"
#include "demo_decor.hpp"
#include <cstdio>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)

namespace {
struct Temp {
    const std::string file="vpd_test_decor_layout.vlay";
    ~Temp(){std::remove(file.c_str());}
    void write(const std::vector<uint8_t>& d){
        FILE* f=std::fopen(file.c_str(),"wb");CHECK(f);
        CHECK(std::fwrite(d.data(),1,d.size(),f)==d.size());
        CHECK(std::fclose(f)==0);
    }
};
uint32_t crc32(const uint8_t* p,size_t n){
    uint32_t x=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        x^=p[i];
        for(unsigned k=0;k<8;++k)x=(x>>1)^((x&1)?0xedb88320u:0u);
    }
    return ~x;
}
void patchCrc(std::vector<uint8_t>& v){
    uint32_t crc=crc32(v.data()+16,v.size()-16);
    for(int k=0;k<4;++k)v[12+k]=uint8_t(crc>>(8*k));
}
uint64_t draw(vpd::DecorLayout layout,int camera=0,uint32_t tick=0){
    vpd::SpriteAtlas atlas{};
    CHECK(vpd::openAtlas(atlas,vpd_decor::kAtlasBlob,vpd_decor::kAtlasBytes));
    std::vector<uint32_t> output(vpd::kSceneWidth*vpd::kSceneHeight);
    vpd::SceneView view{};
    view.decor_atlas=&atlas;
    view.decor_layout=layout;
    view.camera_x_px=camera;
    view.frame=tick;
    CHECK(vpd::drawScene(output.data(),vpd::kSceneWidth,
                         vpd::kSceneHeight,vpd::kSceneWidth,view));
    uint64_t hash=14695981039346656037ull;
    for(uint32_t p:output)for(int k=0;k<4;++k){
        hash^=(p>>(k*8))&255u;hash*=1099511628211ull;
    }
    return hash;
}
std::vector<uint8_t> read(const char* path){
    FILE* f=std::fopen(path,"rb");CHECK(f);
    CHECK(std::fseek(f,0,SEEK_END)==0);
    long n=std::ftell(f);CHECK(n>=16 && n<=int(vpd::kDecorLayoutMaxBytes));
    CHECK(std::fseek(f,0,SEEK_SET)==0);
    std::vector<uint8_t> data(static_cast<size_t>(n));
    CHECK(std::fread(data.data(),1,data.size(),f)==data.size());
    CHECK(std::fclose(f)==0);
    return data;
}
}
int main(int argc,char** argv){
    CHECK(argc==2);
    auto blob=read(argv[1]);
    const auto& built=vpd_layout::kLayout;
    CHECK(vpd::validDecorLayout(built)&&built.count==12);
    CHECK(built.placements[0].world_x==80);
    CHECK(built.placements[0].world_y==73);
    CHECK(built.placements[1].world_y==103);
    CHECK(vpd::placedDecorFrame(built.placements[0],0)==0);
    CHECK(vpd::placedDecorFrame(built.placements[0],24)==1);
    CHECK(vpd::placedDecorFrame(built.placements[1],9)==3);
    CHECK(!vpd::validDecorPlacement({0,0,0,1,3,2,1,0}));
    CHECK(!vpd::validDecorPlacement({0,0,0,1,0,2,0,0}));

    Temp temp;
    vpd::DecorLayoutSource layout;
    CHECK(layout.reload(temp.file.c_str())==vpd::LayoutLoadResult::Uninitialized);
    CHECK(!layout.initialize({}));
    CHECK(layout.initialize(built));
    CHECK(!layout.external());
    CHECK(layout.layout().placements==built.placements);
    const auto baseline=draw(layout.layout());
    CHECK(baseline==draw(layout.layout()));
    CHECK(baseline!=draw(layout.layout(),128));
    CHECK(baseline!=draw(layout.layout(),0,24));
    CHECK(layout.loadBytes(blob.data(),blob.size())==vpd::LayoutLoadResult::Loaded);
    CHECK(layout.external());
    CHECK(draw(layout.layout())==baseline);

    // Modify a world position, update checksum and prove the scene changes.
    auto moved=blob;
    moved[16]=uint8_t(180);moved[17]=0; // first object world X=180
    patchCrc(moved);
    temp.write(moved);
    CHECK(layout.reload(temp.file.c_str())==vpd::LayoutLoadResult::Loaded);
    const auto moved_picture=draw(layout.layout());
    CHECK(moved_picture!=baseline);
    const auto accepted=layout.layout().placements;
    auto broken=moved;
    broken.back()^=1;
    temp.write(broken);
    CHECK(layout.reload(temp.file.c_str())==vpd::LayoutLoadResult::Invalid);
    CHECK(layout.layout().placements==accepted);
    CHECK(draw(layout.layout())==moved_picture);

    broken=moved;
    broken[16+7]=0; // first object has zero animation frames, but CRC fixed
    patchCrc(broken);
    temp.write(broken);
    CHECK(layout.reload(temp.file.c_str())==vpd::LayoutLoadResult::Invalid);
    CHECK(draw(layout.layout())==moved_picture);
    broken=moved;
    broken[16+8]=0;broken[16+9]=0; // zero period
    patchCrc(broken);
    CHECK(layout.loadBytes(broken.data(),broken.size())==vpd::LayoutLoadResult::Invalid);
    CHECK(draw(layout.layout())==moved_picture);
    broken=moved;
    broken[6]=65;broken[7]=0; // count >64
    CHECK(layout.loadBytes(broken.data(),broken.size())==vpd::LayoutLoadResult::Invalid);

    // Empty layouts are valid and genuinely clear decorations.
    std::vector<uint8_t> empty(blob.begin(),blob.begin()+16);
    empty[6]=0;empty[7]=0;
    for(unsigned i=12;i<16;++i)empty[i]=0;
    CHECK(layout.loadBytes(empty.data(),empty.size())==vpd::LayoutLoadResult::Loaded);
    CHECK(layout.layout().count==0);
    CHECK(draw(layout.layout())!=baseline); // empty case must not silently fall back
    CHECK(layout.loadBytes(moved.data(),moved.size())==vpd::LayoutLoadResult::Loaded);
    layout.reset();
    CHECK(!layout.external());
    CHECK(layout.layout().placements==built.placements);
    CHECK(draw(layout.layout())==baseline);
    puts("PASS: authored VLAY records, CRC, empty layouts, per-prop animation, rollback and camera");
}
