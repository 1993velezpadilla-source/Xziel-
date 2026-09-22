cmake_minimum_required(VERSION 3.22.1)
project(xziel_native_android LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(game-activity REQUIRED CONFIG)
find_package(games-frame-pacing REQUIRED CONFIG)

set(XZIEL_ENGINE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
add_subdirectory(
    "${CMAKE_CURRENT_LIST_DIR}/../../../../../engine"
    "${CMAKE_CURRENT_BINARY_DIR}/xziel-engine"
)

add_library(xziel-native SHARED
    main.cpp
    android_input.cpp
    android_haptics.cpp
    android_audio.cpp
    vulkan_clear_renderer.cpp
    vulkan_static_mesh_renderer.cpp
)

target_include_directories(xziel-native
    PRIVATE
        "${CMAKE_CURRENT_LIST_DIR}"
)

target_compile_definitions(xziel-native
    PRIVATE
        VK_USE_PLATFORM_ANDROID_KHR=1
)

target_compile_options(xziel-native
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

target_link_libraries(xziel-native
    PRIVATE
        xziel_engine
        game-activity::game-activity_static
        games-frame-pacing::swappy_static
        android
        jnigraphics
        aaudio
        log
        vulkan
)

target_link_options(xziel-native
    PRIVATE
        "-Wl,-u,Java_com_google_androidgamesdk_GameActivity_initializeNativeCode"
)
