#version 450

layout(push_constant) uniform PushConstants {
    vec4 cameraPositionViewYawCos;
    vec4 viewRotationFog;
    vec4 environmentRotation;
    vec4 modelOffsetScale;
    vec4 projectionMode;
    vec4 baseColorFactor;
    vec4 metallicRoughnessNormalOcclusion;
    vec4 emissiveFactorFlags;
} pc;

layout(location = 0) in vec3 inPosition;
layout(location = 2) in vec2 inUv;

layout(location = 0) out vec2 vUv;

void main() {
    vec3 relative =
        inPosition -
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

    vec3 view = vec3(
        yawView.x,
        cp * yawView.y + sp * yawView.z,
       -sp * yawView.y + cp * yawView.z
    );

    const float nearPlane = 0.08;
    const float farPlane = 180.0;

    vec4 clip;
    clip.x =
        view.x *
        pc.projectionMode.y;
    clip.y =
        -view.y *
        pc.projectionMode.x;
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
}
