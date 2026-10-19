# ROM-free libnx raster scene diagnostic, 1280x720 RGBA8888.
.DEFAULT_GOAL := all
DEVKITPRO ?= /opt/devkitpro
DEVKITA64 ?= $(DEVKITPRO)/devkitA64
export PATH := $(DEVKITA64)/bin:$(DEVKITPRO)/tools/bin:$(PATH)
TARGET := vpd_native_scene
CXX := aarch64-none-elf-g++
CXXFLAGS := -O2 -g -Wall -Wextra -Wpedantic -std=gnu++17 -fPIE -ffunction-sections -fdata-sections -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -I$(DEVKITPRO)/libnx/include -I../game_core -I../graphics_core -Igenerated
LDFLAGS := -specs=$(DEVKITPRO)/libnx/switch.specs -Wl,--gc-sections -Wl,-Map,$(TARGET).map
LDLIBS := -L$(DEVKITPRO)/libnx/lib -lnx
.PHONY: all clean
all: $(TARGET).nro
generated/demo_animation.hpp: ../tools/build_animation_manifest.py ../assets/demo_animation.json
	mkdir -p generated
	python3 ../tools/build_animation_manifest.py ../assets/demo_animation.json $@
generated/demo_decor_layout.hpp: ../tools/pack_decor_layout.py ../assets/demo_decor_layout.json
	mkdir -p generated
	python3 ../tools/pack_decor_layout.py ../assets/demo_decor_layout.json --header $@
generated/demo_decor.hpp: ../tools/build_demo_decor.py
	mkdir -p generated
	python3 $< $@
generated/demo_backdrop.hpp: ../tools/build_demo_backdrop.py
	mkdir -p generated
	python3 $< $@
generated/demo_terrain.hpp: ../tools/build_demo_terrain.py
	mkdir -p generated
	python3 $< $@
generated/demo_atlas.hpp: ../tools/build_demo_atlas.py
	mkdir -p generated
	python3 $< $@
$(TARGET).elf: generated/demo_atlas.hpp generated/demo_animation.hpp generated/demo_terrain.hpp generated/demo_backdrop.hpp generated/demo_decor.hpp generated/demo_decor_layout.hpp source/main.cpp ../game_core/simulation.cpp ../game_core/simulation.hpp ../game_core/combat_demo.hpp ../game_core/demo_witness.hpp ../game_core/demo_witness_sd.hpp ../game_core/manual_input_witness.hpp ../game_core/manual_retry.hpp ../game_core/manual_retry_guest_witness.hpp ../game_core/live_defeat_retry_witness.hpp ../game_core/post_defeat_control_witness.hpp ../game_core/post_defeat_fire_witness.hpp ../game_core/third_guard_clear_witness.hpp ../game_core/third_stage_witness.hpp ../game_core/fourth_retry_witness.hpp ../game_core/fourth_combat_witness.hpp ../game_core/fourth_guard_clear_witness.hpp ../game_core/fourth_stage_witness.hpp ../game_core/dash_guest_witness.hpp ../game_core/guard_guest_witness.hpp ../game_core/guard_combat_probe.hpp ../game_core/second_wave_guest_probe.hpp ../game_core/second_wave_live_witness.hpp ../game_core/guard_live_debug.hpp ../game_core/guard_live_witness.hpp ../game_core/guard_live_defeat_witness.hpp ../graphics_core/scene_renderer.cpp ../graphics_core/scene_renderer.hpp ../graphics_core/combat_scene_bridge.hpp ../graphics_core/asset_atlas.cpp ../graphics_core/asset_atlas.hpp ../graphics_core/animation.cpp ../graphics_core/animation.hpp ../graphics_core/asset_source.cpp ../graphics_core/asset_source.hpp ../graphics_core/animation_resource.cpp ../graphics_core/animation_resource.hpp ../graphics_core/asset_bundle.cpp ../graphics_core/asset_bundle.hpp ../graphics_core/terrain_source.cpp ../graphics_core/terrain_source.hpp ../graphics_core/backdrop_source.cpp ../graphics_core/backdrop_source.hpp ../graphics_core/decor_source.cpp ../graphics_core/decor_source.hpp ../graphics_core/decor_layout.cpp ../graphics_core/decor_layout.hpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) source/main.cpp ../game_core/simulation.cpp ../graphics_core/scene_renderer.cpp ../graphics_core/asset_atlas.cpp ../graphics_core/animation.cpp ../graphics_core/asset_source.cpp ../graphics_core/animation_resource.cpp ../graphics_core/asset_bundle.cpp ../graphics_core/terrain_source.cpp ../graphics_core/backdrop_source.cpp ../graphics_core/decor_source.cpp ../graphics_core/decor_layout.cpp $(LDLIBS) -o $@
$(TARGET).nacp:
	nacptool --create "VPD Native Raster Test" "Homebrew Research" "0.3.0" $@
$(TARGET).nro: $(TARGET).elf $(TARGET).nacp
	elf2nro $(TARGET).elf $@ --nacp=$(TARGET).nacp
clean:
	rm -f $(TARGET).elf $(TARGET).nro $(TARGET).nacp $(TARGET).map
	rm -rf generated
