#version 450

layout(location = 0) in vec3 vNormal;
layout(location = 1) in vec3 vWorldPosition;
layout(location = 2) in float vPulse;
layout(location = 3) flat in int vMaterial;
layout(location = 4) in vec4 vEnvironment;
layout(location = 5) in vec4 vWaterSurface;
layout(location = 6) in vec4 vWaterSurfaceExtra;

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

    float wetRipple =
        0.5 +
        0.5 *
        sin(
            vWorldPosition.x *
                2.7 +
            vWorldPosition.z *
                3.3 +
            pulse *
                4.0);

    float wetFloorHighlight =
        vMaterial == 0
        ? floorFacing *
            wetness *
            (0.06 +
             wetRipple * 0.10)
        : 0.0;

    lit +=
        vec3(
            0.12,
            0.25,
            0.38) *
        wetFloorHighlight;

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

        float waveA =
            sin(
                vWorldPosition.x * 4.8 +
                vWorldPosition.z * 2.6 +
                wavePhase * 6.2831853);

        float waveB =
            cos(
                vWorldPosition.z * 5.3 -
                vWorldPosition.x * 1.9 -
                wavePhase * 8.1);

        float wave =
            0.5 +
            0.25 * waveA +
            0.25 * waveB;

        float gloss =
            (1.0 - roughness) *
            reflectionStrength;

        vec3 reflectedSky =
            vec3(
                0.10,
                0.22,
                0.34) *
            (0.45 +
             wave * 0.55);

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
            foam *
            smoothstep(
                0.64,
                0.96,
                wave) *
            0.34;

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

        lit =
            mix(
                vec3(
                    0.025,
                    0.032,
                    0.042),
                vec3(
                    0.18,
                    0.25,
                    0.34),
                0.40 +
                    glossy * 0.45) +
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
