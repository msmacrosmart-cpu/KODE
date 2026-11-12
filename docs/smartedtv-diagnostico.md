# Diagnóstico das dependências

- run: `43215437672`
- commit: `ed6d9b2eb349f2565a542e33b71f8830933a5085`
- quando: 2026-11-12T12:11:22Z

### disco antes
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/root        73G   63G  9.8G  87% /
```
### clone
clone exit=0

  git switch -

Turn off this advice by setting config variable advice.detachedHead to false

commit: a3a448d26b8d560a65655dab2cd122994dc4e146
### bootstrap exit=0
### configure exit=0
### disco antes do make
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/root        73G   63G  9.7G  87% /
```
### make exit=0
### disco depois
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/root        73G   71G  1.7G  98% /
```

## Últimas 80 linhas do make
```
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hmac.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_cuda.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_d3d11va.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_drm.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_dxva2.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_qsv.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_mediacodec.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_opencl.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_vaapi.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_videotoolbox.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_vdpau.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/hwcontext_vulkan.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/imgutils.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/intfloat.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/intreadwrite.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/lfg.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/log.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/lzo.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/macros.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/mathematics.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/mastering_display_metadata.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/md5.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/mem.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/motion_vector.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/murmur3.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/opt.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/parseutils.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/pixdesc.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/pixelutils.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/pixfmt.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/random_seed.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/rc4.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/rational.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/replaygain.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/ripemd.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/samplefmt.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/sha.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/sha512.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/spherical.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/stereo3d.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/threadmessage.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/time.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/timecode.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/timestamp.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/tree.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/twofish.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/uuid.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/version.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/video_enc_params.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/xtea.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/tea.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/tx.h
INSTALL	tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/libavutil/film_grain_params.h
INSTALL	libavutil/avconfig.h
INSTALL	libavutil/ffversion.h
INSTALL	libavutil/libavutil.pc
make[6]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build/ffmpeg-prefix/src/ffmpeg-build'
[100%] Completed 'ffmpeg'
make[5]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
[100%] Built target ffmpeg
make[4]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
make[3]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
touch .build-aarch64-linux-android-21-debug
make -C aarch64-linux-android-21-debug/build install
make[3]: Entering directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
make[4]: Entering directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
make[5]: Entering directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
make[5]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
[100%] Built target ffmpeg
make[4]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
Install the project...
-- Install configuration: "Debug"
Done
make[3]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
touch .installed-aarch64-linux-android-21-debug
make[2]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg'
touch .installed-aarch64-linux-android-21-debug
Dependencies built successfully.
make[1]: Leaving directory '/tmp/kodi-src/tools/depends/target'
```

## Linhas de erro
```
74958:not found 
74960:not found 
74964:Checking whether sysconf(_SC_NPROC_ONLN) is available                             : not found 
74970:Checking whether to use the Darwin-specific initgroups system call                : not found 
74977:not found 
74979:not found 
74982:not found 
74984:not found 
74987:not found 
74995:getcwd takes a NULL argument                                                      : not found 
74999:not found 
75001:Checking for getspnam                                                             : not found 
75005:not found 
75014:for XFS QUOTA in <sys/quota.h>                                                    : not found 
75016:not found 
75017:Checking for member dqb_curbytes in struct dqblk                                  : not found 
75027:not found 
75034:Checking for glusterfs-api >= 4                                                   : not found 
75038:not found 
75039:Checking for glusterfs-api >= 7.6                                                 : not found 
75040:Checking for glusterfs-api >= 7.9                                                 : not found 
75041:Checking for liburing package                                                     : not found 
75051:Checking for glib-2.0                                                             : not found 
75052:Checking for 'tracker-sparql-2.0'                                                 : not found 
75053:Checking for 'tracker-sparql-1.0'                                                 : not found 
75054:Checking for 'tracker-sparql-0.16'                                                : not found 
75055:Checking for 'tracker-sparql-0.14'                                                : not found 
75069:not found 
75096:not found 
75103:not found 
75109:not found 
75110:Checking for system libtasn1 (>=3.8)                                              : not found 
75896:librpc/idl/auth.idl:128: error: Unable to determine origin of type `struct cli_credentials'
75897:librpc/idl/auth.idl:128: error: Unable to determine origin of type `struct cli_credentials'
76024:librpc/idl/winbind.idl:183: error: winbind_SamLogon: [out] argument 'validation' is not a pointer or array, skip client functions
76033:source4/librpc/idl/irpc.idl:70: error: nbtd_information: [out] argument 'info' is not a pointer or array, skip client functions
76034:source4/librpc/idl/irpc.idl:83: error: nbtd_getdcname: [out] argument 'dcname' is a pointer to type 'string', skip client functions
76035:source4/librpc/idl/irpc.idl:91: error: nbtd_proxy_wins_challenge: [out] argument 'num_addrs' is not a pointer or array, skip client functions
76036:source4/librpc/idl/irpc.idl:113: error: kdc_check_generic_kerberos: [out] argument 'generic_reply' is not a pointer or array, skip client functions
76037:source4/librpc/idl/irpc.idl:159: error: smbsrv_information: [out] argument 'info' is not a pointer or array, skip client functions
```

## Último alvo do make
```
80317:make[5]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80319:make[4]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80320:make[3]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80322:make -C aarch64-linux-android-21-debug/build install
80323:make[3]: Entering directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80324:make[4]: Entering directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80325:make[5]: Entering directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80326:make[5]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80328:make[4]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80332:make[3]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg/aarch64-linux-android-21-debug/build'
80334:make[2]: Leaving directory '/tmp/kodi-src/tools/depends/target/ffmpeg'
80337:make[1]: Leaving directory '/tmp/kodi-src/tools/depends/target'
```
