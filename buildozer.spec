[app]
title = Alien Invasion
package.name = alieninvasion
package.domain = org.manuel

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 1.0

# python-for-android has a 'pygame' recipe
requirements = python3==3.11.0,pygame==2.6.0

orientation = landscape

# Android target
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33

android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE

android.archs = arm64-v8a, armeabi-v7a

# Fullscreen with no title bar
fullscreen = 1

# App icon — leave blank (pygame draws everything procedurally)
# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
