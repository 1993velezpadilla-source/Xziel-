#ifndef XZ_VRIL_BRIDGE_H
#define XZ_VRIL_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

void XzVrilBridge_Init(void);
void XzVrilBridge_CapturePresentation(int source_frame);
void XzVrilBridge_Shutdown(void);
int XzVrilBridge_SelfTest(void);

#ifdef __cplusplus
}
#endif

#endif
