# Build Directory

The build directory is used to house all the build files and assets for your application. 

The structure is:

* bin - Output directory
* darwin - macOS specific files
* windows - Windows specific files

## macOS

The `darwin` directory holds files specific to macOS builds.
These may be customised and used as part of the build. To return these files to the default state, simply delete them and build using `task build` or `wails3 dev`.

The directory contains the following files:

- `Info.plist` - the main plist file used for macOS builds. It is used when building using `task build` or packaging using `task package`.
- `Info.dev.plist` - same as the main plist file but used when running in development mode using `wails3 dev`.
- `icons.icns` - The icon bundle generated for macOS.

## Windows

The `windows` directory contains the manifest, metadata, and installer configurations used when building for Windows.
These may be customised for your application. To return these files to the default state, simply delete them and build with `task build`.

- `icon.ico` - The icon used for the application. This is used when building with `task build`. If you wish to use a different icon, simply replace this file with your own, or regenerate it using the `appicon.png` in the build directory.
- `installer/*` - The files used to create the Windows installer. These are used when packaging using `task package`.
- `info.json` - Application details used for Windows builds. The data here will be used by the Windows installer, as well as the application itself (right click the exe -> properties -> details).
- `wails.exe.manifest` - The main application manifest file.