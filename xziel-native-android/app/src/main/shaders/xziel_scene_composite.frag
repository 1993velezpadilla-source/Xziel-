#version 450

layout(set = 0, binding = 0) uniform sampler2D uScene;
layout(location = 0) in vec2 vUv;
layout(location = 0) out vec4 outColor;

void main() {
    // The fullscreen triangle only covers the viewport interior and the
    // sampler is already CLAMP_TO_EDGE, so clamping UVs in the fragment
    // shader duplicates address handling for every swapchain pixel.
    outColor = texture(uScene, vUv);
}
