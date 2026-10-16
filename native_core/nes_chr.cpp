#include "nes_chr.hpp"
#include <fstream>
#include <stdexcept>
#include <string>

namespace vpd {
Tile decodeTile(const uint8_t* p) {
    Tile out{};
    for (int y = 0; y < 8; ++y) for (int x = 0; x < 8; ++x) {
        int bit = 7 - x;
        out[y * 8 + x] = static_cast<uint8_t>(((p[y] >> bit) & 1) | (((p[8+y] >> bit) & 1) << 1));
    }
    return out;
}

std::vector<uint8_t> loadChr(const std::filesystem::path& rom_path) {
    std::ifstream f(rom_path, std::ios::binary);
    if (!f) throw std::runtime_error("Failed to open ROM: " + rom_path.string());
    std::vector<uint8_t> b(std::istreambuf_iterator<char>(f), {});
    if (b.size() < 16 || b[0]!='N' || b[1]!='E' || b[2]!='S' || b[3]!=0x1a)
        throw std::runtime_error("Not a NES ROM");
    bool nes2 = (b[7] & 0x0c)==0x08;
    uint16_t mapper = static_cast<uint16_t>((b[6]>>4) | (b[7]&0xf0));
    if (nes2) mapper |= static_cast<uint16_t>((b[8]&15)<<8);
    if (mapper!=4) throw std::runtime_error("This viewer only accepts mapper 4 ROMs");
    auto calc_size=[](uint8_t base, uint8_t high, std::size_t unit)->std::size_t {
        return high==15 ? (std::size_t(1) << (base>>2))*(2*(base&3)+1) :
                          ((std::size_t(high)<<8)|base)*unit;
    };
    std::size_t prg = nes2 ? calc_size(b[4],b[9]&15,16384):b[4]*std::size_t(16384);
    std::size_t chr = nes2 ? calc_size(b[5],b[9]>>4,8192):b[5]*std::size_t(8192);
    std::size_t begin = 16 + ((b[6]&4)?512:0) + prg;
    if (chr==0 || chr%16!=0 || begin>b.size() || chr>b.size()-begin)
        throw std::runtime_error("Missing or truncated CHR ROM");
    return std::vector<uint8_t>(b.begin()+static_cast<std::ptrdiff_t>(begin),
                                b.begin()+static_cast<std::ptrdiff_t>(begin+chr));
}

std::vector<uint8_t> makeRgbPage(const std::vector<uint8_t>& chr, std::size_t page, int scale,
                                 const Palette& palette) {
    if (scale<1 || scale>16 || (page+1)*256u*16u>chr.size())
        throw std::invalid_argument("Page out of range or invalid scale");
    const int edge=128*scale;
    std::vector<uint8_t> pixels(static_cast<std::size_t>(edge)*edge*3);
    for (int tile=0;tile<256;tile++) {
        auto decoded=decodeTile(chr.data()+page*4096u+static_cast<std::size_t>(tile)*16);
        for (int y=0;y<8;y++) for (int x=0;x<8;x++) {
            const auto& rgb=palette[decoded[y*8+x]];
            for (int sy=0;sy<scale;sy++) for (int sx=0;sx<scale;sx++) {
                int px=((tile%16)*8+x)*scale+sx;
                int py=((tile/16)*8+y)*scale+sy;
                std::size_t index=(static_cast<std::size_t>(py)*edge+px)*3;
                for (int c=0;c<3;c++) pixels[index+c]=rgb[c];
            }
        }
    }
    return pixels;
}

static void le16(std::ofstream& f, uint32_t v) {for (int i=0;i<2;++i) f.put(static_cast<char>((v>>(8*i))&255));}
static void le32(std::ofstream& f, uint32_t v) {for (int i=0;i<4;++i) f.put(static_cast<char>((v>>(8*i))&255));}
void writeBmp24(const std::filesystem::path& filename, int w, int h, const std::vector<uint8_t>& rgb) {
    if (w<=0 || h<=0 || rgb.size()!=static_cast<std::size_t>(w)*h*3)
        throw std::invalid_argument("Invalid image dimensions");
    int row_bytes=(w*3+3)&~3;
    uint32_t byte_size=static_cast<uint32_t>(54+row_bytes*h);
    std::ofstream f(filename, std::ios::binary);
    if (!f) throw std::runtime_error("Failed to write BMP");
    f.put('B'); f.put('M'); le32(f,byte_size);le16(f,0);le16(f,0);le32(f,54);
    le32(f,40);le32(f,static_cast<uint32_t>(w));le32(f,static_cast<uint32_t>(h));
    le16(f,1);le16(f,24);le32(f,0);le32(f,static_cast<uint32_t>(row_bytes*h));
    le32(f,2835);le32(f,2835);le32(f,0);le32(f,0);
    for (int y=h-1;y>=0;--y) {
        for (int x=0;x<w;x++) {
            auto off=(static_cast<std::size_t>(y)*w+x)*3;
            f.put(static_cast<char>(rgb[off+2]));f.put(static_cast<char>(rgb[off+1]));
            f.put(static_cast<char>(rgb[off]));
        }
        for (int pad=w*3;pad<row_bytes;pad++)f.put(0);
    }
    if (!f)throw std::runtime_error("BMP write failed");
}
}
