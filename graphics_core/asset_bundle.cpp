#include "asset_bundle.hpp"
namespace vpd {
bool AssetBundle::initialize(const uint8_t* bytes,size_t size,
                             const AnimationBank& bank){
    embedded_bytes_=nullptr;
    embedded_size_=0;
    embedded_animation_=nullptr;
    if(!validAnimationBank(bank) ||
       !atlas_.initialize(bytes,size,bank.atlas_frame_count) ||
       !animation_.initialize(bank))
        return false;
    embedded_bytes_=bytes;
    embedded_size_=size;
    embedded_animation_=&bank;
    return true;
}
BundleReload AssetBundle::reload(const char* atlas_path,const char* anim_path){
    if(!embedded_animation_)return BundleReload::NotInitialized;
    // Build an entirely independent candidate pair first.
    AssetSource next_atlas;
    AnimationResource next_animation;
    if(!next_atlas.initialize(embedded_bytes_,embedded_size_,
                              embedded_animation_->atlas_frame_count) ||
       !next_animation.initialize(*embedded_animation_))
        return BundleReload::NotInitialized;
    const AtlasLoadResult texture=next_atlas.reloadFromFile(atlas_path);
    if(texture==AtlasLoadResult::FileMissing)return BundleReload::MissingAtlas;
    if(texture!=AtlasLoadResult::Loaded)return BundleReload::BadAtlas;

    const AnimationLoadResult timing=
        next_animation.loadFile(anim_path,next_atlas.atlas().frame_count,
                                next_atlas.atlas().pixel_crc32);
    if(timing!=AnimationLoadResult::Loaded &&
       timing!=AnimationLoadResult::Missing)
        return BundleReload::BadAnimation;
    // Both independent candidates have passed validation. No disk
    // operations can fail after this point, so swap the accepted pair.
    if(!atlas_.swapLoaded(next_atlas))return BundleReload::BadAtlas;
    animation_.swapExternal(next_animation);
    return timing==AnimationLoadResult::Loaded ?
           BundleReload::LoadedPair : BundleReload::LoadedAtlasOnly;
}
void AssetBundle::reset(){
    atlas_.resetToEmbedded();
    animation_.reset();
}
}
