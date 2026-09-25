#version 450

layout(set = 0, binding = 0) uniform sampler2D uScene;
layout(location = 0) in vec2 vUv;
layout(location = 0) out vec4 outColor;

void main() {
    // SCENE_CONTRAST_ADAPTIVE_SHARPEN_V1
    // The scene may be dynamically rendered below native resolution. Restore
    // local edge definition before the HUD pass without sharpening UI/text.
    vec2 texel =
        1.0 /
        vec2(textureSize(uScene, 0));

    vec3 c = texture(uScene, vUv).rgb;
    vec3 n = texture(uScene, vUv + vec2(0.0, -texel.y)).rgb;
    vec3 s = texture(uScene, vUv + vec2(0.0,  texel.y)).rgb;
    vec3 w = texture(uScene, vUv + vec2(-texel.x, 0.0)).rgb;
    vec3 e = texture(uScene, vUv + vec2( texel.x, 0.0)).rgb;

    vec3 localMin = min(c, min(min(n, s), min(w, e)));
    vec3 localMax = max(c, max(max(n, s), max(w, e)));
    vec3 span = max(localMax - localMin, vec3(1.0e-4));

    float localContrast =
        max(
            max(span.r, span.g),
            span.b);

    float strength =
        mix(
            0.16,
            0.34,
            clamp(
                localContrast * 4.0,
                0.0,
                1.0));

    vec3 laplacian =
        c * 4.0 -
        (n + s + w + e);

    vec3 sharpened =
        c +
        laplacian * strength;

    // Tight local clamp prevents ringing/halos around gothic windows and the
    // weapon silhouette while still restoring texture/stone definition.
    vec3 guard =
        vec3(0.025) +
        span * 0.08;

    sharpened =
        clamp(
            sharpened,
            localMin - guard,
            localMax + guard);

    outColor =
        vec4(
            max(sharpened, vec3(0.0)),
            1.0);
}
