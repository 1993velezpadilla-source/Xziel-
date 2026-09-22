#include "xz_gles3_shadow.h"
#include "xz_gles3_resource_plan.h"
#include "xz_pass_targets.h"
#include "xz_pass_inputs.h"
#include "xz_texture_tap.h"

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
#define XZ_VERTEX_FLOATS 7u
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
typedef void (*XzGlGenFramebuffersFn)(GLsizei, GLuint *);
typedef void (*XzGlDeleteFramebuffersFn)(GLsizei, const GLuint *);
typedef void (*XzGlBindFramebufferFn)(GLenum, GLuint);
typedef void (*XzGlFramebufferTexture2DFn)(
    GLenum, GLenum, GLenum, GLuint, GLint);
typedef void (*XzGlFramebufferRenderbufferFn)(
    GLenum, GLenum, GLenum, GLuint);
typedef GLenum (*XzGlCheckFramebufferStatusFn)(GLenum);
typedef void (*XzGlGenVertexArraysFn)(GLsizei, GLuint *);
typedef void (*XzGlDeleteVertexArraysFn)(GLsizei, const GLuint *);
typedef void (*XzGlBindVertexArrayFn)(GLuint);
typedef void (*XzGlEnableVertexAttribArrayFn)(GLuint);
typedef void (*XzGlVertexAttribPointerFn)(
    GLuint, GLint, GLenum, GLboolean, GLsizei, const void *);
typedef void (*XzGlUseProgramFn)(GLuint);
typedef void (*XzGlActiveTextureFn)(GLenum);
typedef GLint (*XzGlGetUniformLocationFn)(GLuint, const GLchar *);
typedef void (*XzGlUniform1iFn)(GLint, GLint);
typedef void (*XzGlUniformMatrix4fvFn)(
    GLint, GLsizei, GLboolean, const GLfloat *);
typedef void (*XzGlViewportFn)(GLint, GLint, GLsizei, GLsizei);
typedef void (*XzGlClearColorFn)(GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (*XzGlClearFn)(GLbitfield);
typedef void (*XzGlEnableFn)(GLenum);
typedef void (*XzGlDisableFn)(GLenum);
typedef void (*XzGlBlendFuncFn)(GLenum, GLenum);
typedef void (*XzGlDepthMaskFn)(GLboolean);
typedef void (*XzGlDrawArraysFn)(GLenum, GLint, GLsizei);
typedef void (*XzGlDrawElementsFn)(
    GLenum, GLsizei, GLenum, const void *);
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

    XzGlGenFramebuffersFn GenFramebuffers;
    XzGlDeleteFramebuffersFn DeleteFramebuffers;
    XzGlBindFramebufferFn BindFramebuffer;
    XzGlFramebufferTexture2DFn FramebufferTexture2D;
    XzGlFramebufferRenderbufferFn FramebufferRenderbuffer;
    XzGlCheckFramebufferStatusFn CheckFramebufferStatus;

    XzGlGenVertexArraysFn GenVertexArrays;
    XzGlDeleteVertexArraysFn DeleteVertexArrays;
    XzGlBindVertexArrayFn BindVertexArray;
    XzGlEnableVertexAttribArrayFn EnableVertexAttribArray;
    XzGlVertexAttribPointerFn VertexAttribPointer;

    XzGlUseProgramFn UseProgram;
    XzGlActiveTextureFn ActiveTexture;
    XzGlGetUniformLocationFn GetUniformLocation;
    XzGlUniform1iFn Uniform1i;
    XzGlUniformMatrix4fvFn UniformMatrix4fv;
    XzGlViewportFn Viewport;
    XzGlClearColorFn ClearColor;
    XzGlClearFn Clear;
    XzGlEnableFn Enable;
    XzGlDisableFn Disable;
    XzGlBlendFuncFn BlendFunc;
    XzGlDepthMaskFn DepthMask;
    XzGlDrawArraysFn DrawArrays;
    XzGlDrawElementsFn DrawElements;
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
    unsigned int legacy_id;
    unsigned int width;
    unsigned int height;
    uint64_t revision;
    GLuint object;
    int alive;
} XzGles3RealTexture;

typedef struct {
    int ready;

    EGLDisplay display;
    EGLConfig config;
    EGLSurface surface;
    EGLContext context;

    EGLConfig visible_config;
    EGLContext visible_context;
    GLuint visible_vao;
    GLuint visible_fbo;
    GLuint visible_color;
    GLuint visible_depth;
    unsigned int visible_width;
    unsigned int visible_height;

    GLuint program;
    GLuint fullscreen_program;
    GLint fullscreen_input_count_loc;
    GLuint vbo;
    GLuint vao;

    GLuint real_program;
    GLint real_modelview_loc;
    GLint real_projection_loc;
    GLint real_texture_loc;
    GLuint real_vbo;
    GLuint real_ibo;
    GLuint real_vao;
    GLuint real_fallback_texture;
    XzGles3RealTexture real_textures[XZ_TEXTURE_MAX_ENTRIES];

    GLuint scratch_fbo;

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

    XZ_GL_LOAD(GenFramebuffers, "glGenFramebuffers");
    XZ_GL_LOAD(DeleteFramebuffers, "glDeleteFramebuffers");
    XZ_GL_LOAD(BindFramebuffer, "glBindFramebuffer");
    XZ_GL_LOAD(FramebufferTexture2D, "glFramebufferTexture2D");
    XZ_GL_LOAD(FramebufferRenderbuffer, "glFramebufferRenderbuffer");
    XZ_GL_LOAD(CheckFramebufferStatus, "glCheckFramebufferStatus");

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
    XZ_GL_LOAD(ActiveTexture, "glActiveTexture");
    XZ_GL_LOAD(GetUniformLocation, "glGetUniformLocation");
    XZ_GL_LOAD(Uniform1i, "glUniform1i");
    XZ_GL_LOAD(UniformMatrix4fv, "glUniformMatrix4fv");
    XZ_GL_LOAD(Viewport, "glViewport");
    XZ_GL_LOAD(ClearColor, "glClearColor");
    XZ_GL_LOAD(Clear, "glClear");
    XZ_GL_LOAD(Enable, "glEnable");
    XZ_GL_LOAD(Disable, "glDisable");
    XZ_GL_LOAD(BlendFunc, "glBlendFunc");
    XZ_GL_LOAD(DepthMask, "glDepthMask");
    XZ_GL_LOAD(DrawArrays, "glDrawArrays");
    XZ_GL_LOAD(DrawElements, "glDrawElements");
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
        "layout(location=2) in vec4 aColor;\n"
        "out vec4 vColor;\n"
        "void main(){\n"
        "  gl_Position=vec4(aPos,0.0,1.0);\n"
        "  gl_PointSize=1.0+3.0*aWeight;\n"
        "  vColor=vec4(aColor.rgb*(0.85+0.15*aWeight),aColor.a);\n"
        "}\n";

    static const char *fs_source =
        "#version 300 es\n"
        "precision mediump float;\n"
        "in vec4 vColor;\n"
        "out vec4 outColor;\n"
        "void main(){\n"
        "  outColor=vColor;\n"
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

    gl->EnableVertexAttribArray(2u);
    gl->VertexAttribPointer(
        2u,
        4,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)(XZ_VERTEX_FLOATS * sizeof(float)),
        (const void *)(uintptr_t)(3u * sizeof(float)));

    gl->BindVertexArray(0u);
    gl->BindBuffer(GL_ARRAY_BUFFER, 0u);

    gl->GenFramebuffers(1, &xz_shadow.scratch_fbo);
    if (!xz_shadow.scratch_fbo)
        return 0;

    return gl->GetError() == GL_NO_ERROR;
}

static int XzCreateRealGeometryProgram(void)
{
    static const char *vs_source =
        "#version 300 es\n"
        "layout(location=0) in vec3 aPos;\n"
        "layout(location=1) in vec2 aUV;\n"
        "uniform mat4 uModelView;\n"
        "uniform mat4 uProjection;\n"
        "out vec2 vUV;\n"
        "void main(){\n"
        "  gl_Position=uProjection*uModelView*vec4(aPos,1.0);\n"
        "  vUV=aUV;\n"
        "}\n";

    static const char *fs_source =
        "#version 300 es\n"
        "precision mediump float;\n"
        "in vec2 vUV;\n"
        "uniform sampler2D uTexture;\n"
        "out vec4 outColor;\n"
        "void main(){\n"
        "  vec4 texel=texture(uTexture,vUV);\n"
        "  if(texel.a<0.08) discard;\n"
        "  outColor=texel;\n"
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

    xz_shadow.real_program = gl->CreateProgram();
    if (!xz_shadow.real_program) {
        gl->DeleteShader(vs);
        gl->DeleteShader(fs);
        return 0;
    }

    gl->AttachShader(xz_shadow.real_program, vs);
    gl->AttachShader(xz_shadow.real_program, fs);
    gl->LinkProgram(xz_shadow.real_program);
    gl->GetProgramiv(
        xz_shadow.real_program,
        GL_LINK_STATUS,
        &linked);

    gl->DeleteShader(vs);
    gl->DeleteShader(fs);

    if (!linked)
        return 0;

    xz_shadow.real_modelview_loc =
        gl->GetUniformLocation(
            xz_shadow.real_program,
            "uModelView");
    xz_shadow.real_projection_loc =
        gl->GetUniformLocation(
            xz_shadow.real_program,
            "uProjection");
    xz_shadow.real_texture_loc =
        gl->GetUniformLocation(
            xz_shadow.real_program,
            "uTexture");

    if (xz_shadow.real_modelview_loc < 0 ||
        xz_shadow.real_projection_loc < 0 ||
        xz_shadow.real_texture_loc < 0)
        return 0;

    gl->UseProgram(xz_shadow.real_program);
    gl->Uniform1i(xz_shadow.real_texture_loc, 0);
    gl->UseProgram(0u);

    gl->GenVertexArrays(1, &xz_shadow.real_vao);
    gl->BindVertexArray(xz_shadow.real_vao);

    gl->GenBuffers(1, &xz_shadow.real_vbo);
    gl->BindBuffer(
        GL_ARRAY_BUFFER,
        xz_shadow.real_vbo);
    gl->BufferData(
        GL_ARRAY_BUFFER,
        (GLsizeiptr)(
            XZ_GEOMETRY_MAX_VERTICES *
            sizeof(XzGeometryVertex)),
        NULL,
        GL_STREAM_DRAW);

    gl->GenBuffers(1, &xz_shadow.real_ibo);
    gl->BindBuffer(
        GL_ELEMENT_ARRAY_BUFFER,
        xz_shadow.real_ibo);
    gl->BufferData(
        GL_ELEMENT_ARRAY_BUFFER,
        (GLsizeiptr)(
            XZ_GEOMETRY_MAX_INDICES *
            sizeof(uint32_t)),
        NULL,
        GL_STREAM_DRAW);

    gl->EnableVertexAttribArray(0u);
    gl->VertexAttribPointer(
        0u,
        3,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)sizeof(XzGeometryVertex),
        (const void *)0);

    gl->EnableVertexAttribArray(1u);
    gl->VertexAttribPointer(
        1u,
        2,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)sizeof(XzGeometryVertex),
        (const void *)(uintptr_t)(
            3u * sizeof(float)));

    gl->BindVertexArray(0u);
    gl->BindBuffer(GL_ARRAY_BUFFER, 0u);
    gl->BindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0u);

    {
        static const unsigned char fallback_rgba[4] = {
            255u, 0u, 255u, 255u
        };

        gl->GenTextures(
            1, &xz_shadow.real_fallback_texture);
        if (!xz_shadow.real_fallback_texture)
            return 0;

        gl->ActiveTexture(GL_TEXTURE0);
        gl->BindTexture(
            GL_TEXTURE_2D,
            xz_shadow.real_fallback_texture);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MIN_FILTER,
            GL_NEAREST);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MAG_FILTER,
            GL_NEAREST);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_S,
            GL_REPEAT);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_T,
            GL_REPEAT);
        gl->TexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            1,
            1,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            fallback_rgba);
        gl->BindTexture(GL_TEXTURE_2D, 0u);
    }

    return gl->GetError() == GL_NO_ERROR;
}

static XzGles3RealTexture *XzFindRealTexture(
    unsigned int legacy_id)
{
    unsigned int i;

    for (i = 0u; i < XZ_TEXTURE_MAX_ENTRIES; ++i) {
        if (xz_shadow.real_textures[i].alive &&
            xz_shadow.real_textures[i].legacy_id ==
                legacy_id)
            return &xz_shadow.real_textures[i];
    }

    return NULL;
}

static XzGles3RealTexture *XzFindFreeRealTexture(void)
{
    unsigned int i;

    for (i = 0u; i < XZ_TEXTURE_MAX_ENTRIES; ++i) {
        if (!xz_shadow.real_textures[i].alive)
            return &xz_shadow.real_textures[i];
    }

    return NULL;
}

static int XzBindRealTexture(
    XzGles3ShadowState *state,
    int legacy_texture_id,
    int *has_real_texture)
{
    XzNativeGles3Api *gl = &xz_shadow.gl;
    XzTextureSnapshot snapshot;
    XzGles3RealTexture *cached;
    GLenum error;
    int created = 0;

    if (has_real_texture)
        *has_real_texture = 0;

    gl->ActiveTexture(GL_TEXTURE0);

    if (legacy_texture_id <= 0 ||
        !XzTextureTap_Resolve(
            (unsigned int)legacy_texture_id,
            &snapshot)) {
        state->real_texture_misses++;
        gl->BindTexture(
            GL_TEXTURE_2D,
            xz_shadow.real_fallback_texture);
        return gl->GetError() == GL_NO_ERROR;
    }

    cached = XzFindRealTexture(snapshot.legacy_id);
    if (!cached) {
        cached = XzFindFreeRealTexture();
        if (!cached) {
            state->real_texture_failures++;
            return 0;
        }

        memset(cached, 0, sizeof(*cached));
        gl->GenTextures(1, &cached->object);
        if (!cached->object) {
            state->real_texture_failures++;
            return 0;
        }

        cached->legacy_id = snapshot.legacy_id;
        cached->alive = 1;
        created = 1;
    }

    gl->BindTexture(GL_TEXTURE_2D, cached->object);

    if (created ||
        cached->revision != snapshot.revision ||
        cached->width != snapshot.width ||
        cached->height != snapshot.height) {
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MIN_FILTER,
            GL_LINEAR);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MAG_FILTER,
            GL_LINEAR);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_S,
            GL_REPEAT);
        gl->TexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_T,
            GL_REPEAT);
        gl->TexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            (GLsizei)snapshot.width,
            (GLsizei)snapshot.height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            snapshot.rgba);

        error = gl->GetError();
        if (error != GL_NO_ERROR) {
            state->real_texture_failures++;
            if (created) {
                gl->DeleteTextures(
                    1, &cached->object);
                memset(cached, 0, sizeof(*cached));
            }
            if (state->last_gl_error == 0u)
                state->last_gl_error =
                    (unsigned int)error;
            return 0;
        }

        cached->width = snapshot.width;
        cached->height = snapshot.height;
        cached->revision = snapshot.revision;

        state->real_texture_uploads++;
        state->real_texture_bytes +=
            (uint64_t)snapshot.bytes;
    }

    state->real_texture_binds++;
    if (has_real_texture)
        *has_real_texture = 1;

    return 1;
}

static void XzDestroyRealTextures(void)
{
    XzNativeGles3Api *gl = &xz_shadow.gl;
    unsigned int i;

    for (i = 0u; i < XZ_TEXTURE_MAX_ENTRIES; ++i) {
        XzGles3RealTexture *cached =
            &xz_shadow.real_textures[i];

        if (cached->alive && cached->object)
            gl->DeleteTextures(1, &cached->object);

        memset(cached, 0, sizeof(*cached));
    }

    if (xz_shadow.real_fallback_texture) {
        gl->DeleteTextures(
            1, &xz_shadow.real_fallback_texture);
        xz_shadow.real_fallback_texture = 0u;
    }
}

static int XzDrawRealGeometry(
    XzGles3ShadowState *state,
    const XzGeometryFrame *geometry)
{
    XzNativeGles3Api *gl = &xz_shadow.gl;
    unsigned int i;
    unsigned int kind_mask = 0u;
    unsigned int texture_kind_mask = 0u;
    unsigned int texture_misses = 0u;
    unsigned int texture_batches = 0u;
    unsigned int drops;

    if (!state || !geometry ||
        geometry->batch_count == 0u ||
        geometry->vertex_count == 0u ||
        geometry->index_count == 0u)
        return 0;

    drops =
        geometry->dropped_batches +
        geometry->dropped_vertices +
        geometry->dropped_indices;

    state->last_geometry_batches =
        geometry->batch_count;
    state->last_geometry_vertices =
        geometry->vertex_count;
    state->last_geometry_indices =
        geometry->index_count;
    state->last_geometry_drops = drops;

    if (drops != 0u) {
        state->real_geometry_failures++;
        state->real_geometry_ready = 0;
        return 0;
    }

    if (geometry->vertex_count >
            XZ_GEOMETRY_MAX_VERTICES ||
        geometry->index_count >
            XZ_GEOMETRY_MAX_INDICES ||
        geometry->batch_count >
            XZ_GEOMETRY_MAX_BATCHES) {
        state->real_geometry_failures++;
        state->real_geometry_ready = 0;
        return 0;
    }

    state->last_texture_batches = 0u;
    state->last_texture_misses = 0u;

    gl->UseProgram(xz_shadow.real_program);
    gl->Uniform1i(xz_shadow.real_texture_loc, 0);
    gl->BindVertexArray(xz_shadow.real_vao);

    gl->BindBuffer(
        GL_ARRAY_BUFFER,
        xz_shadow.real_vbo);
    gl->BufferSubData(
        GL_ARRAY_BUFFER,
        0,
        (GLsizeiptr)(
            geometry->vertex_count *
            sizeof(XzGeometryVertex)),
        geometry->vertices);

    gl->BindBuffer(
        GL_ELEMENT_ARRAY_BUFFER,
        xz_shadow.real_ibo);
    gl->BufferSubData(
        GL_ELEMENT_ARRAY_BUFFER,
        0,
        (GLsizeiptr)(
            geometry->index_count *
            sizeof(uint32_t)),
        geometry->indices);

    if (gl->GetError() != GL_NO_ERROR) {
        state->real_geometry_failures++;
        state->real_geometry_ready = 0;
        return 0;
    }

    gl->Enable(GL_DEPTH_TEST);
    gl->Disable(GL_BLEND);
    gl->BlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    gl->DepthMask(GL_TRUE);

    for (i = 0u; i < geometry->batch_count; ++i) {
        const XzGeometryBatch *batch =
            &geometry->batches[i];

        if (batch->vertex_count == 0u ||
            batch->index_count == 0u ||
            batch->first_vertex +
                batch->vertex_count >
                geometry->vertex_count ||
            batch->first_index +
                batch->index_count >
                geometry->index_count) {
            state->real_geometry_failures++;
            state->real_geometry_ready = 0;
            return 0;
        }

        gl->UniformMatrix4fv(
            xz_shadow.real_modelview_loc,
            1,
            GL_FALSE,
            batch->modelview);
        gl->UniformMatrix4fv(
            xz_shadow.real_projection_loc,
            1,
            GL_FALSE,
            batch->projection);

        {
            int has_real_texture = 0;

            texture_batches++;
            if (!XzBindRealTexture(
                    state,
                    batch->texture_id,
                    &has_real_texture)) {
                state->real_geometry_failures++;
                state->real_geometry_ready = 0;
                state->real_textures_ready = 0;
                return 0;
            }

            if (has_real_texture) {
                if (batch->kind == XZ_GEOMETRY_ALIAS)
                    texture_kind_mask |= 1u;
                else if (batch->kind == XZ_GEOMETRY_SURFACE)
                    texture_kind_mask |= 2u;
                else if (batch->kind == XZ_GEOMETRY_SPRITE)
                    texture_kind_mask |= 4u;
            } else {
                texture_misses++;
            }
        }

        if (batch->kind == XZ_GEOMETRY_SPRITE) {
            gl->Enable(GL_BLEND);
            gl->DepthMask(GL_FALSE);
        } else {
            gl->Disable(GL_BLEND);
            gl->DepthMask(GL_TRUE);
        }

        gl->DrawElements(
            GL_TRIANGLES,
            (GLsizei)batch->index_count,
            GL_UNSIGNED_INT,
            (const void *)(uintptr_t)(
                batch->first_index *
                sizeof(uint32_t)));

        if (gl->GetError() != GL_NO_ERROR) {
            state->real_geometry_failures++;
            state->real_geometry_ready = 0;
            return 0;
        }

        if (batch->kind == XZ_GEOMETRY_ALIAS)
            kind_mask |= 1u;
        else if (batch->kind == XZ_GEOMETRY_SURFACE)
            kind_mask |= 2u;
        else if (batch->kind == XZ_GEOMETRY_SPRITE)
            kind_mask |= 4u;

        state->real_geometry_draw_calls++;
    }

    gl->DepthMask(GL_TRUE);
    gl->Disable(GL_BLEND);
    gl->Disable(GL_DEPTH_TEST);

    state->real_geometry_submissions++;
    state->real_geometry_vertices +=
        geometry->vertex_count;
    state->real_geometry_indices +=
        geometry->index_count;
    state->real_geometry_kind_mask |= kind_mask;

    state->real_geometry_ready =
        state->real_geometry_failures == 0u &&
        (state->real_geometry_kind_mask & 0x7u) == 0x7u;

    state->last_texture_batches =
        texture_batches;
    state->last_texture_misses =
        texture_misses;
    state->real_texture_kind_mask |=
        texture_kind_mask;
    state->real_textures_ready =
        state->real_texture_failures == 0u &&
        texture_batches > 0u &&
        texture_misses == 0u &&
        (state->real_texture_kind_mask & 0x7u) == 0x7u;

    return 1;
}

static int XzCreateFullscreenProgram(void)
{
    static const char *vs_source =
        "#version 300 es\n"
        "out vec2 vUV;\n"
        "void main(){\n"
        "  vec2 p;\n"
        "  if(gl_VertexID==0) p=vec2(-1.0,-1.0);\n"
        "  else if(gl_VertexID==1) p=vec2(3.0,-1.0);\n"
        "  else p=vec2(-1.0,3.0);\n"
        "  gl_Position=vec4(p,0.0,1.0);\n"
        "  vUV=p*0.5+0.5;\n"
        "}\n";

    static const char *fs_source =
        "#version 300 es\n"
        "precision mediump float;\n"
        "in vec2 vUV;\n"
        "uniform sampler2D uInput0;\n"
        "uniform sampler2D uInput1;\n"
        "uniform int uInputCount;\n"
        "out vec4 outColor;\n"
        "void main(){\n"
        "  vec4 c=texture(uInput0,vUV);\n"
        "  if(uInputCount>1){\n"
        "    float d=texture(uInput1,vUV).r;\n"
        "    c.rgb*=0.75+0.25*d;\n"
        "  }\n"
        "  outColor=c;\n"
        "}\n";

    XzNativeGles3Api *gl = &xz_shadow.gl;
    GLuint vs = 0u;
    GLuint fs = 0u;
    GLint linked = 0;
    GLint input0;
    GLint input1;

    if (!XzCompileShader(
            gl, GL_VERTEX_SHADER, vs_source, &vs))
        return 0;

    if (!XzCompileShader(
            gl, GL_FRAGMENT_SHADER, fs_source, &fs)) {
        gl->DeleteShader(vs);
        return 0;
    }

    xz_shadow.fullscreen_program =
        gl->CreateProgram();
    if (!xz_shadow.fullscreen_program) {
        gl->DeleteShader(vs);
        gl->DeleteShader(fs);
        return 0;
    }

    gl->AttachShader(
        xz_shadow.fullscreen_program, vs);
    gl->AttachShader(
        xz_shadow.fullscreen_program, fs);
    gl->LinkProgram(
        xz_shadow.fullscreen_program);
    gl->GetProgramiv(
        xz_shadow.fullscreen_program,
        GL_LINK_STATUS,
        &linked);

    gl->DeleteShader(vs);
    gl->DeleteShader(fs);

    if (!linked)
        return 0;

    input0 = gl->GetUniformLocation(
        xz_shadow.fullscreen_program,
        "uInput0");
    input1 = gl->GetUniformLocation(
        xz_shadow.fullscreen_program,
        "uInput1");
    xz_shadow.fullscreen_input_count_loc =
        gl->GetUniformLocation(
            xz_shadow.fullscreen_program,
            "uInputCount");

    if (input0 < 0 || input1 < 0 ||
        xz_shadow.fullscreen_input_count_loc < 0)
        return 0;

    gl->UseProgram(
        xz_shadow.fullscreen_program);
    gl->Uniform1i(input0, 0);
    gl->Uniform1i(input1, 1);
    gl->UseProgram(0u);

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
                XZ_G3_RESOURCE_TEXTURE_2D ||
            resource->spec.kind ==
                XZ_G3_RESOURCE_DEPTH_TEXTURE) {
            xz_shadow.gl.DeleteTextures(
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
    case XZ_G3_RESOURCE_DEPTH_TEXTURE:
        xz_shadow.gl.BindTexture(
            GL_TEXTURE_2D,
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
            state->resource_proxy_max > 0u
                ? state->resource_proxy_max
                : XZ_G3_RESOURCE_PROXY_MAX,
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
        XZ_G3_RESOURCE_DEPTH_TEXTURE) {
        GLenum depth_type =
            spec.logical_format ==
                XZ_RG_FORMAT_DEPTH16
                ? GL_UNSIGNED_SHORT
                : GL_UNSIGNED_INT;

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
            (GLint)XzDepthInternalFormat(
                spec.logical_format),
            (GLsizei)spec.physical_width,
            (GLsizei)spec.physical_height,
            0,
            GL_DEPTH_COMPONENT,
            depth_type,
            NULL);
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
                    XZ_G3_RESOURCE_TEXTURE_2D ||
                spec.kind ==
                    XZ_G3_RESOURCE_DEPTH_TEXTURE)
                xz_shadow.gl.DeleteTextures(
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

static XzGles3PhysicalResource *XzPhysicalForHandle(
    XzGpuHandle handle)
{
    unsigned int index;

    if (handle == XZ_GPU_INVALID_HANDLE)
        return NULL;

    index = XzGpuHandle_Index(handle);
    if (index >= XZ_GPU_MAX_RESOURCES)
        return NULL;

    if (!xz_shadow.physical[index].alive ||
        xz_shadow.physical[index].handle != handle)
        return NULL;

    return &xz_shadow.physical[index];
}

static int XzBindPassTarget(
    XzGles3ShadowState *state,
    const XzPassTarget *target)
{
    XzGles3PhysicalResource *color = NULL;
    XzGles3PhysicalResource *depth = NULL;
    XzGles3PhysicalResource *external = NULL;
    unsigned int width = XZ_SHADOW_WIDTH;
    unsigned int height = XZ_SHADOW_HEIGHT;
    GLbitfield clear_mask = 0u;
    GLenum status;
    GLenum error;

    if (!state || !target)
        return 0;

    if (target->external != XZ_GPU_INVALID_HANDLE) {
        external = XzPhysicalForHandle(target->external);
        if (!external ||
            external->spec.kind !=
                XZ_G3_RESOURCE_EXTERNAL_SURFACE) {
            state->framebuffer_failures++;
            return 0;
        }

        xz_shadow.gl.BindFramebuffer(
            GL_FRAMEBUFFER, 0u);
        xz_shadow.gl.Viewport(
            0, 0, XZ_SHADOW_WIDTH, XZ_SHADOW_HEIGHT);
        xz_shadow.gl.ClearColor(
            0.015f, 0.020f, 0.025f, 1.0f);
        xz_shadow.gl.Clear(GL_COLOR_BUFFER_BIT);

        state->framebuffer_binds++;
        state->framebuffer_external_passes++;

        error = xz_shadow.gl.GetError();
        if (error != GL_NO_ERROR) {
            state->framebuffer_failures++;
            return 0;
        }

        return 1;
    }

    if (target->color != XZ_GPU_INVALID_HANDLE) {
        color = XzPhysicalForHandle(target->color);
        if (!color ||
            color->spec.kind !=
                XZ_G3_RESOURCE_TEXTURE_2D) {
            state->framebuffer_failures++;
            return 0;
        }
        width = color->spec.physical_width;
        height = color->spec.physical_height;
        clear_mask |= GL_COLOR_BUFFER_BIT;
    }

    if (target->depth != XZ_GPU_INVALID_HANDLE) {
        depth = XzPhysicalForHandle(target->depth);
        if (!depth ||
            depth->spec.kind !=
                XZ_G3_RESOURCE_DEPTH_TEXTURE) {
            state->framebuffer_failures++;
            return 0;
        }

        if (!color) {
            width = depth->spec.physical_width;
            height = depth->spec.physical_height;
        } else {
            if (depth->spec.physical_width < width)
                width = depth->spec.physical_width;
            if (depth->spec.physical_height < height)
                height = depth->spec.physical_height;
        }

        clear_mask |= GL_DEPTH_BUFFER_BIT;
    }

    if (!color && !depth) {
        state->framebuffer_failures++;
        return 0;
    }

    xz_shadow.gl.BindFramebuffer(
        GL_FRAMEBUFFER,
        xz_shadow.scratch_fbo);

    xz_shadow.gl.FramebufferTexture2D(
        GL_FRAMEBUFFER,
        GL_COLOR_ATTACHMENT0,
        GL_TEXTURE_2D,
        color ? color->object : 0u,
        0);

    xz_shadow.gl.FramebufferTexture2D(
        GL_FRAMEBUFFER,
        GL_DEPTH_ATTACHMENT,
        GL_TEXTURE_2D,
        depth ? depth->object : 0u,
        0);

    state->framebuffer_binds++;
    if (color)
        state->framebuffer_color_attachments++;
    if (depth)
        state->framebuffer_depth_attachments++;

    status = xz_shadow.gl.CheckFramebufferStatus(
        GL_FRAMEBUFFER);
    state->framebuffer_checks++;

    if (status != GL_FRAMEBUFFER_COMPLETE) {
        state->framebuffer_failures++;
        return 0;
    }

    xz_shadow.gl.Viewport(
        0, 0, (GLsizei)width, (GLsizei)height);
    xz_shadow.gl.ClearColor(
        0.010f, 0.015f, 0.020f, 1.0f);
    xz_shadow.gl.Clear(clear_mask);

    error = xz_shadow.gl.GetError();
    if (error != GL_NO_ERROR) {
        state->framebuffer_failures++;
        return 0;
    }

    return 1;
}

static int XzDrawSampledPass(
    XzGles3ShadowState *state,
    const XzPassInput *input)
{
    unsigned int i;
    GLenum error;

    if (!state || !input || input->count == 0u)
        return 0;

    if (input->count > 2u) {
        state->sampled_failures++;
        return 0;
    }

    for (i = 0u; i < input->count; ++i) {
        XzGles3PhysicalResource *resource =
            XzPhysicalForHandle(input->handles[i]);

        if (!resource ||
            (resource->spec.kind !=
                 XZ_G3_RESOURCE_TEXTURE_2D &&
             resource->spec.kind !=
                 XZ_G3_RESOURCE_DEPTH_TEXTURE)) {
            state->sampled_failures++;
            return 0;
        }

        xz_shadow.gl.ActiveTexture(
            GL_TEXTURE0 + (GLenum)i);
        xz_shadow.gl.BindTexture(
            GL_TEXTURE_2D,
            resource->object);
        state->sampled_input_binds++;
    }

    xz_shadow.gl.UseProgram(
        xz_shadow.fullscreen_program);
    xz_shadow.gl.Uniform1i(
        xz_shadow.fullscreen_input_count_loc,
        (GLint)input->count);
    xz_shadow.gl.BindVertexArray(xz_shadow.vao);
    xz_shadow.gl.DrawArrays(
        GL_TRIANGLES, 0, 3);

    error = xz_shadow.gl.GetError();
    if (error != GL_NO_ERROR) {
        state->sampled_failures++;
        if (state->last_gl_error == 0u)
            state->last_gl_error =
                (unsigned int)error;
        return 0;
    }

    for (i = 0u; i < input->count; ++i) {
        xz_shadow.gl.ActiveTexture(
            GL_TEXTURE0 + (GLenum)i);
        xz_shadow.gl.BindTexture(
            GL_TEXTURE_2D, 0u);
    }
    xz_shadow.gl.ActiveTexture(GL_TEXTURE0);

    state->sampled_passes++;
    state->sampled_draws++;
    if (input->count > state->sampled_max_inputs)
        state->sampled_max_inputs = input->count;

    return 1;
}

void XzGles3Shadow_InitState(
    XzGles3ShadowState *state)
{
    if (!state)
        return;

    memset(state, 0, sizeof(*state));
    state->restore_ok = 1;
    state->quality_scale = 1.0f;
    state->resource_proxy_max =
        XZ_G3_RESOURCE_PROXY_MAX;
}

int XzGles3Shadow_SetQualityScale(
    XzGles3ShadowState *state,
    float scale)
{
    unsigned int proxy;

    if (!state)
        return 0;

    if (scale < 0.50f)
        scale = 0.50f;
    if (scale > 1.0f)
        scale = 1.0f;

    proxy = (unsigned int)(
        (float)XZ_G3_RESOURCE_PROXY_MAX *
        scale + 0.5f);

    if (proxy < 64u)
        proxy = 64u;
    if (proxy > XZ_G3_RESOURCE_PROXY_MAX)
        proxy = XZ_G3_RESOURCE_PROXY_MAX;

    if (state->quality_scale == scale &&
        state->resource_proxy_max == proxy)
        return 0;

    state->quality_scale = scale;
    state->resource_proxy_max = proxy;
    state->quality_scale_updates++;
    return 1;
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

    if (!XzCreateRealGeometryProgram())
        goto fail_current;

    if (!XzCreateFullscreenProgram())
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
    const XzRenderPlan *plan,
    XzGpuResourcePool *resources,
    const XzGeometryFrame *geometry)
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
    XzPassTargetPlan target_plan;
    XzPassInputPlan input_plan;
    const XzPassTarget *current_target = NULL;
    const XzPassInput *current_input = NULL;
    unsigned int target_cursor = 0u;
    int target_bound = 0;
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

    if (commands && !resources) {
        state->command_failures++;
        state->physical_failures++;
        state->failures++;
        return 0;
    }

    if (plan->generation == 0u ||
        (plan->generation % state->submit_stride) != 0u) {
        state->skipped_frames++;
        return 1;
    }

    memset(&target_plan, 0, sizeof(target_plan));
    memset(&input_plan, 0, sizeof(input_plan));

    if (commands &&
        !XzPassTargetPlan_Build(
            &target_plan,
            commands,
            resources)) {
        state->target_plan_failures++;
        state->command_failures++;
        state->failures++;
        return 0;
    }

    if (commands &&
        !XzPassInputPlan_Build(
            &input_plan,
            commands,
            resources)) {
        state->sampled_failures++;
        state->command_failures++;
        state->failures++;
        return 0;
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
        vertices[base + 3u] = packet->lit_rgba[0];
        vertices[base + 4u] = packet->lit_rgba[1];
        vertices[base + 5u] = packet->lit_rgba[2];
        vertices[base + 6u] = packet->lit_rgba[3];

        vertices[base + 7u] = x - delta;
        vertices[base + 8u] = y - delta;
        vertices[base + 9u] = weight;
        vertices[base + 10u] = packet->lit_rgba[0];
        vertices[base + 11u] = packet->lit_rgba[1];
        vertices[base + 12u] = packet->lit_rgba[2];
        vertices[base + 13u] = packet->lit_rgba[3];

        vertices[base + 14u] = x + delta;
        vertices[base + 15u] = y - delta;
        vertices[base + 16u] = weight;
        vertices[base + 17u] = packet->lit_rgba[0];
        vertices[base + 18u] = packet->lit_rgba[1];
        vertices[base + 19u] = packet->lit_rgba[2];
        vertices[base + 20u] = packet->lit_rgba[3];

        state->material_packets++;
        state->material_vertices += XZ_VERTICES_PER_PACKET;
        if (packet->contributing_lights > 0u)
            state->material_lit_packets++;
        state->last_material_flags = packet->material_flags;
    }

    XzEncodePlanColor(
        commands ? commands->content_hash
                 : plan->content_hash,
        expected);

    gl->BindFramebuffer(GL_FRAMEBUFFER, 0u);
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

                if (target_cursor >= target_plan.count ||
                    target_plan.passes[target_cursor].pass_index !=
                        command->a) {
                    command_ok = 0;
                    break;
                }

                current_target =
                    &target_plan.passes[target_cursor];
                current_input =
                    XzPassInputPlan_Find(
                        &input_plan,
                        command->a);
                if (!current_input) {
                    command_ok = 0;
                    break;
                }
                target_bound = 0;
                break;

            case XZ_CMD_RESOURCE_READ:
                state->resource_read_commands++;
                if (command->b != XzGpuHandle_Index(
                        (XzGpuHandle)command->c) ||
                    !XzEnsurePhysicalResource(
                        state,
                        resources,
                        (XzGpuHandle)command->c,
                        0)) {
                    command_ok = 0;
                }
                break;

            case XZ_CMD_RESOURCE_WRITE:
                state->resource_write_commands++;
                if (command->b != XzGpuHandle_Index(
                        (XzGpuHandle)command->c) ||
                    !XzEnsurePhysicalResource(
                        state,
                        resources,
                        (XzGpuHandle)command->c,
                        1)) {
                    command_ok = 0;
                }
                break;

            case XZ_CMD_DRAW_PACKETS:
                state->draw_commands++;

                if (commands && !target_bound) {
                    if (!current_target ||
                        !XzBindPassTarget(
                            state,
                            current_target)) {
                        command_ok = 0;
                        break;
                    }
                    target_bound = 1;
                }

                if (saw_draw ||
                    command->a != plan->packet_count ||
                    command->value64 !=
                        (uint64_t)plan->content_hash) {
                    command_ok = 0;
                    break;
                }

                saw_draw = 1;

                if (geometry &&
                    geometry->batch_count > 0u) {
                    if (!XzDrawRealGeometry(
                            state,
                            geometry)) {
                        command_ok = 0;
                        break;
                    }
                    state->draw_calls++;
                } else if (plan->packet_count > 0u) {
                    gl->UseProgram(xz_shadow.program);
                    gl->BindVertexArray(xz_shadow.vao);
                    gl->BindBuffer(
                        GL_ARRAY_BUFFER,
                        xz_shadow.vbo);

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

            case XZ_CMD_END_PASS:
                if (!current_target ||
                    command->a !=
                        current_target->pass_index) {
                    command_ok = 0;
                    break;
                }

                if (!target_bound) {
                    if (!XzBindPassTarget(
                            state,
                            current_target)) {
                        command_ok = 0;
                        break;
                    }
                    target_bound = 1;
                }

                if (current_input->count > 0u) {
                    if (!XzDrawSampledPass(
                            state,
                            current_input)) {
                        command_ok = 0;
                        break;
                    }
                }

                target_cursor++;
                current_target = NULL;
                current_input = NULL;
                target_bound = 0;
                break;

            case XZ_CMD_BEGIN_FRAME:
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

        if (target_cursor != target_plan.count ||
            current_target != NULL ||
            current_input != NULL)
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

    gl->BindFramebuffer(GL_FRAMEBUFFER, 0u);
    gl->Viewport(
        0, 0, XZ_SHADOW_WIDTH, XZ_SHADOW_HEIGHT);

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
        state, NULL, plan, NULL, NULL);
}

int XzGles3Shadow_SubmitCommands(
    XzGles3ShadowState *state,
    const XzCommandStream *commands,
    const XzRenderPlan *plan,
    XzGpuResourcePool *resources,
    const XzGeometryFrame *geometry)
{
    return XzGles3Shadow_SubmitInternal(
        state, commands, plan, resources, geometry);
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
        XzDestroyAllPhysicalResources(state);
        XzDestroyRealTextures();

        if (xz_shadow.gl.DeleteFramebuffers &&
            xz_shadow.scratch_fbo)
            xz_shadow.gl.DeleteFramebuffers(
                1, &xz_shadow.scratch_fbo);

        if (xz_shadow.gl.DeleteBuffers &&
            xz_shadow.vbo)
            xz_shadow.gl.DeleteBuffers(
                1, &xz_shadow.vbo);
        if (xz_shadow.gl.DeleteBuffers &&
            xz_shadow.real_vbo)
            xz_shadow.gl.DeleteBuffers(
                1, &xz_shadow.real_vbo);
        if (xz_shadow.gl.DeleteBuffers &&
            xz_shadow.real_ibo)
            xz_shadow.gl.DeleteBuffers(
                1, &xz_shadow.real_ibo);
        if (xz_shadow.gl.DeleteVertexArrays &&
            xz_shadow.vao)
            xz_shadow.gl.DeleteVertexArrays(
                1, &xz_shadow.vao);
        if (xz_shadow.gl.DeleteVertexArrays &&
            xz_shadow.real_vao)
            xz_shadow.gl.DeleteVertexArrays(
                1, &xz_shadow.real_vao);
        if (xz_shadow.gl.DeleteProgram &&
            xz_shadow.program)
            xz_shadow.gl.DeleteProgram(
                xz_shadow.program);
        if (xz_shadow.gl.DeleteProgram &&
            xz_shadow.real_program)
            xz_shadow.gl.DeleteProgram(
                xz_shadow.real_program);
        if (xz_shadow.gl.DeleteProgram &&
            xz_shadow.fullscreen_program)
            xz_shadow.gl.DeleteProgram(
                xz_shadow.fullscreen_program);

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
