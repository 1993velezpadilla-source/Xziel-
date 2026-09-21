#version 450

layout(push_constant) uniform PushConstants {
    float timeSeconds;
    float aspect;
    float horrorPulse;
    float materialId;

    vec4 translation;
    vec4 scale;

    vec4 cameraPositionYaw;
    vec4 cameraPitchFov;
} pc;

layout(location = 0) out vec3 vNormal;
layout(location = 1) out vec3 vWorldPosition;
layout(location = 2) out float vPulse;
layout(location = 3) flat out int vMaterial;

const vec3 kPositions[36] = vec3[](
    vec3(-0.75, -0.75, -0.75), vec3( 0.75, -0.75, -0.75), vec3( 0.75,  0.75, -0.75),
    vec3(-0.75, -0.75, -0.75), vec3( 0.75,  0.75, -0.75), vec3(-0.75,  0.75, -0.75),

    vec3( 0.75, -0.75,  0.75), vec3(-0.75, -0.75,  0.75), vec3(-0.75,  0.75,  0.75),
    vec3( 0.75, -0.75,  0.75), vec3(-0.75,  0.75,  0.75), vec3( 0.75,  0.75,  0.75),

    vec3(-0.75, -0.75,  0.75), vec3(-0.75, -0.75, -0.75), vec3(-0.75,  0.75, -0.75),
    vec3(-0.75, -0.75,  0.75), vec3(-0.75,  0.75, -0.75), vec3(-0.75,  0.75,  0.75),

    vec3( 0.75, -0.75, -0.75), vec3( 0.75, -0.75,  0.75), vec3( 0.75,  0.75,  0.75),
    vec3( 0.75, -0.75, -0.75), vec3( 0.75,  0.75,  0.75), vec3( 0.75,  0.75, -0.75),

    vec3(-0.75, -0.75,  0.75), vec3( 0.75, -0.75,  0.75), vec3( 0.75, -0.75, -0.75),
    vec3(-0.75, -0.75,  0.75), vec3( 0.75, -0.75, -0.75), vec3(-0.75, -0.75, -0.75),

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

vec3 worldToView(vec3 world) {
    vec3 relative =
        world - pc.cameraPositionYaw.xyz;

    float yaw =
        pc.cameraPositionYaw.w;

    float cy = cos(yaw);
    float sy = sin(yaw);

    vec3 yawView = vec3(
        cy * relative.x - sy * relative.z,
        relative.y,
        sy * relative.x + cy * relative.z
    );

    float pitch =
        pc.cameraPitchFov.x;

    float cp = cos(pitch);
    float sp = sin(pitch);

    return vec3(
        yawView.x,
        cp * yawView.y + sp * yawView.z,
       -sp * yawView.y + cp * yawView.z
    );
}

void main() {
    int material = int(pc.materialId + 0.5);

    float turn = material == 3
        ? pc.timeSeconds * 0.46
        : 0.0;

    float lean = material == 3
        ? sin(pc.timeSeconds * 0.31) * 0.10
        : 0.0;

    mat3 rotation =
        rotateY(turn) *
        rotateX(lean);

    vec3 objectScale =
        max(
            abs(pc.scale.xyz),
            vec3(0.001));

    vec3 local =
        kPositions[gl_VertexIndex] *
        objectScale;

    vec3 world =
        rotation * local +
        pc.translation.xyz;

    vec3 scaledNormal =
        kNormals[gl_VertexIndex] /
        objectScale;

    vec3 normal =
        normalize(
            rotation *
            scaledNormal);

    vec3 camera =
        material >= 10
        ? world
        : worldToView(world);

    const float nearPlane = 0.08;
    const float farPlane = 48.0;

    float fovDegrees =
        clamp(
            pc.cameraPitchFov.y,
            50.0,
            110.0);

    float focal =
        1.0 /
        tan(
            radians(fovDegrees) *
            0.5);

    float aspect =
        max(
            pc.aspect,
            0.25);

    vec4 clip;
    clip.x =
        camera.x *
        focal /
        aspect;
    clip.y =
        -camera.y *
        focal;
    clip.z =
        (farPlane /
         (farPlane - nearPlane)) *
        camera.z
        - (farPlane *
           nearPlane /
           (farPlane - nearPlane));
    clip.w =
        camera.z;

    gl_Position = clip;

    vNormal = normal;
    vWorldPosition = world;
    vPulse = pc.horrorPulse;
    vMaterial = material;
}
