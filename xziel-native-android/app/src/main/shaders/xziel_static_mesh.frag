#version 450

layout(set = 0, binding = 0)
uniform sampler2D uAlbedo;

layout(location = 0) in vec2 vUv;
layout(location = 1) in vec4 vColor;
layout(location = 2) in float vDistance;
layout(location = 3) in float vFogDensity;
layout(location = 4) in float vLightning;

layout(location = 0) out vec4 outColor;

void main() {
    vec4 albedo =
        texture(
            uAlbedo,
            vUv);

    vec3 baked =
        max(
            vColor.rgb,
            vec3(0.035));

    vec3 lit =
        albedo.rgb *
        baked;

    lit +=
        vec3(
            0.42,
            0.52,
            0.72) *
        vLightning *
        0.22;

    float fog =
        clamp(
            smoothstep(
                28.0,
                150.0,
                vDistance) *
            (0.12 +
             vFogDensity * 0.78),
            0.0,
            0.86);

    vec3 fogColor =
        vec3(
            0.008,
            0.011,
            0.018);

    lit =
        mix(
            lit,
            fogColor,
            fog);

    outColor =
        vec4(
            lit,
            albedo.a);
}
