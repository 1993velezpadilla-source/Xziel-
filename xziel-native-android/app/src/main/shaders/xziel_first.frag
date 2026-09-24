#version 450

layout(location = 0) in vec3 vNormal;
layout(location = 1) in vec3 vWorldPosition;
layout(location = 2) in float vPulse;
layout(location = 3) flat in int vMaterial;
layout(location = 4) in vec4 vEnvironment;
layout(location = 5) in vec4 vWaterSurface;
layout(location = 6) in vec4 vWaterSurfaceExtra;
layout(location = 7) in vec4 vReflectionClip;
layout(location = 8) flat in int vReflectionOwnerMaterial;

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

    if (material == 15) {
        // Warm, worn furniture/wood tone for the native rifle viewmodel.
        return vec3(0.085, 0.032, 0.014);
    }

    if (material == 16) {
        // Matte black polymer/rubber. Kept almost neutral so moonlight does
        // not turn the first-person weapon into a bright cyan prototype.
        return vec3(0.018, 0.022, 0.026);
    }

    if (material == 17) {
        // Desaturated dead flesh. Keep it organic without the bright green
        // proxy tone that made zombies read like debug mannequins.
        return vec3(0.105, 0.078, 0.058);
    }

    if (material == 18) {
        // Torn, rain-darkened clothing.
        return vec3(0.026, 0.032, 0.028);
    }

    vec3 core = vec3(0.12, 0.015, 0.040);
    vec3 hot = vec3(0.78, 0.025, 0.22);
    return mix(core, hot, 0.30 + 0.32 * pulse);
}

void main() {
    vec3 normal = normalize(vNormal);

    float pulse = clamp(vPulse, 0.0, 1.0);

    bool viewmodelMaterial =
        (vMaterial >= 10 &&
         vMaterial <= 12) ||
        (vMaterial >= 15 &&
         vMaterial <= 16);

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

    if (viewmodelMaterial) {
        // VIEWMODEL_WORLD_LIGHTING_GATE_V1
        // Viewmodel shading returns before world floor/rim lighting. Resolve
        // its base here so first-person fragments never evaluate that dead
        // world-lighting work.
        vec3 base =
            materialBase(
                vMaterial,
                pulse);

        // Viewmodel coordinates are camera-local, not world-space. The old
        // path applied floor/cold-bounce lighting to those coordinates and
        // made the gun read as a large cyan block. Give first-person parts a
        // dedicated neutral key/fill response instead.
        vec3 viewKeyDirection =
            normalize(
                vec3(
                    -0.42,
                     0.62,
                    -0.66));
        vec3 viewSpecDirection =
            normalize(
                vec3(
                     0.30,
                     0.46,
                    -0.84));

        float viewKey =
            max(
                dot(
                    normal,
                    viewKeyDirection),
                0.0);
        float viewSpecBase =
            max(
                dot(
                    normal,
                    viewSpecDirection),
                0.0);
        float viewSpec2 =
            viewSpecBase *
            viewSpecBase;
        float viewSpec4 =
            viewSpec2 *
            viewSpec2;
        float viewSpec8 =
            viewSpec4 *
            viewSpec4;
        float viewSpec =
            viewSpec8 *
            viewSpec4;

        float metalResponse =
            vMaterial == 10
            ? 0.34
            : (vMaterial == 16 ? 0.10 : 0.05);

        vec3 viewLit =
            base *
                (0.46 +
                 viewKey * 0.94)
            + vec3(
                  0.030,
                  0.027,
                  0.024)
            + vec3(0.42) *
                viewSpec *
                metalResponse
            + vec3(
                  0.40,
                  0.48,
                  0.66) *
                lightning *
                0.18;

        if (vMaterial == 11) {
            viewLit +=
                vec3(
                    1.0,
                    0.12,
                    0.015) *
                (0.60 +
                 pulse * 0.85);
        }

        outColor =
            vec4(
                viewLit,
                1.0);
        return;
    }

    vec3 lit =
        vec3(0.0);

    // REFLECTIVE_COMMON_LIGHTING_GATE_V1
    // Water and mirror paths fully replace lit before returning, so do not
    // evaluate generic base/key/rim/floor lighting for those materials.
    if (vMaterial != 13 &&
        vMaterial != 14) {
        vec3 keyDirection =
            normalize(
                vec3(
                    -0.38,
                     0.78,
                    -0.48));
        vec3 rimDirection =
            normalize(
                vec3(
                     0.72,
                     0.14,
                     0.68));

        float key =
            max(
                dot(
                    normal,
                    keyDirection),
                0.0);

        // FIXED_INTEGER_POW_MULTIPLIES_V1
        float rimBase =
            max(
                dot(
                    normal,
                    rimDirection),
                0.0);
        float rim =
            rimBase *
            rimBase *
            rimBase;

        vec3 base =
            materialBase(
                vMaterial,
                pulse);

        float floorCold =
            smoothstep(
                -1.55,
                -0.6,
                -vWorldPosition.y);

        vec3 coldBounce =
            vec3(
                0.015,
                0.08,
                0.12) *
            floorCold;

        float horrorRimScale =
            (vMaterial == 17 ||
             vMaterial == 18)
            ? 0.022
            : (0.10 + 0.18 * pulse);

        vec3 magentaRim =
            vec3(
                0.60,
                0.02,
                0.18) *
            rim *
            horrorRimScale;

        lit =
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
    }

    if (vMaterial == 0 &&
        wetness > 0.001) {
        // RAIN_DETAIL_MATERIAL_GATE_V1
        // Rain-detail controls are consumed only by wet floor and water.
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
        float floorFacing =
            max(
                normal.y,
                0.0);
        float rainResponse =
            rainIntensity *
            rainDetailScale;

        // WET_FLOOR_SHARED_PRIMARY_WAVE_V1
        // The high-quality branch uses the same primary puddle sine as the
        // baseline branch. Evaluate it once per wet-floor fragment.
        float puddlePrimaryWave =
            sin(
                vWorldPosition.x * 1.35 +
                vWorldPosition.z * 1.80);

        float broadPuddle =
            0.5 +
            0.5 *
                puddlePrimaryWave;

        if (surfaceQuality > 0.68) {
            broadPuddle =
                0.5 +
                0.25 *
                    puddlePrimaryWave +
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
        // RAIN_DETAIL_MATERIAL_GATE_V1
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

        // PLANAR_REFLECTION_PROJECTION_GATE_V1
        // Projection/division/distortion are dead when water does not own a
        // live target or reflection strength is zero. Gate the whole lookup
        // path, not just the final texture fetch.
        if (vReflectionOwnerMaterial == 13 &&
            reflectionStrength > 0.0) {
            // Perspective-correct lookup from the same reflected camera used
            // by the offscreen capture. Vulkan NDC Y is texture space.
            float reflectionW =
                max(
                    vReflectionClip.w,
                    0.0001);
            vec2 reflectionNdc =
                vReflectionClip.xy /
                reflectionW;
            vec2 reflectionUv =
                vec2(
                    reflectionNdc.x * 0.5 + 0.5,
                    reflectionNdc.y * 0.5 + 0.5);
            bool reflectionProjectionValid =
                vReflectionClip.w > 0.08 &&
                reflectionUv.x >= -0.02 &&
                reflectionUv.x <= 1.02 &&
                reflectionUv.y >= -0.02 &&
                reflectionUv.y <= 1.02;

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
            reflectionProjectionValid =
                reflectionProjectionValid &&
                reflectionUv.x >= -0.015 &&
                reflectionUv.x <= 1.015 &&
                reflectionUv.y >= -0.015 &&
                reflectionUv.y <= 1.015;

            // PLANAR_REFLECTION_FETCH_GATE_V1
            if (reflectionProjectionValid) {
                vec3 planarScene =
                    texture(
                        uPlanarReflection,
                        clamp(
                            reflectionUv,
                            vec2(0.002),
                            vec2(0.998))).rgb;

                float fresnelBase =
                    clamp(
                        1.0 -
                        abs(normal.y),
                        0.0,
                        1.0);
                float fresnel =
                    fresnelBase *
                    fresnelBase *
                    fresnelBase;

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
            }
        }

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

        float glossyBase =
            clamp(
                1.0 -
                facing,
                0.0,
                1.0);
        float glossy =
            glossyBase *
            glossyBase;

        vec3 mirrorProbe =
            mix(
                vec3(0.018, 0.024, 0.034),
                vec3(0.11, 0.16, 0.23),
                0.30 + glossy * 0.52);

        vec3 mirrorBase =
            mirrorProbe;

        // MIRROR_REFLECTION_PROJECTION_GATE_V1
        // A non-owner mirror uses the probe only, so skip projective divide,
        // UV bounds and texture lookup entirely.
        if (vReflectionOwnerMaterial == 14) {
            float mirrorW =
                max(
                    vReflectionClip.w,
                    0.0001);
            vec2 mirrorNdc =
                vReflectionClip.xy /
                mirrorW;
            vec2 mirrorUv =
                vec2(
                    mirrorNdc.x * 0.5 + 0.5,
                    mirrorNdc.y * 0.5 + 0.5);
            bool mirrorProjectionValid =
                vReflectionClip.w > 0.08 &&
                mirrorUv.x >= -0.015 &&
                mirrorUv.x <= 1.015 &&
                mirrorUv.y >= -0.015 &&
                mirrorUv.y <= 1.015;

            if (mirrorProjectionValid) {
                vec3 mirrorPlanar =
                    texture(
                        uPlanarReflection,
                        clamp(
                            mirrorUv,
                            vec2(0.002),
                            vec2(0.998))).rgb;

                mirrorBase =
                    mix(
                        mirrorProbe,
                        mirrorPlanar,
                        clamp(
                            0.76 +
                            glossy * 0.18,
                            0.0,
                            0.94));
            }
        }

        lit =
            mirrorBase +
            vec3(
                0.48,
                0.58,
                0.86) *
                lightning *
                (0.22 + glossy * 0.18);
    }

    if (vMaterial == 13 ||
        vMaterial == 14) {
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
