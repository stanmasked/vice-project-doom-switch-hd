#include "simulation.hpp"
#include <algorithm>
#include <cstdint>

namespace vpd {
namespace {
constexpr int32_t kRunSpeed=2*kFixed;
constexpr int32_t kGravity=54;
constexpr int32_t kMaxFall=5*kFixed;
constexpr int32_t kJumpVelocity=-5*kFixed;
constexpr int32_t kProjectileSpeed=6*kFixed;
constexpr uint16_t kProjectileLifetime=90;
constexpr uint8_t kFireInterval=10;
// Fixed point floor division, including negatives.
int floorDiv(int value,int divisor) {
    int quotient=value/divisor;
    int remainder=value%divisor;
    return quotient-(remainder<0 ? 1:0);
}
}
Scene::Scene() {
    for(int x=0;x<kMapWidth;++x) setSolid(x,kMapHeight-1,true);
    for(int x=12;x<=21;++x) setSolid(x,11,true);
    for(int x=28;x<=35;++x) setSolid(x,9,true);
    for(int x=43;x<=52;++x) setSolid(x,12,true);
    for(int y=11;y<=13;++y) setSolid(59,y,true);
}
bool Scene::solid(int tx,int ty) const {
    if(tx<0 || tx>=kMapWidth || ty>=kMapHeight) return true;
    if(ty<0) return false;
    return tiles_[static_cast<std::size_t>(ty)*kMapWidth+static_cast<std::size_t>(tx)]!=0;
}
void Scene::setSolid(int tx,int ty,bool value) {
    if(tx>=0 && tx<kMapWidth && ty>=0 && ty<kMapHeight)
        tiles_[static_cast<std::size_t>(ty)*kMapWidth+static_cast<std::size_t>(tx)]=value?1:0;
}
char Scene::cell(int tx,int ty) const { return solid(tx,ty)?'#':' '; }
Simulation::Simulation(){ reset(); }
void Simulation::reset(){
    scene_=Scene{};
    player_=Actor{};
    player_.x=3*kTileSize*kFixed;
    player_.y=((kMapHeight-1)*kTileSize-kPlayerHeight)*kFixed;
    player_.grounded=true;
    frame_=0;
    camera_x_=0;
    jump_was_down_=false;
    facing_left_=false;
    fire_cooldown_=0;
    shots_fired_=0;
    projectiles_.fill(Projectile{});
}
bool Simulation::collideAt(int32_t x,int32_t y) const{
    constexpr int tile=kTileSize*kFixed;
    const int x0=floorDiv(x,tile);
    const int x1=floorDiv(x+kPlayerWidth*kFixed-1,tile);
    const int y0=floorDiv(y,tile);
    const int y1=floorDiv(y+kPlayerHeight*kFixed-1,tile);
    for(int ty=y0;ty<=y1;++ty)
        for(int tx=x0;tx<=x1;++tx)
            if(scene_.solid(tx,ty)) return true;
    return false;
}
void Simulation::moveHorizontal(int32_t delta){
    const int dir=delta<0?-1:1;
    while(delta!=0){
        const int32_t step=dir*std::min<int32_t>(delta<0?-delta:delta,kFixed);
        if(collideAt(player_.x+step,player_.y)){
            const int tile=kTileSize*kFixed;
            if(dir>0){
                const int hit=floorDiv(player_.x+step+kPlayerWidth*kFixed-1,tile);
                player_.x=hit*tile-kPlayerWidth*kFixed;
            } else{
                const int hit=floorDiv(player_.x+step,tile);
                player_.x=(hit+1)*tile;
            }
            player_.vx=0;
            break;
        }
        player_.x+=step;
        delta-=step;
    }
}
void Simulation::moveVertical(int32_t delta){
    const int dir=delta<0?-1:1;
    player_.grounded=false;
    while(delta!=0){
        const int32_t step=dir*std::min<int32_t>(delta<0?-delta:delta,kFixed);
        if(collideAt(player_.x,player_.y+step)){
            const int tile=kTileSize*kFixed;
            if(dir>0){
                const int hit=floorDiv(player_.y+step+kPlayerHeight*kFixed-1,tile);
                player_.y=hit*tile-kPlayerHeight*kFixed;
                player_.grounded=true;
            } else{
                const int hit=floorDiv(player_.y+step,tile);
                player_.y=(hit+1)*tile;
            }
            player_.vy=0;
            break;
        }
        player_.y+=step;
        delta-=step;
    }
}
void Simulation::advanceProjectiles(){
    constexpr int32_t tile=kTileSize*kFixed;
    // Small swept steps prevent skipping a one-tile obstacle.
    for(auto& shot:projectiles_){
        if(!shot.active)continue;
        if(++shot.age>=kProjectileLifetime){
            shot.active=false;
            continue;
        }
        const int dir=shot.vx<0?-1:1;
        int32_t remaining=shot.vx<0?-shot.vx:shot.vx;
        while(remaining>0){
            const int32_t step=std::min<int32_t>(remaining,kFixed);
            const int32_t next=shot.x+dir*step;
            if(scene_.solid(floorDiv(next,tile),floorDiv(shot.y,tile))){
                shot.active=false;
                break;
            }
            shot.x=next;
            remaining-=step;
        }
    }
}
void Simulation::fireProjectile(){
    for(auto& shot:projectiles_){
        if(shot.active)continue;
        const int dir=facing_left_?-1:1;
        const int32_t x=player_.x+
            (facing_left_?-kFixed:kPlayerWidth*kFixed);
        const int32_t y=player_.y+(kPlayerHeight/2)*kFixed;
        constexpr int32_t tile=kTileSize*kFixed;
        if(scene_.solid(floorDiv(x,tile),floorDiv(y,tile)))return;
        shot=Projectile{x,y,dir*kProjectileSpeed,0,true};
        ++shots_fired_;
        fire_cooldown_=kFireInterval;
        return;
    }
}
void Simulation::tick(Input input){
    const bool left=(input.buttons&Left)!=0;
    const bool right=(input.buttons&Right)!=0;
    player_.vx=left==right?0:(left?-kRunSpeed:kRunSpeed);
    if(left!=right)facing_left_=left;
    const bool jump_down=(input.buttons&Jump)!=0;
    if(jump_down && !jump_was_down_ && player_.grounded){
        player_.vy=kJumpVelocity;
        player_.grounded=false;
    }
    jump_was_down_=jump_down;
    player_.vy=std::min(player_.vy+kGravity,kMaxFall);
    moveHorizontal(player_.vx);
    moveVertical(player_.vy);
    advanceProjectiles();
    if(fire_cooldown_>0)--fire_cooldown_;
    if((input.buttons&Fire)!=0 && fire_cooldown_==0)
        fireProjectile();
    camera_x_=std::clamp(player_.x/kFixed-10*kTileSize,0,(kMapWidth-40)*kTileSize);
    ++frame_;
}
uint64_t Simulation::fingerprint() const{
    // Explicit byte-order FNV-1a, not a hash of compiler struct layout.
    uint64_t hash=14695981039346656037ull;
    auto append=[&hash](uint32_t value){
        for(int byte=0;byte<4;++byte){
            hash^=static_cast<uint8_t>(value>>(8*byte));
            hash*=1099511628211ull;
        }
    };
    append(static_cast<uint32_t>(player_.x));
    append(static_cast<uint32_t>(player_.y));
    append(static_cast<uint32_t>(player_.vx));
    append(static_cast<uint32_t>(player_.vy));
    append(static_cast<uint32_t>(player_.grounded?1:0));
    append(static_cast<uint32_t>(camera_x_));
    append(frame_);
    append(static_cast<uint32_t>(jump_was_down_?1:0));
    // Preserve the existing no-shot golden-replay hash. Projectile state
    // participates in replay identity as soon as shooting is exercised.
    if(shots_fired_){
        append(0x53484f54u); // explicit SHOT discriminator
        append(shots_fired_);
        append(static_cast<uint32_t>(fire_cooldown_));
        append(static_cast<uint32_t>(facing_left_?1:0));
        for(const auto& shot:projectiles_){
            append(static_cast<uint32_t>(shot.active?1:0));
            append(static_cast<uint32_t>(shot.x));
            append(static_cast<uint32_t>(shot.y));
            append(static_cast<uint32_t>(shot.vx));
            append(static_cast<uint32_t>(shot.age));
        }
    }
    return hash;
}
}
