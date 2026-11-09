# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in /home/user/KODE/app/build.gradle.kts
# You can edit this file to customize which code is kept.

-keep class androidx.media3.** { *; }
-keep class com.smarted.tv.** { *; }

-dontwarn androidx.media3.**
-dontwarn com.smarted.tv.**
