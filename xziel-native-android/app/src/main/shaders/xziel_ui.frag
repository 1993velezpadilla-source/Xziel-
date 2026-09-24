#version 450

layout(push_constant) uniform UiPushConstants {
    vec4 rect;
    vec4 color;
    vec4 params;
} pc;

layout(location = 0) in vec2 vLocal;

layout(location = 0) out vec4 outColor;

void main() {
    int rawShape =
        int(pc.params.x + 0.5);
    int shape =
        rawShape == 3
        ? 0
        : rawShape;
    float ringWidth =
        clamp(
            pc.params.y,
            0.02,
            0.90);
    vec4 color =
        pc.color;

    float alpha =
        color.a;

    if (shape == 1 ||
        shape == 2) {
        float distanceToCenter =
            length(vLocal);

        float edgeWidth =
            max(
                fwidth(distanceToCenter) * 1.5,
                0.008);

        float outer =
            1.0 -
            smoothstep(
                1.0 - edgeWidth,
                1.0 + edgeWidth,
                distanceToCenter);

        if (shape == 1) {
            alpha *= outer;
        } else {
            float innerRadius =
                clamp(
                    1.0 - ringWidth,
                    0.02,
                    0.98);

            float inner =
                smoothstep(
                    innerRadius - edgeWidth,
                    innerRadius + edgeWidth,
                    distanceToCenter);

            alpha *=
                outer *
                inner;
        }
    }

    if (alpha <= 0.002) {
        discard;
    }

    outColor =
        vec4(
            color.rgb,
            alpha);
}
