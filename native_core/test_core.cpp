#include "nes_chr.hpp"
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <vector>
int main() {
    uint8_t b[16]{};
    auto all_zeros=vpd::decodeTile(b);
    for (auto px:all_zeros)assert(px==0);
    for (int i=0;i<8;i++)b[i]=0xff;
    auto plane0=vpd::decodeTile(b);
    for (auto px:plane0)assert(px==1);
    for (int i=8;i<16;i++)b[i]=0xff;
    auto both=vpd::decodeTile(b);
    for (auto px:both)assert(px==3);
    for (int i=0;i<8;i++)b[i]=0;
    auto plane1=vpd::decodeTile(b);
    for (auto px:plane1)assert(px==2);
    std::vector<uint8_t> chr(4096);
    chr[0]=0x80; chr[8]=0x80;
    auto rgb=vpd::makeRgbPage(chr,0,1);
    assert(rgb.size()==128u*128u*3u);
    assert(rgb[0]==vpd::kDiagnosticPalette[3][0]);
    assert(rgb[3]==vpd::kDiagnosticPalette[0][0]);
    bool threw=false;try{vpd::makeRgbPage(chr,1,1);}catch(const std::invalid_argument&){threw=true;}
    assert(threw);
    std::cout<<"PASS: planar 2bpp decode, atlas positioning, bounds checks\n";
}
