#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <vector>

namespace vpd {
using Tile = std::array<uint8_t, 64>;
using Palette = std::array<std::array<uint8_t, 3>, 4>;
constexpr Palette kDiagnosticPalette = {{{18,22,33},{86,108,136},{172,195,214},{248,249,250}}};
Tile decodeTile(const uint8_t* data16);
std::vector<uint8_t> loadChr(const std::filesystem::path& rom_path);
std::vector<uint8_t> makeRgbPage(const std::vector<uint8_t>& chr, std::size_t page, int pixel_scale,
                                 const Palette& palette = kDiagnosticPalette);
void writeBmp24(const std::filesystem::path& filename, int width, int height,
                const std::vector<uint8_t>& rgb);
}
