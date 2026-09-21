#version 450

layout(location = 0) in vec3 vNormal;
layout(location = 1) in vec3 vWorldPosition;
layout(location = 2) in float vPulse;
layout(location = 3) flat in int vMaterial;
layout(location = 4) in vec4 vEnvironment;
layout(location = 5) in vec4 vWaterSurface;
layout(location = 6) in vec4 vWaterSurfaceExtra;

layout(set = 0, binding = 0) uniform sampler2D uPlanarReflection;

layout(location = 0) out vec4 outColor;

vec3 materialBase(int material, float pulse) {
    if (material == 0) {
        return vec3(0.055, 0.060, 0.070);
    }

    if (material == 1) {
        return vec3(0.075, 0.070, 0.080);
    }

    if (material == 2) {
        return vec3(0.040, 0.055, 0.065);
    }

    if (material == 4) {
        return vec3(0.055, 0.075, 0.045);
    }

    if (material == 5) {
        return vec3(0.145, 0.105, 0.085);
    }

    if (material == 6) {
        return vec3(0.30, 0.012, 0.018);
    }

    if (material == 7) {
        return vec3(0.006, 0.008, 0.012);
    }

    if (material == 8) {
        return vec3(0.20, 0.48, 0.68);
    }

    if (material == 10) {
        return vec3(0.055, 0.065, 0.078);
    }

    if (material == 11) {
        return vec3(1.0, 0.24, 0.035);
    }

    if (material == 12) {
        return vec3(0.045, 0.050, 0.060);
    }

    if (material == 13) {
        return vec3(0.018, 0.055, 0.078);
    }

    if (material == 14) {
        return vec3(0.095, 0.115, 0.135);
    }

    vec3 core = vec3(0.12, 0.015, 0.040);
    vec3 hot = vec3(0.78, 0.025, 0.22);
    return mix(core, hot, 0.30 + 0.32 * pulse);
}

void main() {
    vec3 normal = normalize(vNormal);

    vec3 keyDirection = normalize(vec3(-0.38, 0.78, -0.48));
    vec3 rimDirection = normalize(vec3(0.72, 0.14, 0.68));

    float key = max(dot(normal, keyDirection), 0.0);
    float rim = pow(max(dot(normal, rimDirection), 0.0), 3.0);

    float pulse = clamp(vPulse, 0.0, 1.0);

    vec3 base = materialBase(vMaterial, pulse);

    float floorCold =
        smoothstep(-1.55, -0.6, -vWorldPosition.y);

    vec3 coldBounce = vec3(0.015, 0.08, 0.12) * floorCold;
    vec3 magentaRim = vec3(0.60, 0.02, 0.18) * rim * (0.10 + 0.18 * pulse);

    float wetness =
        clamp(
            vEnvironment.z,
            0.0,
            1.0);

    float lightning =
        clamp(
            vEnvironment.y,
            0.0,
            2.0);

    float rainIntensity =
        clamp(
            vEnvironment.w,
            0.0,
            1.0);

    float surfaceQuality =
        clamp(
            vWaterSurfaceExtra.y,
            0.35,
            1.0);

    float rainDetailScale =
        clamp(
            vWaterSurfaceExtra.z,
            0.25,
            1.0);

    vec3 lit =
        base *
            (0.20 +
             key * 0.90) *
            mix(
                1.0,
                0.78,
                wetness)
        + coldBounce *
            mix(
                1.0,
                1.65,
                wetness)
        + magentaRim
        + vec3(
              0.55,
              0.68,
              0.95) *
            lightning *
            0.55;

    float floorFacing =
        max(
            normal.y,
            0.0);

    if (vMaterial == 0 &&
        wetness > 0.001) {
        float rainResponse =
            rainIntensity *
            rainDetailScale;

        float broadPuddle =
            0.5 +
            0.5 *
                sin(
                    vWorldPosition.x * 1.35 +
                    vWorldPosition.z * 1.80);

        if (surfaceQuality > 0.68) {
            broadPuddle =
                0.5 +
                0.25 *
                    sin(
                        vWorldPosition.x * 1.35 +
                        vWorldPosition.z * 1.80) +
                0.25 *
                    cos(
                        vWorldPosition.z * 1.10 -
                        vWorldPosition.x * 1.65);
        }

        float puddleMask =
            smoothstep(
                0.42,
                0.78,
                broadPuddle +
                wetness * 0.28);

        float rainRipple = 0.5;

        if (surfaceQuality > 0.60 &&
            rainResponse > 0.025) {
            rainRipple =
                0.5 +
                0.5 *
                    sin(
                        vWorldPosition.x * 8.4 +
                        vWorldPosition.z * 10.2 +
                        vWaterSurface.x * 31.0);
        }

        float wetFloorHighlight =
            floorFacing *
            wetness *
            puddleMask *
            (0.055 +
             rainRipple *
                 rainResponse *
                 surfaceQuality *
                 0.10);

        // Wet concrete darkens while the sky/lightning response becomes more
        // visible. This is a reflection proxy, not a second scene render.
        lit =
            mix(
                lit,
                lit * 0.76,
                puddleMask *
                    wetness *
                    0.24);

        lit +=
            vec3(
                0.10,
                0.22,
                0.34) *
            wetFloorHighlight;

        lit +=
            vec3(
                0.42,
                0.55,
                0.82) *
            lightning *
            puddleMask *
            wetness *
            (0.06 +
             0.10 * surfaceQuality);
    }

    if (vMaterial == 8) {
        lit +=
            vec3(
                0.18,
                0.38,
                0.58) *
            (0.35 +
             lightning * 0.40);
    }

    if (vMaterial == 13) {
        float wavePhase =
            vWaterSurface.x;

        float foam =
            clamp(
                vWaterSurface.y,
                0.0,
                1.0);

        float reflectionStrength =
            clamp(
                vWaterSurface.z,
                0.0,
                1.0);

        float refractionStrength =
            clamp(
                vWaterSurface.w,
                0.0,
                1.0);

        float roughness =
            clamp(
                vWaterSurfaceExtra.x,
                0.02,
                0.85);

        float rainResponse =
            rainIntensity *
            rainDetailScale;

        roughness =
            clamp(
                roughness +
                    (1.0 - surfaceQuality) * 0.16 -
                    rainResponse * 0.035,
                0.02,
                0.92);

        float waveA =
            sin(
                vWorldPosition.x * 4.8 +
                vWorldPosition.z * 2.6 +
                wavePhase * 6.2831853);

        float waveB =
            waveA * 0.65;

        if (surfaceQuality > 0.58) {
            waveB =
                cos(
                    vWorldPosition.z * 5.3 -
                    vWorldPosition.x * 1.9 -
                    wavePhase * 8.1);
        }

        float microWave = 0.0;

        if (surfaceQuality > 0.72 &&
            rainResponse > 0.025) {
            microWave =
                sin(
                    (vWorldPosition.x -
                     vWorldPosition.z) *
                        12.0 +
                    wavePhase *
                        18.0) *
                rainResponse *
                surfaceQuality;
        }

        float wave =
            clamp(
                0.5 +
                    0.25 * waveA +
                    0.25 * waveB +
                    microWave * 0.075,
                0.0,
                1.0);

        float gloss =
            (1.0 - roughness) *
            reflectionStrength *
            (0.55 +
             0.45 * surfaceQuality);

        vec3 reflectedSky =
            vec3(
                0.10,
                0.22,
                0.34) *
            (0.45 +
             wave * 0.55);

        // Project the prototype horizontal water plane into a stable
        // screen-like lookup. Wave offsets provide inexpensive roughness
        // distortion while the reflected scene itself comes from Vulkan's
        // offscreen planar pass.
        vec2 reflectionUv =
            vec2(
                0.5 +
                    vWorldPosition.x / 8.4,
                0.5 -
                    vWorldPosition.z / 10.0);

        float distortion =
            (1.0 - roughness) *
            (0.003 +
             rainResponse * 0.006) *
            surfaceQuality;

        reflectionUv +=
            vec2(
                waveA,
                waveB) *
            distortion;

        vec3 planarScene =
            texture(
                uPlanarReflection,
                clamp(
                    reflectionUv,
                    vec2(0.002),
                    vec2(0.998))).rgb;

        float fresnel =
            pow(
                clamp(
                    1.0 -
                    abs(normal.y),
                    0.0,
                    1.0),
                3.0);

        reflectedSky =
            mix(
                reflectedSky,
                planarScene,
                clamp(
                    reflectionStrength *
                    (0.42 +
                     fresnel * 0.48) *
                    (1.0 - roughness * 0.72),
                    0.0,
                    0.92));

        vec3 refractedDepth =
            vec3(
                0.006,
                0.028,
                0.040) *
            (0.70 +
             refractionStrength *
                0.45);

        vec3 foamColor =
            vec3(
                0.42,
                0.58,
                0.66) *
            clamp(
                foam +
                    rainResponse * 0.16,
                0.0,
                1.0) *
            smoothstep(
                0.64,
                0.96,
                wave) *
            (0.24 +
             0.10 * surfaceQuality);

        lit =
            mix(
                refractedDepth,
                reflectedSky,
                clamp(
                    0.28 +
                    gloss * 0.62,
                    0.0,
                    1.0)) +
            foamColor +
            vec3(
                0.58,
                0.72,
                0.96) *
                lightning *
                0.28;
    }

    if (vMaterial == 14) {
        float facing =
            abs(
                dot(
                    normal,
                    normalize(
                        vec3(
                            0.72,
                            0.10,
                            -0.68))));

        float glossy =
            pow(
                clamp(
                    1.0 -
                    facing,
                    0.0,
                    1.0),
                2.0);

        vec2 mirrorUv =
            clamp(
                vec2(
                    0.5 +
                        vWorldPosition.z / 8.0,
                    0.5 -
                        vWorldPosition.y / 4.4),
                vec2(0.002),
                vec2(0.998));

        vec3 planarScene =
            texture(
                uPlanarReflection,
                mirrorUv).rgb;

        lit =
            mix(
                vec3(
                    0.025,
                    0.032,
                    0.042),
                planarScene,
                0.62 +
                    glossy * 0.28) +
            vec3(
                0.48,
                0.58,
                0.86) *
                lightning *
                0.35;
    }

    if (vMaterial >= 10) {
        if (vMaterial == 11) {
            lit +=
                vec3(1.0, 0.15, 0.02) *
                (0.35 + pulse * 0.55);
        }

        outColor =
            vec4(
                lit,
                1.0);
        return;
    }

    float distanceFog =
        clamp(
            (vWorldPosition.z + 3.0) /
                8.0,
            0.0,
            1.0);

    float fogDensity =
        clamp(
            vEnvironment.x,
            0.0,
            1.0);

    vec3 fogColor =
        vec3(
            0.010,
            0.014,
            0.022);

    lit =
        mix(
            lit,
            fogColor,
            clamp(
                distanceFog *
                    (0.10 +
                     fogDensity *
                         0.52),
                0.0,
                0.72));

    outColor = vec4(lit, 1.0);
}
