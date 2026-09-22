#version 450

layout(push_constant) uniform PushConstants {
    vec4 cameraPositionYaw;
    vec4 cameraPitchFovAspectFog;
    vec4 environment;
    vec4 modelTranslationYaw;
    vec4 modelScale;
} pc;

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
layout(location = 3) in vec4 inColor;

layout(location = 0) out vec2 vUv;
layout(location = 1) out vec3 vNormal;
layout(location = 2) out vec4 vColor;
layout(location = 3) out float vDistance;
layout(location = 4) out float vFogDensity;
layout(location = 5) out float vLightning;

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
        pc.cameraPitchFovAspectFog.x;

    float cp = cos(pitch);
    float sp = sin(pitch);

    return vec3(
        yawView.x,
        cp * yawView.y + sp * yawView.z,
       -sp * yawView.y + cp * yawView.z
    );
}

void main() {
    float modelYaw = pc.modelTranslationYaw.w;
    float cy = cos(modelYaw);
    float sy = sin(modelYaw);
    float scale = max(pc.modelScale.x, 0.01);

    vec3 local = inPosition * scale;
    vec3 worldPosition = vec3(
        pc.modelTranslationYaw.x +
            cy * local.x +
            sy * local.z,
        pc.modelTranslationYaw.y +
            local.y,
        pc.modelTranslationYaw.z -
            sy * local.x +
            cy * local.z
    );

    vec3 normal = normalize(vec3(
        cy * inNormal.x +
            sy * inNormal.z,
        inNormal.y,
       -sy * inNormal.x +
            cy * inNormal.z
    ));

    vec3 view = worldToView(worldPosition);

    const float nearPlane = 0.08;
    const float farPlane = 180.0;

    float fovDegrees =
        clamp(
            pc.cameraPitchFovAspectFog.y,
            50.0,
            110.0);

    float focal =
        1.0 /
        tan(
            radians(fovDegrees) *
            0.5);

    float aspect =
        max(
            pc.cameraPitchFovAspectFog.z,
            0.25);

    vec4 clip;
    clip.x =
        view.x * focal / aspect;
    clip.y =
        -view.y * focal;
    clip.z =
        (farPlane /
         (farPlane - nearPlane)) *
        view.z
        - (farPlane *
           nearPlane /
           (farPlane - nearPlane));
    clip.w = view.z;

    gl_Position = clip;

    vUv = inUv;
    vNormal = normal;
    vColor = inColor;
    vDistance = max(view.z, 0.0);
    vFogDensity =
        clamp(
            pc.cameraPitchFovAspectFog.w,
            0.0,
            1.0);
    vLightning =
        clamp(
            pc.environment.x,
            0.0,
            2.0);
}
