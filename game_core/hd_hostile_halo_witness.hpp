#pragma once
// CPU RGBA8888 witness for a source-owned active sentry projectile.
// This is authored ROM-free homebrew behavior, NOT a NES fidelity claim.
#include "simulation.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>
namespace vpd {
constexpr int kHostileHaloBox=32;
constexpr unsigned kHostileHaloSamples=1024u;
constexpr const char* kHostileHaloWitnessPath=
    "sdmc:/switch/vice_project_doom/hd_hostile_halo_witness.txt";
struct HostileHaloSample {
    std::array<uint32_t,kHostileHaloSamples> rgba{};
    uint64_t hash=14695981039346656037ull;
    unsigned count=0;
};
inline HostileHaloSample sampleHostileHalo(
    const uint32_t* pixels,int width,int height,int stride,
    int center_x,int center_y){
    HostileHaloSample result{};
    if(!pixels || width!=1280 || height!=720 || stride<width)
        return result;
    const int64_t x0=static_cast<int64_t>(center_x)-16;
    const int64_t y0=static_cast<int64_t>(center_y)-16;
    if(x0<0 || y0<0 || x0+kHostileHaloBox>width ||
       y0+kHostileHaloBox>height)return result;
    for(int y=0;y<kHostileHaloBox;++y)
        for(int x=0;x<kHostileHaloBox;++x){
            const uint32_t value=pixels[
                static_cast<std::size_t>(y0+y)*stride+
                static_cast<std::size_t>(x0+x)];
            result.rgba[result.count++]=value;
            for(unsigned byte=0;byte<4;++byte){
                result.hash^=(value>>(byte*8u))&255u;
                result.hash*=1099511628211ull;
            }
        }
    return result;
}
inline unsigned countHostileHaloChanges(
    const HostileHaloSample& original,const HostileHaloSample& lit){
    if(original.count!=kHostileHaloSamples ||
       lit.count!=kHostileHaloSamples)return 0;
    unsigned changes=0;
    for(unsigned i=0;i<kHostileHaloSamples;++i)
        changes+=original.rgba[i]!=lit.rgba[i]?1u:0u;
    return changes;
}
inline bool writeHostileHaloWitness(
    std::FILE* file,const Simulation& game,unsigned slot,
    const HostileHaloSample& original,const HostileHaloSample& lit,
    unsigned changed){
    if(!file || !game.enemyEncounterEnabled() ||
       !game.secondWaveActive() || game.stageCleared() ||
       game.guardEnemy().health!=0 || game.playerHealth()==0 ||
       game.sentry().health==0 || game.sentry().shots_fired==0 ||
       slot>=kMaxEnemyProjectiles ||
       original.count!=kHostileHaloSamples ||
       lit.count!=kHostileHaloSamples ||
       changed<3u || changed>kHostileHaloSamples ||
       changed!=countHostileHaloChanges(original,lit) ||
       original.hash==lit.hash)return false;
    const auto& bullet=game.enemyProjectiles()[slot];
    if(!bullet.active || bullet.vx==0 || bullet.age>=90)return false;
    char line[512]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_HOSTILE_HALO_V1 event=fourth_turret_bullet "
        "frame=%u bullet_slot=%u bullet_x=%ld bullet_y=%ld "
        "bullet_age=%u bullet_vx=%ld "
        "sentry_hp=%u sentry_shots=%u guard_hp=0 wave=1 clear=0 "
        "hero_hp=%u samples=1024 changed=%u "
        "unlit_hash=%016llx lit_hash=%016llx "
        "same_guest_frame=yes native_framebuffer=yes "
        "source=live_guest original_game_proven=no\n",
        game.frame(),slot,static_cast<long>(bullet.x),
        static_cast<long>(bullet.y),static_cast<unsigned>(bullet.age),
        static_cast<long>(bullet.vx),
        static_cast<unsigned>(game.sentry().health),
        static_cast<unsigned>(game.sentry().shots_fired),
        static_cast<unsigned>(game.playerHealth()),changed,
        static_cast<unsigned long long>(original.hash),
        static_cast<unsigned long long>(lit.hash));
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),file)==
               static_cast<std::size_t>(n) && std::fflush(file)==0;
}
inline void resetHostileHaloWitness(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(auto* f=std::fopen(kHostileHaloWitnessPath,"w"))std::fclose(f);
}
inline bool appendHostileHaloWitness(
    bool sd,const Simulation& game,unsigned slot,
    const HostileHaloSample& original,const HostileHaloSample& lit,
    unsigned changed){
    if(!sd)return false;
    std::FILE* file=std::fopen(kHostileHaloWitnessPath,"a");
    if(!file)return false;
    const bool ok=writeHostileHaloWitness(
        file,game,slot,original,lit,changed);
    return std::fclose(file)==0 && ok;
}
} // namespace vpd
