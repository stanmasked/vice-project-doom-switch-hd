#include "terrain_source.hpp"
#include "scene_renderer.hpp"
#include "demo_terrain.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>
#define CHECK(x) do { if(!(x))throw std::runtime_error(#x); } while(0)

namespace {
struct LocalFile {
    std::string path="vpd_terrain_synthetic_reload.vpat";
    ~LocalFile(){std::remove(path.c_str());}
    void write(const std::vector<uint8_t>& bytes) const {
        auto* f=std::fopen(path.c_str(),"wb");CHECK(f);
        CHECK(std::fwrite(bytes.data(),1,bytes.size(),f)==bytes.size());
        CHECK(std::fclose(f)==0);
    }
};
uint32_t crc32(const uint8_t* p,size_t n){
    uint32_t c=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        c^=p[i];
        for(int k=0;k<8;++k)c=(c>>1)^((c&1u)?0xedb88320u:0);
    }
    return ~c;
}
void patchCrc(std::vector<uint8_t>& raw){
    uint32_t sum=crc32(raw.data()+vpd::kVpatHeaderBytes,raw.size()-vpd::kVpatHeaderBytes);
    for(unsigned i=0;i<4;++i)raw[18+i]=uint8_t(sum>>(8*i));
}
uint64_t fingerprint(const std::vector<uint32_t>& pixels){
    uint64_t c=14695981039346656037ull;
    for(auto p:pixels)for(unsigned i=0;i<4;++i){
        c^=(p>>(8*i))&255u;c*=1099511628211ull;
    }
    return c;
}
bool syntheticMap(void*,int x,int y){
    if(y==14)return true;
    return x==15 && y>=9 && y<=13;
}
uint64_t render(vpd::SceneView view){
    std::vector<uint32_t> pixels(vpd::kSceneWidth*vpd::kSceneHeight);
    CHECK(vpd::drawScene(pixels.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                         vpd::kSceneWidth,view));
    return fingerprint(pixels);
}
}
int main() {
    vpd::TerrainSource terrain;
    LocalFile file;
    CHECK(terrain.reload(file.path.c_str())==vpd::TerrainReload::Uninitialized);
    CHECK(!terrain.initialize(nullptr,0));
    CHECK(terrain.initialize(vpd_terrain::kAtlasBlob,vpd_terrain::kAtlasBytes));
    CHECK(vpd::terrainScale(terrain.atlas())==2);
    CHECK(terrain.atlas().frame_count==4);
    CHECK(!terrain.external());
    CHECK(vpd::terrainFrame(false,true,true,2,4)==0);
    CHECK(vpd::terrainFrame(false,true,true,3,4)==1);
    CHECK(vpd::terrainFrame(true,false,true,3,4)==2);
    CHECK(vpd::terrainFrame(true,true,false,3,4)==3);
    CHECK(vpd::terrainFrame(true,true,true,3,4)==1);

    vpd::SceneView view{};
    view.solid_at=syntheticMap;
    view.player_x_px=40;
    view.player_y_px=208;
    const auto without=render(view);
    view.terrain_atlas=&terrain.atlas();
    const auto embedded=render(view);
    CHECK(without!=embedded);
    CHECK(embedded==render(view));

    const auto* builtin=terrain.atlas().pixels;
    CHECK(terrain.reload("missing_dev_terrain.vpat")==vpd::TerrainReload::Missing);
    CHECK(terrain.atlas().pixels==builtin);

    std::vector<uint8_t> raw(vpd_terrain::kAtlasBlob,
                             vpd_terrain::kAtlasBlob+vpd_terrain::kAtlasBytes);
    raw[vpd::kVpatHeaderBytes]^=0x55u;
    patchCrc(raw);
    file.write(raw);
    CHECK(terrain.reload(file.path.c_str())==vpd::TerrainReload::Loaded);
    CHECK(terrain.external());
    const auto* external=terrain.atlas().pixels;
    CHECK(external!=builtin);
    const auto changed=render(view);
    CHECK(changed!=embedded);

    auto bad=raw;
    bad.back()^=1;
    file.write(bad);
    CHECK(terrain.reload(file.path.c_str())==vpd::TerrainReload::Invalid);
    CHECK(terrain.atlas().pixels==external);
    CHECK(render(view)==changed);

    bad=raw;
    bad[10]=8;bad[11]=0; // syntactically valid 8x16 cells but not square
    file.write(bad);
    CHECK(terrain.reload(file.path.c_str())==vpd::TerrainReload::UnsupportedGeometry);
    CHECK(terrain.atlas().pixels==external);
    CHECK(render(view)==changed);

    bad=raw;
    bad[14]=3;bad[15]=0;
    file.write(bad);
    CHECK(terrain.reload(file.path.c_str())==vpd::TerrainReload::Invalid);
    CHECK(terrain.atlas().pixels==external);

    terrain.reset();
    CHECK(!terrain.external()&&terrain.atlas().pixels==builtin);
    CHECK(render(view)==embedded);
    puts("PASS: environment tiles, external reload, pixel output, invalid geometry and rollback");
}
