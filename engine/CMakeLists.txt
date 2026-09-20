cmake_minimum_required(VERSION 3.22)
project(xziel_engine LANGUAGES CXX)

option(XZIEL_ENGINE_BUILD_TESTS "Build Xziel Engine smoke tests" ON)

add_library(xziel_engine STATIC
    src/engine.cpp
    src/movement.cpp
    src/mobile_controls.cpp
    src/environment.cpp
    src/particles.cpp
    src/performance.cpp
    src/horror.cpp
    src/render_features.cpp
    src/renderer_capabilities.cpp
    src/streaming.cpp
    src/scene_fx.cpp
    src/audio_scene.cpp
    src/frame_graph.cpp
    src/visibility.cpp
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

    add_executable(xziel_engine_smoke tests/engine_smoke.cpp)
    target_link_libraries(xziel_engine_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_engine_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_engine_smoke COMMAND xziel_engine_smoke)

    add_executable(xziel_movement_smoke tests/movement_smoke.cpp)
    target_link_libraries(xziel_movement_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_movement_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_movement_smoke COMMAND xziel_movement_smoke)

    add_executable(xziel_environment_smoke tests/environment_smoke.cpp)
    target_link_libraries(xziel_environment_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_environment_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_environment_smoke COMMAND xziel_environment_smoke)

    add_executable(xziel_particles_smoke tests/particles_smoke.cpp)
    target_link_libraries(xziel_particles_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_particles_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_particles_smoke COMMAND xziel_particles_smoke)

    add_executable(xziel_performance_smoke tests/performance_smoke.cpp)
    target_link_libraries(xziel_performance_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_performance_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_performance_smoke COMMAND xziel_performance_smoke)

    add_executable(xziel_horror_smoke tests/horror_smoke.cpp)
    target_link_libraries(xziel_horror_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_horror_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_horror_smoke COMMAND xziel_horror_smoke)

    add_executable(xziel_render_features_smoke tests/render_features_smoke.cpp)
    target_link_libraries(xziel_render_features_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_render_features_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_render_features_smoke COMMAND xziel_render_features_smoke)

    add_executable(xziel_renderer_capabilities_smoke tests/renderer_capabilities_smoke.cpp)
    target_link_libraries(xziel_renderer_capabilities_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_renderer_capabilities_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_renderer_capabilities_smoke COMMAND xziel_renderer_capabilities_smoke)

    add_executable(xziel_streaming_smoke tests/streaming_smoke.cpp)
    target_link_libraries(xziel_streaming_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_streaming_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_streaming_smoke COMMAND xziel_streaming_smoke)

    add_executable(xziel_scene_fx_smoke tests/scene_fx_smoke.cpp)
    target_link_libraries(xziel_scene_fx_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_scene_fx_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_scene_fx_smoke COMMAND xziel_scene_fx_smoke)

    add_executable(xziel_audio_scene_smoke tests/audio_scene_smoke.cpp)
    target_link_libraries(xziel_audio_scene_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_audio_scene_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_audio_scene_smoke COMMAND xziel_audio_scene_smoke)

    add_executable(xziel_frame_graph_smoke tests/frame_graph_smoke.cpp)
    target_link_libraries(xziel_frame_graph_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_frame_graph_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_frame_graph_smoke COMMAND xziel_frame_graph_smoke)

    add_executable(xziel_visibility_smoke tests/visibility_smoke.cpp)
    target_link_libraries(xziel_visibility_smoke PRIVATE xziel_engine)
    target_compile_features(xziel_visibility_smoke PRIVATE cxx_std_20)
    add_test(NAME xziel_visibility_smoke COMMAND xziel_visibility_smoke)
endif()
