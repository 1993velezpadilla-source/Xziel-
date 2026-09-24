#version 450

layout(set = 0, binding = 0)
uniform sampler2D uAlbedo;
layout(set = 0, binding = 1)
uniform sampler2D uNormal;
layout(set = 0, binding = 2)
uniform sampler2D uOrm;
layout(set = 0, binding = 3)
uniform sampler2D uEmissive;

layout(set = 0, binding = 4, std140)
uniform SceneLighting {
    // xyz = surface-to-light direction in view space, w = intensity.
    vec4 keyDirectionIntensity;
    // rgb = key color, w = ambient intensity.
    vec4 keyColorAmbientIntensity;
    // rgb = ambient color, w = exposure multiplier.
    vec4 ambientColorExposure;
    // rgb = atmospheric fog color, w = density.
    vec4 fogColorDensity;
    // x = contrast, y = saturation, z = height falloff, w = local count.
    vec4 post;

    // Local lights are deliberately fixed-size for predictable mobile cost.
    vec4 localPositionRange[4];
    vec4 localColorIntensity[4];
    // xyz = spot forward direction in view space, w = 0 point / 1 spot.
    vec4 localDirectionType[4];
    // x = inner cone cos, y = outer cone cos, z = volumetric author flag.
    vec4 localConeVolumetric[4];
} uLighting;

layout(push_constant) uniform PushConstants {
    vec4 cameraPositionYaw;
    vec4 cameraPitchFovAspectFog;
    vec4 environment;
    vec4 modelOffsetScale;
    vec4 modelRotationMode;
    vec4 baseColorFactor;
    vec4 metallicRoughnessNormalOcclusion;
    vec4 emissiveFactorFlags;
} pc;

layout(location = 0) in vec2 vUv;
layout(location = 1) in vec3 vNormal;
layout(location = 2) in vec4 vColor;
layout(location = 3) in float vDistance;
layout(location = 4) in float vFogDensity;
layout(location = 5) in float vLightning;
layout(location = 6) in float vViewmodel;
layout(location = 7) in vec3 vViewPosition;

layout(location = 0) out vec4 outColor;

const float PI = 3.14159265358979323846;

float distributionGgx(
    vec3 normal,
    vec3 halfVector,
    float roughness) {
    float alpha = roughness * roughness;
    float alpha2 = alpha * alpha;
    float nDotH = max(dot(normal, halfVector), 0.0);
    float denominator =
        nDotH * nDotH * (alpha2 - 1.0) + 1.0;

    return alpha2 /
        max(PI * denominator * denominator, 0.0001);
}

float geometrySchlickGgx(
    float nDotV,
    float roughness) {
    float r = roughness + 1.0;
    float k = (r * r) * 0.125;

    return nDotV /
        max(nDotV * (1.0 - k) + k, 0.0001);
}

float geometrySmith(
    vec3 normal,
    vec3 viewDirection,
    vec3 lightDirection,
    float roughness) {
    return
        geometrySchlickGgx(
            max(dot(normal, viewDirection), 0.0),
            roughness) *
        geometrySchlickGgx(
            max(dot(normal, lightDirection), 0.0),
            roughness);
}

vec3 fresnelSchlick(
    float cosine,
    vec3 f0) {
    return
        f0 +
        (1.0 - f0) *
        pow(
            clamp(1.0 - cosine, 0.0, 1.0),
            5.0);
}

vec3 mappedNormal(
    vec3 geometricNormal,
    float normalScale) {
    vec3 dpdx = dFdx(vViewPosition);
    vec3 dpdy = dFdy(vViewPosition);
    vec2 duvdx = dFdx(vUv);
    vec2 duvdy = dFdy(vUv);

    float determinant =
        duvdx.x * duvdy.y -
        duvdx.y * duvdy.x;

    if (abs(determinant) < 1.0e-8) {
        return geometricNormal;
    }

    vec3 tangent =
        normalize(
            (dpdx * duvdy.y -
             dpdy * duvdx.y) /
            determinant);

    tangent =
        normalize(
            tangent -
            geometricNormal *
            dot(geometricNormal, tangent));

    vec3 bitangent =
        normalize(
            cross(
                geometricNormal,
                tangent));

    vec3 sampled =
        texture(
            uNormal,
            vUv).xyz *
            2.0 -
        1.0;

    sampled.xy *= normalScale;
    sampled = normalize(sampled);

    return normalize(
        mat3(
            tangent,
            bitangent,
            geometricNormal) *
        sampled);
}

vec3 evaluatePbrLight(
    vec3 normal,
    vec3 viewDirection,
    vec3 lightDirection,
    vec3 radiance,
    vec3 albedo,
    float metallic,
    float roughness) {
    float nDotL =
        max(
            dot(normal, lightDirection),
            0.0);

    if (nDotL <= 0.00001) {
        return vec3(0.0);
    }

    vec3 halfVector =
        normalize(
            viewDirection +
            lightDirection);

    float nDotV =
        max(
            dot(normal, viewDirection),
            0.0);
    float hDotV =
        max(
            dot(halfVector, viewDirection),
            0.0);

    vec3 f0 =
        mix(
            vec3(0.04),
            albedo,
            metallic);

    vec3 fresnel =
        fresnelSchlick(
            hDotV,
            f0);

    float distribution =
        distributionGgx(
            normal,
            halfVector,
            roughness);

    float geometry =
        geometrySmith(
            normal,
            viewDirection,
            lightDirection,
            roughness);

    vec3 specular =
        (distribution *
         geometry *
         fresnel) /
        max(
            4.0 *
            nDotV *
            nDotL,
            0.001);

    vec3 diffuseWeight =
        (vec3(1.0) - fresnel) *
        (1.0 - metallic);

    return
        (diffuseWeight *
             albedo /
             PI +
         specular) *
        radiance *
        nDotL;
}

float localDistanceAttenuation(
    float distanceToLight,
    float rangeMeters) {
    float safeRange =
        max(rangeMeters, 0.05);

    float normalized =
        clamp(
            distanceToLight /
            safeRange,
            0.0,
            1.0);

    float cutoff =
        max(
            1.0 -
            pow(normalized, 4.0),
            0.0);

    cutoff *= cutoff;

    // A softened inverse-square response avoids singular highlights when the
    // player walks directly through a practical fixture.
    float inverseSquare =
        1.0 /
        max(
            distanceToLight *
            distanceToLight,
            0.35);

    return cutoff * inverseSquare;
}

float spotAttenuation(
    int index,
    vec3 surfaceToLight) {
    if (uLighting.localDirectionType[index].w < 0.5) {
        return 1.0;
    }

    vec3 spotForward =
        normalize(
            uLighting.localDirectionType[index].xyz);

    // surfaceToLight points from the fragment to the light; negate it to get
    // the direction in which light travels away from the fixture.
    float cosine =
        dot(
            normalize(-surfaceToLight),
            spotForward);

    float inner =
        uLighting.localConeVolumetric[index].x;
    float outer =
        uLighting.localConeVolumetric[index].y;

    return smoothstep(
        outer,
        max(inner, outer + 0.0001),
        cosine);
}

vec3 evaluateLegacyRelight(vec3 normal) {
    vec3 illumination =
        vec3(0.22) +
        uLighting.ambientColorExposure.rgb *
        uLighting.keyColorAmbientIntensity.w *
        0.85;

    vec3 keyDirection =
        normalize(
            uLighting.keyDirectionIntensity.xyz);

    float keyDiffuse =
        max(
            dot(
                normal,
                keyDirection),
            0.0);

    illumination +=
        uLighting.keyColorAmbientIntensity.rgb *
        max(
            uLighting.keyDirectionIntensity.w,
            0.0) *
        keyDiffuse *
        0.52;

    int localCount =
        clamp(
            int(
                uLighting.post.w +
                0.5),
            0,
            4);

    for (int index = 0;
         index < 4;
         ++index) {
        if (index >= localCount) {
            break;
        }

        vec3 toLight =
            uLighting.localPositionRange[index].xyz -
            vViewPosition;

        float distanceToLight =
            length(toLight);

        if (distanceToLight <= 0.0001) {
            continue;
        }

        vec3 lightDirection =
            toLight /
            distanceToLight;

        float attenuation =
            localDistanceAttenuation(
                distanceToLight,
                uLighting.localPositionRange[index].w) *
            spotAttenuation(
                index,
                lightDirection);

        float diffuse =
            max(
                dot(
                    normal,
                    lightDirection),
                0.0);

        illumination +=
            uLighting.localColorIntensity[index].rgb *
            max(
                uLighting.localColorIntensity[index].w,
                0.0) *
            attenuation *
            diffuse *
            0.34;
    }

    // Preserve enough of the scan's source texture to retain masonry/detail,
    // but no longer let captured daylight define the scene exposure.
    return clamp(
        illumination,
        vec3(0.16),
        vec3(1.25));
}

vec3 applyAtmosphere(
    vec3 color,
    bool viewmodel) {
    if (viewmodel) {
        return color;
    }

    float density =
        max(
            vFogDensity,
            uLighting.fogColorDensity.w);

    float heightFalloff =
        max(
            uLighting.post.z,
            0.0);

    // Camera-relative height shaping is intentionally mild. It gives floor
    // haze more body without requiring a volumetric texture/froxel pass.
    float heightWeight =
        mix(
            1.0,
            0.70,
            clamp(
                abs(vViewPosition.y) *
                heightFalloff *
                0.20,
                0.0,
                1.0));

    float opticalDepth =
        max(vDistance, 0.0) *
        density *
        0.085 *
        heightWeight;

    float fog =
        clamp(
            1.0 -
            exp(-opticalDepth),
            0.0,
            0.94);

    // Lightning should reveal silhouettes through the haze rather than simply
    // whitening the whole scene.
    vec3 fogColor =
        uLighting.fogColorDensity.rgb *
        (1.0 + clamp(vLightning, 0.0, 2.0) * 0.40);

    return mix(
        color,
        fogColor,
        fog);
}

vec3 acesFitted(vec3 value) {
    // Narkowicz-style ACES approximation. This is deliberately cheap enough
    // for the mobile path and keeps bright emissive/lightning detail from
    // clipping into flat white.
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;

    return clamp(
        (value * (a * value + b)) /
        (value * (c * value + d) + e),
        0.0,
        1.0);
}

vec3 toneMapPbr(vec3 color) {
    return
        acesFitted(
            max(
                color,
                vec3(0.0)));
}

void main() {
    int flags =
        int(
            pc.emissiveFactorFlags.w +
            0.5);

    bool pbrEnabled =
        (flags & 1) != 0;
    bool hasNormal =
        (flags & 2) != 0;
    bool hasOrm =
        (flags & 4) != 0;
    bool hasEmissive =
        (flags & 8) != 0;

    vec4 albedo =
        texture(
            uAlbedo,
            vUv) *
        pc.baseColorFactor;

    bool viewmodel =
        vViewmodel > 0.5;

    vec3 normal =
        normalize(vNormal);

    if (!gl_FrontFacing) {
        normal = -normal;
    }

    // Photogrammetry textures contain captured illumination, but treating
    // that capture as final lighting leaves a daylight scan looking pasted
    // into a night/horror scene. Preserve the source detail while modulating
    // it with the same motivated key/practical lights as authored PBR assets.
    if (!pbrEnabled && !viewmodel) {
        vec3 legacy =
            albedo.rgb *
            evaluateLegacyRelight(normal);

        legacy =
            applyAtmosphere(
                legacy,
                false);

        outColor =
            vec4(
                clamp(
                    legacy,
                    0.0,
                    1.0),
                albedo.a);
        return;
    }

    if (pbrEnabled && hasNormal) {
        normal =
            mappedNormal(
                normal,
                max(
                    pc.metallicRoughnessNormalOcclusion.z,
                    0.0));
    }

    float metallic =
        pbrEnabled
        ? clamp(
              pc.metallicRoughnessNormalOcclusion.x,
              0.0,
              1.0)
        : 0.0;

    float roughness =
        pbrEnabled
        ? clamp(
              pc.metallicRoughnessNormalOcclusion.y,
              0.045,
              1.0)
        : 0.72;

    float occlusion = 1.0;

    if (pbrEnabled && hasOrm) {
        vec3 orm =
            texture(
                uOrm,
                vUv).rgb;

        occlusion =
            mix(
                1.0,
                orm.r,
                clamp(
                    pc.metallicRoughnessNormalOcclusion.w,
                    0.0,
                    1.0));

        roughness =
            clamp(
                orm.g * roughness,
                0.045,
                1.0);

        metallic =
            clamp(
                orm.b * metallic,
                0.0,
                1.0);
    }

    vec3 emissive =
        pbrEnabled
        ? pc.emissiveFactorFlags.rgb
        : vec3(0.0);

    if (pbrEnabled && hasEmissive) {
        emissive *=
            texture(
                uEmissive,
                vUv).rgb;
    }

    vec3 viewDirection =
        normalize(
            -vViewPosition);

    vec3 color =
        albedo.rgb *
        uLighting.ambientColorExposure.rgb *
        uLighting.keyColorAmbientIntensity.w *
        occlusion;

    vec3 keyDirection =
        normalize(
            uLighting.keyDirectionIntensity.xyz);

    vec3 keyRadiance =
        uLighting.keyColorAmbientIntensity.rgb *
        max(
            uLighting.keyDirectionIntensity.w,
            0.0);

    color +=
        evaluatePbrLight(
            normal,
            viewDirection,
            keyDirection,
            keyRadiance,
            albedo.rgb,
            metallic,
            roughness);

    int localCount =
        clamp(
            int(
                uLighting.post.w +
                0.5),
            0,
            4);

    for (int index = 0;
         index < 4;
         ++index) {
        if (index >= localCount) {
            break;
        }

        vec3 toLight =
            uLighting.localPositionRange[index].xyz -
            vViewPosition;

        float distanceToLight =
            length(toLight);

        if (distanceToLight <= 0.0001) {
            continue;
        }

        float attenuation =
            localDistanceAttenuation(
                distanceToLight,
                uLighting.localPositionRange[index].w);

        vec3 localDirection =
            toLight /
            distanceToLight;

        attenuation *=
            spotAttenuation(
                index,
                localDirection);

        if (attenuation <= 0.000001) {
            continue;
        }

        vec3 localRadiance =
            uLighting.localColorIntensity[index].rgb *
            max(
                uLighting.localColorIntensity[index].w,
                0.0) *
            attenuation;

        color +=
            evaluatePbrLight(
                normal,
                viewDirection,
                localDirection,
                localRadiance,
                albedo.rgb,
                metallic,
                roughness);
    }

    color += emissive;

    color =
        applyAtmosphere(
            color,
            viewmodel);

    outColor =
        vec4(
            toneMapPbr(color),
            albedo.a);
}
