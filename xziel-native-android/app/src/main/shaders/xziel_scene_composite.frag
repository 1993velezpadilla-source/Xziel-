#version 450

layout(set = 0, binding = 0) uniform sampler2D uScene;
layout(location = 0) in vec2 vUv;
layout(location = 0) out vec4 outColor;

void main() {
    // FIDELITYFX_CAS_SHARPEN_V1
    // Five-tap sharpen-only adaptation of AMD FidelityFX CAS (MIT), pinned to
    // GPUOpen-Effects/FidelityFX-CAS commit
    // 9fabcc9a2c45f958aff55ddfda337e74ef894b7f.
    //
    // CAS shapes its negative neighbor weight from the local signal headroom
    // instead of applying one fixed Laplacian everywhere. That is exactly what
    // this mobile compositor needs: recover stone/photogrammetry detail after
    // dynamic-resolution sampling while avoiding halos on gothic windows,
    // weapon silhouettes, HUD edges and bright highlights.
    vec2 texel =
        1.0 /
        vec2(textureSize(uScene, 0));

    vec3 c = texture(uScene, vUv).rgb;
    vec3 n = texture(uScene, vUv + vec2(0.0, -texel.y)).rgb;
    vec3 s = texture(uScene, vUv + vec2(0.0,  texel.y)).rgb;
    vec3 w = texture(uScene, vUv + vec2(-texel.x, 0.0)).rgb;
    vec3 e = texture(uScene, vUv + vec2( texel.x, 0.0)).rgb;

    vec3 localMin =
        min(
            c,
            min(
                min(n, s),
                min(w, e)));

    vec3 localMax =
        max(
            c,
            max(
                max(n, s),
                max(w, e)));

    // FidelityFX CAS uses the green channel for one shared filter coefficient
    // in its fast path. Preserve that property so RGB edges remain aligned and
    // the shader stays at five texture reads.
    float maxGreen =
        max(
            localMax.g,
            1.0e-4);

    float amplitude =
        clamp(
            min(
                localMin.g,
                1.0 - localMax.g) /
                maxGreen,
            0.0,
            1.0);

    amplitude =
        sqrt(amplitude);

    // 0 = conservative CAS, 1 = maximum CAS.
    // #580 proved the CAS path itself is healthy: 3/4 deterministic views
    // cleared the pixel-quality gate and the entry view missed by only
    // blur=0.0028 / high-frequency=0.0018. Move one bounded step stronger
    // rather than stacking another post-process pass.
    // SANCTUM_ENTRY_CAS_TUNING_V2
    const float sharpness = 0.88;
    const float peak =
        -1.0 /
        mix(
            8.0,
            5.0,
            sharpness);

    float weight =
        amplitude *
        peak;

    float reciprocalWeight =
        1.0 /
        max(
            1.0 +
                4.0 *
                weight,
            0.20);

    vec3 sharpened =
        (
            (n + s + w + e) *
                weight +
            c
        ) *
        reciprocalWeight;

    // The current scene target is display-referred before the separate HUD
    // pass. Saturation here matches the reference CAS sharpen-only path and
    // prevents negative/overshoot ringing from leaking into presentation.
    sharpened =
        clamp(
            sharpened,
            vec3(0.0),
            vec3(1.0));

    outColor =
        vec4(
            sharpened,
            1.0);
}
