// Pure host-side deterministic tests for original ROM-free game scaffolding.
#include "simulation.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <stdexcept>

namespace {
void require(bool ok,const char* msg) {
    if(!ok)throw std::runtime_error(msg);
}
uint32_t step(uint32_t& x) {
    x^=x<<13;
    x^=x>>17;
    x^=x<<5;
    return x;
}
uint64_t mix(uint64_t hash,uint64_t value) {
    for(unsigned i=0;i<8;++i){
        hash^=static_cast<uint8_t>(value>>(i*8));
        hash*=1099511628211ULL;
    }
    return hash;
}
struct Result { uint64_t digest=0; uint64_t shots=0; uint64_t hits=0; };
Result matrix() {
    using namespace vpd;
    Result r{14695981039346656037ULL,0,0};
    for(uint32_t seed=1;seed<=16;++seed){
        Simulation first,second,control;
        uint32_t random=seed*0x9e3779b9U+0x85ebca6bU;
        uint64_t last_shots=0;
        uint8_t last_health=3;
        for(unsigned frame=0;frame<512;++frame){
            const uint32_t bits=step(random);
            const uint8_t horizontal=static_cast<uint8_t>(bits&3U);
            uint8_t buttons=horizontal==0?Left:horizontal==1?Right:0;
            if((bits&0x40U)!=0)buttons|=Jump;
            if((bits&0x80U)!=0)buttons|=Fire;
            // Self-authored geometry changes; no original game map data.
            if(frame==24 || frame==170 || frame==300){
                const bool present=frame!=170;
                first.scene().setSolid(57,3,present);
                second.scene().setSolid(57,3,present);
                control.scene().setSolid(57,3,present);
            }
            if(frame==77)control.scene().setSolid(56,4,true);
            if(frame==240)control.scene().setSolid(56,4,false);
            const Input input{buttons};
            first.tick(input);
            second.tick(input);
            control.tick(input);
            require(first.fingerprint()==second.fingerprint(),
                    "duplicated randomized gameplay run diverged");
            if(frame>=77 && frame<240)
                require(first.fingerprint()!=control.fingerprint(),
                        "remote tile mutation failed to change replay hash");
            if(frame==240)
                require(first.fingerprint()==control.fingerprint(),
                        "restoring remote tile did not restore replay hash");
            const auto& target=first.trainingTarget();
            require(target.health<=3 && target.hits<=3 &&
                    target.hits+target.health==3,
                    "target took invalid repeated damage");
            require(first.shotsFired()>=last_shots &&
                    first.shotsFired()<=frame+1U,
                    "invalid fired shot count");
            require(target.health<=last_health,
                    "target health increased without reset");
            unsigned live=0;
            for(const auto& shot:first.projectiles()){
                if(!shot.active)continue;
                ++live;
                require(shot.age<90,
                        "active projectile reached its expired lifetime");
                require(shot.vx==6*kFixed || shot.vx==-6*kFixed,
                        "projectile has invalid horizontal speed");
                const int tx=shot.x/(kFixed*kTileSize);
                const int ty=shot.y/(kFixed*kTileSize);
                require(!first.scene().solid(tx,ty),
                        "active projectile is already in solid map geometry");
            }
            require(live<=kMaxProjectiles,
                    "active projectile pool exceeded fixed capacity");
            r.digest=mix(r.digest,first.fingerprint());
            last_health=target.health;
            last_shots=first.shotsFired();
        }
        r.shots+=first.shotsFired();
        r.hits+=first.trainingTarget().hits;
    }
    return r;
}
} // namespace
int main(){
    try {
        const auto a=matrix(),b=matrix();
        require(a.digest==b.digest && a.shots==b.shots && a.hits==b.hits,
                "randomized matrix is not reproducible");
        require(a.shots==746U && a.hits==44U &&
                a.digest==6449042941889583905ULL,
                "pinned 8192-frame combat matrix witness changed");
        std::printf("VPD_ROMFREE_COMBAT_MATRIX_PASS seeds=16 frames_per_seed=512 "
                    "total_frames=8192 shots=%llu target_hits=%llu "
                    "digest=%llu independent_replays=identical "
                    "geometry_mutation=rejected geometry_restoration=clean "
                    "synthetic_only=yes original_game_proven=no "
                    "switch_runtime_proven=no\n",
                    static_cast<unsigned long long>(a.shots),
                    static_cast<unsigned long long>(a.hits),
                    static_cast<unsigned long long>(a.digest));
        return 0;
    }catch(const std::exception& exc){
        std::fprintf(stderr,"COMBAT_MATRIX_REJECT: %s\n",exc.what());
        return 1;
    }
}
