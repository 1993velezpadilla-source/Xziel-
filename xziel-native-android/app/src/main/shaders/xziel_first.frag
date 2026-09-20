#version 450

layout(location = 0) in vec3 vColor;
layout(location = 0) out vec4 outColor;

void main() {
    vec3 horrorTint = vec3(0.12, 0.015, 0.045);
    vec3 color = mix(horrorTint, vColor, 0.82);
    outColor = vec4(color, 1.0);
}
