#version 450

layout(push_constant) uniform PushConstants {
    // cameraPositionViewYawCos: xyz camera position, w yaw cosine.
    vec4 cameraPositionViewYawCos;
    // viewRotationFog: x yaw sine, y pitch cosine, z pitch sine, w fog.
    vec4 viewRotationFog;
    // environmentRotation: x direct-light scale, y roll cosine, z roll sine.
    vec4 environmentRotation;
    vec4 modelOffsetScale;
    // Same 16-byte slot as the CPU block: two projection floats, one
    // reserved float, then an integer viewmodel flag at byte offset 76.
    vec2 projectionFocalAspect;
    float projectionReserved;
    uint viewmodelMode;
    vec4 baseColorFactor;
    vec4 metallicRoughnessNormalOcclusion;
    vec3 emissiveFactor;
    uint materialFlags;
} pc;

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;

layout(location = 0) out vec2 vUv;
layout(location = 1) out vec3 vNormal;
// xyz=view-space position, w=non-negative view distance.
layout(location = 2) out vec4 vViewData;
layout(location = 3) out vec3 vWorldPosition;

vec3 worldToView(vec3 world) {
    vec3 relative =
        world -
        pc.cameraPositionViewYawCos.xyz;

    float cy =
        pc.cameraPositionViewYawCos.w;
    float sy =
        pc.viewRotationFog.x;

    vec3 yawView = vec3(
        cy * relative.x - sy * relative.z,
        relative.y,
        sy * relative.x + cy * relative.z
    );

    float cp =
        pc.viewRotationFog.y;
    float sp =
        pc.viewRotationFog.z;

    return vec3(
        yawView.x,
        cp * yawView.y + sp * yawView.z,
       -sp * yawView.y + cp * yawView.z
    );
}

vec3 worldDirectionToView(vec3 direction) {
    float cy =
        pc.cameraPositionViewYawCos.w;
    float sy =
        pc.viewRotationFog.x;

    vec3 yawView = vec3(
        cy * direction.x - sy * direction.z,
        direction.y,
        sy * direction.x + cy * direction.z
    );

    float cp =
        pc.viewRotationFog.y;
    float sp =
        pc.viewRotationFog.z;

    return vec3(
        yawView.x,
        cp * yawView.y + sp * yawView.z,
       -sp * yawView.y + cp * yawView.z
    );
}

vec3 rotateViewmodel(vec3 value) {
    float cy =
        pc.cameraPositionViewYawCos.w;
    float sy =
        pc.viewRotationFog.x;
    value = vec3(
        cy * value.x + sy * value.z,
        value.y,
       -sy * value.x + cy * value.z
    );

    float cp =
        pc.viewRotationFog.y;
    float sp =
        pc.viewRotationFog.z;
    value = vec3(
        value.x,
        cp * value.y - sp * value.z,
        sp * value.y + cp * value.z
    );

    float cr =
        pc.environmentRotation.y;
    float sr =
        pc.environmentRotation.z;
    return vec3(
        cr * value.x - sr * value.y,
        sr * value.x + cr * value.y,
        value.z
    );
}

void main() {
    bool viewmodel =
        pc.viewmodelMode != 0u;
    bool pbrEnabled =
        (pc.materialFlags & 1u) != 0u;

    vec3 view;
    vec3 surfaceNormal;

    if (viewmodel) {
        view =
            rotateViewmodel(
                inPosition *
                pc.modelOffsetScale.w) +
            pc.modelOffsetScale.xyz;

        // STATIC_VERTEX_NORMALIZE_DEFER_V1
        // Every fragment path that consumes a viewmodel normal normalizes
        // vNormal before lighting. Rotation preserves direction, so defer the
        // normalization to that single consumer instead of doing it here too.
        surfaceNormal =
            rotateViewmodel(
                inNormal);
    } else {
        view = worldToView(inPosition);

        if (pbrEnabled) {
            // STATIC_VERTEX_NORMALIZE_DEFER_V1
            // PBR fragment shading always normalizes vNormal before normal-map
            // or direct-light work. Avoid the redundant per-vertex normalize.
            surfaceNormal =
                worldDirectionToView(
                    inNormal);
        } else {
            // STATIC_VERTEX_NORMAL_WORK_GATE_V1
            // Legacy photogrammetry returns captured albedo directly and
            // never reads vNormal. Skip the whole normal rotation for those
            // draw-uniform legacy batches.
            surfaceNormal =
                vec3(
                    0.0,
                    0.0,
                    1.0);
        }
    }

    const float nearPlane = 0.08;
    const float farPlane = 180.0;

    float focal =
        pc.projectionFocalAspect.x;
    float focalOverAspect =
        pc.projectionFocalAspect.y;

    vec4 clip;
    clip.x =
        view.x *
        focalOverAspect;
    clip.y =
        -view.y *
        focal;
    clip.z =
        (farPlane /
         (farPlane - nearPlane)) *
        view.z
        - (farPlane *
           nearPlane /
           (farPlane - nearPlane));
    clip.w = view.z;

    gl_Position = clip;

    vUv = inUv;
    vNormal = surfaceNormal;
    vViewData =
        vec4(
            view,
            max(view.z, 0.0));
    vWorldPosition =
        viewmodel
        ? vec3(0.0)
        : inPosition;
}
