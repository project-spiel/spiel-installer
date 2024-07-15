# Spiel Installer

An app to make the installation of Spiel voices easier.

It provides a view of Spiel voices available via Flatpak. When installing a voice it will also install the
speech provider it needs and refreshes any currently running speech providers so apps will have access to the
voice immediately.
It installs voices in Flatpak format, and the speech provider it depends on.


## Installation

[Install this Flatpak](http://project-spiel.org/spiel-it/spiel-installer.flatpakref)

## Build instructions

```sh
meson setup build
meson compile -C build
```

To run the app without installing:
```sh
./build/src/spiel-installer
```