[app]
title = Alien Invasion
package.name = alieninvasion
package.domain = org.manuel

source.dir = .
source.include_exts = py,json

version = 1.0

p4a.bootstrap = sdl2

# hostpython3 must match python3 exactly or p4a refuses to build
requirements = python3==3.10.14,hostpython3==3.10.14,pygame==2.1.2

orientation = landscape

android.api = 35
android.minapi = 21
android.accept_sdk_license = True
android.build_tools_version = 34.0.0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE

android.archs = arm64-v8a

fullscreen = 1

android.keystore = release.jks
android.keystore_password = AlienInvasion2024!
android.keyalias = alieninvasion
android.keyalias_password = AlienInvasion2024!

[buildozer]
log_level = 2
warn_on_root = 1
