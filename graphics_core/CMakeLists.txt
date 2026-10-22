cmake_minimum_required(VERSION 3.16)
project(vpd_scene_renderer LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_library(vpd_scene_renderer STATIC scene_renderer.cpp asset_atlas.cpp animation.cpp asset_source.cpp animation_resource.cpp asset_bundle.cpp terrain_source.cpp backdrop_source.cpp decor_source.cpp decor_layout.cpp)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
target_include_directories(vpd_scene_renderer PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_scene_renderer PRIVATE -Wall -Wextra -Wpedantic)
endif()
set(DEMO_HEADER ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_atlas.hpp)
set(DEMO_ATLAS_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_atlas.vpat)
add_custom_command(OUTPUT ${DEMO_HEADER} ${DEMO_ATLAS_BINARY}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_atlas.py
          ${DEMO_HEADER} --raw ${DEMO_ATLAS_BINARY}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_atlas.py
  VERBATIM)
add_custom_target(vpd_demo_atlas DEPENDS ${DEMO_HEADER} ${DEMO_ATLAS_BINARY})
set(DEMO_TERRAIN_HEADER ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_terrain.hpp)
set(DEMO_TERRAIN_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_terrain.vpat)
add_custom_command(OUTPUT ${DEMO_TERRAIN_HEADER} ${DEMO_TERRAIN_BINARY}
  COMMAND ${Python3_EXECUTABLE}
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_terrain.py
          ${DEMO_TERRAIN_HEADER} --raw ${DEMO_TERRAIN_BINARY}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_terrain.py
  VERBATIM)
add_custom_target(vpd_demo_terrain DEPENDS ${DEMO_TERRAIN_HEADER} ${DEMO_TERRAIN_BINARY})
set(DEMO_BACKDROP_HEADER ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_backdrop.hpp)
set(DEMO_BACKDROP_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_backdrop.vpat)
add_custom_command(OUTPUT ${DEMO_BACKDROP_HEADER} ${DEMO_BACKDROP_BINARY}
  COMMAND ${Python3_EXECUTABLE}
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_backdrop.py
          ${DEMO_BACKDROP_HEADER} --raw ${DEMO_BACKDROP_BINARY}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_backdrop.py
  VERBATIM)
add_custom_target(vpd_demo_backdrop DEPENDS ${DEMO_BACKDROP_HEADER} ${DEMO_BACKDROP_BINARY})
set(DEMO_DECOR_HEADER ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_decor.hpp)
set(DEMO_DECOR_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_decor.vpat)
add_custom_command(OUTPUT ${DEMO_DECOR_HEADER} ${DEMO_DECOR_BINARY}
  COMMAND ${Python3_EXECUTABLE}
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_decor.py
          ${DEMO_DECOR_HEADER} --raw ${DEMO_DECOR_BINARY}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_demo_decor.py
  VERBATIM)
add_custom_target(vpd_demo_decor DEPENDS ${DEMO_DECOR_HEADER} ${DEMO_DECOR_BINARY})
set(DEMO_LAYOUT_HEADER ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_decor_layout.hpp)
set(DEMO_LAYOUT_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_decor_layout.vlay)
add_custom_command(OUTPUT ${DEMO_LAYOUT_HEADER} ${DEMO_LAYOUT_BINARY}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/pack_decor_layout.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_decor_layout.json
          --header ${DEMO_LAYOUT_HEADER} --binary ${DEMO_LAYOUT_BINARY}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_decor_layout.json
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/pack_decor_layout.py
  VERBATIM)
add_custom_target(vpd_demo_decor_layout DEPENDS ${DEMO_LAYOUT_HEADER} ${DEMO_LAYOUT_BINARY})
add_executable(vpd_decor_layout_test ../tests/test_decor_layout.cpp)
target_include_directories(vpd_decor_layout_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_decor_layout_test vpd_demo_decor vpd_demo_decor_layout)
target_link_libraries(vpd_decor_layout_test PRIVATE vpd_scene_renderer)
add_test(NAME authored_layout_and_runtime_reload
         COMMAND vpd_decor_layout_test ${DEMO_LAYOUT_BINARY})
add_executable(vpd_decor_source_test ../tests/test_decor_source.cpp)
target_include_directories(vpd_decor_source_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_decor_source_test vpd_demo_decor)
target_link_libraries(vpd_decor_source_test PRIVATE vpd_scene_renderer)
add_test(NAME decorative_effects_and_reload COMMAND vpd_decor_source_test)
add_executable(vpd_backdrop_source_test ../tests/test_backdrop_source.cpp)
target_include_directories(vpd_backdrop_source_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_backdrop_source_test vpd_demo_backdrop)
target_link_libraries(vpd_backdrop_source_test PRIVATE vpd_scene_renderer)
add_test(NAME backdrop_parallax_and_reload COMMAND vpd_backdrop_source_test)
add_executable(vpd_terrain_source_test ../tests/test_terrain_source.cpp)
target_include_directories(vpd_terrain_source_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_terrain_source_test vpd_demo_terrain)
target_link_libraries(vpd_terrain_source_test PRIVATE vpd_scene_renderer)
add_test(NAME terrain_atlas_and_reload COMMAND vpd_terrain_source_test)

set(DEMO_ANIMATION_HEADER ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_animation.hpp)
add_custom_command(OUTPUT ${DEMO_ANIMATION_HEADER}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_animation_manifest.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_animation.json ${DEMO_ANIMATION_HEADER}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_animation.json
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_animation_manifest.py
  VERBATIM)
add_custom_target(vpd_demo_animation DEPENDS ${DEMO_ANIMATION_HEADER})
add_executable(vpd_animation_test ../tests/test_animation.cpp)
target_include_directories(vpd_animation_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_animation_test vpd_demo_animation)
target_link_libraries(vpd_animation_test PRIVATE vpd_scene_renderer)
add_executable(vpd_asset_atlas_test ../tests/test_asset_atlas.cpp)
target_include_directories(vpd_asset_atlas_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_asset_atlas_test vpd_demo_atlas)
target_link_libraries(vpd_asset_atlas_test PRIVATE vpd_scene_renderer)
add_executable(vpd_scene_renderer_test ../tests/test_scene_renderer.cpp)
target_link_libraries(vpd_scene_renderer_test PRIVATE vpd_scene_renderer)
enable_testing()
add_test(NAME scene_renderer_unit COMMAND vpd_scene_renderer_test)
add_test(NAME asset_atlas_unit COMMAND vpd_asset_atlas_test)
add_executable(vpd_asset_source_test ../tests/test_asset_source.cpp)
target_include_directories(vpd_asset_source_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_asset_source_test vpd_demo_atlas)
target_link_libraries(vpd_asset_source_test PRIVATE vpd_scene_renderer)
add_test(NAME external_asset_reload_unit COMMAND vpd_asset_source_test)
set(DEMO_ANIMATION_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_animation.vanm)
add_custom_command(OUTPUT ${DEMO_ANIMATION_BINARY}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/pack_animation_binary.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_animation.json ${DEMO_ANIMATION_BINARY}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_animation.json
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/pack_animation_binary.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_animation_manifest.py
  VERBATIM)
add_custom_target(vpd_demo_animation_binary DEPENDS ${DEMO_ANIMATION_BINARY})
set(DEMO_BOUND_ANIMATION_BINARY ${CMAKE_CURRENT_BINARY_DIR}/generated/demo_bound_animation.vanm)
add_custom_command(OUTPUT ${DEMO_BOUND_ANIMATION_BINARY}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/pack_animation_binary.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_animation.json
          ${DEMO_BOUND_ANIMATION_BINARY} --atlas ${DEMO_ATLAS_BINARY}
  DEPENDS ${DEMO_ATLAS_BINARY}
          ${CMAKE_CURRENT_SOURCE_DIR}/../assets/demo_animation.json
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/pack_animation_binary.py
          ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_animation_manifest.py
  VERBATIM)
add_custom_target(vpd_demo_bound_animation DEPENDS ${DEMO_BOUND_ANIMATION_BINARY})
add_executable(vpd_asset_bundle_test ../tests/test_asset_bundle.cpp)
target_include_directories(vpd_asset_bundle_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_asset_bundle_test vpd_demo_atlas vpd_demo_animation vpd_demo_animation_binary vpd_demo_bound_animation)
target_link_libraries(vpd_asset_bundle_test PRIVATE vpd_scene_renderer)
add_test(NAME paired_texture_and_animation_reload
         COMMAND vpd_asset_bundle_test ${DEMO_ANIMATION_BINARY} ${DEMO_BOUND_ANIMATION_BINARY})
add_test(NAME animation_unit COMMAND vpd_animation_test)

# Integrate the same portable deterministic simulation as the libnx NRO.
add_subdirectory(../game_core "${CMAKE_CURRENT_BINARY_DIR}/native_game_core")
add_executable(vpd_graphics_integration_test ../tests/test_graphics_integration.cpp)
target_link_libraries(vpd_graphics_integration_test PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME game_to_graphics_integration COMMAND vpd_graphics_integration_test)
# End-to-end source-derived Fire / target hit state -> actual RGBA pixels.
# This native host test never requires the NES ROM or Nintendo Switch SDK.
add_executable(vpd_graphics_combat_integration_test
               ../tests/test_graphics_combat_integration.cpp)
target_link_libraries(vpd_graphics_combat_integration_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_combat_to_raster_integration
         COMMAND vpd_graphics_combat_integration_test)
# Opt-in dash mechanics must reach pixels through the same NRO render bridge.
add_executable(vpd_manual_dash_raster_test ../tests/test_manual_dash_raster.cpp)
target_link_libraries(vpd_manual_dash_raster_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_manual_dash_to_raster COMMAND vpd_manual_dash_raster_test)
# Same guard encounter bridge used by both libnx and native host rendering.
add_executable(vpd_guard_enemy_raster_test ../tests/test_guard_enemy_raster.cpp)
target_link_libraries(vpd_guard_enemy_raster_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_guard_enemy_to_raster COMMAND vpd_guard_enemy_raster_test)
# Source-owned guard detection and post-strike cooldown: optional HD-only
# readiness icon, isolated from source HP, actor sprite and all old gameplay.
add_executable(vpd_hd_guard_threat_tell_test
               ../tests/test_hd_guard_threat_tell.cpp)
target_link_libraries(vpd_hd_guard_threat_tell_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_guard_threat_tell_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_hd_guard_threat_tell
         COMMAND vpd_hd_guard_threat_tell_test)
# Shared libnx/host proof of turret sprite, HP and hostile shot pixels.
add_executable(vpd_second_wave_raster_test ../tests/test_second_wave_raster.cpp)
target_link_libraries(vpd_second_wave_raster_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_second_wave_to_raster COMMAND vpd_second_wave_raster_test)
# Source-derived world-space exit gate and earned stage-clear overlay.
add_executable(vpd_stage_exit_portal_test ../tests/test_stage_exit_portal.cpp)
target_link_libraries(vpd_stage_exit_portal_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_stage_exit_portal
         COMMAND vpd_stage_exit_portal_test)
# Actual terminal simulation outcomes drive replay prompts in shared RGBA.
add_executable(vpd_manual_retry_raster_test
               ../tests/test_manual_retry_raster.cpp)
target_link_libraries(vpd_manual_retry_raster_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_manual_retry_to_raster
         COMMAND vpd_manual_retry_raster_test)
# Manual HUD layout must remain legible; hit pulses derive from live combat.
add_executable(vpd_combat_hud_feedback_test ../tests/test_combat_hud_feedback.cpp)
target_link_libraries(vpd_combat_hud_feedback_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME romfree_combat_hud_feedback COMMAND vpd_combat_hud_feedback_test)
# Optional HD low-HP pulse derives from authentic guard damage to HP2;
# its complete image diff must exclude gameplay art and legacy HUD hearts.
add_executable(vpd_hd_low_health_warning_test
               ../tests/test_hd_low_health_warning.cpp)
target_link_libraries(vpd_hd_low_health_warning_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_low_health_warning_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_hd_low_health_warning
         COMMAND vpd_hd_low_health_warning_test)
add_executable(vpd_graphics_animation_test ../tests/test_graphics_animation_integration.cpp)
target_include_directories(vpd_graphics_animation_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_graphics_animation_test vpd_demo_atlas vpd_demo_animation)
target_link_libraries(vpd_graphics_animation_test PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME gameplay_sprite_animation_integration COMMAND vpd_graphics_animation_test)

# Portable HD-visuals shoulder toggle must preserve replay and source state.
add_executable(vpd_hd_fx_toggle_test ../tests/test_hd_fx_toggle.cpp)
target_link_libraries(vpd_hd_fx_toggle_test PRIVATE vpd_scene_renderer)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_fx_toggle_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_hd_effects_runtime_toggle
         COMMAND vpd_hd_fx_toggle_test)
# Assert the full game_core combat/retry fingerprint is identical for
# different HD preferences; compare real scene pixels without a HUD shortcut.
add_executable(vpd_hd_fx_gameplay_invariance_test
               ../tests/test_hd_fx_simulation_invariance.cpp)
target_link_libraries(vpd_hd_fx_gameplay_invariance_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_fx_gameplay_invariance_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_hd_fx_gameplay_invariance
         COMMAND vpd_hd_fx_gameplay_invariance_test)
# Two real combat events: three swept guard hits and a live hostile bullet.
add_executable(vpd_hd_fx_live_combat_test
               ../tests/test_hd_fx_live_combat.cpp)
target_link_libraries(vpd_hd_fx_live_combat_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_fx_live_combat_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_hd_fx_live_combat
         COMMAND vpd_hd_fx_live_combat_test)
# Real second-wave sentry bullet: isolated HD projectile halo differs only
# in raster, while both simulations deliver identical hostile collision damage.
add_executable(vpd_hd_fx_live_sentry_replay_test
               ../tests/test_hd_fx_live_sentry_replay.cpp)
target_link_libraries(vpd_hd_fx_live_sentry_replay_test
                      PRIVATE vpd_scene_renderer vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_fx_live_sentry_replay_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_hd_fx_live_sentry_projectile_replay
         COMMAND vpd_hd_fx_live_sentry_replay_test)

# Independent pixel-safe original-style combat hit-light regression.
add_executable(vpd_hd_impact_lighting_test
               ../tests/test_impact_lighting.cpp)
target_include_directories(vpd_hd_impact_lighting_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR})
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_hd_impact_lighting_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME hd_impact_lighting_bounds
         COMMAND vpd_hd_impact_lighting_test)

# Stage 160: ROM-free overhead driving preview, with hard-clipped road and
# separately bounded HUD. Opt-in only; approved platform golden unchanged.
add_executable(vpd_driving_preview_test ../tests/test_driving_preview.cpp)
target_link_libraries(vpd_driving_preview_test PRIVATE vpd_scene_renderer)
target_include_directories(vpd_driving_preview_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_preview_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_preview_hud_road_isolation
         COMMAND vpd_driving_preview_test)

# Stage 161: synthetic driving state is independent from the original
# platform simulation, with deterministic steering/collision invariants.
add_executable(vpd_driving_simulation_test
               ../tests/test_driving_simulation.cpp)
target_link_libraries(vpd_driving_simulation_test PRIVATE vpd_simulation)
target_include_directories(vpd_driving_simulation_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_simulation_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_independent_vehicle_controls
         COMMAND vpd_driving_simulation_test)

# Stage 162: the exact header-only adapter used by the NRO maps each live
# synthetic physics snapshot to the renderer. The platform path is immutable.
add_executable(vpd_driving_scene_bridge_test
               ../tests/test_driving_scene_bridge.cpp)
target_link_libraries(vpd_driving_scene_bridge_test PRIVATE
                      vpd_scene_renderer vpd_simulation)
target_include_directories(vpd_driving_scene_bridge_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_scene_bridge_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_scene_bridge
         COMMAND vpd_driving_scene_bridge_test)
# Stage 163: ROM-free source-owned guest record state machine.
add_executable(vpd_driving_guest_witness_test ../tests/test_driving_guest_witness.cpp)
target_link_libraries(vpd_driving_guest_witness_test PRIVATE vpd_simulation)
target_include_directories(vpd_driving_guest_witness_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_guest_witness_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_guest_witness COMMAND vpd_driving_guest_witness_test)
# Stage 164: proof of source-colored framebuffer pixels, sampled at the
# same drawScene frame as real vehicle input/collision (host reference).
add_executable(vpd_driving_raster_witness_test ../tests/test_driving_raster_witness.cpp)
target_include_directories(vpd_driving_raster_witness_test PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_raster_witness_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_same_frame_raster COMMAND vpd_driving_raster_witness_test)
# Stage 165: opt-in, source-backed 41-presented-frame blackout, with the
# platform simulation frozen and original platform frame restored afterward.
add_executable(vpd_driving_stage_exit_test ../tests/test_driving_stage_exit.cpp)
target_link_libraries(vpd_driving_stage_exit_test PRIVATE vpd_scene_renderer vpd_simulation)
target_include_directories(vpd_driving_stage_exit_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_stage_exit_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_to_platform_blackout
         COMMAND vpd_driving_stage_exit_test)
# Stage 166: 43 strict native source-owned blackout/pad transition events.
add_executable(vpd_driving_exit_guest_test ../tests/test_driving_exit_guest.cpp)
target_link_libraries(vpd_driving_exit_guest_test PRIVATE vpd_simulation)
target_include_directories(vpd_driving_exit_guest_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_exit_guest_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_exit_guest_witness COMMAND vpd_driving_exit_guest_test)
# Stage 167: preserve only image-space original numerical road observations.
add_executable(vpd_driving_road_reference_test ../tests/test_driving_road_reference.cpp)
target_include_directories(vpd_driving_road_reference_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_road_reference_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_original_road_cross_section_reference
         COMMAND vpd_driving_road_reference_test)
# Stage 168: numeric frame-only original image/PPU CPU writer alignment.
add_executable(vpd_road_ppu_alignment_test ../tests/test_driving_road_ppu_alignment.cpp)
target_include_directories(vpd_road_ppu_alignment_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_road_ppu_alignment_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_original_road_ppu_exact_frame_alignment
         COMMAND vpd_road_ppu_alignment_test)
# Stage 172: optional manual-only exact-frame roadway median X-interval
# swatch. Original sprite/collision/PPU data never enter the renderer.
add_executable(vpd_driving_road_review_test ../tests/test_driving_road_review.cpp)
target_link_libraries(vpd_driving_road_review_test PRIVATE
                      vpd_scene_renderer vpd_simulation)
target_include_directories(vpd_driving_road_review_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_road_review_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_exact_image_interval_review
         COMMAND vpd_driving_road_review_test)
# Stage 173: source-owned NeXium guest evidence for all seven exact numeric
# reference swatches and the eighth OFF image, never original NES art.
add_executable(vpd_driving_road_review_guest_test
               ../tests/test_driving_road_review_guest.cpp)
target_link_libraries(vpd_driving_road_review_guest_test PRIVATE vpd_simulation)
target_include_directories(vpd_driving_road_review_guest_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_driving_road_review_guest_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_driving_road_reference_guest_witness
         COMMAND vpd_driving_road_review_guest_test)
# Stage 176: private-only binary numeric road bundle parser. All fixtures
# synthetic, no original ROM/FM2/media or report rows in the repository.
add_executable(vpd_private_road_bundle_test
               ../tests/test_driving_road_private_bundle.cpp)
target_include_directories(vpd_private_road_bundle_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_private_road_bundle_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_private_road_bundle_validation
         COMMAND vpd_private_road_bundle_test)
# Stage 177: isolated optional 37-frame numeric-only private manual
# reviewer. No original proprietary data or SD file in public CI.
add_executable(vpd_private_road_review_test
               ../tests/test_driving_private_review.cpp)
target_include_directories(vpd_private_road_review_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_private_road_review_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_private_37_road_visual_review
         COMMAND vpd_private_road_review_test)
# Stage 178: optional private numeric SD startup witness, built on
# completely invented synthetic data, never owner ROM or picture bytes.
add_executable(vpd_private_road_sd_guest_test
               ../tests/test_driving_private_road_sd_guest.cpp)
target_include_directories(vpd_private_road_sd_guest_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_private_road_sd_guest_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_private_road_sd_nro_startup
         COMMAND vpd_private_road_sd_guest_test)
# Stage 179: actual NeXium R3 input and source framebuffer proof for 37
# fully synthetic private SD numeric observations and OFF.
add_executable(vpd_private_road_r3_guest_test
               ../tests/test_driving_private_road_r3_guest.cpp)
target_include_directories(vpd_private_road_r3_guest_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../game_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_private_road_r3_guest_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_private_37_road_real_guest_r3_witness
         COMMAND vpd_private_road_r3_guest_test)
