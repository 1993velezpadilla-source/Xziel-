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

// PROCEDURAL_TRIG_LOOKUP_V1
// Procedural sphere/cylinder topology uses fixed angular grids. Store their
// sin/cos pairs once in shader constants instead of evaluating transcendentals
// for every generated vertex.
const vec2 kSphereSegmentTrig[9] = vec2[](
    vec2( 1.0,  0.0),
    vec2( 0.7071067811865476,  0.7071067811865476),
    vec2( 0.0,  1.0),
    vec2(-0.7071067811865476,  0.7071067811865476),
    vec2(-1.0,  0.0),
    vec2(-0.7071067811865476, -0.7071067811865476),
    vec2( 0.0, -1.0),
    vec2( 0.7071067811865476, -0.7071067811865476),
    vec2( 1.0,  0.0)
);

const vec2 kSphereBandTrig[7] = vec2[](
    vec2(0.0, -1.0),
    vec2(0.5, -0.8660254037844386),
    vec2(0.8660254037844386, -0.5),
    vec2(1.0,  0.0),
    vec2(0.8660254037844386,  0.5),
    vec2(0.5,  0.8660254037844386),
    vec2(0.0,  1.0)
);

const vec2 kCylinderSegmentTrig[13] = vec2[](
    vec2( 1.0,  0.0),
    vec2( 0.8660254037844386,  0.5),
    vec2( 0.5,  0.8660254037844386),
    vec2( 0.0,  1.0),
    vec2(-0.5,  0.8660254037844386),
    vec2(-0.8660254037844386,  0.5),
    vec2(-1.0,  0.0),
    vec2(-0.8660254037844386, -0.5),
    vec2(-0.5, -0.8660254037844386),
    vec2( 0.0, -1.0),
    vec2( 0.5, -0.8660254037844386),
    vec2( 0.8660254037844386, -0.5),
    vec2( 1.0,  0.0)
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

vec3 worldToView(
    vec3 world,
    bool cameraBasisCached) {
    vec3 relative =
        world - pc.cameraPositionYaw.xyz;

    float cy;
    float sy;
    float cp;
    float sp;

    if (cameraBasisCached) {
        // CAMERA_TRIG_CPU_CACHE_V1
        // Non-reflective draws do not consume reflectionPlane. Reuse those
        // four push-constant floats for the CPU-computed camera trig basis,
        // removing sin/cos work from every vertex without growing the
        // 128-byte mobile push block.
        cy = pc.reflectionPlane.x;
        sy = pc.reflectionPlane.y;
        cp = pc.reflectionPlane.z;
        sp = pc.reflectionPlane.w;
    } else {
        float yaw =
            pc.cameraPositionYaw.w;
        cy = cos(yaw);
        sy = sin(yaw);

        float pitch =
            pc.cameraPitchFov.x;
        cp = cos(pitch);
        sp = sin(pitch);
    }

    vec3 yawView = vec3(
        cy * relative.x - sy * relative.z,
        relative.y,
        sy * relative.x + cy * relative.z
    );

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

    int shape =
        int(pc.scale.w + 0.5);

    float objectYaw =
        pc.translation.w;

    float objectPitch =
        pc.cameraPitchFov.w;

    float rotationYaw =
        objectYaw + turn;
    float rotationPitch =
        objectPitch + lean;
    bool identityRotation =
        rotationYaw == 0.0 &&
        rotationPitch == 0.0;

    vec3 objectScale =
        max(
            abs(pc.scale.xyz),
            vec3(0.001));

    vec3 unitPosition;
    vec3 unitNormal;

    if (shape == 1) {
        // Low-poly UV sphere generated from gl_VertexIndex. Scaling this unit
        // sphere produces rounded heads, torsos and limbs without adding a
        // vertex buffer or asset upload cost to the mobile prototype.
        const int segments = 8;
        const int bands = 6;
        const float pi = 3.14159265358979323846;

        int triangleIndex =
            gl_VertexIndex / 3;
        int triangleCorner =
            gl_VertexIndex % 3;
        int quadIndex =
            triangleIndex / 2;
        int triangleInQuad =
            triangleIndex % 2;
        int segment =
            quadIndex % segments;
        int band =
            quadIndex / segments;

        int segmentCorner;
        int bandCorner;

        if (triangleInQuad == 0) {
            segmentCorner =
                triangleCorner == 0
                ? segment
                : segment + 1;
            bandCorner =
                triangleCorner == 2
                ? band + 1
                : band;
        } else {
            segmentCorner =
                triangleCorner == 2
                ? segment
                : segment + 1;
            bandCorner =
                triangleCorner == 0
                ? band
                : band + 1;
        }

        vec2 segmentTrig =
            kSphereSegmentTrig[
                segmentCorner];
        vec2 bandTrig =
            kSphereBandTrig[
                bandCorner];

        // PROCEDURAL_SPHERE_UNIT_NORMAL_V1
        // Spherical coordinates produce a unit vector by construction. The
        // fixed angle grid comes from the lookup tables above.
        unitNormal =
            vec3(
                bandTrig.x *
                    segmentTrig.x,
                bandTrig.y,
                bandTrig.x *
                    segmentTrig.y);

        unitPosition =
            unitNormal * 0.75;
    } else if (shape == 2) {
        // Compact procedural cylinder for barrels, magazines and grips.
        // The cylinder's long axis is local Z; object scale/rotation turns
        // it into viewmodel parts without allocating another vertex buffer.
        const int segments = 12;
        const float pi = 3.14159265358979323846;
        int triangleIndex = gl_VertexIndex / 3;
        int triangleCorner = gl_VertexIndex % 3;

        if (triangleIndex < segments * 2) {
            int segment = triangleIndex / 2;
            int triangleInQuad = triangleIndex % 2;
            int segmentCorner;
            float localZ;

            if (triangleInQuad == 0) {
                segmentCorner =
                    triangleCorner == 0
                    ? segment
                    : segment + 1;
                localZ =
                    triangleCorner == 2
                    ? 0.75
                    : -0.75;
            } else {
                segmentCorner =
                    triangleCorner == 2
                    ? segment
                    : segment + 1;
                localZ =
                    triangleCorner == 0
                    ? -0.75
                    : 0.75;
            }

            vec2 radial =
                kCylinderSegmentTrig[
                    segmentCorner];

            unitPosition =
                vec3(
                    radial * 0.75,
                    localZ);
            unitNormal =
                vec3(
                    radial,
                    0.0);
        } else {
            int capTriangle =
                triangleIndex -
                segments * 2;
            bool front =
                capTriangle >= segments;
            int segment =
                capTriangle % segments;
            float localZ =
                front ? 0.75 : -0.75;
            float normalZ =
                front ? 1.0 : -1.0;

            if (triangleCorner == 0) {
                unitPosition =
                    vec3(0.0, 0.0, localZ);
            } else {
                int segmentCorner =
                    triangleCorner == 1
                    ? segment
                    : segment + 1;
                vec2 radial =
                    kCylinderSegmentTrig[
                        segmentCorner];
                unitPosition =
                    vec3(
                        radial * 0.75,
                        localZ);
            }

            unitNormal =
                vec3(
                    0.0,
                    0.0,
                    normalZ);
        }
    } else {
        unitPosition =
            kPositions[gl_VertexIndex];
        unitNormal =
            kNormals[gl_VertexIndex];
    }

    vec3 local =
        unitPosition *
        objectScale;

    vec3 world;
    vec3 normal;

    if (identityRotation) {
        // IDENTITY_OBJECT_ROTATION_FAST_PATH_V1
        // Most static gameplay primitives have zero yaw/pitch. The branch is
        // draw-uniform, so those vertices can bypass six trig evaluations,
        // two matrix constructions/multiplication and the matrix-vector
        // transforms without changing their world position or normal.
        world =
            local +
            pc.translation.xyz;

        if (shape == 0) {
            // BOX_NORMAL_FAST_PATH_V1
            // Cube face normals are axis-aligned and constant across each
            // triangle. Non-uniform object scale changes only magnitude, and
            // the fragment stage normalizes the interpolated normal.
            normal =
                unitNormal;
        } else {
            normal =
                normalize(
                    unitNormal /
                    objectScale);
        }
    } else {
        mat3 rotation =
            rotateY(rotationYaw) *
            rotateX(rotationPitch);

        world =
            rotation * local +
            pc.translation.xyz;

        if (shape == 0) {
            // BOX_NORMAL_FAST_PATH_V1
            normal =
                rotation *
                unitNormal;
        } else {
            vec3 scaledNormal =
                unitNormal /
                objectScale;

            normal =
                normalize(
                    rotation *
                    scaledNormal);
        }
    }

    bool viewmodelMaterial =
        (material >= 10 &&
         material <= 12) ||
        (material >= 15 &&
         material <= 16);

    bool reflectionMaterial =
        material == 13 ||
        material == 14;

    vec3 camera =
        viewmodelMaterial
        ? world
        : worldToView(
              world,
              !reflectionMaterial);

    const float nearPlane = 0.08;
    const float farPlane = 48.0;

    // PROJECTION_TERMS_CPU_PRECOMPUTED_V1
    // CPU computes these once per frame/pass instead of evaluating tan() and
    // division independently in every vertex invocation.
    float focal =
        pc.waterSurfaceExtra.w;
    float focalOverAspect =
        pc.aspect;

    vec4 clip;
    clip.x =
        camera.x *
        focalOverAspect;
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

    int reflectionOwnerMaterial =
        int(
            pc.cameraPitchFov.z +
            0.5);
    bool reflectionVertexNeeded =
        (material == 13 &&
         reflectionOwnerMaterial == 13 &&
         pc.waterSurface.z > 0.0) ||
        (material == 14 &&
         reflectionOwnerMaterial == 14);

    // REFLECTION_VERTEX_MATERIAL_GATE_V1
    // REFLECTION_VERTEX_CONTRIBUTION_GATE_V1
    // Reprojection is consumed only by the live target owner. Water also
    // needs positive reflection strength. These values are draw-uniform, so
    // non-contributing surfaces skip all reflection trig/atan work coherently.
    if (reflectionVertexNeeded) {
        // Reproject each world position through the camera mirrored across the
        // authored planar surface. The fragment shader then samples the live
        // reflection target using true projective coordinates.
        // REFLECTION_PLANE_CPU_NORMALIZED_V1
        // The renderer validates, normalizes and camera-orients this plane
        // once per pass before writing the push constants. Reuse it directly
        // instead of length/divide work in every water/mirror vertex.
        vec3 planeNormal =
            pc.reflectionPlane.xyz;
        float planeDistance =
            pc.reflectionPlane.w;
        float cameraPlaneDistance =
            dot(
                planeNormal,
                pc.cameraPositionYaw.xyz) +
            planeDistance;
        vec3 reflectedPosition =
            pc.cameraPositionYaw.xyz -
            2.0 *
                cameraPlaneDistance *
                planeNormal;

        float yaw = pc.cameraPositionYaw.w;
        float pitch = pc.cameraPitchFov.x;
        float cosPitch =
            cos(pitch);
        vec3 forward =
            vec3(
                sin(yaw) * cosPitch,
                -sin(pitch),
                cos(yaw) * cosPitch);

        // REFLECTED_FORWARD_UNIT_LENGTH_V1
        // The camera forward vector is unit length by construction and a
        // reflection across a unit plane preserves length exactly. Skip the
        // redundant normalize after reflection.
        forward =
            forward -
            2.0 *
                dot(
                    forward,
                    planeNormal) *
                planeNormal;
        float reflectedYaw =
            atan(
                forward.x,
                forward.z);
        float reflectedPitch =
            atan(
                -forward.y,
                length(forward.xz));
        vec3 relativeReflection =
            world -
            reflectedPosition;
        float rcy = cos(reflectedYaw);
        float rsy = sin(reflectedYaw);
        vec3 reflectionYawView =
            vec3(
                rcy * relativeReflection.x -
                    rsy * relativeReflection.z,
                relativeReflection.y,
                rsy * relativeReflection.x +
                    rcy * relativeReflection.z);
        float rcp = cos(reflectedPitch);
        float rsp = sin(reflectedPitch);
        vec3 reflectionView =
            vec3(
                reflectionYawView.x,
                rcp * reflectionYawView.y +
                    rsp * reflectionYawView.z,
                -rsp * reflectionYawView.y +
                    rcp * reflectionYawView.z);
        vReflectionClip =
            vec4(
                reflectionView.x *
                    focalOverAspect,
                -reflectionView.y *
                    focal,
                reflectionView.z,
                reflectionView.z);
    } else {
        vReflectionClip =
            vec4(0.0);
    }

    vNormal = normal;
    vWorldPosition = world;
    vPulse = pc.horrorPulse;
    vMaterial = material;
    vEnvironment = pc.environment;
    vWaterSurface = pc.waterSurface;
    vWaterSurfaceExtra = pc.waterSurfaceExtra;
    vReflectionOwnerMaterial =
        reflectionOwnerMaterial;
    // vReflectionClip was populated above from the reflected camera.
}
