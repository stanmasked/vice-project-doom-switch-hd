#include "scene_renderer.hpp"
#include "asset_atlas.hpp"
#include "terrain_source.hpp"
#include "backdrop_source.hpp"
#include "decor_source.hpp"
#include <cstdint>
#include <algorithm>

namespace vpd {
namespace {
constexpr uint32_t rgba(int r,int g,int b) {
    return static_cast<uint32_t>(r) | (static_cast<uint32_t>(g)<<8) |
           (static_cast<uint32_t>(b)<<16) | 0xff000000u;
}
int floorDiv(int x,int d) { return x/d - (x%d<0 ? 1 : 0); }
struct Surface {
    uint32_t* pixels;
    int w,h,stride;
    void rect(int x,int y,int width,int height,uint32_t color) {
        if(width<=0 || height<=0)return;
        int x0=std::max(0,x), y0=std::max(0,y);
        int x1=std::min(w,x+width),y1=std::min(h,y+height);
        if(x0>=x1||y0>=y1)return;
        for(int py=y0;py<y1;++py)
            std::fill(pixels+static_cast<size_t>(py)*stride+x0,
                      pixels+static_cast<size_t>(py)*stride+x1,color);
    }
    void circle(int cx,int cy,int radius,uint32_t color) {
        if(radius<=0)return;
        for(int dy=-radius;dy<=radius;++dy){
            int64_t r2=static_cast<int64_t>(radius)*radius-static_cast<int64_t>(dy)*dy;
            if(r2<0)continue;
            int dx=0;
            while(static_cast<int64_t>(dx+1)*(dx+1)<=r2)++dx;
            rect(cx-dx,cy+dy,dx*2+1,1,color);
        }
    }
    void glyph(int x,int y,char c,uint32_t color,int scale=2) {
        // Hand-authored 5x7 ASCII bitmap font; each row contains five bits.
        static constexpr char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:/+- .";
        static constexpr uint8_t font[][7]={
            {14,17,17,31,17,17,17}, // A
            {30,17,17,30,17,17,30}, // B
            {15,16,16,16,16,16,15}, // C
            {30,17,17,17,17,17,30}, // D
            {31,16,16,30,16,16,31}, // E
            {31,16,16,30,16,16,16}, // F
            {15,16,16,23,17,17,15}, // G
            {17,17,17,31,17,17,17}, // H
            {31,4,4,4,4,4,31},       // I
            {7,2,2,2,18,18,12},     // J
            {17,18,20,24,20,18,17}, // K
            {16,16,16,16,16,16,31}, // L
            {17,27,21,21,17,17,17}, // M
            {17,25,21,19,17,17,17}, // N
            {14,17,17,17,17,17,14}, // O
            {30,17,17,30,16,16,16}, // P
            {14,17,17,17,21,18,13}, // Q
            {30,17,17,30,20,18,17}, // R
            {15,16,16,14,1,1,30},   // S
            {31,4,4,4,4,4,4},       // T
            {17,17,17,17,17,17,14}, // U
            {17,17,17,17,17,10,4},  // V
            {17,17,17,21,21,21,10}, // W
            {17,17,10,4,10,17,17},  // X
            {17,17,10,4,4,4,4},     // Y
            {31,1,2,4,8,16,31},     // Z
            {14,17,19,21,25,17,14}, // 0
            {4,12,4,4,4,4,14},      // 1
            {14,17,1,2,4,8,31},     // 2
            {30,1,1,14,1,1,30},     // 3
            {2,6,10,18,31,2,2},    // 4
            {31,16,16,30,1,1,30},  // 5
            {14,16,16,30,17,17,14},// 6
            {31,1,2,4,8,8,8},      // 7
            {14,17,17,14,17,17,14},// 8
            {14,17,17,15,1,1,14},  // 9
            {0,4,4,0,4,4,0},       // :
            {1,2,2,4,8,8,16},      // /
            {0,4,4,31,4,4,0},      // +
            {0,0,0,31,0,0,0},      // -
            {0,0,0,0,0,0,0},       // space
            {0,0,0,0,0,12,12},     // .
        };
        for(int i=0;alphabet[i];++i) {
            if(alphabet[i]!=c)continue;
            for(int row=0;row<7;++row)
                for(int col=0;col<5;++col)
                    if(font[i][row] & (1u << (4-col)))
                        rect(x+col*scale,y+row*scale,scale,scale,color);
            return;
        }
    }
    void text(int x,int y,const char* t,uint32_t color,int scale=2) {
        for(int i=0;t[i];++i)glyph(x+i*6*scale,y,t[i],color,scale);
    }
};
uint32_t randomHash(uint32_t x) {
    x ^= x>>16; x*=0x7feb352du; x^=x>>15;
    x*=0x846ca68bu; x^=x>>16;return x;
}
void skyline(Surface& s,int camera) {
    // Parallax synthetic skyline: no sprites, backgrounds or tile art from game.
    for(int layer=0;layer<2;++layer){
        int spacing=112-layer*20;
        int parallax=floorDiv(camera,layer==0?7:4);
        uint32_t color=layer==0?rgba(37,40,78):rgba(31,35,67);
        for(int column=-2;column<s.w/spacing+3;++column){
            int k=column+floorDiv(parallax,spacing);
            uint32_t h=randomHash(static_cast<uint32_t>(k)*37u+layer*263u);
            int x=column*spacing-(parallax%spacing);
            int base=485+layer*86;
            int tall=110+static_cast<int>(h%140u);
            s.rect(x,base-tall,spacing-7,tall,color);
            s.rect(x+12,base-tall-18,3,18,color);
            for(int jy=base-tall+21;jy<base-18;jy+=28)
                for(int wx=x+12;wx<x+spacing-17;wx+=23)
                    if(((h+static_cast<uint32_t>(jy+wx))%7u)<2)
                        s.rect(wx,jy,5,8,layer==0?rgba(80,74,113):rgba(69,69,108));
        }
    }
}
void tile(Surface& s,int sx,int sy,int tile_x,int tile_y){
    const uint32_t dirt=rgba(64,67,79),line=rgba(30,37,57);
    s.rect(sx,sy,32,32,dirt);
    s.rect(sx,sy,32,5,rgba(107,124,133));
    s.rect(sx,sy+5,32,3,rgba(80,91,99));
    s.rect(sx,sy+18,32,2,line);
    int seam=(tile_y&1)?8:17;
    s.rect(sx+seam,sy+20,2,12,line);
    s.rect(sx+(tile_x*7+tile_y*11+21)%22,sy+12,7,3,rgba(83,93,99));
    s.rect(sx,sy+30,32,2,line);
}
void drawHero(Surface& s,int x,int y,uint32_t frame,bool grounded){
    // Original placeholder hero with stylized jacket; no NES sprites.
    s.rect(x-6,y+26,37,5,rgba(17,25,41));
    if(grounded)s.rect(x-6,y+31,36,3,rgba(89,95,115));
    int foot=(frame/8)%2 ? 2 : 0;
    s.rect(x+5,y+22,8,7+foot,rgba(33,40,61));
    s.rect(x+16,y+22,8,7+(2-foot),rgba(33,40,61));
    s.rect(x+4,y+11,21,14,rgba(155,52,64));
    s.rect(x+7,y+15,15,4,rgba(209,83,81));
    s.rect(x+8,y+2,15,13,rgba(218,174,127));
    s.rect(x+8,y+1,17,6,rgba(48,42,55));
    s.rect(x+18,y+9,3,2,rgba(25,27,40));
    s.rect(x-1,y+14,6,7,rgba(217,166,115));
    s.rect(x+24,y+13,6,9,rgba(217,166,115));
    s.rect(x+23,y+16,13,3,rgba(156,169,181));
    s.rect(x+33,y+12,3,14,rgba(197,207,207));
}
}
bool drawScene(uint32_t* target,int width,int height,int stride_pixels,
               const SceneView& view) {
    if(!target||width!=kSceneWidth||height!=kSceneHeight||stride_pixels<width)
        return false;
    Surface s{target,width,height,stride_pixels};
    for(int y=0;y<height;++y){
        int t=y*255/height;
        uint32_t shade=rgba(13+(t*45)/255,16+(t*31)/255,39+(t*60)/255);
        std::fill(target+static_cast<size_t>(y)*stride_pixels,
                  target+static_cast<size_t>(y)*stride_pixels+width,shade);
    }
    // Distant moon, architecture and independent star field.
    s.circle(1020,142,62,rgba(85,78,125));
    s.circle(1020,142,49,rgba(185,167,177));
    s.circle(1034,129,42,rgba(203,181,187));
    for(uint32_t n=0;n<130;++n){
        uint32_t h=randomHash(n*59u+17u);
        int x=static_cast<int>((h>>1)%1280),y=80+static_cast<int>((h>>16)%320);
        s.rect(x,y,n%11==0?4:2,2,rgba(145+(n%54),141+(n%25),159+(n%33)));
    }
    // Replace only the skyline, preserving independent sky and HUD.
    // Invalid/no background atlas keeps the original procedural fallback.
    if(!view.backdrop_atlas ||
       !drawBackdropLayers(target,width,height,stride_pixels,
                           *view.backdrop_atlas,view.camera_x_px))
        skyline(s,view.camera_x_px);
    // Decorative background props sit behind solid tiles and player.
    if(view.decor_atlas){
        if(view.decor_layout.placements)
            drawPlacedDecorLayer(target,width,height,stride_pixels,
                                 *view.decor_atlas,view.decor_layout,
                                 view.camera_x_px,view.frame,false);
        else
            drawDecorLayer(target,width,height,stride_pixels,*view.decor_atlas,
                           view.camera_x_px,view.frame,false);
    }
    const int environment_scale=view.terrain_atlas?
        terrainScale(*view.terrain_atlas):-1;
    int left=floorDiv(view.camera_x_px,16)-1;
    int right=left+43;
    for(int ty=0;ty<15;++ty){
        for(int tx=left;tx<right;++tx){
            if(view.solid_at && view.solid_at(view.map_context,tx,ty)){
                int sx=(tx*16-view.camera_x_px)*2;
                int sy=(ty*16+80)*2;
                bool drawn=false;
                if(environment_scale>0){
                    const unsigned frame=terrainFrame(
                        view.solid_at(view.map_context,tx,ty-1),
                        view.solid_at(view.map_context,tx-1,ty),
                        view.solid_at(view.map_context,tx+1,ty),tx,ty);
                    drawn=blitAtlasFrame(target,width,height,stride_pixels,
                                         *view.terrain_atlas,frame,sx,sy,
                                         environment_scale);
                }
                if(!drawn)tile(s,sx,sy,tx,ty);
            }
        }
    }
    int player_x=(view.player_x_px-view.camera_x_px)*2;
    int player_y=(view.player_y_px+80)*2;
    // Atlas-driven sprite when supplied, preserving old fallback for tests.
    if(view.sprite_atlas && view.sprite_atlas->pixels) {
        unsigned sprite_frame=view.sprite_frame>=0?
            static_cast<unsigned>(view.sprite_frame):
            (!view.grounded?3u : view.moving?1u+((view.frame/8)&1u):0u);
        if(!blitAtlasFrame(target,width,height,stride_pixels,*view.sprite_atlas,
                           sprite_frame,player_x-4,player_y-12,2,view.facing_left))
            drawHero(s,player_x,player_y,view.frame,view.grounded);
    } else drawHero(s,player_x,player_y,view.frame,view.grounded);
    // Original, asset-free muzzle/projectile visual; simulation owns movement.
    // Inactive slots are completely invisible, preserving old golden frames.
    for(const auto& shot:view.projectiles){
        if(!shot.active)continue;
        const int sx=(shot.x_px-view.camera_x_px)*2;
        const int sy=(shot.y_px+80)*2;
        s.rect(sx-4,sy-2,16,7,rgba(244,186,76));
        s.rect(sx,sy-1,12,4,rgba(255,235,164));
    }
    // Foreground objects are visual only: no hitbox/collision changes.
    if(view.decor_atlas){
        if(view.decor_layout.placements)
            drawPlacedDecorLayer(target,width,height,stride_pixels,
                                 *view.decor_atlas,view.decor_layout,
                                 view.camera_x_px,view.frame,true);
        else
            drawDecorLayer(target,width,height,stride_pixels,*view.decor_atlas,
                           view.camera_x_px,view.frame,true);
    }
    s.rect(0,0,1280,76,rgba(14,23,43));
    s.rect(0,73,1280,3,rgba(170,67,85));
    s.text(30,17,"VICE : NATIVE SCENE TEST",rgba(240,223,216),3);
    s.text(32,51,"ROM-FREE / ART TEST / NOT THE ORIGINAL GAME",rgba(149,178,200),2);
    s.rect(932,22,200,16,rgba(56,70,88));
    s.rect(932,22,125,16,rgba(171,66,75));
    s.rect(932,47,126,8,rgba(55,88,108));
    s.rect(932,47,83,8,rgba(87,184,194));
    if(view.external_animation_source)
        s.text(788,54,"ANIM: SD OVERRIDE",rgba(164,210,193),2);
    if(view.terrain_atlas) {
        const char* terrain_message=view.terrain_reload_failed ?
            "TERRAIN: FAILED" : (view.external_terrain_asset ?
            "TERRAIN: SD" : "TERRAIN: EMBEDDED");
        s.text(951,100,terrain_message,
               view.terrain_reload_failed?rgba(243,121,104):
               rgba(153,218,195),2);
    }
    if(view.backdrop_atlas) {
        const char* label=view.backdrop_reload_failed?
            "BG: FAILED" : (view.external_backdrop_asset?
            "BG: SD" : "BG: EMBEDDED");
        s.text(951,126,label,
               view.backdrop_reload_failed?rgba(243,121,104):
               rgba(153,218,195),2);
    }
    if(view.decor_atlas) {
        const char* label=view.decor_reload_failed?"DECOR: FAILED":
            view.external_decor_asset?"DECOR: SD":"DECOR: EMBEDDED";
        s.text(951,152,label,
               view.decor_reload_failed?rgba(243,121,104):
               rgba(153,218,195),2);
    }
    if(view.decor_layout.placements){
        const char* label=view.decor_layout_reload_failed?"LAYOUT: FAILED":
            view.external_decor_layout?"LAYOUT: SD":"LAYOUT: EMBEDDED";
        s.text(951,178,label,
               view.decor_layout_reload_failed?rgba(243,121,104):
               rgba(153,218,195),2);
    }
    s.rect(0,689,1280,31,rgba(13,19,33));
    s.text(25,697,"MOVE : D PAD  /  JUMP : A OR B  /  EXIT : PLUS",rgba(173,184,207),2);
    s.text(760,697,view.asset_reload_failed?"RELOAD FAILED":
       (view.external_sprite_asset?"ART: SD OVERRIDE":"ART: EMBEDDED"),
       view.asset_reload_failed?rgba(243,121,104):rgba(164,210,193),2);
    return true;
}
}
