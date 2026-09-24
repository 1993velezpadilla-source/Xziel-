#include <jni.h>
#include <SDL.h>
#include <SDL_system.h>

static JNIEnv *Xziel_Env(void)
{
    return (JNIEnv *)SDL_AndroidGetJNIEnv();
}

static jobject Xziel_Activity(JNIEnv *env)
{
    if (!env) return NULL;
    return SDL_AndroidGetActivity();
}

static jmethodID Xziel_Method(JNIEnv *env, jobject activity,
    const char *name, const char *signature)
{
    jclass cls;
    jmethodID method;

    if (!env || !activity) return NULL;
    cls = (*env)->GetObjectClass(env, activity);
    if (!cls) return NULL;
    method = (*env)->GetMethodID(env, cls, name, signature);
    (*env)->DeleteLocalRef(env, cls);
    return method;
}

static void Xziel_CallVoid(const char *name)
{
    JNIEnv *env = Xziel_Env();
    jobject activity = Xziel_Activity(env);
    jmethodID method = Xziel_Method(env, activity, name, "()V");

    if (method)
        (*env)->CallVoidMethod(env, activity, method);
    if (activity)
        (*env)->DeleteLocalRef(env, activity);
    if (env && (*env)->ExceptionCheck(env))
        (*env)->ExceptionClear(env);
}

static int Xziel_CallBoolean(const char *name)
{
    JNIEnv *env = Xziel_Env();
    jobject activity = Xziel_Activity(env);
    jmethodID method = Xziel_Method(env, activity, name, "()Z");
    jboolean value = JNI_FALSE;

    if (method)
        value = (*env)->CallBooleanMethod(env, activity, method);
    if (activity)
        (*env)->DeleteLocalRef(env, activity);
    if (env && (*env)->ExceptionCheck(env))
        (*env)->ExceptionClear(env);
    return value == JNI_TRUE;
}

void Xziel_Android_OpenMultiplayer(void)
{
    Xziel_CallVoid("xzielOpenMultiplayer");
}

void Xziel_Android_VoiceToggleMic(void)
{
    Xziel_CallVoid("xzielVoiceToggleMic");
}

void Xziel_Android_VoiceToggleSpeaker(void)
{
    Xziel_CallVoid("xzielVoiceToggleSpeaker");
}

void Xziel_Android_VoiceToggleMode(void)
{
    Xziel_CallVoid("xzielVoiceToggleMode");
}

int Xziel_Android_VoiceInRoom(void)
{
    return Xziel_CallBoolean("xzielVoiceInRoom");
}

int Xziel_Android_VoiceMicMuted(void)
{
    return Xziel_CallBoolean("xzielVoiceMicMuted");
}

int Xziel_Android_VoiceSpeakerMuted(void)
{
    return Xziel_CallBoolean("xzielVoiceSpeakerMuted");
}

int Xziel_Android_VoiceProximityMode(void)
{
    return Xziel_CallBoolean("xzielVoiceProximityMode");
}

void Xziel_Android_VoiceUpdatePosition(float x, float y, float z)
{
    JNIEnv *env = Xziel_Env();
    jobject activity = Xziel_Activity(env);
    jmethodID method = Xziel_Method(env, activity,
        "xzielVoiceUpdatePosition", "(FFF)V");

    if (method)
        (*env)->CallVoidMethod(env, activity, method, x, y, z);
    if (activity)
        (*env)->DeleteLocalRef(env, activity);
    if (env && (*env)->ExceptionCheck(env))
        (*env)->ExceptionClear(env);
}
