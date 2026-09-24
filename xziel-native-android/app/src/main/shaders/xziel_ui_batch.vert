#version 450

layout(location = 0) in vec2 inPosition;
layout(location = 1) in vec2 inLocal;
layout(location = 2) in vec4 inColor;
layout(location = 3) in vec2 inParams;

layout(location = 0) out vec2 vLocal;
layout(location = 1) flat out vec4 vColor;
layout(location = 2) flat out int vShape;
layout(location = 3) flat out float vRingWidth;

void main() {
    gl_Position = vec4(inPosition, 0.0, 1.0);
    vLocal = inLocal;
    vColor = inColor;
    vShape = int(inParams.x + 0.5);
    vRingWidth = inParams.y;
}
