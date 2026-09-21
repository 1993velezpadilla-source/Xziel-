#ifndef XZ_GLES3_PROBE_H
#define XZ_GLES3_PROBE_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    XZ_GLES3_PROBE_NOT_RUN = 0,
    XZ_GLES3_PROBE_UNAVAILABLE,
    XZ_GLES3_PROBE_CONTEXT_OK,
    XZ_GLES3_PROBE_SHADER_OK
} XzGles3ProbeStatus;

typedef struct {
    XzGles3ProbeStatus status;
    int egl_major;
    int egl_minor;
    int gl_major;
    int gl_minor;
    int shader_compile_ok;
    int shader_link_ok;
    int restore_ok;
    unsigned int gl_error;
    char vendor[96];
    char renderer[128];
    char version[128];
} XzGles3ProbeResult;

void XzGles3Probe_InitResult(XzGles3ProbeResult *result);
int XzGles3Probe_Run(XzGles3ProbeResult *result);
const char *XzGles3ProbeStatus_Name(XzGles3ProbeStatus status);

#ifdef __cplusplus
}
#endif

#endif
