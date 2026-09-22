#version 450

layout(push_constant) uniform PushConstants {
    vec4 cameraPositionYaw;
    vec4 cameraPitchFovAspectFog;
    vec4 environment;
    vec4 modelOffsetScale;
    vec4 modelRotationMode;
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
layout(location = 6) out float vViewmodel;

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

vec3 rotateViewmodel(vec3 value) {
    float yaw = pc.modelRotationMode.x;
    float pitch = pc.modelRotationMode.y;
    float roll = pc.modelRotationMode.z;

    float cy = cos(yaw);
    float sy = sin(yaw);
    value = vec3(
        cy * value.x + sy * value.z,
        value.y,
       -sy * value.x + cy * value.z
    );

    float cp = cos(pitch);
    float sp = sin(pitch);
    value = vec3(
        value.x,
        cp * value.y - sp * value.z,
        sp * value.y + cp * value.z
    );

    float cr = cos(roll);
    float sr = sin(roll);
    return vec3(
        cr * value.x - sr * value.y,
        sr * value.x + cr * value.y,
        value.z
    );
}

void main() {
    float viewmodel =
        step(
            0.5,
            pc.modelRotationMode.w);

    vec3 view;
    vec3 surfaceNormal;

    if (viewmodel > 0.5) {
        view =
            rotateViewmodel(
                inPosition *
                pc.modelOffsetScale.w) +
            pc.modelOffsetScale.xyz;

        surfaceNormal =
            normalize(
                rotateViewmodel(
                    inNormal));
    } else {
        view = worldToView(inPosition);
        surfaceNormal =
            normalize(inNormal);
    }

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
    vNormal = surfaceNormal;
    vColor = inColor;
    vDistance = max(view.z, 0.0);
    vFogDensity =
        viewmodel > 0.5
        ? 0.0
        : clamp(
              pc.cameraPitchFovAspectFog.w,
              0.0,
              1.0);
    vLightning =
        viewmodel > 0.5
        ? 0.0
        : clamp(
              pc.environment.x,
              0.0,
              2.0);
    vViewmodel = viewmodel;
}
