# Top-level NDK build. Each dependency lives under app/jni after
# scripts/prepare_android.sh creates the generated Android project.

# Keep SDL_mixer focused on the formats NZ:P actually needs and avoid pulling
# optional external codec trees into the first native port.
SUPPORT_WAV := true
SUPPORT_FLAC_DRFLAC := true
SUPPORT_FLAC_LIBFLAC := false
SUPPORT_OGG_STB := true
SUPPORT_OGG := false
SUPPORT_MP3_MINIMP3 := true
SUPPORT_MP3_MPG123 := false
SUPPORT_WAVPACK := false
SUPPORT_GME := false
SUPPORT_MOD_XMP := false
SUPPORT_MID_TIMIDITY := false

include $(call all-subdir-makefiles)
