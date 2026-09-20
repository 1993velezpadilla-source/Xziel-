#version 450

layout(push_constant) uniform PushConstants {
    float timeSeconds;
    float aspect;
    float horrorPulse;
    float padding;
} pc;

layout(location = 0) out vec3 vNormal;
layout(location = 1) out vec3 vWorldPosition;
layout(location = 2) out float vPulse;

const vec3 kPositions[36] = vec3[](
    // front
    vec3(-0.75, -0.75, -0.75), vec3( 0.75, -0.75, -0.75), vec3( 0.75,  0.75, -0.75),
    vec3(-0.75, -0.75, -0.75), vec3( 0.75,  0.75, -0.75), vec3(-0.75,  0.75, -0.75),
    // back
    vec3( 0.75, -0.75,  0.75), vec3(-0.75, -0.75,  0.75), vec3(-0.75,  0.75,  0.75),
    vec3( 0.75, -0.75,  0.75), vec3(-0.75,  0.75,  0.75), vec3( 0.75,  0.75,  0.75),
    // left
    vec3(-0.75, -0.75,  0.75), vec3(-0.75, -0.75, -0.75), vec3(-0.75,  0.75, -0.75),
    vec3(-0.75, -0.75,  0.75), vec3(-0.75,  0.75, -0.75), vec3(-0.75,  0.75,  0.75),
    // right
    vec3( 0.75, -0.75, -0.75), vec3( 0.75, -0.75,  0.75), vec3( 0.75,  0.75,  0.75),
    vec3( 0.75, -0.75, -0.75), vec3( 0.75,  0.75,  0.75), vec3( 0.75,  0.75, -0.75),
    // bottom
    vec3(-0.75, -0.75,  0.75), vec3( 0.75, -0.75,  0.75), vec3( 0.75, -0.75, -0.75),
    vec3(-0.75, -0.75,  0.75), vec3( 0.75, -0.75, -0.75), vec3(-0.75, -0.75, -0.75),
    // top
    vec3(-0.75,  0.75, -0.75), vec3( 0.75,  0.75, -0.75), vec3( 0.75,  0.75,  0.75),
    vec3(-0.75,  0.75, -0.75), vec3( 0.75,  0.75,  0.75), vec3(-0.75,  0.75,  0.75)
);

const vec3 kNormals[36] = vec3[](
    vec3( 0, 0,-1), vec3( 0, 0,-1), vec3( 0, 0,-1),
    vec3( 0, 0,-1), vec3( 0, 0,-1), vec3( 0, 0,-1),

    vec3( 0, 0, 1), vec3( 0, 0, 1), vec3( 0, 0, 1),
    vec3( 0, 0, 1), vec3( 0, 0, 1), vec3( 0, 0, 1),

    vec3(-1, 0, 0), vec3(-1, 0, 0), vec3(-1, 0, 0),
    vec3(-1, 0, 0), vec3(-1, 0, 0), vec3(-1, 0, 0),

    vec3( 1, 0, 0), vec3( 1, 0, 0), vec3( 1, 0, 0),
    vec3( 1, 0, 0), vec3( 1, 0, 0), vec3( 1, 0, 0),

    vec3( 0,-1, 0), vec3( 0,-1, 0), vec3( 0,-1, 0),
    vec3( 0,-1, 0), vec3( 0,-1, 0), vec3( 0,-1, 0),

    vec3( 0, 1, 0), vec3( 0, 1, 0), vec3( 0, 1, 0),
    vec3( 0, 1, 0), vec3( 0, 1, 0), vec3( 0, 1, 0)
);

mat3 rotateY(float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return mat3(
         c, 0.0, -s,
       0.0, 1.0, 0.0,
         s, 0.0,  c
    );
}

mat3 rotateX(float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return mat3(
        1.0, 0.0, 0.0,
        0.0,   c,   s,
        0.0,  -s,   c
    );
}

void main() {
    float turn = pc.timeSeconds * 0.38;
    float lean = sin(pc.timeSeconds * 0.27) * 0.16;

    mat3 rotation = rotateY(turn) * rotateX(lean);

    vec3 world = rotation * kPositions[gl_VertexIndex];
    vec3 normal = normalize(rotation * kNormals[gl_VertexIndex]);

    vec3 camera = world + vec3(0.0, 0.0, 3.25);

    const float nearPlane = 0.10;
    const float farPlane = 20.0;
    const float focal = 1.58;

    float aspect = max(pc.aspect, 0.25);

    vec4 clip;
    clip.x = camera.x * focal / aspect;
    clip.y = -camera.y * focal;
    clip.z =
        (farPlane / (farPlane - nearPlane)) * camera.z
        - (farPlane * nearPlane / (farPlane - nearPlane));
    clip.w = camera.z;

    gl_Position = clip;

    vNormal = normal;
    vWorldPosition = world;
    vPulse = pc.horrorPulse;
}
