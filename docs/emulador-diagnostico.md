# Diagnostico do emulador

- run: `43084523378`
- commit: `a8db4a4039b06002a888127b831bc46109ad7532`
- quando: 2026-11-11T19:16:32Z

## Home.png (imagem, ver artefato)

## kodi-logcat.txt
```
689  4028 W Kodi    : 2026-11-11 19:14:50.784 T:4028  warning <general>: JSONRPC: Could not parse type "Setting.Details.SettingList"
11-11 19:14:50.818  2689  4028 I Kodi    : 2026-11-11 19:14:50.818 T:4028     info <general>: JSONRPC: Adding type "Setting.Details.SettingList" to list of incomplete definitions (waiting for "Setting.Details.Setting")
11-11 19:14:50.849  2689  4028 I Kodi    : 2026-11-11 19:14:50.849 T:4028     info <general>: JSONRPC: Resolving incomplete types/methods referencing Setting.Details.Setting
11-11 19:14:53.530  2689  4028 I Kodi    : 2026-11-11 19:14:53.530 T:4028     info <general>: JSONRPC v13.5.0: Successfully initialized
11-11 19:14:54.426  2689  4028 I Kodi    : 2026-11-11 19:14:54.425 T:4028     info <general>: CPeripheralBusAndroid: scanning for input devices...
11-11 19:14:54.833  2689  4028 I Kodi    : 2026-11-11 19:14:54.832 T:4028     info <general>: Register - new keyboard device registered on application->keyboard: Keyboard (0000:0000)
11-11 19:14:54.865  2689  4028 I Kodi    : 2026-11-11 19:14:54.865 T:4028     info <general>: Register - new mouse device registered on application->mouse: Mouse (0000:0000)
11-11 19:14:55.690  2689  4028 I Kodi    : 2026-11-11 19:14:55.690 T:4028     info <general>: Loading player core factory settings from special://xbmc/system/playercorefactory.xml.
11-11 19:14:55.776  2689  4028 I Kodi    : 2026-11-11 19:14:55.776 T:4028     info <general>: Loaded playercorefactory configuration
11-11 19:14:55.780  2689  4028 I Kodi    : 2026-11-11 19:14:55.780 T:4028     info <general>: Loading player core factory settings from special://masterprofile/playercorefactory.xml.
11-11 19:14:55.782  2689  4028 I Kodi    : 2026-11-11 19:14:55.782 T:4028     info <general>: special://masterprofile/playercorefactory.xml does not exist. Skipping.
11-11 19:14:55.788  2689  4028 I Kodi    : 2026-11-11 19:14:55.788 T:4028     info <general>: removing tempfiles
11-11 19:14:56.045  2689  4028 I Kodi    : 2026-11-11 19:14:56.045 T:4028     info <general>: initialize done
11-11 19:14:56.050  2689  4028 I Kodi    : 2026-11-11 19:14:56.050 T:4028     info <general>: Running the application...
11-11 19:14:56.401  2689  4028 I Kodi    : 2026-11-11 19:14:56.401 T:4028     info <general>: starting zeroconf publishing
11-11 19:14:56.489  2689  4834 I Kodi    : 2026-11-11 19:14:56.488 T:4834     info <general>: ES: Starting UDP Event server on port 9777
11-11 19:14:56.539  2689  4834 I Kodi    : 2026-11-11 19:14:56.539 T:4834     info <general>: UDP: Listening on port 9777 (ipv6 : false)
11-11 19:14:56.711  2689  4028 I Kodi    : 2026-11-11 19:14:56.711 T:4028     info <general>: JSONRPC Server: Successfully initialized
11-11 19:14:56.759  2689  4028 I Kodi    : 2026-11-11 19:14:56.758 T:4028     info <general>: CWSDiscoveryListenerUDP::Start - Started
11-11 19:15:35.329  2689  5567 W Kodi    : 2026-11-11 19:15:35.328 T:5567  warning <general>: CPythonInvoker(4): Script invoked without an addon. Adding all addon modules installed to python path as fallback. This behaviour will be removed in future version.
11-11 19:15:35.483  2689  4820 E Kodi    : 2026-11-11 19:15:35.483 T:4820    error <general>: EXCEPTION Thrown (PythonToCppException) : -->Python callback/script returned the following error<--
11-11 19:15:35.483  2689  4820 E Kodi    :                                                     - NOTE: IGNORING THIS CAN LEAD TO MEMORY LEAKS!
11-11 19:15:35.483  2689  4820 E Kodi    :                                                    Error Type: <class 'subprocess.CalledProcessError'>
11-11 19:15:35.483  2689  4820 E Kodi    :                                                    Error Contents: Command '('uname', '-rs')' died with <Signals.SIGSEGV: 11>.
11-11 19:15:35.483  2689  4820 E Kodi    :                                                    Traceback (most recent call last):
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/runner.py", line 14, in <module>
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        from version_check import service  # pylint: disable=import-error
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/service.py", line 44, in <module>
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        DISTRIBUTION = distro.linux_distribution(full_distribution_name=False)[0].lower()
11-11 19:15:35.483  2689  4820 E Kodi    :                                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 123, in linux_distribution
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        return _distro.linux_distribution(full_distribution_name)
11-11 19:15:35.483  2689  4820 E Kodi    :                                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 677, in linux_distribution
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        self.name() if full_distribution_name else self.id(),
11-11 19:15:35.483  2689  4820 E Kodi    :                                                                                                   ^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 703, in id
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        distro_id = self.uname_attr('id')
11-11 19:15:35.483  2689  4820 E Kodi    :                                                                    ^^^^^^^^^^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 918, in uname_attr
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        return self._uname_info.get(attribute, '')
11-11 19:15:35.483  2689  4820 E Kodi    :                                                               ^^^^^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 553, in __get__
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        ret = obj.__dict__[self._fname] = self._f(obj)
11-11 19:15:35.483  2689  4820 E Kodi    :                                                                                          ^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 1048, in _uname_info
11-11 19:15:35.483  2689  4820 E Kodi    :                                                        stdout = subprocess.check_output(cmd, stderr=devnull)
11-11 19:15:35.483  2689  4820 E Kodi    :                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
11-11 19:15:35.483  2689  4820 E Kodi    :                                                      File "/data/user/0/org.xbmc.kodi/cache/apk/assets/python3.11/lib/python3.11/subprocess.py", line 466, in check_output
11-11 19:15:50.729  2689  4703 E Kodi    : 2026-11-11 19:15:50.729 T:4703    error <general>: Unable to find plugin plugin.video.BrazucaPlay.Matrix
11-11 19:15:50.741  2689  4705 E Kodi    : 2026-11-11 19:15:50.740 T:4705    error <general>: Unable to find plugin plugin.video.BrazucaPlay.Matrix
11-11 19:15:50.749  2689  4704 E Kodi    : 2026-11-11 19:15:50.749 T:4704    error <general>: Unable to find plugin plugin.video.BrazucaPlay.Matrix
11-11 19:15:50.762  2689  4704 E Kodi    : 2026-11-11 19:15:50.762 T:4704    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23series_menu&mode=27&name=&iconimage=&fanart=&description=
11-11 19:15:50.765  2689  4703 E Kodi    : 2026-11-11 19:15:50.765 T:4703    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23todoscanais&mode=21&name=&iconimage=&fanart=&description=
11-11 19:15:50.768  2689  4705 E Kodi    : 2026-11-11 19:15:50.768 T:4705    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23filmes_menu&mode=27&name=&iconimage=&fanart=&description=
11-11 19:15:50.912  2689  4703 E Kodi    : 2026-11-11 19:15:50.912 T:4703    error <general>: Unable to find plugin plugin.video.BrazucaPlay.Matrix
11-11 19:15:50.913  2689  4703 E Kodi    : 2026-11-11 19:15:50.913 T:4703    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23menu_canais&mode=21&name=&iconimage=&fanart=&description=
11-11 19:15:51.123  2689  4705 W Kodi    : 2026-11-11 19:15:51.123 T:4705  warning <general>: SMARTED-TV: carrossel filmes sem dados
11-11 19:15:51.136  2689  4540 E Kodi    : 2026-11-11 19:15:51.136 T:4540    error <general>: GetDirectory - Error getting plugin://plugin.video.smarted/?route=carrossel&alvo=filmes
11-11 19:15:51.162  2689  4704 W Kodi    : 2026-11-11 19:15:51.162 T:4704  warning <general>: SMARTED-TV: carrossel series sem dados
11-11 19:15:51.163  2689  4702 E Kodi    : 2026-11-11 19:15:51.163 T:4702    error <general>: GetDirectory - Error getting plugin://plugin.video.smarted/?route=carrossel&alvo=series
11-11 19:15:51.206  2689  4703 I Kodi    : 2026-11-11 19:15:51.205 T:4703     info <general>: SMARTED-TV: carrossel canais em modo favoritos
11-11 19:15:54.139  2689  4831 I Kodi    : 2026-11-11 19:15:54.138 T:4831     info <general>: ZeroconfAndroid: Kodi (10.0.2.16). now registered and active
11-11 19:15:54.139  2689  4831 I Kodi    : 2026-11-11 19:15:54.139 T:4831     info <general>: ZeroconfAndroid: Kodi (10.0.2.16). now registered and active
11-11 19:16:02.976  2689  6121 I Kodi    : 2026-11-11 19:16:02.976 T:6121     info <general>: SMARTED-TV: carrossel canais em modo favoritos
11-11 19:16:03.709  2689  5567 I Kodi    : 2026-11-11 19:16:03.708 T:5567     info <general>: SMARTED_TEST_CARROSSEL CANAIS total=1 midia=1 arte=1 menu=0
11-11 19:16:03.712  2689  5567 I Kodi    : 2026-11-11 19:16:03.712 T:5567     info <general>: SMARTED_TEST_CARROSSEL   Canal sintetico | file | image://DefaultFolder.png/
11-11 19:16:07.351  2689  6145 W Kodi    : 2026-11-11 19:16:07.351 T:6145  warning <general>: SMARTED-TV: carrossel filmes sem dados
11-11 19:16:07.353  2689  5567 E Kodi    : 2026-11-11 19:16:07.353 T:5567    error <general>: GetDirectory - Error getting plugin://plugin.video.smarted/?route=carrossel&alvo=filmes
11-11 19:16:07.357  2689  5567 E Kodi    : 2026-11-11 19:16:07.357 T:5567    error <general>: SMARTED_TEST_CARROSSEL_FAILED RuntimeError('Files.GetDirectory: Invalid params.')
```

## kodi.log
```
     info <general>: Unloaded skin
2026-11-11 19:14:43.381 T:4028     info <general>:   load skin from: /data/user/0/org.xbmc.kodi/cache/apk/assets/addons/skin.novatv/ (version: 1.0.5)
2026-11-11 19:14:43.382 T:4028     info <general>:   load fonts for skin...
2026-11-11 19:14:43.427 T:4028     info <general>: Loading skin includes from /data/user/0/org.xbmc.kodi/cache/apk/assets/addons/skin.novatv/xml/Includes.xml
2026-11-11 19:14:44.193 T:4028     info <general>: LoadFontsFromFile: Loading <fontset> with name 'Default' from '/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/skin.novatv/xml/Font.xml'
2026-11-11 19:14:44.461 T:4028     info <general>: LoadTimers: Trying to load skin timers from /data/user/0/org.xbmc.kodi/cache/apk/assets/addons/skin.novatv/xml/Timers.xml
2026-11-11 19:14:44.623 T:4028     info <general>:   load new skin...
2026-11-11 19:14:44.625 T:4028     info <general>: Loading custom window XMLs from skin path /data/user/0/org.xbmc.kodi/cache/apk/assets/addons/skin.novatv/xml
2026-11-11 19:14:44.798 T:4028     info <general>:   initialize new skin...
2026-11-11 19:14:44.812 T:4028     info <general>: Loading skin file: DialogBusy.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:44.948 T:4028     info <general>: Skipped 1 duplicate messages..
2026-11-11 19:14:44.947 T:4028     info <general>: Loading skin file: DialogNotification.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:45.058 T:4028     info <general>: Loading skin file: DialogVolumeBar.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:45.203 T:4028     info <general>: Loading skin file: DialogExtendedProgressBar.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:45.263 T:4028     info <general>: Loading skin file: Pointer.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:45.304 T:4028     info <general>: Loading skin file: DialogSeekBar.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:45.880 T:4028     info <general>: Loading skin file: Custom_1109_TopBarOverlay.xml, load type: LOAD_ON_GUI_INIT
2026-11-11 19:14:46.266 T:4028     info <general>: Loading resource://resource.uisounds.kodi/sounds.xml
2026-11-11 19:14:46.786 T:4028     info <general>:   skin loaded...
2026-11-11 19:14:46.827 T:4028     info <general>: Loading skin file: Startup.xml, load type: LOAD_EVERY_TIME
2026-11-11 19:14:46.870 T:4028     info <general>: Loading skin file: Home.xml, load type: KEEP_IN_MEMORY
2026-11-11 19:14:50.784 T:4028  warning <general>: JSONRPC: Could not parse type "Setting.Details.SettingList"
2026-11-11 19:14:50.818 T:4028     info <general>: JSONRPC: Adding type "Setting.Details.SettingList" to list of incomplete definitions (waiting for "Setting.Details.Setting")
2026-11-11 19:14:50.849 T:4028     info <general>: JSONRPC: Resolving incomplete types/methods referencing Setting.Details.Setting
2026-11-11 19:14:53.530 T:4028     info <general>: JSONRPC v13.5.0: Successfully initialized
2026-11-11 19:14:54.425 T:4028     info <general>: CPeripheralBusAndroid: scanning for input devices...
2026-11-11 19:14:54.832 T:4028     info <general>: Register - new keyboard device registered on application->keyboard: Keyboard (0000:0000)
2026-11-11 19:14:54.865 T:4028     info <general>: Register - new mouse device registered on application->mouse: Mouse (0000:0000)
2026-11-11 19:14:55.690 T:4028     info <general>: Loading player core factory settings from special://xbmc/system/playercorefactory.xml.
2026-11-11 19:14:55.776 T:4028     info <general>: Loaded playercorefactory configuration
2026-11-11 19:14:55.780 T:4028     info <general>: Loading player core factory settings from special://masterprofile/playercorefactory.xml.
2026-11-11 19:14:55.782 T:4028     info <general>: special://masterprofile/playercorefactory.xml does not exist. Skipping.
2026-11-11 19:14:55.788 T:4028     info <general>: removing tempfiles
2026-11-11 19:14:56.045 T:4028     info <general>: initialize done
2026-11-11 19:14:56.050 T:4028     info <general>: Running the application...
2026-11-11 19:14:56.401 T:4028     info <general>: starting zeroconf publishing
2026-11-11 19:14:56.488 T:4834     info <general>: ES: Starting UDP Event server on port 9777
2026-11-11 19:14:56.539 T:4834     info <general>: UDP: Listening on port 9777 (ipv6 : false)
2026-11-11 19:14:56.711 T:4028     info <general>: JSONRPC Server: Successfully initialized
2026-11-11 19:14:56.758 T:4028     info <general>: CWSDiscoveryListenerUDP::Start - Started
2026-11-11 19:15:35.328 T:5567  warning <general>: CPythonInvoker(4): Script invoked without an addon. Adding all addon modules installed to python path as fallback. This behaviour will be removed in future version.
2026-11-11 19:15:35.483 T:4820    error <general>: EXCEPTION Thrown (PythonToCppException) : -->Python callback/script returned the following error<--
                                                    - NOTE: IGNORING THIS CAN LEAD TO MEMORY LEAKS!
                                                   Error Type: <class 'subprocess.CalledProcessError'>
                                                   Error Contents: Command '('uname', '-rs')' died with <Signals.SIGSEGV: 11>.
                                                   Traceback (most recent call last):
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/runner.py", line 14, in <module>
                                                       from version_check import service  # pylint: disable=import-error
                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/service.py", line 44, in <module>
                                                       DISTRIBUTION = distro.linux_distribution(full_distribution_name=False)[0].lower()
                                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 123, in linux_distribution
                                                       return _distro.linux_distribution(full_distribution_name)
                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 677, in linux_distribution
                                                       self.name() if full_distribution_name else self.id(),
                                                                                                  ^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 703, in id
                                                       distro_id = self.uname_attr('id')
                                                                   ^^^^^^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 918, in uname_attr
                                                       return self._uname_info.get(attribute, '')
                                                              ^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 553, in __get__
                                                       ret = obj.__dict__[self._fname] = self._f(obj)
                                                                                         ^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/addons/service.xbmc.versioncheck/resources/lib/version_check/distro/distro.py", line 1048, in _uname_info
                                                       stdout = subprocess.check_output(cmd, stderr=devnull)
                                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/python3.11/lib/python3.11/subprocess.py", line 466, in check_output
                                                       return run(*popenargs, stdout=PIPE, timeout=timeout, check=True,
                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                     File "/data/user/0/org.xbmc.kodi/cache/apk/assets/python3.11/lib/python3.11/subprocess.py", line 571, in run
                                                       raise CalledProcessError(retcode, process.args,
                                                   subprocess.CalledProcessError: Command '('uname', '-rs')' died with <Signals.SIGSEGV: 11>.
                                                   -->End of Python script error report<--
                                                   
2026-11-11 19:15:50.729 T:4703    error <general>: Unable to find plugin plugin.video.BrazucaPlay.Matrix
2026-11-11 19:15:50.763 T:4704     info <general>: Skipped 2 duplicate messages..
2026-11-11 19:15:50.762 T:4704    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23series_menu&mode=27&name=&iconimage=&fanart=&description=
2026-11-11 19:15:50.765 T:4703    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23todoscanais&mode=21&name=&iconimage=&fanart=&description=
2026-11-11 19:15:50.768 T:4705    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23filmes_menu&mode=27&name=&iconimage=&fanart=&description=
2026-11-11 19:15:50.912 T:4703    error <general>: Unable to find plugin plugin.video.BrazucaPlay.Matrix
2026-11-11 19:15:50.913 T:4703    error <general>: GetDirectory - Error getting plugin://plugin.video.BrazucaPlay.Matrix/?url=%23menu_canais&mode=21&name=&iconimage=&fanart=&description=
2026-11-11 19:15:51.123 T:4705  warning <general>: SMARTED-TV: carrossel filmes sem dados
2026-11-11 19:15:51.136 T:4540    error <general>: GetDirectory - Error getting plugin://plugin.video.smarted/?route=carrossel&alvo=filmes
2026-11-11 19:15:51.162 T:4704  warning <general>: SMARTED-TV: carrossel series sem dados
2026-11-11 19:15:51.163 T:4702    error <general>: GetDirectory - Error getting plugin://plugin.video.smarted/?route=carrossel&alvo=series
2026-11-11 19:15:51.205 T:4703     info <general>: SMARTED-TV: carrossel canais em modo favoritos
2026-11-11 19:15:54.138 T:4831     info <general>: ZeroconfAndroid: Kodi (10.0.2.16). now registered and active
2026-11-11 19:16:02.977 T:6121     info <general>: Skipped 1 duplicate messages..
2026-11-11 19:16:02.976 T:6121     info <general>: SMARTED-TV: carrossel canais em modo favoritos
2026-11-11 19:16:03.708 T:5567     info <general>: SMARTED_TEST_CARROSSEL CANAIS total=1 midia=1 arte=1 menu=0
2026-11-11 19:16:03.712 T:5567     info <general>: SMARTED_TEST_CARROSSEL   Canal sintetico | file | image://DefaultFolder.png/
2026-11-11 19:16:07.351 T:6145  warning <general>: SMARTED-TV: carrossel filmes sem dados
2026-11-11 19:16:07.353 T:5567    error <general>: GetDirectory - Error getting plugin://plugin.video.smarted/?route=carrossel&alvo=filmes
2026-11-11 19:16:07.357 T:5567    error <general>: SMARTED_TEST_CARROSSEL_FAILED RuntimeError('Files.GetDirectory: Invalid params.')
```

## logcat.txt
```
ice_id=21 ]
I/Zygote  (  289): Process 5230 exited due to signal 9 (Killed)
V/AvrcpMediaPlayerList(  702): onActiveSessionsChanged: number of controllers: 0
I/libprocessgroup(  499): Successfully killed process cgroup uid 10142 pid 5230 in 90ms
W/system_server(  499): Long monitor contention with owner android.bg (539) at void com.android.server.am.ActivityManagerService$5.handleMessage(android.os.Message)(ActivityManagerService.java:2067) waiters=0 in android.content.Intent com.android.server.am.ActivityManagerService.registerReceiverWithFeature(android.app.IApplicationThread, java.lang.String, java.lang.String, android.content.IIntentReceiver, android.content.IntentFilter, java.lang.String, int, int) for 115ms
I/FirebaseCrashApiImpl( 6285): FirebaseCrashApiImpl created by ClassLoader ax[DexPathList[[zip file "/data/user_de/0/com.google.android.gms/app_chimera/m/00000004/DynamiteModulesC.apk"],nativeLibraryDirectories=[/data/user_de/0/com.google.android.gms/app_chimera/m/00000004/n/x86_64, /data/user_de/0/com.google.android.gms/app_chimera/m/00000004/n/arm64-v8a, /system/lib64, /system_ext/lib64]]]
I/FirebaseCrash( 6285): FirebaseCrash reporting loaded - cxy@fde825f
I/DynamiteModule( 6285): Considering local module com.google.android.gms.flags:3 and remote module com.google.android.gms.flags:3
I/DynamiteModule( 6285): Selected local version of com.google.android.gms.flags
W/DynamiteModule( 6285): Local module descriptor class for com.google.android.gms.crash not found.
I/TetheringManager( 6285): registerTetheringEventCallback:com.google.android.apps.restore
I/FirebaseCrashApiImpl( 6285): FirebaseCrash reporting API initialized
I/FirebaseCrash( 6285): FirebaseCrash reporting initialized cxy@fde825f
W/FirebaseCrashAnalytics( 6285): Unable to log event, missing Google Analytics for Firebase library
I/Fitness ( 1163): OnPackageChangedOperation got intent: Intent { act=android.intent.action.PACKAGE_CHANGED dat=package:com.google.android.youtube flg=0x5000010 cmp=com.google.android.gms/.chimera.PersistentIntentOperationService (has extras) } [CONTEXT service_id=17 ]
I/Pixelmigrate( 6191): [PhenotypeSyncHelper] Phenotype registered successfully.
V/Pixelmigrate( 6285): [PhenotypeSyncHelper] Waiting for task(s) to complete (timeout: 5000 ms).
I/Fitness ( 1163): FitCleanupIntentOperation received Intent android.intent.action.PACKAGE_CHANGED [CONTEXT service_id=17 ]
I/Icing   ( 1500): Indexing com.google.android.gms-apps from com.google.android.gms [CONTEXT service_id=21 ]
I/Icing   ( 1500): Indexing done com.google.android.gms-apps [CONTEXT service_id=21 ]
I/Fitness ( 1163): OnPackageChangedOperation got intent: Intent { act=android.intent.action.PACKAGE_CHANGED dat=package:com.android.vending flg=0x5000010 cmp=com.google.android.gms/.chimera.PersistentIntentOperationService (has extras) } [CONTEXT service_id=17 ]
I/Pixelmigrate( 6191): [PhenotypeSyncHelper] Phenotype flags updated successfully.
I/MS_Utils( 1500): version of com.google.android.apps.maps = 1043701040
D/PackageManager(  499): Instant App installer not found with android.intent.action.INSTALL_INSTANT_APP_PACKAGE
D/PackageManager(  499): Clear ephemeral installer activity
E/PhenotypeFlagCommitter( 1163): Retrieving snapshot for com.google.android.gms.beacon failed
E/PhenotypeFlagCommitter( 1163): java.util.concurrent.TimeoutException: Timed out waiting for Task
E/PhenotypeFlagCommitter( 1163): 	at auct.a(:com.google.android.gms@201817023@20.18.17 (040800-311416286):22)
E/PhenotypeFlagCommitter( 1163): 	at anen.a(:com.google.android.gms@201817023@20.18.17 (040800-311416286):23)
E/PhenotypeFlagCommitter( 1163): 	at anen.a(:com.google.android.gms@201817023@20.18.17 (040800-311416286):16)
E/PhenotypeFlagCommitter( 1163): 	at anen.a(:com.google.android.gms@201817023@20.18.17 (040800-311416286):27)
E/PhenotypeFlagCommitter( 1163): 	at rom.c(:com.google.android.gms@201817023@20.18.17 (040800-311416286):5)
E/PhenotypeFlagCommitter( 1163): 	at rom.a(:com.google.android.gms@201817023@20.18.17 (040800-311416286):3)
E/PhenotypeFlagCommitter( 1163): 	at com.google.android.gms.common.config.PhenotypeUpdateOperation.onHandleIntent(:com.google.android.gms@201817023@20.18.17 (040800-311416286):19)
E/PhenotypeFlagCommitter( 1163): 	at com.google.android.chimera.IntentOperation.onHandleIntent(:com.google.android.gms@201817023@20.18.17 (040800-311416286):2)
E/PhenotypeFlagCommitter( 1163): 	at qgf.onHandleIntent(:com.google.android.gms@201817023@20.18.17 (040800-311416286):4)
E/PhenotypeFlagCommitter( 1163): 	at cui.run(:com.google.android.gms@201817023@20.18.17 (040800-311416286):5)
E/PhenotypeFlagCommitter( 1163): 	at cuh.run(:com.google.android.gms@201817023@20.18.17 (040800-311416286):9)
E/PhenotypeFlagCommitter( 1163): 	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1167)
E/PhenotypeFlagCommitter( 1163): 	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:641)
E/PhenotypeFlagCommitter( 1163): 	at java.lang.Thread.run(Thread.java:923)
I/Auth    ( 1163): [AuthManaged,PasswordComplexityHelperImpl] Updating password complexity components state.
I/Auth    ( 1163): [AuthManaged,PasswordComplexityHelperImpl] Disabling com.google.android.gms.auth.managed.admin.DeviceAdminReceiver
I/Auth    ( 1163): [AuthManaged,PasswordComplexityHelperImpl] Disabling com.google.android.gms.auth.managed.ui.SetNewPasswordActivity
I/ActivityManager(  499): Killing 5314:com.google.android.youtube/u0a146 (adj 975): empty #17
D/ConnectivityService(  499): ConnectivityService NetworkRequestInfo binderDied(NetworkRequest [ TRACK_DEFAULT id=35, [ Capabilities: INTERNET&NOT_RESTRICTED&TRUSTED Uid: 10146 AdministratorUids: [] RequestorUid: 10146 RequestorPackageName: com.google.android.youtube] ], android.os.BinderProxy@87d8f76)
D/ConnectivityService(  499): ConnectivityService NetworkRequestInfo binderDied(NetworkRequest [ LISTEN id=36, [ Capabilities: INTERNET&NOT_RESTRICTED&TRUSTED&FOREGROUND Uid: 10146 AdministratorUids: [] RequestorUid: 10146 RequestorPackageName: com.google.android.youtube] ], android.os.BinderProxy@a703977)
D/ConnectivityService(  499): releasing NetworkRequest [ TRACK_DEFAULT id=35, [ Capabilities: INTERNET&NOT_RESTRICTED&TRUSTED Uid: 10146 AdministratorUids: [] RequestorUid: 10146 RequestorPackageName: com.google.android.youtube] ] (release request)
V/KeyguardUpdateMonitor(  720): onSubscriptionInfoChanged()
V/KeyguardUpdateMonitor(  720): SubInfo:{id=1 iccId=89014103211118510720 simSlotIndex=0 carrierId=1 displayName=T-Mobile carrierName=T-Mobile nameSource=3 iconTint=-16746133 number=+15555215554 dataRoaming=0 iconBitmap=android.graphics.Bitmap@2237228 mcc=310 mnc=260 countryIso=us isEmbedded=false nativeAccessRules=null cardString=89014103211118510720 cardId=-1 isOpportunistic=false groupUUID=null isGroupDisabled=false profileClass=-1 ehplmns=null hplmns=null subscriptionType=0 groupOwner=null carrierConfigAccessRules=null areUiccApplicationsEnabled=true}
D/Telephony( 1070): isEmergencyPreferredAccount: subId=1, activeData=1
D/Telephony( 1070): isEmergencyPreferredAccount: Device does not require preference.
I/BeaconBle( 1163): Client requested scan, settings=BleSettings [scanMode=ZERO_POWER, callbackType=ALL_MATCHES, reportDelayMillis=0, 5 filters, 1 clients, callingClientName=Nearby] [CONTEXT service_id=111 ]
I/BeaconBle( 1163): Stopping scan on delegate scanner. BT state: 12 [CONTEXT service_id=111 ]
D/BluetoothAdapter( 1163): isLeEnabled(): ON
I/Zygote  (  288): Process 5314 exited due to signal 9 (Killed)
W/PhenotypeFlagCommitter( 5120): Committing snapshot for com.google.android.projection.gearhead failed, retrying
W/PhenotypeFlagCommitter( 5120): java.util.concurrent.TimeoutException: Timed out waiting for Task
W/PhenotypeFlagCommitter( 5120): 	at com.google.android.gms.tasks.Tasks.a(SourceFile:13)
W/PhenotypeFlagCommitter( 5120): 	at com.google.android.gms.phenotype.PhenotypeFlagCommitter.a(SourceFile:12)
W/PhenotypeFlagCommitter( 5120): 	at evm.run(Unknown Source:9)
W/PhenotypeFlagCommitter( 5120): 	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1167)
W/PhenotypeFlagCommitter( 5120): 	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:641)
W/PhenotypeFlagCommitter( 5120): 	at java.lang.Thread.run(Thread.java:923)
I/libprocessgroup(  499): Successfully killed process cgroup uid 10146 pid 5314 in 136ms
I/BeaconBle( 1163): Resetting - new scanner available: true [CONTEXT service_id=111 ]
I/BeaconBle( 1163): ZERO_POWER is disabled. [CONTEXT service_id=111 ]
I/BeaconBle( 1163): 'L' hardware scan: scan stopped, no powered clients [CONTEXT service_id=111 ]
E/PhenotypeFlagCommitter( 6223): Retrieving snapshot for com.google.android.libraries.internal.growth.growthkit#com.google.android.apps.docs failed
E/PhenotypeFlagCommitter( 6223): java.util.concurrent.TimeoutException: Timed out waiting for Task
E/PhenotypeFlagCommitter( 6223): 	at kxk.a(PG:18)
E/PhenotypeFlagCommitter( 6223): 	at kph.a(PG:29)
E/PhenotypeFlagCommitter( 6223): 	at kph.a(PG:34)
E/PhenotypeFlagCommitter( 6223): 	at mox.run(Unknown Source:11)
E/PhenotypeFlagCommitter( 6223): 	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1167)
E/PhenotypeFlagCommitter( 6223): 	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:641)
E/PhenotypeFlagCommitter( 6223): 	at java.lang.Thread.run(Thread.java:923)
I/Icing   ( 1500): Indexing com.google.android.gms-apps from com.google.android.gms [CONTEXT service_id=21 ]
I/Fitness ( 1163): FitCleanupIntentOperation received Intent android.intent.action.PACKAGE_CHANGED [CONTEXT service_id=17 ]
I/Fitness ( 1163): OnPackageChangedOperation got intent: Intent { act=android.intent.action.PACKAGE_CHANGED dat=package:com.google.android.apps.maps flg=0x5000010 cmp=com.google.android.gms/.chimera.PersistentIntentOperationService (has extras) } [CONTEXT service_id=17 ]
E/PhenotypeFlagCommitter( 6223): Retrieving snapshot for com.google.android.libraries.internal.growth.growthkit#com.google.android.apps.docs failed
E/PhenotypeFlagCommitter( 6223): java.util.concurrent.TimeoutException: Timed out waiting for Task
E/PhenotypeFlagCommitter( 6223): 	at kxk.a(PG:18)
E/PhenotypeFlagCommitter( 6223): 	at kph.a(PG:29)
E/PhenotypeFlagCommitter( 6223): 	at kph.a(PG:34)
E/PhenotypeFlagCommitter( 6223): 	at mox.run(Unknown Source:11)
E/PhenotypeFlagCommitter( 6223): 	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1167)
E/PhenotypeFlagCommitter( 6223): 	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:641)
E/PhenotypeFlagCommitter( 6223): 	at java.lang.Thread.run(Thread.java:923)
E/PhenotypeFlagCommitter( 6223): Retrieving snapshot for com.google.android.libraries.internal.growth.growthkit#com.google.android.apps.docs failed
E/PhenotypeFlagCommitter( 6223): java.util.concurrent.TimeoutException: Timed out waiting for Task
E/PhenotypeFlagCommitter( 6223): 	at kxk.a(PG:18)
E/PhenotypeFlagCommitter( 6223): 	at kph.a(PG:29)
E/PhenotypeFlagCommitter( 6223): 	at kph.a(PG:34)
E/PhenotypeFlagCommitter( 6223): 	at mox.run(Unknown Source:11)
E/PhenotypeFlagCommitter( 6223): 	at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1167)
E/PhenotypeFlagCommitter( 6223): 	at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:641)
E/PhenotypeFlagCommitter( 6223): 	at java.lang.Thread.run(Thread.java:923)
I/Fitness ( 1163): FitCleanupIntentOperation received Intent android.intent.action.PACKAGE_CHANGED [CONTEXT service_id=17 ]
I/Fitness ( 1163): OnPackageChangedOperation got intent: Intent { act=android.intent.action.PACKAGE_CHANGED dat=package:com.google.android.videos flg=0x5000010 cmp=com.google.android.gms/.chimera.PersistentIntentOperationService (has extras) } [CONTEXT service_id=17 ]
I/Fitness ( 1163): FitCleanupIntentOperation received Intent android.intent.action.PACKAGE_CHANGED [CONTEXT service_id=17 ]
```

## tela-final.png (imagem, ver artefato)

