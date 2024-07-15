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

import gi

gi.require_version("AppStream", "1.0")

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import AppStream
from gi.repository import GObject

from .voices_store import VoicesStore
from .voice_row import VoiceRow


@Gtk.Template(resource_path="/org/project_spiel/SpielInstaller/window.ui")
class VoiceshopWindow(Adw.ApplicationWindow):
    __gtype_name__ = "VoiceshopWindow"

    voices_list = Gtk.Template.Child()
    providers_dropdown = Gtk.Template.Child()
    languages_dropdown = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    searchbar = Gtk.Template.Child()
    search_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vstore = VoicesStore()
        self.voices_list.bind_model(self.vstore, self._create_voice_row)

        self.providers_dropdown.set_expression(
            Gtk.PropertyExpression.new(
                AppStream.Component,
                None,
                "name",
            )
        )
        self.providers_dropdown.set_model(self.vstore.providers_list)
        self.providers_dropdown.connect("notify::selected", self._on_provider_changed)

        self.languages_dropdown.set_expression(
            Gtk.ClosureExpression.new(
                GObject.TYPE_STRING,
                lambda obj: obj.get_string(),
                None,
            )
        )
        self.languages_dropdown.set_model(self.vstore.languages_list)
        self.languages_dropdown.connect("notify::selected", self._on_languages_changed)

        self.vstore.connect("populated", self._on_vstore_populated)
        self.vstore.populate()

    def _on_provider_changed(self, dropdown, params):
        self.vstore.set_provider_filter(self.providers_dropdown.get_selected_item())

    def _on_languages_changed(self, dropdown, params):
        self.vstore.set_language_filter(self.languages_dropdown.get_selected())
        pass

    def _on_vstore_populated(self, vstore):
        self.stack.set_visible_child(self.scrolled_window)
        self.providers_dropdown.set_sensitive(True)
        self.languages_dropdown.set_sensitive(True)

    def _create_voice_row(self, voice):
        return VoiceRow(voice)

    @Gtk.Template.Callback()
    def _search_toggled(self, button):
        self.searchbar.set_search_mode(button.get_active())

    @Gtk.Template.Callback()
    def _search_changed(self, entry):
        self.vstore.set_text_filter(entry.get_text())

    def open_search(self):
        self.search_button.set_active(True)
