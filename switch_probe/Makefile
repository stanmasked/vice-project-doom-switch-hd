# ROM-free fixed-step native game scaffold (libnx only).
.DEFAULT_GOAL := all
DEVKITPRO ?= /opt/devkitpro
DEVKITA64 ?= $(DEVKITPRO)/devkitA64
export PATH := $(DEVKITA64)/bin:$(DEVKITPRO)/tools/bin:$(PATH)
TARGET := vpd_native_probe
CXX := aarch64-none-elf-g++
CXXFLAGS := -O2 -g -Wall -Wextra -Wpedantic -std=gnu++17 -fPIE -ffunction-sections -fdata-sections -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -I$(DEVKITPRO)/libnx/include -I../game_core
LDFLAGS := -specs=$(DEVKITPRO)/libnx/switch.specs -Wl,--gc-sections -Wl,-Map,$(TARGET).map
LDLIBS := -L$(DEVKITPRO)/libnx/lib -lnx
.PHONY: all clean
all: $(TARGET).nro
$(TARGET).elf: source/main.cpp ../game_core/simulation.cpp ../game_core/simulation.hpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) source/main.cpp ../game_core/simulation.cpp $(LDLIBS) -o $@
$(TARGET).nacp:
	nacptool --create "VPD Native Scene Test" "Homebrew Research" "0.2.0" $@
$(TARGET).nro: $(TARGET).elf $(TARGET).nacp
	elf2nro $(TARGET).elf $@ --nacp=$(TARGET).nacp
clean:
	rm -f $(TARGET).elf $(TARGET).nro $(TARGET).nacp $(TARGET).map
