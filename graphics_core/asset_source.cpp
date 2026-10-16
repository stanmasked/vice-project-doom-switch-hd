#include "asset_source.hpp"
#include <cstdio>
#include <memory>
#include <new>
#include <utility>

namespace vpd {

bool AssetSource::initialize(const uint8_t* embedded,size_t size,uint16_t expected){
    // A failed initialization must not leave a stale external pointer.
    external_bytes_.reset();
    embedded_={};
    active_={};
    external_=false;
    expected_count_=0;
    SpriteAtlas candidate{};
    if(expected==0 || !openAtlas(candidate,embedded,size) ||
       candidate.frame_count!=expected) return false;
    embedded_=candidate;
    active_=candidate;
    expected_count_=expected;
    return true;
}

AtlasLoadResult AssetSource::reloadFromFile(const char* path){
    if(!embedded_.pixels || expected_count_==0)
        return AtlasLoadResult::NotInitialized;
    if(!path || !*path)return AtlasLoadResult::FileMissing;
    std::FILE* f=std::fopen(path,"rb");
    if(!f)return AtlasLoadResult::FileMissing;
    if(std::fseek(f,0,SEEK_END)!=0){
        std::fclose(f);return AtlasLoadResult::IoError;
    }
    long count=std::ftell(f);
    if(count<0){
        std::fclose(f);return AtlasLoadResult::IoError;
    }
    if(static_cast<unsigned long>(count)>kMaxExternalAtlasBytes){
        std::fclose(f);return AtlasLoadResult::TooLarge;
    }
    if(count<static_cast<long>(kVpatHeaderBytes)){
        std::fclose(f);return AtlasLoadResult::InvalidAtlas;
    }
    if(std::fseek(f,0,SEEK_SET)!=0){
        std::fclose(f);return AtlasLoadResult::IoError;
    }
    const size_t size=static_cast<size_t>(count);
    std::unique_ptr<uint8_t[]> candidate_bytes(new(std::nothrow) uint8_t[size]);
    if(!candidate_bytes){
        std::fclose(f);return AtlasLoadResult::IoError;
    }
    const size_t read=std::fread(candidate_bytes.get(),1,size,f);
    const bool io_failure=read!=size || std::ferror(f)!=0;
    const int extra=io_failure?EOF:std::fgetc(f);
    std::fclose(f);
    if(io_failure)return AtlasLoadResult::IoError;
    if(extra!=EOF)return AtlasLoadResult::IoError;  // changed while reading
    SpriteAtlas candidate{};
    if(!openAtlas(candidate,candidate_bytes.get(),size))
        return AtlasLoadResult::InvalidAtlas;
    if(candidate.frame_count!=expected_count_)
        return AtlasLoadResult::WrongFrameCount;

    // Commit only after all I/O, VPAT and frame count checks pass.
    // The temporary unique_ptr owns the exact memory referenced by candidate.
    external_bytes_.swap(candidate_bytes);
    active_=candidate;
    external_=true;
    return AtlasLoadResult::Loaded;
}

bool AssetSource::swapLoaded(AssetSource& other){
    if(!embedded_.pixels || !other.embedded_.pixels ||
       embedded_.pixels!=other.embedded_.pixels ||
       expected_count_!=other.expected_count_)return false;
    external_bytes_.swap(other.external_bytes_);
    std::swap(active_,other.active_);
    std::swap(external_,other.external_);
    return true;
}
void AssetSource::resetToEmbedded(){
    if(embedded_.pixels){
        active_=embedded_;
        external_=false;
        external_bytes_.reset();
    }
}
}
