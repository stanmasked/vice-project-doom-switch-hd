#pragma once
#include "asset_source.hpp"
#include "animation_resource.hpp"
#include <cstddef>
#include <cstdint>

namespace vpd {

// Paired VPAT+VANM hot reload, preserving legacy atlas-only overrides.
// An atlas is NEVER partially replaced when its accompanying animation
// resource is present but invalid. No files are modified by this API.
enum class BundleReload : uint8_t {
    LoadedPair, LoadedAtlasOnly, MissingAtlas, BadAtlas, BadAnimation,
    NotInitialized
};
class AssetBundle {
public:
    bool initialize(const uint8_t* embedded,size_t embedded_size,
                    const AnimationBank& embedded_animation);
    BundleReload reload(const char* atlas_path,const char* animation_path);
    void reset();
    const SpriteAtlas& atlas() const { return atlas_.atlas(); }
    const AnimationBank& animation() const { return animation_.bank(); }
    bool externalAtlas() const { return atlas_.external(); }
    bool externalAnimation() const { return animation_.external(); }
private:
    const uint8_t* embedded_bytes_=nullptr;
    size_t embedded_size_=0;
    const AnimationBank* embedded_animation_=nullptr;
    AssetSource atlas_{};
    AnimationResource animation_{};
};
}
