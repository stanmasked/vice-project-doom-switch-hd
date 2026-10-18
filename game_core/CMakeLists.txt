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
# ROM-free command-line replay is a host-side integration proof only.
add_executable(vpd_combat_replay combat_replay.cpp)
target_link_libraries(vpd_combat_replay PRIVATE vpd_simulation)
add_test(NAME romfree_combat_replay COMMAND vpd_combat_replay --verify)
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
add_test(NAME romfree_combat_replay_csv
         COMMAND vpd_combat_replay --frames 200)
set_tests_properties(romfree_combat_replay_csv PROPERTIES
    PASS_REGULAR_EXPRESSION
    "200,0,12288,53760,0,11,0,3,0,5947277116621119566")
# Fail closed on invalid, out-of-range input rather than overflowing
# a simulation-frame counter or accepting a malformed control script.
add_test(NAME romfree_combat_replay_invalid
         COMMAND vpd_combat_replay --frames 3601)
set_tests_properties(romfree_combat_replay_invalid PROPERTIES WILL_FAIL TRUE)
# Independent Python auditor checks each frame and whole-trace SHA256,
# rather than trusting the replay binary's own PASS marker.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(NAME romfree_combat_full_trace
         COMMAND ${Python3_EXECUTABLE}
                 ${CMAKE_CURRENT_SOURCE_DIR}/../tools/audit_romfree_combat_trace.py
                 --binary $<TARGET_FILE:vpd_combat_replay>)
