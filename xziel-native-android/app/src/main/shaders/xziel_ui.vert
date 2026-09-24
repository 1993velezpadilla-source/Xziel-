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
    int shape =
        int(pc.params.x + 0.5);

    int vertexInPrimitive =
        gl_VertexIndex % 6;

    vec2 local =
        kQuad[vertexInPrimitive];

    vec2 position =
        pc.rect.xy +
        local * pc.rect.zw;

    // Shape 3 is a batched seven-segment digit. One 42-vertex draw replaces
    // up to seven push-constant + draw pairs while producing the same quads.
    if (shape == 3) {
        int segmentIndex =
            gl_VertexIndex / 6;

        int digitMask =
            int(pc.params.z + 0.5);

        int segmentBit = 0;
        vec2 centerOffset = vec2(0.0);
        vec2 halfExtent = vec2(0.0);

        float scale =
            max(pc.rect.z, 0.0);

        const float xStep =
            0.0168;
        const float yStep =
            0.0160;

        const vec2 horizontalHalf =
            vec2(0.0156, 0.0025);
        const vec2 verticalHalf =
            vec2(0.0024, 0.0124);

        if (segmentIndex == 0) {
            segmentBit = 0x01;
            centerOffset =
                vec2(0.0, 2.0 * yStep) * scale;
            halfExtent =
                horizontalHalf * scale;
        } else if (segmentIndex == 1) {
            segmentBit = 0x02;
            centerOffset =
                vec2(xStep, yStep) * scale;
            halfExtent =
                verticalHalf * scale;
        } else if (segmentIndex == 2) {
            segmentBit = 0x04;
            centerOffset =
                vec2(xStep, -yStep) * scale;
            halfExtent =
                verticalHalf * scale;
        } else if (segmentIndex == 3) {
            segmentBit = 0x08;
            centerOffset =
                vec2(0.0, -2.0 * yStep) * scale;
            halfExtent =
                horizontalHalf * scale;
        } else if (segmentIndex == 4) {
            segmentBit = 0x10;
            centerOffset =
                vec2(-xStep, -yStep) * scale;
            halfExtent =
                verticalHalf * scale;
        } else if (segmentIndex == 5) {
            segmentBit = 0x20;
            centerOffset =
                vec2(-xStep, yStep) * scale;
            halfExtent =
                verticalHalf * scale;
        } else {
            segmentBit = 0x40;
            halfExtent =
                horizontalHalf * scale;
        }

        if ((digitMask & segmentBit) == 0) {
            gl_Position =
                vec4(2.0, 2.0, 0.0, 1.0);
            vLocal = local;
            vColor = pc.color;
            vShape = 0;
            vRingWidth = pc.params.y;
            return;
        }

        position =
            pc.rect.xy +
            centerOffset +
            local * halfExtent;
    }

    gl_Position =
        vec4(
            position,
            0.0,
            1.0);

    vLocal = local;
    vColor = pc.color;
    vShape =
        shape == 3
        ? 0
        : shape;
    vRingWidth =
        clamp(
            pc.params.y,
            0.02,
            0.90);
}
