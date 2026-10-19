#pragma once
// A fourth live, physically controlled ground-step: measure unlit/dust
// native RGBA8888 pixels at the exact same source simulation frame.
// Does not make any statement about original NES game graphics or timing.
#include "fourth_retry_witness.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>
namespace vpd {
constexpr int kDustProofWidth=48;
constexpr int kDustProofHeight=22;
constexpr int kDustProofPixels=kDustProofWidth*kDustProofHeight;
constexpr const char* kDustProofPath=
    "sdmc:/switch/vice_project_doom/hd_footstep_evidence.txt";
struct DustFrameSample {
    std::array<uint32_t,kDustProofPixels> rgba{};
    uint64_t hash=14695981039346656037ull;
    unsigned count=0;
};
inline DustFrameSample sampleFootstep(
    const uint32_t* pixels,int width,int height,int stride_pixels,
    int heel_x,int ground_y){
    DustFrameSample result{};
    if(!pixels||width!=1280||height!=720||stride_pixels<width)return result;
    const int64_t sx=static_cast<int64_t>(heel_x)-36;
    const int64_t sy=static_cast<int64_t>(ground_y)-18;
    // Reject partial samples rather than inventing off-screen zeroes.
    if(sx<0||sy<0||sx+kDustProofWidth>width||
       sy+kDustProofHeight>height)return result;
    for(int y=0;y<kDustProofHeight;++y)
        for(int x=0;x<kDustProofWidth;++x){
            const uint32_t pixel=pixels[
                static_cast<std::size_t>(sy+y)*stride_pixels+
                static_cast<std::size_t>(sx+x)];
            result.rgba[result.count++]=pixel;
            for(int byte=0;byte<4;++byte){
                result.hash^=(pixel>>(8*byte))&255u;
                result.hash*=1099511628211ull;
            }
        }
    return result;
}
inline unsigned changedFootstepPixels(
    const DustFrameSample& before,const DustFrameSample& after){
    if(before.count!=kDustProofPixels||
       after.count!=kDustProofPixels)return 0;
    unsigned changed=0;
    for(int i=0;i<kDustProofPixels;++i)
        if(before.rgba[i]!=after.rgba[i])++changed;
    return changed;
}
inline bool writeFootstepProof(
    std::FILE* f,const Simulation& game,
    const DustFrameSample& no_dust,const DustFrameSample& dust,
    unsigned changed){
    const int32_t spawn=3*kTileSize*kFixed;
    if(!f||!fourthFresh(game)||game.frame()<8||game.frame()>100||
       !game.player().grounded||game.player().vx!=2*kFixed||
       game.player().x<spawn+16*kFixed||
       game.player().x>spawn+120*kFixed||
       no_dust.count!=kDustProofPixels||dust.count!=kDustProofPixels||
       changed<3||changed>kDustProofPixels||
       changed!=changedFootstepPixels(no_dust,dust)||
       no_dust.hash==dust.hash)return false;
    char line[440]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_HD_FOOTSTEP_V1 event=fourth_ground_move "
        "frame=%u hero_x=%ld hero_vx=512 grounded=1 "
        "hero_hp=5 guard_hp=3 shots=0 wave=0 clear=0 "
        "samples=1056 changed=%u "
        "no_dust_hash=%016llx dust_hash=%016llx "
        "same_guest_frame=yes native_framebuffer=yes "
        "source=live_guest original_game_proven=no\n",
        game.frame(),static_cast<long>(game.player().x),changed,
        static_cast<unsigned long long>(no_dust.hash),
        static_cast<unsigned long long>(dust.hash));
    return n>0&&static_cast<std::size_t>(n)<sizeof(line)&&
           std::fwrite(line,1,static_cast<std::size_t>(n),f)==
           static_cast<std::size_t>(n)&&std::fflush(f)==0;
}
inline void resetFootstepProof(bool mounted){
    if(!mounted)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(auto* f=std::fopen(kDustProofPath,"w"))std::fclose(f);
}
inline bool appendFootstepProof(
    bool mounted,const Simulation& game,
    const DustFrameSample& no_dust,const DustFrameSample& dust,
    unsigned changed){
    if(!mounted)return false;
    auto* f=std::fopen(kDustProofPath,"a");
    if(!f)return false;
    const bool ok=writeFootstepProof(f,game,no_dust,dust,changed);
    return std::fclose(f)==0&&ok;
}
} // namespace vpd
