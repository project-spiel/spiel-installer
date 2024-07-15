# window.py
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

from gi.repository import Adw
from gi.repository import Gtk

from .voices_store import Voice, VoiceStatus


@Gtk.Template(resource_path="/org/project_spiel/SpielInstaller/voice_row.ui")
class VoiceRow(Adw.ActionRow):
    __gtype_name__ = "VoiceRow"

    language_label = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    btn_download = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    btn_remove = Gtk.Template.Child()

    def __init__(self, voice):
        super().__init__()
        self.voice = voice
        self.voice.connect("notify::status", self.status_changed)
        self.set_title(voice.name)
        self.set_subtitle(voice.provider_name)
        lang_names = self.voice.language_and_region_names
        self.language_label.set_label(", ".join(lang_names))
        lang_name_chunks = [", ".join(c) for c in zip(*[iter(lang_names)] * 4)]
        self.language_label.set_tooltip_text("\n".join(lang_name_chunks))
        self.update_status()

    @Gtk.Template.Callback()
    def download_clicked(self, button):
        self.voice.install(None)

    @Gtk.Template.Callback()
    def remove_clicked(self, button):
        self.voice.uninstall(None)

    def status_changed(self, voice, param):
        self.update_status()

    def update_status(self):
        status = self.voice.status
        if status == VoiceStatus.INSTALLED:
            self.stack.set_visible_child(self.btn_remove)
        elif status == VoiceStatus.INSTALLING or status == VoiceStatus.UNINSTALLING:
            self.stack.set_visible_child(self.spinner)
        elif status == VoiceStatus.UNINSTALLED:
            self.stack.set_visible_child(self.btn_download)
