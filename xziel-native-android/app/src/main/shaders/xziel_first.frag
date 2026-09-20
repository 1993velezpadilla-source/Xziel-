#version 450

layout(location = 0) in vec3 vNormal;
layout(location = 1) in vec3 vWorldPosition;
layout(location = 2) in float vPulse;

layout(location = 0) out vec4 outColor;

void main() {
    vec3 normal = normalize(vNormal);

    vec3 keyDirection = normalize(vec3(-0.45, 0.72, -0.52));
    vec3 rimDirection = normalize(vec3(0.65, 0.18, 0.74));

    float key = max(dot(normal, keyDirection), 0.0);
    float rim = pow(max(dot(normal, rimDirection), 0.0), 3.0);

    vec3 coldSteel = vec3(0.055, 0.075, 0.105);
    vec3 magenta = vec3(0.72, 0.025, 0.20);
    vec3 cyan = vec3(0.035, 0.42, 0.58);

    float heightGlow = smoothstep(-0.8, 0.8, vWorldPosition.y);
    float pulse = clamp(vPulse, 0.0, 1.0);

    vec3 base =
        coldSteel
        + magenta * (0.10 + 0.16 * pulse) * heightGlow
        + cyan * 0.05 * (1.0 - heightGlow);

    vec3 lit =
        base * (0.24 + key * 0.92)
        + magenta * rim * (0.16 + 0.14 * pulse);

    outColor = vec4(lit, 1.0);
}
