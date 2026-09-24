#version 450

layout(set = 0, binding = 0)
uniform sampler2D uAlbedo;

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

layout(location = 0) in vec2 vUv;
layout(location = 0) out vec4 outColor;

void main() {
    outColor =
        texture(
            uAlbedo,
            vUv) *
        pc.baseColorFactor;
}
