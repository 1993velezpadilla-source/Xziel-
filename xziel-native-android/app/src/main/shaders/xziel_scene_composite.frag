#version 450

layout(set = 0, binding = 0)
uniform sampler2D uScene;

layout(push_constant) uniform SceneGrade {
    // x exposure scale, y contrast, z saturation, w vignette.
    vec4 grade;
    // x post-process quality scale, y lightning flash.
    vec4 effects;
} pc;

layout(location = 0) in vec2 vUv;
layout(location = 0) out vec4 outColor;

void main() {
    vec2 uv =
        clamp(
            vUv,
            vec2(0.0),
            vec2(1.0));

    vec3 color =
        texture(
            uScene,
            uv).rgb;

    float quality =
        clamp(
            pc.effects.x,
            0.35,
            1.0);

    color *=
        clamp(
            pc.grade.x,
            0.10,
            2.0);

    float luminance =
        dot(
            color,
            vec3(
                0.2126,
                0.7152,
                0.0722));

    float saturation =
        mix(
            1.0,
            clamp(
                pc.grade.z,
                0.50,
                1.20),
            quality);

    color =
        mix(
            vec3(luminance),
            color,
            saturation);

    float contrast =
        mix(
            1.0,
            clamp(
                pc.grade.y,
                0.70,
                1.40),
            quality);

    // 0.18 is middle grey in linear space and is a better photographic pivot
    // than display-space 0.5 for a scene-grade operation.
    color =
        (color - vec3(0.18)) *
            contrast +
        vec3(0.18);

    vec2 centered =
        uv * 2.0 -
        1.0;

    float radial =
        dot(
            centered,
            centered);

    float vignetteMask =
        smoothstep(
            0.25,
            1.45,
            radial);

    float vignette =
        clamp(
            pc.grade.w,
            0.0,
            0.78) *
        quality;

    color *=
        1.0 -
        vignetteMask *
        vignette *
        0.62;

    // A tiny cool lift during lightning keeps the whole scene connected to
    // weather without turning the frame into a flat white flash. Geometry
    // lighting remains the primary lightning response.
    float lightning =
        clamp(
            pc.effects.y,
            0.0,
            2.0);

    color +=
        vec3(
            0.016,
            0.024,
            0.040) *
        lightning *
        quality;

    outColor =
        vec4(
            clamp(
                color,
                0.0,
                1.0),
            1.0);
}
