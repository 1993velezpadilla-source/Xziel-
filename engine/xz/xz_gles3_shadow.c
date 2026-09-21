#include "xz_gles3_shadow.h"
#include "xz_shadow_packets.h"

#include <EGL/egl.h>
#include <GLES3/gl3.h>

#include <dlfcn.h>
#include <stddef.h>
#include <string.h>

#ifndef EGL_OPENGL_ES3_BIT_KHR
#define EGL_OPENGL_ES3_BIT_KHR 0x00000040
#endif

#define XZ_SHADOW_WIDTH 32
#define XZ_SHADOW_HEIGHT 32
#define XZ_SHADOW_PIXEL_BYTES \
    (XZ_SHADOW_WIDTH * XZ_SHADOW_HEIGHT * 4)

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
typedef void (*XzGlUseProgramFn)(GLuint);
typedef void (*XzGlGenVertexArraysFn)(GLsizei, GLuint *);
typedef void (*XzGlBindVertexArrayFn)(GLuint);
typedef void (*XzGlDeleteVertexArraysFn)(GLsizei, const GLuint *);
typedef void (*XzGlGenBuffersFn)(GLsizei, GLuint *);
typedef void (*XzGlBindBufferFn)(GLenum, GLuint);
typedef void (*XzGlBufferDataFn)(
    GLenum, GLsizeiptr, const void *, GLenum);
typedef void (*XzGlBufferSubDataFn)(
    GLenum, GLintptr, GLsizeiptr, const void *);
typedef void (*XzGlDeleteBuffersFn)(GLsizei, const GLuint *);
typedef void (*XzGlEnableVertexAttribArrayFn)(GLuint);
typedef void (*XzGlVertexAttribPointerFn)(
    GLuint, GLint, GLenum, GLboolean, GLsizei, const void *);
typedef void (*XzGlVertexAttribDivisorFn)(GLuint, GLuint);
typedef void (*XzGlViewportFn)(GLint, GLint, GLsizei, GLsizei);
typedef void (*XzGlClearColorFn)(GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (*XzGlClearFn)(GLbitfield);
typedef void (*XzGlDrawArraysInstancedFn)(
    GLenum, GLint, GLsizei, GLsizei);
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
    XzGlUseProgramFn UseProgram;

    XzGlGenVertexArraysFn GenVertexArrays;
    XzGlBindVertexArrayFn BindVertexArray;
    XzGlDeleteVertexArraysFn DeleteVertexArrays;

    XzGlGenBuffersFn GenBuffers;
    XzGlBindBufferFn BindBuffer;
    XzGlBufferDataFn BufferData;
    XzGlBufferSubDataFn BufferSubData;
    XzGlDeleteBuffersFn DeleteBuffers;

    XzGlEnableVertexAttribArrayFn EnableVertexAttribArray;
    XzGlVertexAttribPointerFn VertexAttribPointer;
    XzGlVertexAttribDivisorFn VertexAttribDivisor;

    XzGlViewportFn Viewport;
    XzGlClearColorFn ClearColor;
    XzGlClearFn Clear;
    XzGlDrawArraysInstancedFn DrawArraysInstanced;
    XzGlReadPixelsFn ReadPixels;
    XzGlFinishFn Finish;
    XzGlGetErrorFn GetError;
} XzNativeGl;

typedef struct {
    int initialized;

    EGLDisplay display;
    EGLSurface surface;
    EGLContext context;
    EGLConfig config;

    XzNativeGl gl;

    GLuint program;
    GLuint vao;
    GLuint vertex_buffer;
    GLuint instance_buffer;

    XzShadowInstance instances[XZ_RENDER_MAX_PACKETS];
    unsigned char pixels[XZ_SHADOW_PIXEL_BYTES];
} XzGles3ShadowImpl;

static XzGles3ShadowImpl xz_shadow;

static uint32_t XzHashBytes(
    const unsigned char *bytes,
    unsigned int count)
{
    uint32_t hash = 2166136261u;
    unsigned int i;

    for (i = 0u; i < count; ++i) {
        hash ^= bytes[i];
        hash *= 16777619u;
    }

    return hash;
}

static int XzLoadNativeGl(XzNativeGl *gl)
{
#define XZ_GL_LOAD(field, symbol)                                  \
    do {                                                           \
        *(void **)(&gl->field) = dlsym(gl->library, symbol);       \
        if (!gl->field)                                            \
            return 0;                                              \
    } while (0)

    memset(gl, 0, sizeof(*gl));

    gl->library = dlopen(
        "libGLESv2.so",
        RTLD_NOW | RTLD_LOCAL);
    if (!gl->library)
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
    XZ_GL_LOAD(UseProgram, "glUseProgram");

    XZ_GL_LOAD(GenVertexArrays, "glGenVertexArrays");
    XZ_GL_LOAD(BindVertexArray, "glBindVertexArray");
    XZ_GL_LOAD(DeleteVertexArrays, "glDeleteVertexArrays");

    XZ_GL_LOAD(GenBuffers, "glGenBuffers");
    XZ_GL_LOAD(BindBuffer, "glBindBuffer");
    XZ_GL_LOAD(BufferData, "glBufferData");
    XZ_GL_LOAD(BufferSubData, "glBufferSubData");
    XZ_GL_LOAD(DeleteBuffers, "glDeleteBuffers");

    XZ_GL_LOAD(
        EnableVertexAttribArray,
        "glEnableVertexAttribArray");
    XZ_GL_LOAD(
        VertexAttribPointer,
        "glVertexAttribPointer");
    XZ_GL_LOAD(
        VertexAttribDivisor,
        "glVertexAttribDivisor");

    XZ_GL_LOAD(Viewport, "glViewport");
    XZ_GL_LOAD(ClearColor, "glClearColor");
    XZ_GL_LOAD(Clear, "glClear");
    XZ_GL_LOAD(
        DrawArraysInstanced,
        "glDrawArraysInstanced");
    XZ_GL_LOAD(ReadPixels, "glReadPixels");
    XZ_GL_LOAD(Finish, "glFinish");
    XZ_GL_LOAD(GetError, "glGetError");

#undef XZ_GL_LOAD
    return 1;
}

static void XzUnloadNativeGl(XzNativeGl *gl)
{
    if (!gl)
        return;

    if (gl->library)
        dlclose(gl->library);

    memset(gl, 0, sizeof(*gl));
}

static int XzCompileShader(
    const XzNativeGl *gl,
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
    gl->GetShaderiv(shader, GL_COMPILE_STATUS, &ok);

    if (!ok) {
        gl->DeleteShader(shader);
        return 0;
    }

    *shader_out = shader;
    return 1;
}

static int XzBuildProgram(
    XzGles3ShadowImpl *impl)
{
    static const char *vertex_source =
        "#version 300 es\n"
        "layout(location=0) in vec2 aVertex;\n"
        "layout(location=1) in vec4 aWorldMeta;\n"
        "layout(location=2) in vec4 aRenderMeta;\n"
        "out vec4 vColor;\n"
        "void main(){\n"
        "  vec2 seed=fract(abs(aWorldMeta.xy)*0.0137"
        " + vec2(aRenderMeta.z*7.1,aRenderMeta.w*11.3));\n"
        "  vec2 center=seed*1.8-0.9;\n"
        "  float size=mix(0.018,0.045,1.0-aRenderMeta.x);\n"
        "  gl_Position=vec4(center+aVertex*size,0.0,1.0);\n"
        "  vColor=vec4(0.2+0.8*aWorldMeta.w,"
        "0.2+0.8*aRenderMeta.x,"
        "0.2+0.8*aRenderMeta.y,1.0);\n"
        "}\n";
    static const char *fragment_source =
        "#version 300 es\n"
        "precision mediump float;\n"
        "in vec4 vColor;\n"
        "out vec4 outColor;\n"
        "void main(){ outColor=vColor; }\n";

    GLuint vs = 0u;
    GLuint fs = 0u;
    GLuint program = 0u;
    GLint linked = 0;

    if (!XzCompileShader(
            &impl->gl,
            GL_VERTEX_SHADER,
            vertex_source,
            &vs))
        return 0;

    if (!XzCompileShader(
            &impl->gl,
            GL_FRAGMENT_SHADER,
            fragment_source,
            &fs)) {
        impl->gl.DeleteShader(vs);
        return 0;
    }

    program = impl->gl.CreateProgram();
    if (!program) {
        impl->gl.DeleteShader(vs);
        impl->gl.DeleteShader(fs);
        return 0;
    }

    impl->gl.AttachShader(program, vs);
    impl->gl.AttachShader(program, fs);
    impl->gl.LinkProgram(program);
    impl->gl.GetProgramiv(
        program,
        GL_LINK_STATUS,
        &linked);

    impl->gl.DeleteShader(vs);
    impl->gl.DeleteShader(fs);

    if (!linked) {
        impl->gl.DeleteProgram(program);
        return 0;
    }

    impl->program = program;
    return 1;
}

static int XzRestorePrevious(
    EGLDisplay display,
    EGLSurface draw,
    EGLSurface read,
    EGLContext context)
{
    if (display == EGL_NO_DISPLAY ||
        context == EGL_NO_CONTEXT)
        return 1;

    return eglMakeCurrent(
        display,
        draw,
        read,
        context) ? 1 : 0;
}

int XzGles3Shadow_Init(XzGles3ShadowStats *stats)
{
    static const GLfloat triangle[] = {
         0.0f,  1.0f,
        -0.866f, -0.5f,
         0.866f, -0.5f
    };

    const EGLint config_attribs[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT_KHR,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    const EGLint pbuffer_attribs[] = {
        EGL_WIDTH, XZ_SHADOW_WIDTH,
        EGL_HEIGHT, XZ_SHADOW_HEIGHT,
        EGL_NONE
    };
    const EGLint context_attribs[] = {
        EGL_CONTEXT_CLIENT_VERSION, 3,
        EGL_NONE
    };

    EGLDisplay previous_display;
    EGLSurface previous_draw;
    EGLSurface previous_read;
    EGLContext previous_context;
    EGLint config_count = 0;
    EGLint egl_major = 0;
    EGLint egl_minor = 0;
    int ok = 0;

    if (!stats)
        return 0;

    memset(stats, 0, sizeof(*stats));
    memset(&xz_shadow, 0, sizeof(xz_shadow));

    stats->surface_width = XZ_SHADOW_WIDTH;
    stats->surface_height = XZ_SHADOW_HEIGHT;

    previous_display = eglGetCurrentDisplay();
    previous_draw = eglGetCurrentSurface(EGL_DRAW);
    previous_read = eglGetCurrentSurface(EGL_READ);
    previous_context = eglGetCurrentContext();

    xz_shadow.display = previous_display;
    if (xz_shadow.display == EGL_NO_DISPLAY)
        xz_shadow.display =
            eglGetDisplay(EGL_DEFAULT_DISPLAY);

    if (xz_shadow.display == EGL_NO_DISPLAY)
        goto cleanup;

    if (!eglInitialize(
            xz_shadow.display,
            &egl_major,
            &egl_minor))
        goto cleanup;

    if (!eglBindAPI(EGL_OPENGL_ES_API))
        goto cleanup;

    if (!eglChooseConfig(
            xz_shadow.display,
            config_attribs,
            &xz_shadow.config,
            1,
            &config_count) ||
        config_count < 1)
        goto cleanup;

    xz_shadow.surface = eglCreatePbufferSurface(
        xz_shadow.display,
        xz_shadow.config,
        pbuffer_attribs);
    if (xz_shadow.surface == EGL_NO_SURFACE)
        goto cleanup;

    xz_shadow.context = eglCreateContext(
        xz_shadow.display,
        xz_shadow.config,
        EGL_NO_CONTEXT,
        context_attribs);
    if (xz_shadow.context == EGL_NO_CONTEXT)
        goto cleanup;

    if (!eglMakeCurrent(
            xz_shadow.display,
            xz_shadow.surface,
            xz_shadow.surface,
            xz_shadow.context))
        goto cleanup;

    if (!XzLoadNativeGl(&xz_shadow.gl))
        goto cleanup;

    if (!XzBuildProgram(&xz_shadow))
        goto cleanup;

    xz_shadow.gl.GenVertexArrays(
        1, &xz_shadow.vao);
    xz_shadow.gl.BindVertexArray(
        xz_shadow.vao);

    xz_shadow.gl.GenBuffers(
        1, &xz_shadow.vertex_buffer);
    xz_shadow.gl.BindBuffer(
        GL_ARRAY_BUFFER,
        xz_shadow.vertex_buffer);
    xz_shadow.gl.BufferData(
        GL_ARRAY_BUFFER,
        (GLsizeiptr)sizeof(triangle),
        triangle,
        GL_STATIC_DRAW);
    xz_shadow.gl.EnableVertexAttribArray(0u);
    xz_shadow.gl.VertexAttribPointer(
        0u, 2, GL_FLOAT, GL_FALSE,
        2 * (GLsizei)sizeof(GLfloat), NULL);

    xz_shadow.gl.GenBuffers(
        1, &xz_shadow.instance_buffer);
    xz_shadow.gl.BindBuffer(
        GL_ARRAY_BUFFER,
        xz_shadow.instance_buffer);
    xz_shadow.gl.BufferData(
        GL_ARRAY_BUFFER,
        (GLsizeiptr)sizeof(xz_shadow.instances),
        NULL,
        GL_DYNAMIC_DRAW);

    xz_shadow.gl.EnableVertexAttribArray(1u);
    xz_shadow.gl.VertexAttribPointer(
        1u,
        4,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)sizeof(XzShadowInstance),
        (const void *)offsetof(
            XzShadowInstance, world_meta));
    xz_shadow.gl.VertexAttribDivisor(1u, 1u);

    xz_shadow.gl.EnableVertexAttribArray(2u);
    xz_shadow.gl.VertexAttribPointer(
        2u,
        4,
        GL_FLOAT,
        GL_FALSE,
        (GLsizei)sizeof(XzShadowInstance),
        (const void *)offsetof(
            XzShadowInstance, render_meta));
    xz_shadow.gl.VertexAttribDivisor(2u, 1u);

    xz_shadow.gl.BindVertexArray(0u);

    if (xz_shadow.gl.GetError() != GL_NO_ERROR)
        goto cleanup;

    xz_shadow.initialized = 1;
    stats->initialized = 1;
    stats->available = 1;
    ok = 1;

cleanup:
    stats->last_restore_ok = XzRestorePrevious(
        previous_display,
        previous_draw,
        previous_read,
        previous_context);

    if (!stats->last_restore_ok) {
        stats->restore_failures++;
        ok = 0;
    }

    if (!ok) {
        XzGles3Shadow_Shutdown(stats);
        return 0;
    }

    return 1;
}

int XzGles3Shadow_RenderPlan(
    XzGles3ShadowStats *stats,
    const XzRenderPlan *plan)
{
    EGLDisplay previous_display;
    EGLSurface previous_draw;
    EGLSurface previous_read;
    EGLContext previous_context;
    unsigned int count;
    GLenum error;
    int need_readback;

    if (!stats || !plan ||
        !xz_shadow.initialized ||
        !stats->available)
        return 0;

    stats->attempted_frames++;

    if (!XzRenderPlan_Validate(plan))
        return 0;

    previous_display = eglGetCurrentDisplay();
    previous_draw = eglGetCurrentSurface(EGL_DRAW);
    previous_read = eglGetCurrentSurface(EGL_READ);
    previous_context = eglGetCurrentContext();

    if (!eglMakeCurrent(
            xz_shadow.display,
            xz_shadow.surface,
            xz_shadow.surface,
            xz_shadow.context)) {
        stats->gl_failures++;
        return 0;
    }

    count = XzShadowPackets_Pack(
        plan,
        xz_shadow.instances,
        XZ_RENDER_MAX_PACKETS);

    xz_shadow.gl.Viewport(
        0, 0,
        XZ_SHADOW_WIDTH,
        XZ_SHADOW_HEIGHT);

    xz_shadow.gl.ClearColor(
        0.015f, 0.020f, 0.030f, 1.0f);
    xz_shadow.gl.Clear(GL_COLOR_BUFFER_BIT);

    xz_shadow.gl.UseProgram(xz_shadow.program);
    xz_shadow.gl.BindVertexArray(xz_shadow.vao);

    if (count > 0u) {
        xz_shadow.gl.BindBuffer(
            GL_ARRAY_BUFFER,
            xz_shadow.instance_buffer);
        xz_shadow.gl.BufferSubData(
            GL_ARRAY_BUFFER,
            0,
            (GLsizeiptr)(
                count * sizeof(XzShadowInstance)),
            xz_shadow.instances);

        xz_shadow.gl.DrawArraysInstanced(
            GL_TRIANGLES,
            0,
            3,
            (GLsizei)count);

        stats->draw_calls++;
        stats->submitted_instances += count;
    }

    need_readback =
        count > 0u &&
        (stats->rendered_frames == 0u ||
         ((stats->rendered_frames + 1u) % 60u) == 0u);

    if (need_readback) {
        xz_shadow.gl.ReadPixels(
            0, 0,
            XZ_SHADOW_WIDTH,
            XZ_SHADOW_HEIGHT,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            xz_shadow.pixels);
        xz_shadow.gl.Finish();

        stats->last_pixel_hash = XzHashBytes(
            xz_shadow.pixels,
            XZ_SHADOW_PIXEL_BYTES);
    }

    error = xz_shadow.gl.GetError();

    xz_shadow.gl.BindVertexArray(0u);

    stats->last_gl_error = (unsigned int)error;
    stats->last_instance_count = count;
    stats->last_plan_hash = plan->content_hash;

    if (error != GL_NO_ERROR)
        stats->gl_failures++;

    stats->last_restore_ok = XzRestorePrevious(
        previous_display,
        previous_draw,
        previous_read,
        previous_context);

    if (!stats->last_restore_ok)
        stats->restore_failures++;

    if (error != GL_NO_ERROR ||
        !stats->last_restore_ok)
        return 0;

    stats->rendered_frames++;
    return 1;
}

void XzGles3Shadow_Shutdown(
    XzGles3ShadowStats *stats)
{
    EGLDisplay previous_display;
    EGLSurface previous_draw;
    EGLSurface previous_read;
    EGLContext previous_context;

    if (!stats)
        return;

    if (!xz_shadow.initialized) {
        stats->initialized = 0;
        stats->available = 0;
        return;
    }

    previous_display = eglGetCurrentDisplay();
    previous_draw = eglGetCurrentSurface(EGL_DRAW);
    previous_read = eglGetCurrentSurface(EGL_READ);
    previous_context = eglGetCurrentContext();

    if (eglMakeCurrent(
            xz_shadow.display,
            xz_shadow.surface,
            xz_shadow.surface,
            xz_shadow.context)) {
        if (xz_shadow.gl.DeleteBuffers) {
            if (xz_shadow.instance_buffer)
                xz_shadow.gl.DeleteBuffers(
                    1, &xz_shadow.instance_buffer);
            if (xz_shadow.vertex_buffer)
                xz_shadow.gl.DeleteBuffers(
                    1, &xz_shadow.vertex_buffer);
        }

        if (xz_shadow.gl.DeleteVertexArrays &&
            xz_shadow.vao)
            xz_shadow.gl.DeleteVertexArrays(
                1, &xz_shadow.vao);

        if (xz_shadow.gl.DeleteProgram &&
            xz_shadow.program)
            xz_shadow.gl.DeleteProgram(
                xz_shadow.program);
    }

    XzRestorePrevious(
        previous_display,
        previous_draw,
        previous_read,
        previous_context);

    if (xz_shadow.context != EGL_NO_CONTEXT)
        eglDestroyContext(
            xz_shadow.display,
            xz_shadow.context);

    if (xz_shadow.surface != EGL_NO_SURFACE)
        eglDestroySurface(
            xz_shadow.display,
            xz_shadow.surface);

    XzUnloadNativeGl(&xz_shadow.gl);
    memset(&xz_shadow, 0, sizeof(xz_shadow));

    stats->initialized = 0;
    stats->available = 0;
}
