# utils.py
#
# Copyright 2024 Eitan Isaacson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os, signal, re, pathlib, subprocess
import gi

gi.require_version("Flatpak", "1.0")
gi.require_version("AppStream", "1.0")

from gi.repository import Flatpak, GLib, Gio, AppStream, GObject, Gtk
from langcodes import standardize_tag, Language

os.environ["FLATPAK_USER_DIR"] = str(
    pathlib.Path.home() / ".local" / "share" / "flatpak"
)


class _VoiceInstaller:
    _FLATPAK_SP = ("flatpak-spawn", "--host")

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(_VoiceInstaller, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.queue = []
        self._proc_launcher = None
        self._command_prefix = []
        if os.path.exists("/.flatpak-info"):
            try:
                self._command_prefix = ["flatpak-spawn", "--host"]
                subprocess.check_call(
                    self._command_prefix + ["which", "which"],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                )
            except:
                self._command_prefix = []

    def _pump_queue(self):
        if not self.queue:
            return
        func, args = self.queue.pop(0)
        func(*args)

    def install_voice(self, voice, cancellable):
        self.queue.append((self._do_install_voice, (voice, cancellable)))
        if len(self.queue) == 1:
            self._pump_queue()

    def _do_install_voice(self, voice, cancellable):
        if voice.status != VoiceStatus.UNINSTALLED:
            return
        voice.update_status(VoiceStatus.INSTALLING)
        task = Gio.Task.new(voice, cancellable, self._install_sync_done, None)
        task.run_in_thread(self._install_sync)

    def _install_sync(self, task, voice, task_data, cancellable):
        remote_name = voice.remote.get_name()
        voice_ref = voice.voice_component.get_bundle(AppStream.BundleKind.FLATPAK)
        args = [
            "flatpak",
            "install",
            "--noninteractive",
            remote_name,
            voice_ref.get_id(),
        ]
        installed_refs = set(
            [r.get_name() for r in voice.installation.list_installed_refs(cancellable)]
        )
        if voice.provider_component.get_id() not in installed_refs:
            provider_ref = voice.provider_component.get_bundle(
                AppStream.BundleKind.FLATPAK
            )
            args.append(provider_ref.get_id())

        print(args)
        rc = subprocess.run(self._command_prefix + args)

        self._restart_service(voice.provider_component.get_id())
        task.return_boolean(rc.returncode == 0)

    def _install_sync_done(self, voice, task, user_data):
        success = task.propagate_boolean()
        if success:
            voice.update_status(VoiceStatus.INSTALLED)
        else:
            voice.update_status(VoiceStatus.UNINSTALLED)

        self._pump_queue()

    def uninstall_voice(self, voice, cancellable):
        self.queue.append((self._do_uninstall_voice, (voice, cancellable)))
        if len(self.queue) == 1:
            self._pump_queue()

    def _do_uninstall_voice(self, voice, cancellable):
        if voice.status != VoiceStatus.INSTALLED:
            return
        voice.update_status(VoiceStatus.UNINSTALLING)
        task = Gio.Task.new(voice, cancellable, self._uninstall_sync_done, None)
        task.run_in_thread(self._uninstall_sync)

    def _uninstall_sync(self, task, voice, task_data, cancellable):
        voice_ref = voice.voice_component.get_bundle(AppStream.BundleKind.FLATPAK)
        args = ["flatpak", "uninstall", "--noninteractive", voice_ref.get_id()]

        print(args)
        rc = subprocess.run(self._command_prefix + args)

        self._restart_service(voice.provider_component.get_id())
        task.return_boolean(rc.returncode == 0)

    def _uninstall_sync_done(self, voice, task, user_data):
        success = task.propagate_boolean()
        if success:
            voice.update_status(VoiceStatus.UNINSTALLED)
        else:
            voice.update_status(VoiceStatus.INSTALLED)

        self._pump_queue()

    def _restart_service(self, service_name):
        iface = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.freedesktop.DBus",
            "/",
            "org.freedesktop.DBus",
            None,
        )
        try:
            pid = iface.GetConnectionUnixProcessID("(s)", service_name)
        except Exception as e:
            # service is not running
            pass
        else:
            rc = subprocess.run(self._command_prefix + ["kill", str(pid)])

        rc = subprocess.run(
            self._command_prefix
            + [
                "dbus-send",
                "--session",
                "--print-reply",
                f"--dest={service_name}",
                "/",
                "org.freedesktop.DBus.Peer.Ping",
            ]
        )


class VoiceStatus:
    UNINSTALLED = 0
    INSTALLING = 1
    INSTALLED = 2
    UNINSTALLING = 3


class Voice(GObject.Object):
    def __init__(
        self, installation, remote, voice_component, provider_component, status
    ):
        self._installation = installation
        self._remote = remote
        self._voice_component = voice_component
        self._provider_component = provider_component
        self._status = status
        self._langs = [
            Language.get(standardize_tag(l))
            for l in self.voice_component.get_languages()
        ]
        super().__init__()

    @GObject.Property(type=Flatpak.Installation)
    def installation(self):
        return self._installation

    @GObject.Property(type=Flatpak.Remote)
    def remote(self):
        return self._remote

    @GObject.Property(type=AppStream.Component)
    def voice_component(self):
        return self._voice_component

    @GObject.Property(type=AppStream.Component)
    def provider_component(self):
        return self._provider_component

    @GObject.Property(type=int)
    def status(self):
        return self._status

    @GObject.Property(type=GObject.TYPE_STRV)
    def language_and_region_names(self):
        lang_names = list(
            set(
                [
                    l.display_name()
                    for l in filter(lambda x: x.has_name_data(), self._langs)
                ]
            )
        )
        lang_names.sort()
        return lang_names

    @GObject.Property(type=GObject.TYPE_STRV)
    def language_names(self):
        langs = [
            Language.get(standardize_tag(l))
            for l in self.voice_component.get_languages()
        ]
        lang_names = list(
            set([l.language_name() for l in filter(lambda x: x.has_name_data(), langs)])
        )
        lang_names.sort()
        return lang_names

    @property
    def identifier(self):
        return self._voice_component.get_id()

    @property
    def name(self):
        return self._voice_component.get_name()

    @property
    def provider_name(self):
        return self._provider_component.get_name()

    def update_status(self, status):
        old_status = self._status
        self._status = status
        if old_status != status:
            self.notify("status")

    def install(self, cancellable=None):
        _VoiceInstaller().install_voice(self, cancellable)

    def uninstall(self, cancellable=None):
        _VoiceInstaller().uninstall_voice(self, cancellable)


class _VoicesFilter(Gtk.Filter):
    def __init__(self):
        super().__init__()
        self._provider = None
        self._language = None
        self._text = ""

    def set_provider(self, provider):
        self._provider = provider
        self.changed(Gtk.FilterChange.DIFFERENT)

    def set_language(self, language):
        self._language = language
        self.changed(Gtk.FilterChange.DIFFERENT)

    def set_text(self, text):
        self._text = text
        self.changed(Gtk.FilterChange.DIFFERENT)

    def _match_provider(self, voice):
        return (
            not self._provider
            or not self._provider.get_id()
            or voice.provider_component == self._provider
        )

    def _match_language(self, voice):
        return not self._language or self._language.get_string() in voice.language_names

    def _match_text(self, voice):
        tokens = [voice.name, voice.provider_name] + voice.language_and_region_names
        return not self._text or re.search(self._text, " ".join(tokens), re.IGNORECASE)

    def do_match(self, voice):
        return (
            self._match_provider(voice)
            and self._match_language(voice)
            and self._match_text(voice)
        )


class VoicesStore(Gtk.FilterListModel):
    def __init__(self):
        super().__init__()
        self._monitors = []
        self.voices_list = Gio.ListStore(item_type=Voice)
        self.providers_list = Gio.ListStore(item_type=AppStream.Component)
        self.providers_list.append(AppStream.Component(name=_("All Providers")))
        self.languages_list = Gtk.StringList()
        self.languages_list.append(_("All Languages"))
        self.set_filter(_VoicesFilter())
        self.set_model(self.voices_list)

    def populate(self):
        task = Gio.Task.new(self, None, self._list_voices_sync_done, None)
        task.run_in_thread(self._list_voices_sync)

    @GObject.Signal
    def populated(self):
        pass

    def set_provider_filter(self, provider):
        filter = self.get_filter()
        filter.set_provider(provider)

    def set_language_filter(self, position):
        filter = self.get_filter()
        if position == 0:
            filter.set_language(None)
        else:
            filter.set_language(self.languages_list.get_item(position))

    def set_text_filter(self, text):
        filter = self.get_filter()
        filter.set_text(text)

    def _list_voices_sync(self, task, source_object, task_data, cancellable):
        visited_remotes = set()
        voices = []
        for installation in [
            Flatpak.Installation.new_system(),
            Flatpak.Installation.new_user(),
        ]:
            installed_refs = set(
                [r.get_name() for r in installation.list_installed_refs(cancellable)]
            )
            monitor = installation.create_monitor(cancellable)
            monitor.connect("changed", self._on_installation_changed, installation)
            self._monitors.append(monitor)
            for remote in installation.list_remotes(cancellable):
                url = remote.get_url()
                if url in visited_remotes or remote.get_disabled():
                    continue
                visited_remotes.add(url)
                appstream_dir = remote.get_appstream_dir()
                if not appstream_dir.query_exists():
                    continue
                app_stream_file = Gio.File.new_build_filenamev(
                    [appstream_dir.get_path(), "appstream.xml.gz"]
                )
                md = AppStream.Metadata.new()
                md.set_format_style(AppStream.FormatStyle.CATALOG)
                md.parse_file(app_stream_file, 1)
                components = dict(
                    [[c.get_id(), c] for c in md.get_components().as_array()]
                )
                for component in components.values():
                    if (
                        "Speech.Provider.Voice" in component.get_id()
                        and len(component.get_extends()) == 1
                    ):
                        provider = components[component.get_extends()[0]]
                        status = (
                            VoiceStatus.INSTALLED
                            if component.get_id() in installed_refs
                            else VoiceStatus.UNINSTALLED
                        )
                        voices.append(
                            Voice(installation, remote, component, provider, status)
                        )
        task.return_value(voices)

    def _list_voices_sync_done(self, source, task, user_data):
        _, voices = task.propagate_value()

        providers = list(
            dict(
                [[v.provider_component.get_id(), v.provider_component] for v in voices]
            ).values()
        )

        languages = list(set([lang for v in voices for lang in v.language_names]))
        languages.sort()

        self.providers_list.splice(1, 0, providers)
        self.languages_list.splice(1, 0, languages)
        self.voices_list.splice(0, 0, voices)

        self.emit("populated")

    def _on_installation_changed(
        self, monitor, file, other_file, evt_type, installation
    ):
        installed_refs = set(
            [r.get_name() for r in installation.list_installed_refs(None)]
        )
        for voice in self:
            if (
                voice._installation == installation
                and voice._status != VoiceStatus.INSTALLING
            ):
                status = (
                    VoiceStatus.INSTALLED
                    if voice.identifier in installed_refs
                    else VoiceStatus.UNINSTALLED
                )
                voice.update_status(status)


if __name__ == "__main__":
    loop = GLib.MainLoop()

    def _cb(model, pos, removed, added):
        print(added)
        # loop.quit()

    voices = VoicesStore()
    voices.connect("items-changed", _cb)
    voices.populate()
    loop.run()
