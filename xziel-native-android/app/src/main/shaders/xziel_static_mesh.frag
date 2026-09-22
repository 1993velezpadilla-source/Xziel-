#version 450

layout(set = 0, binding = 0)
uniform sampler2D uAlbedo;

layout(location = 0) in vec2 vUv;
layout(location = 1) in vec3 vNormal;
layout(location = 2) in vec4 vColor;
layout(location = 3) in float vDistance;
layout(location = 4) in float vFogDensity;
layout(location = 5) in float vLightning;
layout(location = 6) in float vViewmodel;

layout(location = 0) out vec4 outColor;

void main() {
    vec4 albedo =
        texture(
            uAlbedo,
            vUv);

    // The photogrammetry source is naturally low-contrast and becomes even
    // flatter under cold night lighting. Apply a conservative presentation
    // grade in the native shader: slightly deeper shadows and a touch more
    // chroma, without inventing texture detail or altering the source files.
    vec3 sceneAlbedo =
        clamp(
            (albedo.rgb - vec3(0.50)) *
                1.12 +
            vec3(0.50),
            0.0,
            1.0);

    float sceneLuma =
        dot(
            sceneAlbedo,
            vec3(0.2126, 0.7152, 0.0722));

    sceneAlbedo =
        clamp(
            mix(
                vec3(sceneLuma),
                sceneAlbedo,
                1.08),
            0.0,
            1.0);

    vec3 baked =
        max(
            vColor.rgb,
            vec3(0.035));

    vec3 normal =
        normalize(vNormal);

    vec3 moonDirection =
        normalize(
            vec3(
                -0.32,
                 0.93,
                -0.18));

    vec3 fillDirection =
        normalize(
            vec3(
                 0.68,
                 0.18,
                 0.54));

    float moon =
        max(
            dot(
                normal,
                moonDirection),
            0.0);

    float fill =
        pow(
            max(
                dot(
                    normal,
                    fillDirection),
                0.0),
            2.0);

    vec3 dynamicLight =
        vec3(0.235) +
        vec3(
            0.38,
            0.43,
            0.52) *
            moon *
            0.92 +
        vec3(
            0.20,
            0.105,
            0.075) *
            fill *
            0.20;

    vec3 lit;

    if (vViewmodel > 0.5) {
        vec3 viewKey =
            normalize(
                vec3(
                    -0.35,
                     0.70,
                    -0.62));

        float key =
            max(
                dot(
                    normal,
                    viewKey),
                0.0);

        float rim =
            pow(
                max(
                    normal.y,
                    0.0),
                2.0);

        lit =
            albedo.rgb *
            baked *
            (0.60 +
             key * 0.42 +
             rim * 0.10);
    } else {
        lit =
            sceneAlbedo *
            baked *
            dynamicLight;
    }

    lit +=
        vec3(
            0.42,
            0.52,
            0.72) *
        vLightning *
        (0.16 +
         moon * 0.20);

    float fog =
        vViewmodel > 0.5
        ? 0.0
        : clamp(
            smoothstep(
                28.0,
                150.0,
                vDistance) *
            (0.12 +
             vFogDensity * 0.78),
            0.0,
            0.86);

    vec3 fogColor =
        vec3(
            0.008,
            0.011,
            0.018);

    lit =
        mix(
            lit,
            fogColor,
            fog);

    outColor =
        vec4(
            lit,
            albedo.a);
}
