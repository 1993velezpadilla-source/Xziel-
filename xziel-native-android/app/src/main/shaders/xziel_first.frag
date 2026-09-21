#version 450

layout(location = 0) in vec3 vNormal;
layout(location = 1) in vec3 vWorldPosition;
layout(location = 2) in float vPulse;
layout(location = 3) flat in int vMaterial;

layout(location = 0) out vec4 outColor;

vec3 materialBase(int material, float pulse) {
    if (material == 0) {
        return vec3(0.055, 0.060, 0.070);
    }

    if (material == 1) {
        return vec3(0.075, 0.070, 0.080);
    }

    if (material == 2) {
        return vec3(0.040, 0.055, 0.065);
    }

    if (material == 10) {
        return vec3(0.055, 0.065, 0.078);
    }

    if (material == 11) {
        return vec3(1.0, 0.24, 0.035);
    }

    vec3 core = vec3(0.12, 0.015, 0.040);
    vec3 hot = vec3(0.78, 0.025, 0.22);
    return mix(core, hot, 0.30 + 0.32 * pulse);
}

void main() {
    vec3 normal = normalize(vNormal);

    vec3 keyDirection = normalize(vec3(-0.38, 0.78, -0.48));
    vec3 rimDirection = normalize(vec3(0.72, 0.14, 0.68));

    float key = max(dot(normal, keyDirection), 0.0);
    float rim = pow(max(dot(normal, rimDirection), 0.0), 3.0);

    float pulse = clamp(vPulse, 0.0, 1.0);

    vec3 base = materialBase(vMaterial, pulse);

    float floorCold =
        smoothstep(-1.55, -0.6, -vWorldPosition.y);

    vec3 coldBounce = vec3(0.015, 0.08, 0.12) * floorCold;
    vec3 magentaRim = vec3(0.60, 0.02, 0.18) * rim * (0.10 + 0.18 * pulse);

    vec3 lit =
        base * (0.20 + key * 0.90)
        + coldBounce
        + magentaRim;

    if (vMaterial >= 10) {
        if (vMaterial == 11) {
            lit +=
                vec3(1.0, 0.15, 0.02) *
                (0.35 + pulse * 0.55);
        }

        outColor =
            vec4(
                lit,
                1.0);
        return;
    }

    float distanceFog =
        clamp((vWorldPosition.z + 3.0) / 8.0, 0.0, 1.0);

    vec3 fogColor = vec3(0.010, 0.014, 0.022);
    lit = mix(lit, fogColor, distanceFog * 0.16);

    outColor = vec4(lit, 1.0);
}
