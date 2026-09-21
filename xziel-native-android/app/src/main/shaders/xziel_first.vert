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
    vec4 environment;
    vec4 waterSurface;
    vec4 waterSurfaceExtra;
    vec4 reflectionPlane;
} pc;

layout(location = 0) out vec3 vNormal;
layout(location = 1) out vec3 vWorldPosition;
layout(location = 2) out float vPulse;
layout(location = 3) flat out int vMaterial;
layout(location = 4) out vec4 vEnvironment;
layout(location = 5) out vec4 vWaterSurface;
layout(location = 6) out vec4 vWaterSurfaceExtra;
layout(location = 7) out vec4 vReflectionClip;
layout(location = 8) flat out int vReflectionOwnerMaterial;

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

    bool viewmodelMaterial =
        material >= 10 &&
        material <= 12;

    vec3 camera =
        viewmodelMaterial
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

    // Reproject each world position through the camera mirrored across the
    // authored planar surface. The fragment shader can then sample the live
    // reflection target using true projective coordinates instead of a
    // world-space UV approximation.
    vec3 planeNormal = pc.reflectionPlane.xyz;
    float planeLength = length(planeNormal);
    if (planeLength < 0.0001) {
        planeNormal = vec3(0.0, 1.0, 0.0);
        planeLength = 1.0;
    }
    planeNormal /= planeLength;
    float planeDistance = pc.reflectionPlane.w / planeLength;
    float cameraPlaneDistance = dot(planeNormal, pc.cameraPositionYaw.xyz) + planeDistance;
    vec3 reflectedPosition = pc.cameraPositionYaw.xyz - 2.0 * cameraPlaneDistance * planeNormal;

    float yaw = pc.cameraPositionYaw.w;
    float pitch = pc.cameraPitchFov.x;
    vec3 forward = vec3(sin(yaw) * cos(pitch), -sin(pitch), cos(yaw) * cos(pitch));
    forward = normalize(forward - 2.0 * dot(forward, planeNormal) * planeNormal);
    float reflectedYaw = atan(forward.x, forward.z);
    float reflectedPitch = atan(-forward.y, length(forward.xz));
    vec3 relativeReflection = world - reflectedPosition;
    float rcy = cos(reflectedYaw);
    float rsy = sin(reflectedYaw);
    vec3 reflectionYawView = vec3(
        rcy * relativeReflection.x - rsy * relativeReflection.z,
        relativeReflection.y,
        rsy * relativeReflection.x + rcy * relativeReflection.z);
    float rcp = cos(reflectedPitch);
    float rsp = sin(reflectedPitch);
    vec3 reflectionView = vec3(
        reflectionYawView.x,
        rcp * reflectionYawView.y + rsp * reflectionYawView.z,
       -rsp * reflectionYawView.y + rcp * reflectionYawView.z);
    vReflectionClip = vec4(
        reflectionView.x * focal / aspect,
       -reflectionView.y * focal,
        reflectionView.z,
        reflectionView.z);

    vNormal = normal;
    vWorldPosition = world;
    vPulse = pc.horrorPulse;
    vMaterial = material;
    vEnvironment = pc.environment;
    vWaterSurface = pc.waterSurface;
    vWaterSurfaceExtra = pc.waterSurfaceExtra;
    vReflectionOwnerMaterial = int(pc.cameraPitchFov.z + 0.5);
    // vReflectionClip was populated above from the reflected camera.
}
