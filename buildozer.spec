[app]
title = Alien Invasion
package.name = alieninvasion
package.domain = org.manuel

source.dir = .
source.include_exts = py,json

version = 1.0

p4a.bootstrap = sdl2

# Let p4a pick compatible python3 version automatically; only pin pygame
requirements = python3,pygame

orientation = landscape

android.api = 33
android.minapi = 21
android.accept_sdk_license = True

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
