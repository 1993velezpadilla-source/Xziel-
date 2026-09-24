#version 450

layout(push_constant) uniform PushConstants {
    // cameraPositionViewYawCos: xyz camera position, w yaw cosine.
    vec4 cameraPositionViewYawCos;
    // viewRotationFog: x yaw sine, y pitch cosine, z pitch sine, w fog.
    vec4 viewRotationFog;
    // environmentRotation: x lightning, y roll cosine, z roll sine.
    vec4 environmentRotation;
    vec4 modelOffsetScale;
    // projectionMode: x focal, y focal/aspect, w viewmodel mode.
    vec4 projectionMode;
    vec4 baseColorFactor;
    vec4 metallicRoughnessNormalOcclusion;
    vec4 emissiveFactorFlags;
} pc;

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
layout(location = 3) in vec4 inColor;

layout(location = 0) out vec2 vUv;
layout(location = 1) out vec3 vNormal;
// Packed frame-varying data: x=view distance, y=lightning, z=viewmodel.
layout(location = 2) out vec3 vFrameData;
layout(location = 3) out vec3 vViewPosition;

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
    float viewmodel =
        step(
            0.5,
            pc.projectionMode.w);

    vec3 view;
    vec3 surfaceNormal;

    if (viewmodel > 0.5) {
        view =
            rotateViewmodel(
                inPosition *
                pc.modelOffsetScale.w) +
            pc.modelOffsetScale.xyz;

        surfaceNormal =
            normalize(
                rotateViewmodel(
                    inNormal));
    } else {
        view = worldToView(inPosition);
        surfaceNormal =
            normalize(
                worldDirectionToView(
                    inNormal));
    }

    const float nearPlane = 0.08;
    const float farPlane = 180.0;

    float focal =
        pc.projectionMode.x;
    float focalOverAspect =
        pc.projectionMode.y;

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
    vFrameData.x = max(view.z, 0.0);
    vFrameData.y =
        viewmodel > 0.5
        ? 0.0
        : clamp(
              pc.environmentRotation.x,
              0.0,
              2.0);
    vFrameData.z = viewmodel;
    vViewPosition = view;
}
