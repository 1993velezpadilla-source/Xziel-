#version 450

layout(push_constant) uniform UiPushConstants {
    vec4 rect;
    vec4 color;
    vec4 params;
} pc;

layout(location = 0) out vec2 vLocal;
layout(location = 1) out vec4 vColor;
layout(location = 2) flat out int vShape;
layout(location = 3) out float vRingWidth;

const vec2 kQuad[6] = vec2[](
    vec2(-1.0, -1.0),
    vec2( 1.0, -1.0),
    vec2( 1.0,  1.0),
    vec2(-1.0, -1.0),
    vec2( 1.0,  1.0),
    vec2(-1.0,  1.0)
);

void main() {
    vec2 local =
        kQuad[gl_VertexIndex];

    vec2 position =
        pc.rect.xy +
        local * pc.rect.zw;

    gl_Position =
        vec4(
            position,
            0.0,
            1.0);

    vLocal = local;
    vColor = pc.color;
    vShape =
        int(pc.params.x + 0.5);
    vRingWidth =
        clamp(
            pc.params.y,
            0.02,
            0.90);
}
