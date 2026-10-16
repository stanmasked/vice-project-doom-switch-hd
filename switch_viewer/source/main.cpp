// Standalone native diagnostic viewer for original CHR tile atlas pages.
// THIS IS NOT A GAME PORT OR EMULATOR. It uses SDL2 for native presentation.
#include <SDL2/SDL.h>
#include <cstdio>
#ifdef __SWITCH__
#include <switch.h>
#endif

namespace {
constexpr int kPages = 32;
constexpr int kScreenW = 1280;
constexpr int kScreenH = 720;

SDL_Texture* openPage(SDL_Renderer* renderer, int page) {
    char filename[128];
#ifdef __SWITCH__
    std::snprintf(filename, sizeof(filename), "romfs:/chr_page_%02d.bmp", page);
#else
    std::snprintf(filename, sizeof(filename), "assets/chr_page_%02d.bmp", page);
#endif
    SDL_Surface* surface = SDL_LoadBMP(filename);
    if (!surface) {
        std::fprintf(stderr, "Cannot load %s: %s\n", filename, SDL_GetError());
        return nullptr;
    }
    SDL_Texture* texture = SDL_CreateTextureFromSurface(renderer, surface);
    SDL_FreeSurface(surface);
    if (texture) SDL_SetTextureScaleMode(texture, SDL_ScaleModeNearest);
    return texture;
}
}

int main(int, char**) {
#ifdef __SWITCH__
    if (R_FAILED(romfsInit())) return 2;
#endif
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER) != 0) {
#ifdef __SWITCH__
        romfsExit();
#endif
        return 3;
    }
    SDL_Window* win = SDL_CreateWindow("VPD CHR research viewer",SDL_WINDOWPOS_CENTERED,
                    SDL_WINDOWPOS_CENTERED,kScreenW,kScreenH,SDL_WINDOW_SHOWN);
    SDL_Renderer* renderer = win ? SDL_CreateRenderer(win,-1,
                SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC) : nullptr;
    if (!renderer && win) renderer = SDL_CreateRenderer(win,-1,SDL_RENDERER_SOFTWARE);
    if (!renderer) {
        if(win)SDL_DestroyWindow(win);
        SDL_Quit();
#ifdef __SWITCH__
        romfsExit();
#endif
        return 4;
    }
    SDL_RenderSetLogicalSize(renderer,kScreenW,kScreenH);
    SDL_GameController* controller=nullptr;
    for (int i=0;i<SDL_NumJoysticks();++i) if (SDL_IsGameController(i)) {
        controller=SDL_GameControllerOpen(i);break;
    }
    int page=0;
    SDL_Texture* texture=openPage(renderer,page);
    bool done=false;
    while (!done) {
        SDL_Event ev;
        int movement=0;
        while (SDL_PollEvent(&ev)) {
            if (ev.type==SDL_QUIT) done=true;
            if (ev.type==SDL_KEYDOWN && !ev.key.repeat) {
                if (ev.key.keysym.sym==SDLK_ESCAPE)done=true;
                if (ev.key.keysym.sym==SDLK_RIGHT || ev.key.keysym.sym==SDLK_d)movement=1;
                if (ev.key.keysym.sym==SDLK_LEFT || ev.key.keysym.sym==SDLK_a)movement=-1;
            }
            if (ev.type==SDL_CONTROLLERBUTTONDOWN) {
                switch (ev.cbutton.button) {
                    case SDL_CONTROLLER_BUTTON_START: done=true;break;
                    case SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    case SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: movement=1;break;
                    case SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    case SDL_CONTROLLER_BUTTON_LEFTSHOULDER: movement=-1;break;
                    default:break;
                }
            }
        }
        if (movement) {
            const int next=(page+movement+kPages)%kPages;
            SDL_Texture* replacement=openPage(renderer,next);
            if (replacement) {
                SDL_DestroyTexture(texture);
                texture=replacement;
                page=next;
            }
        }
        char title[128];
        std::snprintf(title,sizeof(title),"VPD CHR atlas | %02d/%02d | D-pad or L/R: page | +: exit",
                      page+1,kPages);
        SDL_SetWindowTitle(win,title);
        SDL_SetRenderDrawColor(renderer,18,22,33,255);
        SDL_RenderClear(renderer);
        SDL_Rect bg={304,23,672,672};
        SDL_SetRenderDrawColor(renderer,40,48,62,255);
        SDL_RenderFillRect(renderer,&bg);
        SDL_Rect dst={320,39,640,640};
        if (texture)SDL_RenderCopy(renderer,texture,nullptr,&dst);
        for (int i=0;i<kPages;i++) {
            SDL_Rect marker={64+(i%16)*72,700+(i/16)*8-12,58,4};
            SDL_SetRenderDrawColor(renderer,i==page?245:85,i==page?249:110,i==page?250:135,255);
            SDL_RenderFillRect(renderer,&marker);
        }
        SDL_RenderPresent(renderer);
        SDL_Delay(10);
    }
    if(texture)SDL_DestroyTexture(texture);
    if(controller)SDL_GameControllerClose(controller);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(win);
    SDL_Quit();
#ifdef __SWITCH__
    romfsExit();
#endif
    return 0;
}
