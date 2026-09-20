cmake_minimum_required(VERSION 3.22)
project(xziel_engine LANGUAGES CXX)

option(XZIEL_ENGINE_BUILD_TESTS "Build Xziel Engine smoke tests" ON)

add_library(xziel_engine STATIC
    src/engine.cpp
    src/movement.cpp
    src/mobile_controls.cpp
    src/environment.cpp
)

target_include_directories(xziel_engine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(xziel_engine PUBLIC cxx_std_20)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(xziel_engine PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(XZIEL_ENGINE_BUILD_TESTS)
    enable_testing()

    add_executable(xziel_engine_smoke
        tests/engine_smoke.cpp
    )
    target_link_libraries(xziel_engine_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_engine_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_engine_smoke COMMAND xziel_engine_smoke)

    add_executable(xziel_movement_smoke
        tests/movement_smoke.cpp
    )
    target_link_libraries(xziel_movement_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_movement_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_movement_smoke COMMAND xziel_movement_smoke)

    add_executable(xziel_environment_smoke
        tests/environment_smoke.cpp
    )
    target_link_libraries(xziel_environment_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_environment_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_environment_smoke COMMAND xziel_environment_smoke)
endif()
