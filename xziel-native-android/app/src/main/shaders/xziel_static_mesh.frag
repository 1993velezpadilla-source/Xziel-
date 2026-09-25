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
    vec2 projectionFocalAspect;
    float projectionReserved;
    uint viewmodelMode;
    vec4 baseColorFactor;
    vec4 metallicRoughnessNormalOcclusion;
    vec3 emissiveFactor;
    uint materialFlags;
} pc;

layout(location = 0) in vec2 vUv;
layout(location = 1) in vec3 vNormal;
// xyz=view-space position, w=non-negative view distance.
layout(location = 2) in vec4 vViewData;
layout(location = 3) in vec3 vWorldPosition;

layout(location = 0) out vec4 outColor;

const float PI = 3.14159265358979323846;

// Preserve full close-range material detail while avoiding derivative-heavy
// tangent reconstruction for distant fragments where the normal map is below
// practical screen-space visibility. The fade band prevents visible popping.
const float NORMAL_MAP_FULL_DETAIL_DISTANCE = 32.0;
const float NORMAL_MAP_FADE_END_DISTANCE = 56.0;

// ORM detail remains fully authored through mid range, then fades toward the
// scalar material factors already stored in push constants. Beyond the fade
// band the fragment skips the ORM texture fetch entirely.
const float ORM_MAP_FULL_DETAIL_DISTANCE = 48.0;
const float ORM_MAP_FADE_END_DISTANCE = 80.0;

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

float geometrySmith(
    float nDotV,
    float nDotL,
    float roughness) {
    // GEOMETRY_SMITH_SHARED_K_V1
    // Both Schlick-GGX terms use the same roughness-derived k. Compute it
    // once per lit fragment instead of rebuilding it separately for V and L.
    float r = roughness + 1.0;
    float k = (r * r) * 0.125;
    float oneMinusK = 1.0 - k;

    float visibilityV =
        nDotV /
        max(
            nDotV * oneMinusK + k,
            0.0001);
    float visibilityL =
        nDotL /
        max(
            nDotL * oneMinusK + k,
            0.0001);

    return
        visibilityV *
        visibilityL;
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

    // TANGENT_BASIS_RECIPROCAL_FREE_V1
    // normalize(raw / determinant) only depends on determinant's sign.
    // The following Gram-Schmidt normalize cancels raw magnitude as well,
    // so preserve handedness and skip both the reciprocal and first normalize.
    float handedness =
        determinant < 0.0
        ? -1.0
        : 1.0;
    vec3 tangentRaw =
        (dpdx * duvdy.y -
         dpdy * duvdx.y) *
        handedness;

    vec3 tangent =
        normalize(
            tangentRaw -
            geometricNormal *
            dot(
                geometricNormal,
                tangentRaw));

    // TANGENT_BASIS_SINGLE_NORMALIZE_V2
    // geometricNormal and tangent are unit-length and orthogonal, so their
    // cross product is already the unit bitangent.
    vec3 bitangent =
        cross(
            geometricNormal,
            tangent);

    vec3 sampled =
        texture(
            uNormal,
            vUv).xyz *
            2.0 -
        1.0;

    sampled.xy *= normalScale;

    // Orthonormal TBN preserves direction/length. Normalize once after the
    // transform instead of once before and once after it.
    return normalize(
        mat3(
            tangent,
            bitangent,
            geometricNormal) *
        sampled);
}

// WORLD_SPACE_PHOTOGRAMMETRY_DETAIL_V1
float samplePhotoDetailPlane(
    vec2 unwrappedUv) {
    vec2 dx = dFdx(unwrappedUv);
    vec2 dy = dFdy(unwrappedUv);

    return textureGrad(
        uEmissive,
        fract(unwrappedUv),
        dx,
        dy).r;
}

float samplePhotoDetail(
    vec3 worldPosition) {
    vec3 worldNormal =
        normalize(
            cross(
                dFdx(worldPosition),
                dFdy(worldPosition)));

    vec3 weights =
        pow(
            abs(worldNormal),
            vec3(4.0));
    weights /=
        max(
            weights.x +
            weights.y +
            weights.z,
            0.0001);

    const float tilesPerMeter = 1.25;

    float xProjection =
        samplePhotoDetailPlane(
            worldPosition.zy *
            tilesPerMeter);
    float yProjection =
        samplePhotoDetailPlane(
            worldPosition.xz *
            tilesPerMeter);
    float zProjection =
        samplePhotoDetailPlane(
            worldPosition.xy *
            tilesPerMeter);

    return
        xProjection * weights.x +
        yProjection * weights.y +
        zProjection * weights.z;
}

void main() {
    uint flags =
        pc.materialFlags;

    bool pbrEnabled =
        (flags & 1u) != 0u;
    bool hasNormal =
        (flags & 2u) != 0u;
    bool hasOrm =
        (flags & 4u) != 0u;
    bool hasEmissive =
        (flags & 8u) != 0u;
    bool photogrammetryPbr =
        (flags & 16u) != 0u;

    // Viewmodel mode is uniform for the draw. Direct-light scale is
    // precomputed once on CPU from lightning (or fixed to 1 for viewmodels).
    bool viewmodel =
        pc.viewmodelMode != 0u;

    vec4 albedo =
        texture(
            uAlbedo,
            vUv) *
        pc.baseColorFactor;

    if (!pbrEnabled) {
        if (viewmodel) {
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

    vec3 normal =
        normalize(vNormal);

    if (!gl_FrontFacing) {
        normal = -normal;
    }

    vec3 sourceNormal = normal;

    // The vertex stage guarantees this value is non-negative. Reuse it for
    // both material-detail gates instead of re-clamping the varying.
    float viewDepth = vViewData.w;

    if (hasNormal &&
        viewDepth <
            NORMAL_MAP_FADE_END_DISTANCE) {
        // smoothstep() is identically zero before the fade band. Avoid that
        // per-fragment cubic work for the full-detail majority, and skip the
        // whole block once the map is fully faded.
        float normalDetail =
            viewDepth <=
                    NORMAL_MAP_FULL_DETAIL_DISTANCE
            ? 1.0
            : 1.0 -
                smoothstep(
                    NORMAL_MAP_FULL_DETAIL_DISTANCE,
                    NORMAL_MAP_FADE_END_DISTANCE,
                    viewDepth);

        // Most far-world fragments now skip mappedNormal() entirely. That
        // avoids four derivatives, multiple normalizations and the normal-map
        // texture sample without changing close-range PBR shading.
        if (normalDetail > 0.001) {
            vec3 geometricNormal = normal;
            vec3 detailNormal =
                mappedNormal(
                    geometricNormal,
                    pc.metallicRoughnessNormalOcclusion.z);

            // NORMAL_MAP_FULL_DETAIL_SINGLE_NORMALIZE_V1
            // mappedNormal() already returns a unit vector. In the full-detail
            // region normalDetail is exactly 1, so mix() returns detailNormal
            // and a second normalize is redundant. Keep normalization only
            // for the 32-56m fade blend.
            normal =
                normalDetail >= 1.0
                ? detailNormal
                : normalize(
                      mix(
                          geometricNormal,
                          detailNormal,
                          normalDetail));
        }
    }

    float metallic =
        pc.metallicRoughnessNormalOcclusion.x;
    float roughness =
        pc.metallicRoughnessNormalOcclusion.y;
    float occlusion = 1.0;

    if (hasOrm &&
        viewDepth <
            ORM_MAP_FADE_END_DISTANCE) {
        float ormDetail =
            viewDepth <=
                    ORM_MAP_FULL_DETAIL_DISTANCE
            ? 1.0
            : 1.0 -
                smoothstep(
                    ORM_MAP_FULL_DETAIL_DISTANCE,
                    ORM_MAP_FADE_END_DISTANCE,
                    viewDepth);

        // Fade continuously toward neutral ORM values before the far-field
        // branch skips the texture lookup. This preserves authored close/mid
        // material response while avoiding invisible per-texel detail work.
        if (ormDetail > 0.001) {
            vec3 sampledOrm =
                texture(
                    uOrm,
                    vUv).rgb;
            vec3 orm =
                mix(
                    vec3(1.0),
                    sampledOrm,
                    ormDetail);

            occlusion =
                mix(
                    1.0,
                    orm.r,
                    pc.metallicRoughnessNormalOcclusion.w);
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
    }

    vec3 emissive =
        pc.emissiveFactor;
    if (hasEmissive &&
        !photogrammetryPbr) {
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

    if (photogrammetryPbr &&
        !viewmodel) {
        // PHOTOGRAMMETRY_PBR_SOURCE_FIDELITY_V1
        // Scan albedo already contains captured lighting. Preserve it and
        // apply only the local micro-normal delta plus bounded AO so generated
        // detail does not double-light the photogrammetry.
        float sourceKey =
            max(
                dot(
                    sourceNormal,
                    lightDirection),
                0.0);
        float detailKey =
            max(
                dot(
                    normal,
                    lightDirection),
                0.0);

        float normalResponse =
            clamp(
                1.0 +
                    (detailKey - sourceKey) *
                    0.28,
                0.84,
                1.16);

        float aoResponse =
            mix(
                1.0,
                occlusion,
                0.28);

        float worldDetailResponse = 1.0;

        if (hasEmissive &&
            viewDepth < 42.0) {
            float detailFade =
                1.0 -
                smoothstep(
                    24.0,
                    42.0,
                    viewDepth);

            float detailSample =
                samplePhotoDetail(
                    vWorldPosition);
            float detailSignal =
                (detailSample - 0.5) *
                2.0;

            worldDetailResponse =
                clamp(
                    1.0 +
                    detailSignal *
                    0.18 *
                    detailFade,
                    0.88,
                    1.12);
        }

        vec3 photoColor =
            albedo.rgb *
            normalResponse *
            aoResponse *
            worldDetailResponse;

        outColor =
            vec4(
                max(
                    photoColor,
                    vec3(0.0)),
                albedo.a);
        return;
    }

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

    vec3 ambient =
        albedo.rgb *
        (0.075 +
         0.035 *
         (1.0 - roughness)) *
        occlusion;

    vec3 color =
        direct *
            pc.environment.x +
        ambient +
        emissive;

    outColor =
        vec4(
            max(color, vec3(0.0)),
            albedo.a);
}
