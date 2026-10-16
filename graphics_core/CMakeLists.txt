cmake_minimum_required(VERSION 3.16)
project(vpd_scene_renderer LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_library(vpd_scene_renderer STATIC scene_renderer.cpp asset_atlas.cpp animation.cpp asset_source.cpp animation_resource.cpp asset_bundle.cpp terrain_source.cpp backdrop_source.cpp)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
target_include_directories(vpd_scene_renderer PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
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
add_executable(vpd_graphics_animation_test ../tests/test_graphics_animation_integration.cpp)
target_include_directories(vpd_graphics_animation_test PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
add_dependencies(vpd_graphics_animation_test vpd_demo_atlas vpd_demo_animation)
target_link_libraries(vpd_graphics_animation_test PRIVATE vpd_scene_renderer vpd_simulation)
add_test(NAME gameplay_sprite_animation_integration COMMAND vpd_graphics_animation_test)
