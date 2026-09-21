#include "xz_gles3_shadow.h"
#include "xz_gles3_resource_plan.h"

#include <EGL/egl.h>
#include <GLES3/gl3.h>

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifndef EGL_OPENGL_ES3_BIT_KHR
#define EGL_OPENGL_ES3_BIT_KHR 0x00000040
#endif

#define XZ_SHADOW_WIDTH 64
#define XZ_SHADOW_HEIGHT 64
#define XZ_VERTEX_FLOATS 3u
#define XZ_VERTICES_PER_PACKET 3u
#define XZ_G3_RESOURCE_PROXY_MAX 128u

enum {
    XZ_G3_STAGE_NONE = 0u,
    XZ_G3_STAGE_READBACK = 1u,
    XZ_G3_STAGE_USE_PROGRAM = 2u,
    XZ_G3_STAGE_BIND_VERTEX_ARRAY = 3u,
    XZ_G3_STAGE_BIND_BUFFER = 4u,
    XZ_G3_STAGE_BUFFER_UPLOAD = 5u,
    XZ_G3_STAGE_DRAW = 6u,
    XZ_G3_STAGE_FINISH = 7u,
    XZ_G3_STAGE_UNBIND = 8u
};

typedef GLuint (*XzGlCreateShaderFn)(GLenum);
typedef void (*XzGlShaderSourceFn)(
    GLuint, GLsizei, const GLchar *const *, const GLint *);
typedef void (*XzGlCompileShaderFn)(GLuint);
typedef void (*XzGlGetShaderivFn)(GLuint, GLenum, GLint *);
typedef void (*XzGlDeleteShaderFn)(GLuint);
typedef GLuint (*XzGlCreateProgramFn)(void);
typedef void (*XzGlAttachShaderFn)(GLuint, GLuint);
typedef void (*XzGlLinkProgramFn)(GLuint);
typedef void (*XzGlGetProgramivFn)(GLuint, GLenum, GLint *);
typedef void (*XzGlDeleteProgramFn)(GLuint);
typedef void (*XzGlGenBuffersFn)(GLsizei, GLuint *);
typedef void (*XzGlDeleteBuffersFn)(GLsizei, const GLuint *);
typedef void (*XzGlBindBufferFn)(GLenum, GLuint);
typedef void (*XzGlBufferDataFn)(
    GLenum, GLsizeiptr, const void *, GLenum);
typedef void (*XzGlBufferSubDataFn)(
    GLenum, GLintptr, GLsizeiptr, const void *);
typedef void (*XzGlGenTexturesFn)(GLsizei, GLuint *);
typedef void (*XzGlDeleteTexturesFn)(GLsizei, const GLuint *);
typedef void (*XzGlBindTextureFn)(GLenum, GLuint);
typedef void (*XzGlTexParameteriFn)(GLenum, GLenum, GLint);
typedef void (*XzGlTexImage2DFn)(
    GLenum, GLint, GLint, GLsizei, GLsizei, GLint,
    GLenum, GLenum, const void *);
typedef void (*XzGlGenRenderbuffersFn)(GLsizei, GLuint *);
typedef void (*XzGlDeleteRenderbuffersFn)(GLsizei, const GLuint *);
typedef void (*XzGlBindRenderbufferFn)(GLenum, GLuint);
typedef void (*XzGlRenderbufferStorageFn)(
    GLenum, GLenum, GLsizei, GLsizei);
typedef void (*XzGlGenVertexArraysFn)(GLsizei, GLuint *);
typedef void (*XzGlDeleteVertexArraysFn)(GLsizei, const GLuint *);
typedef void (*XzGlBindVertexArrayFn)(GLuint);
typedef void (*XzGlEnableVertexAttribArrayFn)(GLuint);
typedef void (*XzGlVertexAttribPointerFn)(
    GLuint, GLint, GLenum, GLboolean, GLsizei, const void *);
typedef void (*XzGlUseProgramFn)(GLuint);
typedef void (*XzGlViewportFn)(GLint, GLint, GLsizei, GLsizei);
typedef void (*XzGlClearColorFn)(GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (*XzGlClearFn)(GLbitfield);
typedef void (*XzGlDrawArraysFn)(GLenum, GLint, GLsizei);
typedef void (*XzGlReadPixelsFn)(
    GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void *);
typedef void (*XzGlFinishFn)(void);
typedef GLenum (*XzGlGetErrorFn)(void);

typedef struct {
    void *library;

    XzGlCreateShaderFn CreateShader;
    XzGlShaderSourceFn ShaderSource;
    XzGlCompileShaderFn CompileShader;
    XzGlGetShaderivFn GetShaderiv;
    XzGlDeleteShaderFn DeleteShader;
    XzGlCreateProgramFn CreateProgram;
    XzGlAttachShaderFn AttachShader;
    XzGlLinkProgramFn LinkProgram;
    XzGlGetProgramivFn GetProgramiv;
    XzGlDeleteProgramFn DeleteProgram;

    XzGlGenBuffersFn GenBuffers;
    XzGlDeleteBuffersFn DeleteBuffers;
    XzGlBindBufferFn BindBuffer;
    XzGlBufferDataFn BufferData;
    XzGlBufferSubDataFn BufferSubData;

    XzGlGenTexturesFn GenTextures;
    XzGlDeleteTexturesFn DeleteTextures;
    XzGlBindTextureFn BindTexture;
    XzGlTexParameteriFn TexParameteri;
    XzGlTexImage2DFn TexImage2D;

    XzGlGenRenderbuffersFn GenRenderbuffers;
    XzGlDeleteRenderbuffersFn DeleteRenderbuffers;
    XzGlBindRenderbufferFn BindRenderbuffer;
    XzGlRenderbufferStorageFn RenderbufferStorage;

    XzGlGenVertexArraysFn GenVertexArrays;
    XzGlDeleteVertexArraysFn DeleteVertexArrays;
    XzGlBindVertexArrayFn BindVertexArray;
    XzGlEnableVertexAttribArrayFn EnableVertexAttribArray;
    XzGlVertexAttribPointerFn VertexAttribPointer;

    XzGlUseProgramFn UseProgram;
    XzGlViewportFn Viewport;
    XzGlClearColorFn ClearColor;
    XzGlClearFn Clear;
    XzGlDrawArraysFn DrawArrays;
    XzGlReadPixelsFn ReadPixels;
    XzGlFinishFn Finish;
    XzGlGetErrorFn GetError;
} XzNativeGles3Api;

typedef struct {
    XzGpuHandle handle;
    XzGles3ResourceSpec spec;
    GLuint object;
    int alive;
} XzGles3PhysicalResource;

typedef struct {
    int ready;

    EGLDisplay display;
    EGLConfig config;
    EGLSurface surface;
    EGLContext context;

    GLuint program;
    GLuint vbo;
    GLuint vao;

    XzGles3PhysicalResource
        physical[XZ_GPU_MAX_RESOURCES];

    XzNativeGles3Api gl;
} XzGles3ShadowInternal;

static XzGles3ShadowInternal xz_shadow;

static float XzAbsFloat(float value)
{
    return value < 0.0f ? -value : value;
}

static unsigned int XzAbsByteDiff(
    unsigned char a,
    unsigned char b)
{
    return a > b
        ? (unsigned int)(a - b)
        : (unsigned int)(b - a);
}

static int XzLoadApi(XzNativeGles3Api *api)
{
#define XZ_GL_LOAD(field, symbol)                                      \
    do {                                                               \
        *(void **)(&api->field) = dlsym(api->library, symbol);         \
        if (!api->field)                                               \
            return 0;                                                  \
    } while (0)

    memset(api, 0, sizeof(*api));

    api->library = dlopen(
        "libGLESv2.so",
        RTLD_NOW | RTLD_LOCAL);
    if (!api->library)
        return 0;

    XZ_GL_LOAD(CreateShader, "glCreateShader");
    XZ_GL_LOAD(ShaderSource, "glShaderSource");
    XZ_GL_LOAD(CompileShader, "glCompileShader");
    XZ_GL_LOAD(GetShaderiv, "glGetShaderiv");
    XZ_GL_LOAD(DeleteShader, "glDeleteShader");
    XZ_GL_LOAD(CreateProgram, "glCreateProgram");
    XZ_GL_LOAD(AttachShader, "glAttachShader");
    XZ_GL_LOAD(LinkProgram, "glLinkProgram");
    XZ_GL_LOAD(GetProgramiv, "glGetProgramiv");
    XZ_GL_LOAD(DeleteProgram, "glDeleteProgram");

    XZ_GL_LOAD(GenBuffers, "glGenBuffers");
    XZ_GL_LOAD(DeleteBuffers, "glDeleteBuffers");
    XZ_GL_LOAD(BindBuffer, "glBindBuffer");
    XZ_GL_LOAD(BufferData, "glBufferData");
    XZ_GL_LOAD(BufferSubData, "glBufferSubData");

    XZ_GL_LOAD(GenTextures, "glGenTextures");
    XZ_GL_LOAD(DeleteTextures, "glDeleteTextures");
    XZ_GL_LOAD(BindTexture, "glBindTexture");
    XZ_GL_LOAD(TexParameteri, "glTexParameteri");
    XZ_GL_LOAD(TexImage2D, "glTexImage2D");

    XZ_GL_LOAD(GenRenderbuffers, "glGenRenderbuffers");
    XZ_GL_LOAD(DeleteRenderbuffers, "glDeleteRenderbuffers");
    XZ_GL_LOAD(BindRenderbuffer, "glBindRenderbuffer");
    XZ_GL_LOAD(RenderbufferStorage, "glRenderbufferStorage");

    XZ_GL_LOAD(GenVertexArrays, "glGenVertexArrays");
    XZ_GL_LOAD(DeleteVertexArrays, "glDeleteVertexArrays");
    XZ_GL_LOAD(BindVertexArray, "glBindVertexArray");
    XZ_GL_LOAD(
        EnableVertexAttribArray,
        "glEnableVertexAttribArray");
    XZ_GL_LOAD(
        VertexAttribPointer,
        "glVertexAttribPointer");

    XZ_GL_LOAD(UseProgram, "glUseProgram");
    XZ_GL_LOAD(Viewport, "glViewport");
    XZ_GL_LOAD(ClearColor, "glClearColor");
    XZ_GL_LOAD(Clear, "glClear");
    XZ_GL_LOAD(DrawArrays, "glDrawArrays");
    XZ_GL_LOAD(ReadPixels, "glReadPixels");
    XZ_GL_LOAD(Finish, "glFinish");
    XZ_GL_LOAD(GetError, "glGetError");

#undef XZ_GL_LOAD
    return 1;
}

static void XzUnloadApi(XzNativeGles3Api *api)
{
    if (!api)
        return;

    if (api->library)
        dlclose(api->library);

    memset(api, 0, sizeof(*api));
}

static int XzCompileShader(
    XzNativeGles3Api *gl,
    GLenum type,
    const char *source,
    GLuint *shader_out)
{
    GLuint shader;
    GLint ok = 0;

    shader = gl->CreateShader(type);
    if (!shader)
        return 0;

    gl->ShaderSource(shader, 1, &source, NULL);
    gl->CompileShader(shader);
    gl->GetShaderiv(
        shader,
        GL_COMPILE_STATUS,
        &ok);

    if (!ok) {
        gl->DeleteShader(shader);
        return 0;
    }

    *shader_out = shader;
    return 1;
}

static int XzCreateProgramAndBuffer(void)
{
    static const char *vs_source =
        "#version 300 es\n"
        "layout(location=0) in vec2 aPos;\n"
        "layout(location=1) in float aWeight;\n"
        "out float vWeight;\n"
        "void main(){\n"
        "  gl_Position=vec4(aPos,0.0,1.0);\n"
        "  gl_PointSize=1.0+3.0*aWeight;\n"
        "  vWeight=aWeight;\n"
        "}\n";

    static const char *fs_source =
        "#version 300 es\n"
        "precision mediump float;\n"
        "in float vWeight;\n"
        "out vec4 outColor;\n"
        "void main(){\n"
        "  outColor=vec4(vWeight,1.0-vWeight,0.25,1.0);\n"
        "}\n";

    XzNativeGles3Api *gl = &xz_shadow.gl;
    GLuint vs = 0u;
    GLuint fs = 0u;
    GLint linked = 0;

    if (!XzCompileShader(
            gl, GL_VERTEX_SHADER, vs_source, &vs))
        return 0;

    if (!XzCompileShader(
            gl, GL_FRAGMENT_SHADER, fs_source, &fs)) {
        gl->DeleteShader(vs);
        return 0;
    }

    xz_shadow.program = gl->CreateProgram();
    if (!xz_shadow.program) {
        gl->DeleteShader(vs);
        gl->DeleteShader(fs);
        return 0;
    }

    gl->AttachShader(xz_shadow.program, vs);
    gl->AttachShader(xz_shadow.program, fs);
    gl->LinkProgram(xz_shadow.program);
    gl->GetProgramiv(
        xz_shadow.program,
        GL_LINK_STATUS,
        &linked);

    gl->DeleteShader(vs);
    gl->DeleteShader(fs);

    if (!linked)
        return 0;

    gl->GenVertexArrays(1, &xz_shadow.vao);
    gl->BindVertexArray(xz_shadow.vao);

    gl->GenBuffers(1, &xz_shadow.vbo);
    gl->BindBuffer(GL_ARRAY_BUFFER, xz_shadow.vbo);
    gl->BufferData(
        GL_ARRAY_BUFFER,
        (GLsizeiptr)(
            XZ_RENDER_MAX_PACKETS *
            XZ_VERTICES_PER_PACKET *
            XZ_VERTEX_FLOATS *
            sizeof(float)),
        NULL,
        GL_STREAM_DRAW);

    gl->EnableVertexAttribArray(0u);
    gl->VertexAttribPointer(
        0u,
        2,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)(XZ_VERTEX_FLOATS * sizeof(float)),
        (const void *)0);

    gl->EnableVertexAttribArray(1u);
    gl->VertexAttribPointer(
        1u,
        1,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)(XZ_VERTEX_FLOATS * sizeof(float)),
        (const void *)(uintptr_t)(2u * sizeof(float)));

    gl->BindVertexArray(0u);
    gl->BindBuffer(GL_ARRAY_BUFFER, 0u);

    return gl->GetError() == GL_NO_ERROR;
}

static int XzMakeShadowCurrent(
    EGLDisplay *previous_display,
    EGLSurface *previous_draw,
    EGLSurface *previous_read,
    EGLContext *previous_context)
{
    *previous_display = eglGetCurrentDisplay();
    *previous_draw = eglGetCurrentSurface(EGL_DRAW);
    *previous_read = eglGetCurrentSurface(EGL_READ);
    *previous_context = eglGetCurrentContext();

    return eglMakeCurrent(
        xz_shadow.display,
        xz_shadow.surface,
        xz_shadow.surface,
        xz_shadow.context) ? 1 : 0;
}

static int XzRestorePrevious(
    EGLDisplay previous_display,
    EGLSurface previous_draw,
    EGLSurface previous_read,
    EGLContext previous_context)
{
    if (previous_display != EGL_NO_DISPLAY &&
        previous_context != EGL_NO_CONTEXT) {
        return eglMakeCurrent(
            previous_display,
            previous_draw,
            previous_read,
            previous_context) ? 1 : 0;
    }

    return eglMakeCurrent(
        xz_shadow.display,
        EGL_NO_SURFACE,
        EGL_NO_SURFACE,
        EGL_NO_CONTEXT) ? 1 : 0;
}

static void XzEncodePlanColor(
    uint32_t hash,
    unsigned char rgba[4])
{
    rgba[0] = (unsigned char)(hash & 0xffu);
    rgba[1] = (unsigned char)((hash >> 8) & 0xffu);
    rgba[2] = (unsigned char)((hash >> 16) & 0xffu);
    rgba[3] = 255u;
}

static int XzReadbackMatches(
    const unsigned char expected[4],
    const unsigned char actual[4])
{
    return XzAbsByteDiff(expected[0], actual[0]) <= 2u &&
           XzAbsByteDiff(expected[1], actual[1]) <= 2u &&
           XzAbsByteDiff(expected[2], actual[2]) <= 2u &&
           XzAbsByteDiff(expected[3], actual[3]) <= 2u;
}

static void XzDrainErrors(
    XzGles3ShadowState *state)
{
    GLenum error;

    do {
        error = xz_shadow.gl.GetError();
        if (error != GL_NO_ERROR)
            state->preexisting_errors++;
    } while (error != GL_NO_ERROR);
}

static GLenum XzCaptureError(
    XzGles3ShadowState *state,
    unsigned int stage)
{
    GLenum error = xz_shadow.gl.GetError();

    if (error != GL_NO_ERROR &&
        state->last_error_stage == XZ_G3_STAGE_NONE) {
        state->last_gl_error = (unsigned int)error;
        state->last_error_stage = stage;
    }

    return error;
}

static int XzTextureFormat(
    uint32_t logical_format,
    GLint *internal_format,
    GLenum *format,
    GLenum *type)
{
    if (!internal_format || !format || !type)
        return 0;

    switch ((XzRgFormat)logical_format) {
    case XZ_RG_FORMAT_RGBA16F:
        *internal_format = GL_RGBA16F;
        *format = GL_RGBA;
        *type = GL_HALF_FLOAT;
        return 1;

    case XZ_RG_FORMAT_RG16F:
        *internal_format = GL_RG16F;
        *format = GL_RG;
        *type = GL_HALF_FLOAT;
        return 1;

    case XZ_RG_FORMAT_RGBA8:
    case XZ_RG_FORMAT_UNKNOWN:
        *internal_format = GL_RGBA8;
        *format = GL_RGBA;
        *type = GL_UNSIGNED_BYTE;
        return 1;

    case XZ_RG_FORMAT_DEPTH16:
    case XZ_RG_FORMAT_DEPTH24:
    default:
        return 0;
    }
}

static GLenum XzDepthInternalFormat(
    uint32_t logical_format)
{
    return logical_format == XZ_RG_FORMAT_DEPTH16
        ? GL_DEPTH_COMPONENT16
        : GL_DEPTH_COMPONENT24;
}

static void XzDestroyPhysicalResource(
    XzGles3ShadowState *state,
    unsigned int index)
{
    XzGles3PhysicalResource *resource;

    if (!state || index >= XZ_GPU_MAX_RESOURCES)
        return;

    resource = &xz_shadow.physical[index];
    if (!resource->alive)
        return;

    if (resource->object != 0u) {
        if (resource->spec.kind ==
            XZ_G3_RESOURCE_TEXTURE_2D) {
            xz_shadow.gl.DeleteTextures(
                1, &resource->object);
        } else if (resource->spec.kind ==
                   XZ_G3_RESOURCE_DEPTH_RENDERBUFFER) {
            xz_shadow.gl.DeleteRenderbuffers(
                1, &resource->object);
        }

        if (state->physical_gl_objects > 0u)
            state->physical_gl_objects--;
    }

    if (state->physical_alive > 0u)
        state->physical_alive--;

    if (state->physical_bytes >=
        resource->spec.physical_bytes)
        state->physical_bytes -=
            resource->spec.physical_bytes;
    else
        state->physical_bytes = 0u;

    state->physical_destroys++;
    memset(resource, 0, sizeof(*resource));
}

static int XzBindPhysicalResource(
    XzGles3ShadowState *state,
    XzGles3PhysicalResource *resource,
    int for_write)
{
    GLenum error;

    if (!state || !resource || !resource->alive)
        return 0;

    switch (resource->spec.kind) {
    case XZ_G3_RESOURCE_TEXTURE_2D:
        xz_shadow.gl.BindTexture(
            GL_TEXTURE_2D,
            resource->object);
        break;

    case XZ_G3_RESOURCE_DEPTH_RENDERBUFFER:
        xz_shadow.gl.BindRenderbuffer(
            GL_RENDERBUFFER,
            resource->object);
        break;

    case XZ_G3_RESOURCE_EXTERNAL_SURFACE:
        break;

    case XZ_G3_RESOURCE_INVALID:
    default:
        state->physical_failures++;
        return 0;
    }

    error = xz_shadow.gl.GetError();
    if (error != GL_NO_ERROR) {
        state->physical_failures++;
        if (state->last_gl_error == 0u)
            state->last_gl_error =
                (unsigned int)error;
        return 0;
    }

    if (for_write)
        state->physical_write_binds++;
    else
        state->physical_read_binds++;

    return 1;
}

static int XzEnsurePhysicalResource(
    XzGles3ShadowState *state,
    XzGpuResourcePool *pool,
    XzGpuHandle handle,
    int for_write)
{
    const XzGpuResourceDesc *desc;
    XzGles3PhysicalResource *resource;
    XzGles3ResourceSpec spec;
    unsigned int index;
    GLuint object = 0u;
    GLenum error;

    if (!state || !pool ||
        handle == XZ_GPU_INVALID_HANDLE) {
        if (state)
            state->physical_failures++;
        return 0;
    }

    index = XzGpuHandle_Index(handle);
    if (index >= XZ_GPU_MAX_RESOURCES) {
        state->physical_failures++;
        return 0;
    }

    desc = XzGpuResource_Resolve(pool, handle);
    if (!desc) {
        state->physical_failures++;
        return 0;
    }

    resource = &xz_shadow.physical[index];

    if (resource->alive &&
        resource->handle == handle) {
        state->physical_reuses++;
        return XzBindPhysicalResource(
            state, resource, for_write);
    }

    if (resource->alive)
        XzDestroyPhysicalResource(state, index);

    if (!XzGles3ResourcePlan_Build(
            desc,
            XZ_G3_RESOURCE_PROXY_MAX,
            &spec)) {
        state->physical_failures++;
        return 0;
    }

    if (spec.kind == XZ_G3_RESOURCE_TEXTURE_2D) {
        GLint internal_format;
        GLenum format;
        GLenum type;

        if (!XzTextureFormat(
                spec.logical_format,
                &internal_format,
                &format,
                &type)) {
            state->physical_failures++;
            return 0;
        }

        xz_shadow.gl.GenTextures(1, &object);
        if (!object) {
            state->physical_failures++;
            return 0;
        }

        xz_shadow.gl.BindTexture(
            GL_TEXTURE_2D, object);
        xz_shadow.gl.TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MIN_FILTER,
            GL_NEAREST);
        xz_shadow.gl.TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MAG_FILTER,
            GL_NEAREST);
        xz_shadow.gl.TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_S,
            GL_CLAMP_TO_EDGE);
        xz_shadow.gl.TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_T,
            GL_CLAMP_TO_EDGE);
        xz_shadow.gl.TexImage2D(
            GL_TEXTURE_2D,
            0,
            internal_format,
            (GLsizei)spec.physical_width,
            (GLsizei)spec.physical_height,
            0,
            format,
            type,
            NULL);
    } else if (
        spec.kind ==
        XZ_G3_RESOURCE_DEPTH_RENDERBUFFER) {
        xz_shadow.gl.GenRenderbuffers(
            1, &object);
        if (!object) {
            state->physical_failures++;
            return 0;
        }

        xz_shadow.gl.BindRenderbuffer(
            GL_RENDERBUFFER, object);
        xz_shadow.gl.RenderbufferStorage(
            GL_RENDERBUFFER,
            XzDepthInternalFormat(
                spec.logical_format),
            (GLsizei)spec.physical_width,
            (GLsizei)spec.physical_height);
    } else if (
        spec.kind !=
        XZ_G3_RESOURCE_EXTERNAL_SURFACE) {
        state->physical_failures++;
        return 0;
    }

    error = xz_shadow.gl.GetError();
    if (error != GL_NO_ERROR) {
        if (object != 0u) {
            if (spec.kind ==
                XZ_G3_RESOURCE_TEXTURE_2D)
                xz_shadow.gl.DeleteTextures(
                    1, &object);
            else if (spec.kind ==
                     XZ_G3_RESOURCE_DEPTH_RENDERBUFFER)
                xz_shadow.gl.DeleteRenderbuffers(
                    1, &object);
        }

        state->physical_failures++;
        if (state->last_gl_error == 0u)
            state->last_gl_error =
                (unsigned int)error;
        return 0;
    }

    memset(resource, 0, sizeof(*resource));
    resource->handle = handle;
    resource->spec = spec;
    resource->object = object;
    resource->alive = 1;

    state->physical_alive++;
    if (object != 0u)
        state->physical_gl_objects++;
    state->physical_creates++;
    state->physical_bytes += spec.physical_bytes;

    return XzBindPhysicalResource(
        state, resource, for_write);
}

static void XzDestroyAllPhysicalResources(
    XzGles3ShadowState *state)
{
    unsigned int i;

    if (!state)
        return;

    for (i = 0u; i < XZ_GPU_MAX_RESOURCES; ++i)
        XzDestroyPhysicalResource(state, i);
}

void XzGles3Shadow_InitState(
    XzGles3ShadowState *state)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->restore_ok = 1;
}

int XzGles3Shadow_Init(
    XzGles3ShadowState *state,
    unsigned int submit_stride)
{
    EGLDisplay previous_display;
    EGLSurface previous_draw;
    EGLSurface previous_read;
    EGLContext previous_context;
    EGLint egl_major = 0;
    EGLint egl_minor = 0;
    EGLint config_count = 0;

    const EGLint config_attribs[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT_KHR,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    const EGLint surface_attribs[] = {
        EGL_WIDTH, XZ_SHADOW_WIDTH,
        EGL_HEIGHT, XZ_SHADOW_HEIGHT,
        EGL_NONE
    };
    const EGLint context_attribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };

    if (!state)
        return 0;

    XzGles3Shadow_InitState(state);
    memset(&xz_shadow, 0, sizeof(xz_shadow));

    state->submit_stride =
        submit_stride > 0u ? submit_stride : 8u;

    previous_display = eglGetCurrentDisplay();
    previous_draw = eglGetCurrentSurface(EGL_DRAW);
    previous_read = eglGetCurrentSurface(EGL_READ);
    previous_context = eglGetCurrentContext();

    xz_shadow.display = previous_display;
    if (xz_shadow.display == EGL_NO_DISPLAY)
        xz_shadow.display =
            eglGetDisplay(EGL_DEFAULT_DISPLAY);

    if (xz_shadow.display == EGL_NO_DISPLAY)
        goto fail;

    if (!eglInitialize(
            xz_shadow.display,
            &egl_major,
            &egl_minor))
        goto fail;

    if (!eglBindAPI(EGL_OPENGL_ES_API))
        goto fail;

    if (!eglChooseConfig(
            xz_shadow.display,
            config_attribs,
            &xz_shadow.config,
            1,
            &config_count) ||
        config_count < 1)
        goto fail;

    xz_shadow.surface = eglCreatePbufferSurface(
        xz_shadow.display,
        xz_shadow.config,
        surface_attribs);
    if (xz_shadow.surface == EGL_NO_SURFACE)
        goto fail;

    xz_shadow.context = eglCreateContext(
        xz_shadow.display,
        xz_shadow.config,
        EGL_NO_CONTEXT,
        context_attribs);
    if (xz_shadow.context == EGL_NO_CONTEXT)
        goto fail;

    if (!eglMakeCurrent(
            xz_shadow.display,
            xz_shadow.surface,
            xz_shadow.surface,
            xz_shadow.context))
        goto fail;

    if (!XzLoadApi(&xz_shadow.gl))
        goto fail_current;

    if (!XzCreateProgramAndBuffer())
        goto fail_current;

    xz_shadow.gl.Viewport(
        0, 0, XZ_SHADOW_WIDTH, XZ_SHADOW_HEIGHT);

    if (!XzRestorePrevious(
            previous_display,
            previous_draw,
            previous_read,
            previous_context))
        goto fail_restore;

    xz_shadow.ready = 1;
    state->initialized = 1;
    state->available = 1;
    state->shader_ok = 1;
    state->restore_ok = 1;
    return 1;

fail_current:
    XzUnloadApi(&xz_shadow.gl);

fail_restore:
    if (previous_display != EGL_NO_DISPLAY &&
        previous_context != EGL_NO_CONTEXT) {
        eglMakeCurrent(
            previous_display,
            previous_draw,
            previous_read,
            previous_context);
    }

fail:
    if (xz_shadow.context != EGL_NO_CONTEXT)
        eglDestroyContext(
            xz_shadow.display,
            xz_shadow.context);
    if (xz_shadow.surface != EGL_NO_SURFACE)
        eglDestroySurface(
            xz_shadow.display,
            xz_shadow.surface);

    memset(&xz_shadow, 0, sizeof(xz_shadow));
    state->failures++;
    state->restore_ok = 0;
    return 0;
}

static int XzGles3Shadow_SubmitInternal(
    XzGles3ShadowState *state,
    const XzCommandStream *commands,
    const XzRenderPlan *plan)
{
    float vertices[
        XZ_RENDER_MAX_PACKETS *
        XZ_VERTICES_PER_PACKET *
        XZ_VERTEX_FLOATS];
    EGLDisplay previous_display;
    EGLSurface previous_draw;
    EGLSurface previous_read;
    EGLContext previous_context;
    unsigned int i;
    unsigned char expected[4];
    unsigned char readback[4] = {0u, 0u, 0u, 0u};
    int had_gl_error = 0;
    int readback_ok;
    int command_ok = 1;
    int saw_draw = 0;
    XzNativeGles3Api *gl;

    if (!state || !plan ||
        !state->initialized ||
        !state->available ||
        !xz_shadow.ready)
        return 0;

    state->submit_attempts++;

    if (!XzRenderPlan_Validate(plan)) {
        state->failures++;
        return 0;
    }

    if (commands &&
        !XzCommandStream_Validate(commands)) {
        state->command_failures++;
        state->failures++;
        return 0;
    }

    if (plan->generation == 0u ||
        (plan->generation % state->submit_stride) != 0u) {
        state->skipped_frames++;
        return 1;
    }

    if (!XzMakeShadowCurrent(
            &previous_display,
            &previous_draw,
            &previous_read,
            &previous_context)) {
        state->failures++;
        state->restore_ok = 0;
        return 0;
    }

    gl = &xz_shadow.gl;
    state->last_gl_error = 0u;
    state->last_error_stage = XZ_G3_STAGE_NONE;
    XzDrainErrors(state);

    for (i = 0u; i < plan->packet_count; ++i) {
        const XzRenderPacket *packet =
            &plan->packets[i];
        const float x =
            packet->origin[0] /
            (512.0f + XzAbsFloat(packet->origin[0]));
        const float y =
            packet->origin[1] /
            (512.0f + XzAbsFloat(packet->origin[1]));
        const float weight =
            (float)packet->priority_class / 3.0f;
        const float delta =
            0.004f + 0.004f * weight;
        const unsigned int base =
            i * XZ_VERTICES_PER_PACKET *
            XZ_VERTEX_FLOATS;

        vertices[base + 0u] = x;
        vertices[base + 1u] = y + delta;
        vertices[base + 2u] = weight;

        vertices[base + 3u] = x - delta;
        vertices[base + 4u] = y - delta;
        vertices[base + 5u] = weight;

        vertices[base + 6u] = x + delta;
        vertices[base + 7u] = y - delta;
        vertices[base + 8u] = weight;
    }

    XzEncodePlanColor(
        commands ? commands->content_hash
                 : plan->content_hash,
        expected);

    gl->Viewport(
        0, 0, XZ_SHADOW_WIDTH, XZ_SHADOW_HEIGHT);
    gl->ClearColor(
        (float)expected[0] / 255.0f,
        (float)expected[1] / 255.0f,
        (float)expected[2] / 255.0f,
        1.0f);
    gl->Clear(GL_COLOR_BUFFER_BIT);

    gl->ReadPixels(
        0,
        0,
        1,
        1,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        readback);

    if (XzCaptureError(
            state,
            XZ_G3_STAGE_READBACK) != GL_NO_ERROR)
        had_gl_error = 1;

    readback_ok =
        XzReadbackMatches(expected, readback);

    if (!readback_ok) {
        state->readback_failures++;
        state->failures++;
    }

    gl->UseProgram(xz_shadow.program);
    if (XzCaptureError(
            state,
            XZ_G3_STAGE_USE_PROGRAM) != GL_NO_ERROR)
        had_gl_error = 1;

    gl->BindVertexArray(xz_shadow.vao);
    if (XzCaptureError(
            state,
            XZ_G3_STAGE_BIND_VERTEX_ARRAY) != GL_NO_ERROR)
        had_gl_error = 1;

    gl->BindBuffer(
        GL_ARRAY_BUFFER,
        xz_shadow.vbo);
    if (XzCaptureError(
            state,
            XZ_G3_STAGE_BIND_BUFFER) != GL_NO_ERROR)
        had_gl_error = 1;

    if (commands) {
        state->command_stream_submissions++;
        state->last_command_hash =
            commands->content_hash;

        for (i = 0u; i < commands->count; ++i) {
            const XzCommand *command =
                &commands->commands[i];

            state->commands_executed++;

            switch (command->op) {
            case XZ_CMD_BEGIN_PASS:
                state->passes_executed++;
                break;

            case XZ_CMD_RESOURCE_READ:
                state->resource_read_commands++;
                break;

            case XZ_CMD_RESOURCE_WRITE:
                state->resource_write_commands++;
                break;

            case XZ_CMD_DRAW_PACKETS:
                state->draw_commands++;

                if (saw_draw ||
                    command->a != plan->packet_count ||
                    command->value64 !=
                        (uint64_t)plan->content_hash) {
                    command_ok = 0;
                    break;
                }

                saw_draw = 1;

                if (plan->packet_count > 0u) {
                    gl->BufferSubData(
                        GL_ARRAY_BUFFER,
                        0,
                        (GLsizeiptr)(
                            plan->packet_count *
                            XZ_VERTICES_PER_PACKET *
                            XZ_VERTEX_FLOATS *
                            sizeof(float)),
                        vertices);

                    if (XzCaptureError(
                            state,
                            XZ_G3_STAGE_BUFFER_UPLOAD) !=
                        GL_NO_ERROR)
                        had_gl_error = 1;

                    gl->DrawArrays(
                        GL_TRIANGLES,
                        0,
                        (GLsizei)(
                            plan->packet_count *
                            XZ_VERTICES_PER_PACKET));

                    if (XzCaptureError(
                            state,
                            XZ_G3_STAGE_DRAW) !=
                        GL_NO_ERROR)
                        had_gl_error = 1;

                    state->draw_calls++;
                }
                break;

            case XZ_CMD_BEGIN_FRAME:
            case XZ_CMD_END_PASS:
            case XZ_CMD_END_FRAME:
                break;

            case XZ_CMD_NOP:
            default:
                command_ok = 0;
                break;
            }

            if (!command_ok)
                break;
        }

        if (plan->packet_count > 0u &&
            !saw_draw)
            command_ok = 0;
    } else if (plan->packet_count > 0u) {
        gl->BufferSubData(
            GL_ARRAY_BUFFER,
            0,
            (GLsizeiptr)(
                plan->packet_count *
                XZ_VERTICES_PER_PACKET *
                XZ_VERTEX_FLOATS *
                sizeof(float)),
            vertices);

        if (XzCaptureError(
                state,
                XZ_G3_STAGE_BUFFER_UPLOAD) != GL_NO_ERROR)
            had_gl_error = 1;

        gl->DrawArrays(
            GL_TRIANGLES,
            0,
            (GLsizei)(
                plan->packet_count *
                XZ_VERTICES_PER_PACKET));

        if (XzCaptureError(
                state,
                XZ_G3_STAGE_DRAW) != GL_NO_ERROR)
            had_gl_error = 1;

        state->draw_calls++;
    }

    gl->Finish();
    if (XzCaptureError(
            state,
            XZ_G3_STAGE_FINISH) != GL_NO_ERROR)
        had_gl_error = 1;

    gl->BindVertexArray(0u);
    gl->BindBuffer(GL_ARRAY_BUFFER, 0u);

    if (XzCaptureError(
            state,
            XZ_G3_STAGE_UNBIND) != GL_NO_ERROR)
        had_gl_error = 1;

    state->last_packet_count = plan->packet_count;
    state->last_plan_hash = plan->content_hash;
    memcpy(
        state->last_expected_rgba,
        expected,
        sizeof(expected));
    memcpy(
        state->last_readback_rgba,
        readback,
        sizeof(readback));

    if (!command_ok) {
        state->command_failures++;
        state->failures++;
    }

    if (had_gl_error)
        state->failures++;

    if (!XzRestorePrevious(
            previous_display,
            previous_draw,
            previous_read,
            previous_context)) {
        state->restore_failures++;
        state->failures++;
        state->restore_ok = 0;
        return 0;
    }

    state->restore_ok = 1;
    state->submitted_frames++;
    state->submitted_packets += plan->packet_count;

    return !had_gl_error &&
           readback_ok &&
           command_ok;
}

int XzGles3Shadow_Submit(
    XzGles3ShadowState *state,
    const XzRenderPlan *plan)
{
    return XzGles3Shadow_SubmitInternal(
        state, NULL, plan);
}

int XzGles3Shadow_SubmitCommands(
    XzGles3ShadowState *state,
    const XzCommandStream *commands,
    const XzRenderPlan *plan)
{
    return XzGles3Shadow_SubmitInternal(
        state, commands, plan);
}

void XzGles3Shadow_Shutdown(
    XzGles3ShadowState *state)
{
    EGLDisplay previous_display;
    EGLSurface previous_draw;
    EGLSurface previous_read;
    EGLContext previous_context;

    if (!state || !state->initialized)
        return;

    if (xz_shadow.ready &&
        XzMakeShadowCurrent(
            &previous_display,
            &previous_draw,
            &previous_read,
            &previous_context)) {
        if (xz_shadow.gl.DeleteBuffers &&
            xz_shadow.vbo)
            xz_shadow.gl.DeleteBuffers(
                1, &xz_shadow.vbo);
        if (xz_shadow.gl.DeleteVertexArrays &&
            xz_shadow.vao)
            xz_shadow.gl.DeleteVertexArrays(
                1, &xz_shadow.vao);
        if (xz_shadow.gl.DeleteProgram &&
            xz_shadow.program)
            xz_shadow.gl.DeleteProgram(
                xz_shadow.program);

        XzRestorePrevious(
            previous_display,
            previous_draw,
            previous_read,
            previous_context);
    }

    XzUnloadApi(&xz_shadow.gl);

    if (xz_shadow.context != EGL_NO_CONTEXT)
        eglDestroyContext(
            xz_shadow.display,
            xz_shadow.context);
    if (xz_shadow.surface != EGL_NO_SURFACE)
        eglDestroySurface(
            xz_shadow.display,
            xz_shadow.surface);

    memset(&xz_shadow, 0, sizeof(xz_shadow));
    state->initialized = 0;
    state->available = 0;
}
