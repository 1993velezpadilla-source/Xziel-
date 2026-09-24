#version 450

layout(location = 0) in vec2 vLocal;
layout(location = 1) flat in vec4 vColor;
layout(location = 2) flat in int vShape;
layout(location = 3) flat in float vRingWidth;

layout(location = 0) out vec4 outColor;

void main() {
    int shape = vShape;
    float ringWidth = vRingWidth;

    float alpha = vColor.a;

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
            // ringWidth is already clamped to [0.02, 0.90],
            // therefore 1-ringWidth is guaranteed to be [0.10, 0.98].
            float innerRadius =
                1.0 - ringWidth;

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
            vColor.rgb,
            alpha);
}
