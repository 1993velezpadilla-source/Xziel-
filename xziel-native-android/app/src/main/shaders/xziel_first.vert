#version 450

layout(location = 0) out vec3 vColor;

const vec2 kPositions[3] = vec2[](
    vec2( 0.0, -0.62),
    vec2( 0.58,  0.48),
    vec2(-0.58,  0.48)
);

const vec3 kColors[3] = vec3[](
    vec3(0.95, 0.08, 0.32),
    vec3(0.32, 0.04, 0.72),
    vec3(0.04, 0.65, 0.82)
);

void main() {
    gl_Position = vec4(kPositions[gl_VertexIndex], 0.0, 1.0);
    vColor = kColors[gl_VertexIndex];
}
