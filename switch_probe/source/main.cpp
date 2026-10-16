// ROM-free Nintendo Switch native homebrew launch and gamepad smoke test.
// This is an independent libnx diagnostic, NOT the NES game or a playable port.
#include <switch.h>
#include <cstdio>

int main(int, char**) {
    consoleInit(nullptr);
    std::puts("Vice: Project Doom - native HD research");
    std::puts("ROM-free libnx diagnostic build");
    std::puts("Native Switch executable: no emulator.");
    std::puts("Press + to exit; HOME returns to the Switch menu.");

    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    while (appletMainLoop()) {
        padUpdate(&pad);
        const u64 down = padGetButtonsDown(&pad);
        if (down & HidNpadButton_Plus) break;
        consoleUpdate(nullptr);
    }
    consoleExit(nullptr);
    return 0;
}
