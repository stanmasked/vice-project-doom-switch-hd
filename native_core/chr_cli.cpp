#include "nes_chr.hpp"
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
int main(int argc, char** argv) {
    if (argc!=3) {
        std::cerr << "Usage: vpd_chr_cli <owned.nes> <output-directory>\n";
        return 2;
    }
    try {
        auto chr=vpd::loadChr(argv[1]);
        auto folder=std::filesystem::path(argv[2]);
        std::filesystem::create_directories(folder);
        const std::size_t pages=chr.size()/4096;
        for (std::size_t i=0;i<pages;i++) {
            std::ostringstream name;name<<"chr_page_"<<std::setfill('0')<<std::setw(2)<<i<<".bmp";
            auto rgb=vpd::makeRgbPage(chr,i,2);
            vpd::writeBmp24(folder/name.str(),256,256,rgb);
        }
        std::cout<<"Generated "<<pages<<" ROM-derived BMP atlas pages.\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';return 1;
    }
}
