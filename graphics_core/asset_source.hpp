#pragma once
#include "asset_atlas.hpp"
#include <cstddef>
#include <cstdint>
#include <memory>

namespace vpd {

// Load only independently authored / appropriately licensed VPAT textures.
// The embedded fallback remains valid through every failed reload.
// Max data size is bounded at the largest atlas supported by openAtlas().
constexpr size_t kMaxExternalAtlasBytes = kVpatHeaderBytes + 1024u*1024u*4u;

enum class AtlasLoadResult : uint8_t {
    Loaded,
    FileMissing,
    IoError,
    TooLarge,
    InvalidAtlas,
    WrongFrameCount,
    NotInitialized
};

// Keep the owner alive for the SpriteAtlas non-owning pixel pointer.
// Noncopyable to prevent accidental invalidation of atlas pointers.
class AssetSource {
public:
    bool initialize(const uint8_t* embedded, size_t embedded_size,
                    uint16_t expected_frame_count);
    AtlasLoadResult reloadFromFile(const char* path);
    void resetToEmbedded();
    const SpriteAtlas& atlas() const { return active_; }
    bool external() const { return external_; }
    uint16_t expectedFrameCount() const { return expected_count_; }
private:
    SpriteAtlas embedded_{};
    SpriteAtlas active_{};
    std::unique_ptr<uint8_t[]> external_bytes_{};
    uint16_t expected_count_=0;
    bool external_=false;
};
}
