#version 450

layout(set = 0, binding = 0)
uniform sampler2D uAlbedo;
layout(set = 0, binding = 1)
uniform sampler2D uNormal;
layout(set = 0, binding = 2)
uniform sampler2D uOrm;
layout(set = 0, binding = 3)
uniform sampler2D uEmissive;

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
// xyz=view-space position, w=non-negative view distance.
layout(location = 2) in vec4 vViewData;

layout(location = 0) out vec4 outColor;

const float PI = 3.14159265358979323846;

layout(constant_id = 0) const uint FORCE_LEGACY_MATERIAL = 0u;

// Preserve full close-range material detail while avoiding derivative-heavy
// tangent reconstruction for distant fragments where the normal map is below
// practical screen-space visibility. The fade band prevents visible popping.
const float NORMAL_MAP_FULL_DETAIL_DISTANCE = 32.0;
const float NORMAL_MAP_FADE_END_DISTANCE = 56.0;

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
    float nDotV,
    float nDotL,
    float roughness) {
    // nDotV/nDotL are already computed by main(). Reuse them instead of
    // repeating two per-fragment dot products inside the Smith term.
    return
        geometrySchlickGgx(
            nDotV,
            roughness) *
        geometrySchlickGgx(
            nDotL,
            roughness);
}

vec3 fresnelSchlick(
    float cosine,
    vec3 f0) {
    // pow(x, 5) is exactly x*x*x*x*x. Expanding the fixed exponent avoids a
    // generic transcendental path on mobile fragment hardware.
    float oneMinusCosine =
        clamp(
            1.0 - cosine,
            0.0,
            1.0);
    float squared =
        oneMinusCosine *
        oneMinusCosine;
    float fifth =
        squared *
        squared *
        oneMinusCosine;

    return
        f0 +
        (1.0 - f0) *
        fifth;
}

vec3 mappedNormal(
    vec3 geometricNormal,
    float normalScale) {
    vec3 dpdx = dFdx(vViewData.xyz);
    vec3 dpdy = dFdy(vViewData.xyz);
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

void main() {
    const bool forceLegacyMaterial =
        FORCE_LEGACY_MATERIAL != 0u;

    int flags =
        forceLegacyMaterial
        ? 0
        : int(
              pc.emissiveFactorFlags.w +
              0.5);

    bool pbrEnabled =
        !forceLegacyMaterial &&
        (flags & 1) != 0;

    // Viewmodel mode and lightning are uniform for the entire draw and
    // already live in push constants. Reading them here avoids two
    // redundant interpolants without changing the material result.
    float viewmodel =
        step(
            0.5,
            pc.modelRotationMode.w);
    float lightning =
        viewmodel > 0.5
        ? 0.0
        : clamp(
              pc.environment.x,
              0.0,
              2.0);

    vec4 albedo =
        texture(
            uAlbedo,
            vUv) *
        pc.baseColorFactor;

    if (!pbrEnabled) {
        if (viewmodel > 0.5) {
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

        // Legacy v2-v4 source-fidelity path. Photogrammetry already contains
        // captured lighting, so it stays pixel-faithful and bypasses PBR.
        outColor = albedo;
        return;
    }

    // These texture-feature flags live after the legacy early-return so a
    // FORCE_LEGACY_MATERIAL specialization can dead-strip the entire PBR path.
    bool hasNormal =
        (flags & 2) != 0;
    bool hasOrm =
        (flags & 4) != 0;
    bool hasEmissive =
        (flags & 8) != 0;

    vec3 normal =
        normalize(vNormal);

    if (!gl_FrontFacing) {
        normal = -normal;
    }

    if (hasNormal) {
        float normalDetail =
            1.0 -
            smoothstep(
                NORMAL_MAP_FULL_DETAIL_DISTANCE,
                NORMAL_MAP_FADE_END_DISTANCE,
                max(vViewData.w, 0.0));

        // Most far-world fragments now skip mappedNormal() entirely. That
        // avoids four derivatives, multiple normalizations and the normal-map
        // texture sample without changing close-range PBR shading.
        if (normalDetail > 0.001) {
            vec3 geometricNormal = normal;
            vec3 detailNormal =
                mappedNormal(
                    geometricNormal,
                    max(
                        pc.metallicRoughnessNormalOcclusion.z,
                        0.0));

            normal =
                normalize(
                    mix(
                        geometricNormal,
                        detailNormal,
                        normalDetail));
        }
    }

    float metallic =
        clamp(
            pc.metallicRoughnessNormalOcclusion.x,
            0.0,
            1.0);
    float roughness =
        clamp(
            pc.metallicRoughnessNormalOcclusion.y,
            0.045,
            1.0);
    float occlusion = 1.0;

    if (hasOrm) {
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
        pc.emissiveFactorFlags.rgb;
    if (hasEmissive) {
        emissive *=
            texture(
                uEmissive,
                vUv).rgb;
    }

    vec3 lightDirection =
        normalize(
            vec3(
                -0.35,
                 0.70,
                -0.62));

    float nDotL =
        max(
            dot(
                normal,
                lightDirection),
            0.0);

    // The previous path evaluated the full Cook-Torrance BRDF even when the
    // light was behind the surface, then multiplied the result by nDotL=0.
    // Skip that provably dead work while preserving the exact lit result.
    vec3 direct =
        vec3(0.0);

    if (nDotL > 0.0) {
        vec3 viewDirection =
            normalize(
                -vViewData.xyz);
        vec3 halfVector =
            normalize(
                viewDirection +
                lightDirection);

        float nDotV =
            max(
                dot(
                    normal,
                    viewDirection),
                0.0);
        float hDotV =
            max(
                dot(
                    halfVector,
                    viewDirection),
                0.0);

        vec3 f0 =
            mix(
                vec3(0.04),
                albedo.rgb,
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
                nDotV,
                nDotL,
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

        direct =
            (diffuseWeight *
                 albedo.rgb /
                 PI +
             specular) *
            nDotL;
    }

    float lightningBoost =
        1.0 +
        clamp(lightning, 0.0, 2.0) *
        1.8;

    vec3 ambient =
        albedo.rgb *
        (0.075 +
         0.035 *
         (1.0 - roughness)) *
        occlusion;

    vec3 color =
        direct *
            lightningBoost +
        ambient +
        emissive;

    outColor =
        vec4(
            max(color, vec3(0.0)),
            albedo.a);
}
