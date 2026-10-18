#include "simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
static void check(bool ok,const char* message){
    if(!ok)throw std::runtime_error(message);
}
int main(){
    try{
        using namespace vpd;
        Simulation a,b;
        check(a.fingerprint()==b.fingerprint(),"initial deterministic state");
        const int32_t start_x=a.player().x;
        const int32_t floor_y=a.player().y;
        for(int f=0;f<300;++f){
            uint8_t buttons=f<180?Right:0;
            if((f>=12&&f<24)||(f>=130&&f<144))buttons|=Jump;
            const Input input{buttons};
            a.tick(input);
            b.tick(input);
            check(a.fingerprint()==b.fingerprint(),"two replays differ");
            check(a.player().y+kPlayerHeight*kFixed<=kMapHeight*kTileSize*kFixed,
                "actor falls through floor");
        }
        check(a.player().x>start_x,"actor never moved");
        check(a.cameraX()>0,"camera did not scroll");
        check(a.frame()==300,"incorrect frame count");
        check(a.fingerprint()==7488840217753765732ull,
            "300-frame golden replay hash changed");
        std::cout<<"Replay 300 frames: "<<a.fingerprint()<<'\n';
        a.reset();
        check(a.frame()==0 && a.player().x==start_x && a.player().y==floor_y,
            "reset must restore initial state");
        Simulation rising;
        rising.tick(Input{Jump});
        check(rising.player().y<floor_y,"jump must move actor upward");
        for(int f=0;f<90;++f)rising.tick(Input{});
        check(rising.player().grounded && rising.player().y==floor_y,
            "jump must land exactly on floor");
        Simulation wall;
        wall.scene().setSolid(5,kMapHeight-2,true);
        for(int f=0;f<100;++f)wall.tick(Input{Right});
        check(wall.player().x+kPlayerWidth*kFixed<=5*kTileSize*kFixed,
            "actor passed through wall");
        Simulation held;
        for(int f=0;f<120;++f)held.tick(Input{static_cast<uint8_t>(Jump)});
        check(held.player().grounded && held.player().y==floor_y,
            "holding jump must not auto-repeat");
        // ROM-free fixed-step projectile combat prototype.
        Simulation firing,mirror;
        for(int f=0;f<135;++f) {
            uint8_t controls=(f<55)?static_cast<uint8_t>(Fire):0;
            if(f>=60&&f<65)controls|=Left;
            if(f>=65&&f<100)controls|=Fire;
            const Input input{controls};
            firing.tick(input);
            mirror.tick(input);
            check(firing.fingerprint()==mirror.fingerprint(),
                  "projectile physics broke deterministic replay");
            for(const auto& shot:firing.projectiles()){
                if(!shot.active)continue;
                const int px=shot.x/(kFixed*kTileSize);
                const int py=shot.y/(kFixed*kTileSize);
                check(!firing.scene().solid(px,py),
                      "active projectile crossed a solid tile");
            }
        }
        check(firing.shotsFired()>=5,"holding fire never repeated shots");
        check(firing.fingerprint()!=Simulation{}.fingerprint(),
              "combat-state fingerprint omitted shots");
        Simulation cooldown;
        for(int f=0;f<24;++f)cooldown.tick(Input{Fire});
        check(cooldown.shotsFired()==3,
              "fire cooldown should yield frames 1,11,21");
        Simulation blocking;
        blocking.scene().setSolid(5,kMapHeight-2,true);
        blocking.tick(Input{Fire});
        check(blocking.shotsFired()==1 &&
              blocking.projectiles()[0].active,
              "shot was not launched toward the wall");
        for(int f=0;f<12;++f)blocking.tick(Input{});
        check(!blocking.projectiles()[0].active,
              "shot tunneled through adjacent solid wall");
        Simulation leftshot;
        leftshot.tick(Input{Left});
        leftshot.tick(Input{Fire});
        check(leftshot.projectiles()[0].active &&
              leftshot.projectiles()[0].vx<0,
              "shot did not follow last directional input");
        Simulation expired;
        expired.tick(Input{Fire});
        for(int f=0;f<95;++f)expired.tick(Input{});
        for(const auto& shot:expired.projectiles())
            check(!shot.active,"expired projectile remains active");
        firing.reset();
        check(firing.shotsFired()==0 &&
              firing.fingerprint()==Simulation{}.fingerprint(),
              "combat state survived a full gameplay reset");
        Simulation idle;
        for(int f=0;f<600;++f)idle.tick(Input{});
        check(idle.player().grounded && idle.player().y==floor_y,
            "idle floor drift");
        std::cout<<"PASS: deterministic replay, camera, floor, wall, jump, ROM-free fire cooldown/collision/lifetime, reset\n";
        return 0;
    } catch(const std::exception& e){
        std::cerr<<"FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
