#version 450

layout(location = 0) in vec2 vLocal;
layout(location = 1) in vec4 vColor;
layout(location = 2) flat in int vShape;
layout(location = 3) in float vRingWidth;

layout(location = 0) out vec4 outColor;

void main() {
    float alpha =
        vColor.a;

    if (vShape == 1 ||
        vShape == 2) {
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

        if (vShape == 1) {
            alpha *= outer;
        } else {
            float innerRadius =
                clamp(
                    1.0 - vRingWidth,
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
            vColor.rgb,
            alpha);
}
