cmake_minimum_required(VERSION 3.16)
project(vpd_game_scaffold LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_library(vpd_simulation STATIC simulation.cpp)
target_include_directories(vpd_simulation PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_simulation PRIVATE -Wall -Wextra -Wpedantic)
endif()
add_executable(vpd_simulation_test ../tests/test_simulation.cpp)
target_link_libraries(vpd_simulation_test PRIVATE vpd_simulation)
enable_testing()
add_test(NAME deterministic_simulation COMMAND vpd_simulation_test)
# Manual-only ROM-free burst movement; must not change pinned autoplay hashes.
add_executable(vpd_manual_dash_test ../tests/test_manual_dash.cpp)
target_link_libraries(vpd_manual_dash_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_manual_dash_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_manual_dash COMMAND vpd_manual_dash_test)
# Guard enemy is opt-in: existing 200-frame attract-mode hashes remain pinned.
add_executable(vpd_guard_enemy_test ../tests/test_guard_enemy.cpp)
target_link_libraries(vpd_guard_enemy_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_guard_enemy_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_guard_enemy_encounter COMMAND vpd_guard_enemy_test)
# Second-wave gated ROM-free sentry, hostile shots and staged corridor exit.
add_executable(vpd_second_wave_sentry_test ../tests/test_second_wave_sentry.cpp)
target_link_libraries(vpd_second_wave_sentry_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_second_wave_sentry_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_second_wave_sentry COMMAND vpd_second_wave_sentry_test)
# Same five-event physics script compiled into actual libnx NRO.
add_executable(vpd_second_wave_guest_probe_test
               ../tests/test_second_wave_guest_probe.cpp)
target_link_libraries(vpd_second_wave_guest_probe_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_second_wave_guest_probe_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_second_wave_guest_script
         COMMAND vpd_second_wave_guest_probe_test)
# The native guard first-step proof is emitted only by authoritative gameplay.
add_executable(vpd_guard_guest_witness_test ../tests/test_guard_guest_witness.cpp)
target_link_libraries(vpd_guard_guest_witness_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_guard_guest_witness_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_guard_guest_serializer COMMAND vpd_guard_guest_witness_test)
# Runs exactly the AArch64 guest-script scenarios on the host as a control.
add_executable(vpd_guard_combat_probe_test ../tests/test_guard_combat_probe.cpp)
target_link_libraries(vpd_guard_combat_probe_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_guard_combat_probe_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_guest_scripted_guard_combat
         COMMAND vpd_guard_combat_probe_test)
# Observable events from actual pad-controlled manual encounter.
add_executable(vpd_guard_live_witness_test ../tests/test_guard_live_witness.cpp)
target_link_libraries(vpd_guard_live_witness_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_guard_live_witness_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_guard_live_manual_witness
         COMMAND vpd_guard_live_witness_test)
# Genuine Fire/impact serialization with deterministic source simulation.
add_executable(vpd_guard_live_defeat_test ../tests/test_guard_live_defeat_witness.cpp)
target_link_libraries(vpd_guard_live_defeat_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_guard_live_defeat_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_guard_live_defeat
         COMMAND vpd_guard_live_defeat_test)
# The exact serializer used by libnx to record actual NeXium ZR+Right effects.
add_executable(vpd_dash_guest_witness_test ../tests/test_dash_guest_witness.cpp)
target_link_libraries(vpd_dash_guest_witness_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_dash_guest_witness_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_dash_guest_serializer COMMAND vpd_dash_guest_witness_test)
# ROM-free command-line replay is a host-side integration proof only.
add_executable(vpd_combat_replay combat_replay.cpp)
target_link_libraries(vpd_combat_replay PRIVATE vpd_simulation)
add_test(NAME romfree_combat_replay COMMAND vpd_combat_replay --verify)
# The actual Switch demo controller plays the same script as the host CLI.
add_executable(vpd_combat_demo_test ../tests/test_combat_demo.cpp)
target_link_libraries(vpd_combat_demo_test PRIVATE vpd_simulation)
add_test(NAME romfree_combat_autoplay_demo COMMAND vpd_combat_demo_test)
# Host-side check of the exact bounded witness text emitted by libnx code.
add_executable(vpd_demo_witness_test ../tests/test_demo_witness.cpp)
target_link_libraries(vpd_demo_witness_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_demo_witness_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_switch_demo_witness COMMAND vpd_demo_witness_test)
# Serialize real manual input/effect sequence and lifecycle without libnx.
add_executable(vpd_manual_input_witness_test ../tests/test_manual_input_witness.cpp)
target_link_libraries(vpd_manual_input_witness_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_manual_input_witness_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_manual_input_witness COMMAND vpd_manual_input_witness_test)
# 16 deterministic seed scripts x 512 ticks: movement, fire, jump, wall edits,
# independent duplicate replays, and strict pinned 8,192-frame FNV witness.
add_executable(vpd_combat_matrix_test ../tests/test_combat_replay_matrix.cpp)
target_link_libraries(vpd_combat_matrix_test PRIVATE vpd_simulation)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vpd_combat_matrix_test PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME romfree_combat_matrix COMMAND vpd_combat_matrix_test)
# CSV path must produce the same pinned final row as the verified scenario.
# The independent audit below validates all rows and the exact CSV SHA256.
# Avoid a weak PASS_REGULAR_EXPRESSION that accepts a matching substring
# amid a malformed or truncated transcript.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(NAME romfree_combat_replay_csv
         COMMAND ${Python3_EXECUTABLE}
                 ${CMAKE_CURRENT_SOURCE_DIR}/../tools/audit_romfree_combat_trace.py
                 --binary $<TARGET_FILE:vpd_combat_replay>)
# Fail closed on invalid, out-of-range input rather than overflowing
# a simulation-frame counter or accepting a malformed control script.
add_test(NAME romfree_combat_replay_invalid
         COMMAND vpd_combat_replay --frames 3601)
set_tests_properties(romfree_combat_replay_invalid PROPERTIES WILL_FAIL TRUE)
# Independent Python auditor checks each frame and whole-trace SHA256,
# rather than trusting the replay binary's own PASS marker.
add_test(NAME romfree_combat_full_trace
         COMMAND ${Python3_EXECUTABLE}
                 ${CMAKE_CURRENT_SOURCE_DIR}/../tools/audit_romfree_combat_trace.py
                 --binary $<TARGET_FILE:vpd_combat_replay>)
