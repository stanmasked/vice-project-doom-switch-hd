#include "nes_chr.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

// Deliberately use runtime checks: assert() disappears in Release / -DNDEBUG builds.
static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        uint8_t bytes[16]{};
        for (auto pixel : vpd::decodeTile(bytes)) require(pixel == 0, "zero tile");
        for (int i=0; i<8; ++i) bytes[i] = 0xff;
        for (auto pixel : vpd::decodeTile(bytes)) require(pixel == 1, "bit plane 0");
        for (int i=8; i<16; ++i) bytes[i] = 0xff;
        for (auto pixel : vpd::decodeTile(bytes)) require(pixel == 3, "both planes");
        for (int i=0; i<8; ++i) bytes[i] = 0;
        for (auto pixel : vpd::decodeTile(bytes)) require(pixel == 2, "bit plane 1");

        std::vector<uint8_t> fakeChr(4096);
        fakeChr[0] = 0x80;
        fakeChr[8] = 0x80;
        auto rgb = vpd::makeRgbPage(fakeChr, 0, 1);
        require(rgb.size() == 128u * 128u * 3u, "atlas dimensions");
        require(rgb[0] == vpd::kDiagnosticPalette[3][0], "atlas top-left pixel");
        require(rgb[3] == vpd::kDiagnosticPalette[0][0], "atlas second pixel");

        bool threw = false;
        try { (void)vpd::makeRgbPage(fakeChr, 1, 1); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "out-of-range page must fail");
        threw = false;
        try { (void)vpd::makeRgbPage(fakeChr, 0, 0); }
        catch (const std::invalid_argument&) { threw = true; }
        require(threw, "zero pixel scale must fail");

        std::cout << "PASS: CHR planes, atlas layout, invalid arguments (Release-safe)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
