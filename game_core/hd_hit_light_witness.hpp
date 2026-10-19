#pragma once
// Evidence from two renders of the SAME real source hit, one unlit and
// one lit, directly from the libnx framebuffer (not an authored screenshot).
#include "simulation.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kHitLightEvidencePath=
    "sdmc:/switch/vice_project_doom/hd_hit_light_evidence.txt";
struct ImpactSample {
    uint64_t hash=14695981039346656037ull;
    uint32_t values[25]{};
    unsigned count=0;
};
inline ImpactSample sampleGuardImpact(
    const uint32_t* pixels,int width,int height,int stride,
    int32_t center_x,int32_t center_y){
    ImpactSample result{};
    if(!pixels || width!=1280 || height!=720 || stride<width)return result;
    for(int y=-24;y<=24;y+=12)
        for(int x=-24;x<=24;x+=12){
            const int64_t sx=static_cast<int64_t>(center_x)+x;
            const int64_t sy=static_cast<int64_t>(center_y)+y;
            if(sx<0 || sx>=width || sy<0 || sy>=height)continue;
            const auto rgba=pixels[static_cast<std::size_t>(sy)*stride+
                                   static_cast<std::size_t>(sx)];
            result.values[result.count++]=rgba;
            for(int b=0;b<4;++b){
                result.hash^=(rgba>>(8*b))&255u;
                result.hash*=1099511628211ull;
            }
        }
    return result;
}
inline unsigned diffGuardImpactSamples(const ImpactSample& before,
                                       const ImpactSample& after){
    if(before.count!=25 || after.count!=25)return 0;
    unsigned changes=0;
    for(unsigned i=0;i<25;++i)
        if(before.values[i]!=after.values[i])++changes;
    return changes;
}
inline bool writeHitLightEvidence(
    std::FILE* f,const Simulation& game,const ImpactSample& no_light,
    const ImpactSample& with_light,unsigned altered){
    if(!f || !game.enemyEncounterEnabled() || game.frame()==0 ||
       game.playerHealth()!=5 || game.guardEnemy().health!=2 ||
       game.guardEnemy().projectile_hits!=1 ||
       game.guardEnemy().hit_flash_ticks==0 ||
       game.guardEnemy().attacks!=0 || game.shotsFired()!=1 ||
       game.sentry().health!=2 || game.secondWaveActive() ||
       game.stageCleared() || game.dashEverUsed() ||
       no_light.count!=25 || with_light.count!=25 ||
       altered<3 || altered>25 || no_light.hash==with_light.hash ||
       altered!=diffGuardImpactSamples(no_light,with_light))
        return false;
    char line[420]{};
    const int n=std::snprintf(
        line,sizeof(line),
        "VPD_ROMFREE_HD_HIT_LIGHT_V1 event=source_guard_impact "
        "frame=%u guard_hp=2 guard_hits=1 guard_flash=%u "
        "hero_hp=5 shots=1 sentry_hp=2 wave=0 clear=0 "
        "samples=25 changed=%u "
        "unlit_hash=%016llx lit_hash=%016llx "
        "same_simulation_frame=yes native_framebuffer=yes "
        "source=live_guest original_game_proven=no\n",
        game.frame(),static_cast<unsigned>(game.guardEnemy().hit_flash_ticks),
        altered,static_cast<unsigned long long>(no_light.hash),
        static_cast<unsigned long long>(with_light.hash));
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),f)==
           static_cast<std::size_t>(n) && std::fflush(f)==0;
}
inline void resetHitLightEvidence(bool sd){
    if(!sd)return;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    if(std::FILE* f=std::fopen(kHitLightEvidencePath,"w"))std::fclose(f);
}
inline bool appendHitLightEvidence(
    bool sd,const Simulation& game,const ImpactSample& unlit,
    const ImpactSample& lit,unsigned changed){
    if(!sd)return false;
    auto* f=std::fopen(kHitLightEvidencePath,"a");
    if(!f)return false;
    const bool ok=writeHitLightEvidence(f,game,unlit,lit,changed);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
