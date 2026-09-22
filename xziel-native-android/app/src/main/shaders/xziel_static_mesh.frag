#version 450

layout(set = 0, binding = 0)
uniform sampler2D uAlbedo;

layout(location = 0) in vec2 vUv;
layout(location = 1) in vec3 vNormal;
layout(location = 2) in vec4 vColor;
layout(location = 3) in float vDistance;
layout(location = 4) in float vFogDensity;
layout(location = 5) in float vLightning;
layout(location = 6) in float vViewmodel;

layout(location = 0) out vec4 outColor;

void main() {
    vec4 albedo =
        texture(
            uAlbedo,
            vUv);

    if (vViewmodel > 0.5) {
        vec3 normal =
            normalize(vNormal);
        vec3 keyDirection =
            normalize(
                vec3(
                    -0.35,
                     0.70,
                    -0.62));
        float key =
            max(
                dot(
                    normal,
                    keyDirection),
                0.0);

        outColor =
            vec4(
                albedo.rgb *
                    (0.58 + key * 0.52),
                albedo.a);
        return;
    }

    // CLEAN V2 source-fidelity baseline.
    // The original photogrammetry already contains captured lighting in its
    // base color. Do not tint, fog, rebake, sharpen, or grade it here. SRGB
    // texture sampling + SRGB swapchain gives a direct renderer comparison.
    outColor = albedo;
}
