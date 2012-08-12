#!/usr/bin/python
# vim:et:sw=4:sts=4

# Copyright (c) 2010, Jordan Callicoat <jordan.callicoat@rackspace.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of GPasteItIn nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Jordan Callicoat BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
import sys
import time
import select

try:
    import gtk
    import gobject
except ImportError:
    sys.exit ("This program requires python-gtk.")

try:
    import wnck
except ImportError:
    sys.exit ("This program requires python-wnck or python-gnomedesktop or gnome-python2-libwnck.")

try:
    from configobj import ConfigObj
except:
    sys.exit ("This program requires python-configobj.")

try:
    from Xlib import display, XK, X
except ImportError:
    sys.exit ("This program requires python-xlib.")

try:
    from xdg import BaseDirectory
except ImportError:
    sys.exit ("This program requires python-xdg.")



class GPasteItIn (object):

    config_path = BaseDirectory.save_config_path ("gpasteitin")
    config_file = os.path.join (config_path, "config")
    resdir      = "/usr/share/gpasteitin"

    template    = {
        "Options" : {
            "snip_color"    : "#0000FF",
            "clip_color"    : "#FF0000",
            "single_column" : False,
            "clip_size"     : 8,
            "wrap_width"    : 4,
            "initial_clip"  : True,
            "always_ontop"  : True,
            "x"             : 0,
            "y"             : 0
        },
        "Snippets" : {}
    }

    def __init__ (self):
        self.config = ConfigObj (self.config_file, write_empty_values = True)
        self.populate_config ()

        self.display     = display.Display ()
        self.screen      = wnck.screen_get_default ()
        self.clipboard   = gtk.clipboard_get ("CLIPBOARD")
        self.alt_clip    = gtk.clipboard_get ("PRIMARY")
        self.new_clip    = None
        self.our_data    = None
        self.clips       = []
        self.clips_ins   = 0
        self.pasting     = False
        self.need_paste  = False

        self.terminals = [
            "Terminal", "terminator", "lxterminal", "Yakuake",
            "guake.py", "sakura", "tilda", "ROXTerm"
        ]
        
        self.alt_terms = [
            "xterm", "mrxvt", "urxvt", "Eterm"
        ]

        if self.options["initial_clip"]:
            self.clipboard.request_text (self.on_clipboard_text)
        else:
            self.our_data = self.clipboard.wait_for_text ()
        gobject.timeout_add (500, self.fetch_clipboard_info)

        self.setup_ui ()

        gtk.main ()


    def populate_config (self):
        try:
            self.profile = self.config[self.config["profile"]]
        except KeyError:
            self.config["Default"] = self.template
            self.profile = self.config["Default"]
            self.config["profile"] = "Default"
            self.config.write ()

        try:
            self.options = self.profile["Options"]
        except KeyError:
            self.profile["Options"] = {}
            self.options = self.profile["Options"]

        try:
            self.snippets = self.profile["Snippets"]
        except KeyError:
            self.profile["Snippets"] = {}
            self.snippets = self.profile["Snippets"]

        self.options["single_column"] = self.options.as_bool ("single_column")
        self.options["clip_size"]     = self.options.as_int ("clip_size")
        self.options["wrap_width"]    = self.options.as_int ("wrap_width")
        self.options["initial_clip"]  = self.options.as_bool ("initial_clip")
        self.options["x"]             = self.options.as_int ("x")
        self.options["y"]             = self.options.as_int ("y")
        if not self.options.has_key ("always_ontop"):
            self.options["always_ontop"] = True
        else:
            self.options["always_ontop"] = self.options.as_bool ("always_ontop")


    def setup_ui (self):
        ui = gtk.Builder ()
        ui.add_from_file (os.path.join (self.get_resdir (), "gpasteitin.ui"))

        ui.connect_signals ({
            "on_delete_event"       : self.on_delete_event,
            "on_preferences_dialog" : self.on_show_preferences,
            "on_hide_preferences"   : self.on_hide_preferences,
            "on_save_preferences"   : self.on_save_preferences,
            "on_paste_stuff"        : self.on_paste_stuff,
            "on_add_item"           : self.on_add_item,
            "on_delete_item"        : self.on_delete_item,
            "on_move_down"          : self.on_move_item_down,
            "on_move_up"            : self.on_move_item_up,
            "on_key_press"          : self.on_key_press,
            "on_window_keypress"    : self.on_window_keypress,
            "on_clip_color_set"     : self.on_clip_color_set,
            "on_snip_color_set"     : self.on_snip_color_set,
            "on_column_toggled"     : self.on_column_toggled,
            "on_ontop_toggled"      : self.on_ontop_toggled,
            "on_initclip_toggled"   : self.on_initclip_toggled,
            "on_wrap_spin"          : self.on_wrap_spin,
            "on_clip_spin"          : self.on_clip_spin,
            "on_edit_done"          : self.on_edit_done,
            "on_hide_edit"          : self.on_hide_edit,
            "on_profile_new"        : self.on_profile_new,
            "on_profile_delete"     : self.on_profile_delete,
            "on_profile_activate"   : self.on_profile_activate,
            "on_configure_event"    : self.on_configure_event
        })

        self.window = ui.get_object ("MainWindow")
        self.window.set_keep_above (self.options["always_ontop"])
        self.window.move (self.options["x"], self.options["y"])

        self.pref_window    = ui.get_object ("PreferencesWindow")
        self.snippet_vbox   = ui.get_object ("SnippetInnerVbox")
        self.clip_vbox      = ui.get_object ("ClipInnerVbox")
        self.pref_hbox      = ui.get_object ("PreferencesHbox1")

        self.treeview       = ui.get_object ("PreferencesTreeview")
        self.treeview.sel   = self.treeview.get_selection ()

        self.snip_color     = ui.get_object ("SnipColorButton")
        self.clip_color     = ui.get_object ("ClipColorButton")
        self.column_check   = ui.get_object ("ColumnCheck")
        self.ontop_check    = ui.get_object ("OntopCheck")
        self.initclip_check = ui.get_object ("InitClipCheck")

        self.wrap_spin      = ui.get_object ("WrapSpinButton")
        self.clip_spin      = ui.get_object ("ClipSpinButton")

        self.edit_window    = ui.get_object ("EditWindow")
        self.edit_text      = ui.get_object ("EditTextView")

        self.profile_dialog = ui.get_object ("ProfileDialog")
        self.profile_entry  = ui.get_object ("ProfileEntry")

        self.profile_combo  = gtk.combo_box_new_text ()
        self.populate_combo_box ()
        self.profile_combo.connect ("changed", self.on_profile_changed)
        self.pref_hbox.pack_start (self.profile_combo, True, True, 0)
        self.pref_hbox.reorder_child (self.profile_combo, 0)

        self.populate_snip_buttons ()
        self.populate_clip_buttons ()

        self.setup_tree ()
        self.populate_tree ()


    def populate_combo_box (self):
        while self.profile_combo.get_active () > -1:
            self.profile_combo.remove_text (0)

        keys = self.config.keys ()
        for i, key in zip (range (len (keys)), keys):
            if key == "profile":
                continue
            self.profile_combo.append_text (key)
            if key == self.config["profile"]:
                self.profile_combo.set_active (i - 1)


    def populate_snip_buttons (self):
        for child in self.snippet_vbox.get_children ():
            if not child == self.profile_combo:
                self.snippet_vbox.remove (child)

        count = 0
        if self.options["single_column"] == True:
            hbox = self.snippet_vbox
        else:
            hbox = gtk.HBox (True)
            self.snippet_vbox.pack_start (hbox, False, False, 1)

        for key, value in self.snippets.items ():
            if (self.options["single_column"] == False and
                count > self.options["wrap_width"] - 1):
                hbox = gtk.HBox (True)
                self.snippet_vbox.pack_start (hbox, False, False, 1)
                count = 0
            button = gtk.Button (key.encode("string-escape"))
            label  = button.get_children ()[0]
            color  = gtk.gdk.color_parse (self.options["snip_color"])
            label.modify_fg (gtk.STATE_NORMAL, color)
            label.modify_fg (gtk.STATE_PRELIGHT, color)
            label.modify_fg (gtk.STATE_ACTIVE, color)
            button.set_tooltip_text (str (value)) #.decode ("string-escape"))
            button.connect ("clicked", self.on_paste_stuff)
            hbox.pack_start (button, True, True, 0)
            count += 1
        self.snippet_vbox.show_all ()


    def populate_clip_buttons (self):
        for child in self.clip_vbox.get_children ():
            self.clip_vbox.remove (child)

        count = 0
        if self.options["single_column"] == True:
            hbox = self.clip_vbox
        else:
            hbox = gtk.HBox (True)
            self.clip_vbox.pack_start (hbox, False, False, 1)

        for clip in self.clips:
            if not clip:
                continue
            if (self.options["single_column"] == False and
                count > self.options["wrap_width"] - 1):
                hbox = gtk.HBox (True)
                self.clip_vbox.pack_start (hbox, False, False, 1)
                count = 0
            clip_name = clip.encode("string-escape")
            if len (clip_name) > 15:
                clip_name = clip_name[0:15] + "..."
            button = gtk.Button (clip_name)
            button.set_use_underline (False)
            label  = button.get_children ()[0]
            color  = gtk.gdk.color_parse (self.options["clip_color"])
            label.modify_fg (gtk.STATE_NORMAL, color)
            label.modify_fg (gtk.STATE_PRELIGHT, color)
            label.modify_fg (gtk.STATE_ACTIVE, color)
            button.set_tooltip_text (clip) #.decode ("string-escape"))
            button.connect ("clicked", self.on_paste_stuff)
            hbox.pack_start (button, True, True, 0)
            count += 1
        self.clip_vbox.show_all ()


    def setup_tree (self):
        # setup model
        self.treeview.model = gtk.ListStore (str, str)
        self.treeview.set_model (self.treeview.model)
        self.treeview.cols  = [None, None]
        colwidths           = [100, 360]
        coltexts            = ["Name", "Value"]

        # create the columns
        for i in range (len (self.treeview.cols)):
            renderer = gtk.CellRendererText ()
            renderer.set_property ("editable", True)
            renderer.set_property ("xpad", 5)
            renderer.set_property ("wrap-mode", gtk.WRAP_WORD)
            renderer.set_property ("wrap-width", colwidths[i] - 10)
            renderer.connect ("editing-started", self.on_edit_started)
            renderer.connect ("edited", self.on_edit_item, i)

            # alternating column colors
#            if i % 2 == 0:
#                renderer.set_property("background", "#DEDEDE")
#            else:
#                renderer.set_property("background", "#EFEFEF")

            self.treeview.cols[i] = self.treeview.insert_column_with_attributes (
                -1, coltexts[i], renderer, text=i
            )
            self.treeview.cols[i].set_spacing (10)
            self.treeview.cols[i].set_resizable (True)
            self.treeview.cols[i].set_alignment (0.5)
            self.treeview.cols[i].set_data ("id", i)
            self.treeview.cols[i].renderer = renderer
            self.treeview.cols[i].set_min_width (colwidths[i])
            if i == 0:
                self.treeview.cols[i].set_max_width (colwidths[i])
            if i == 1:
                self.treeview.cols[i].set_expand (True)
#                self.treeview.cols[i].set_sizing (gtk.TREE_VIEW_COLUMN_GROW_ONLY)


    def populate_tree (self):
        self.treeview.model.clear ()
        for row in self.snippets.items ():
            if not row[1]:
                self.treeview.model.append ((row[0].decode ("string-escape"), ""))
            else:
                self.treeview.model.append ((row[0].decode ("string-escape"),
                                             row[1])) #.decode ("string-escape")))


    def populate_preferences (self):
        self.snip_color.set_color (gtk.gdk.color_parse (self.options["snip_color"]))
        self.clip_color.set_color (gtk.gdk.color_parse (self.options["clip_color"]))
        self.column_check.set_active (self.options["single_column"])
        self.ontop_check.set_active (self.options["always_ontop"])
        self.initclip_check.set_active (self.options["initial_clip"])
        self.clip_spin.set_value (self.options["clip_size"])
        self.wrap_spin.set_value (self.options["wrap_width"])


    #############
    # utility
    def send_paste_keypress (self):
        # TODO: configuration option for paste key-sequence?
        ctrl  = self.display.keysym_to_keycode (XK.string_to_keysym ("Control_L"))
        shift = self.display.keysym_to_keycode (XK.string_to_keysym ("Shift_L"))
        v     = self.display.keysym_to_keycode (XK.string_to_keysym ("v"))

        if self.new_clip:
            ins = self.display.keysym_to_keycode (XK.string_to_keysym ("Insert"))
            self.display.xtest_fake_input (X.KeyPress, shift)
            self.display.xtest_fake_input (X.KeyPress, ins)
            self.display.xtest_fake_input (X.KeyRelease, ins)
            self.display.xtest_fake_input (X.KeyRelease, shift)
        else:
            term = self.name in self.terminals or "bash" in self.name
            if term:
                self.display.xtest_fake_input (X.KeyPress, shift)
            self.display.xtest_fake_input (X.KeyPress, ctrl)
            self.display.xtest_fake_input (X.KeyPress, v)
            self.display.xtest_fake_input (X.KeyRelease, v)
            self.display.xtest_fake_input (X.KeyRelease, ctrl)
            if term:
                self.display.xtest_fake_input (X.KeyRelease, shift)

        self.display.sync ()

        # need to give xlib time to do it's thing as the calls are asyncronous
        if self.old_text:
            gobject.timeout_add (200, self.reset_clipboard, self.old_text)
#            self.reset_clipboard (self.old_text)
        else:
            gobject.timeout_add (200, self.clear_clipboard)
#            self.clear_clipboard ()


    def clear_clipboard (self):
        self.pasting = False
        if self.new_clip:
            self.new_clip.clear ()
        else:
            self.clipboard.clear ()
        self.new_clip = None
        return False # cancel the timout


    def reset_clipboard (self, text):
        self.pasting  = False
        self.our_data = text
        if self.new_clip:
            self.new_clip.set_text (text)
        else:
            self.clipboard.set_text (text)
        self.new_clip = None
        return False # cancel the timeout


    def get_selected_rows (self):
        rows = []
        try:
            for row in self.treeview.sel.get_selected_rows ()[1]:
                rows.append (row[0])
        except:
            pass
        return rows


    def get_first_selected_row (self):
        try:
            return self.get_selected_rows ()[0]
        except:
            return None


    def update_config (self):
        self.snippets.clear ()
        for i in range (len (self.treeview.model)):
            row = self.treeview.model[i]
            if row[0]:
                self.snippets[row[0]] = row[1]

        self.config["profile"] = self.profile_combo.get_active_text ()
        self.populate_config ()

        self.options["snip_color"]    = self.snip_color.get_color ().to_string ()
        self.options["clip_color"]    = self.clip_color.get_color ().to_string ()
        self.options["single_column"] = self.column_check.get_active ()
        self.options["always_ontop"]  = self.ontop_check.get_active ()
        self.options["initial_clip"]  = self.initclip_check.get_active ()
        self.options["wrap_width"]    = self.wrap_spin.get_value_as_int ()
        self.options["clip_size"]     = self.clip_spin.get_value_as_int ()

        self.config.write ()

        if self.options["clip_size"] < len (self.clips):
            self.clips = self.clips[0 : self.options["clip_size"]]
        
        self.window.set_keep_above (self.options["always_ontop"])


    def get_resdir (self):
        # when run without installing...
        exedir = os.path.dirname (os.path.realpath (sys.argv[0]))
        if os.path.exists (os.path.join (exedir, "gpasteitin.py")):
            path = os.path.join (os.path.dirname (exedir), "resources")
            if os.path.exists (path):
                return path
        else:
            path = os.path.join (exedir, "resources")
            if os.path.exists (path):
                return path
        # when run from install
        if os.path.exists (self.resdir):
            return self.resdir
        else:
            sys.exit("Something is really broken!\n"
                     "Cant find resources directory!\n"
                     "Reinstall the program!")


    def size_move_window (self):
#        self.window.resize (10, 10)
        return False # cancel the timeout


    def on_configure_event (self, window, event):
        self.window.resize (10, 10)
        return False # cancel the event


    #############
    # callbacks
    def on_show_preferences (self, *args):
        self.populate_tree ()
        self.populate_preferences ()
        self.pref_window.show_all ()


    def on_hide_preferences (self, *args):
        self.pref_window.hide ()
        return True # cancel the delete event


    def on_save_preferences (self, *args):
        self.pref_window.hide ()
        self.update_config ()
        self.options["x"], self.options["y"] = self.window.get_position ()
        self.config.write ()
        self.populate_snip_buttons ()
        self.populate_clip_buttons ()
        gobject.timeout_add (100, self.size_move_window)
        return True # cancel the delete event


    def on_paste_stuff (self, button, *args):
        if self.pasting:
            return
        self.pasting    = True
        self.need_paste = True
    
        new_text = button.get_tooltip_text ()
        window   = window = self.screen.get_active_window ()
        name     = window.get_application ().get_name ().split (" ", 1)[0]

        self.our_data = new_text
        self.name     = name

        if self.name in self.alt_terms:
            self.old_text = self.alt_clip.wait_for_text ()
            self.new_clip = self.alt_clip
            self.alt_clip.set_text (new_text)
        else:
            self.old_text = self.clipboard.wait_for_text ()
            self.clipboard.set_text (new_text)

#        self.send_paste_keypress ()


    def on_add_item (self, widget):
        # insert new row under selected row
#        row = self.get_first_selected_row()
#        if row == None:
#            row = 0
#        else:
#            row = row + 1

        # insert new row at bottom
        row = len (self.treeview.model)
        self.treeview.model.insert (row)
        self.treeview.set_cursor (row, self.treeview.cols[0], True)


    def on_delete_item (self, widget):
        try:
            rows = self.get_selected_rows ()
            while rows:
                del self.treeview.model[rows[0]]
                del self.snippets[rows[0]]
                rows = self.get_selected_rows ()
        except:
            pass
        finally:
            self.treeview.grab_focus ()
            self.treeview.set_cursor (0)


    def on_edit_started (self, renderer, editable, path):
        # should both columns have the edit window?
        row, col = self.treeview.get_cursor ()
        if col and col.get_data ("id") == 1:
            text = renderer.get_property ("text")
            if text:
                self.edit_text.get_buffer ().set_text (text)
            else:
                self.edit_text.get_buffer ().set_text ("")
            self.edit_text.grab_focus ()
            self.edit_window.show_all ()


    def on_edit_done (self, button, *args):
        row = self.get_first_selected_row ()
        self.treeview.model[row][1] = unicode (
            self.edit_text.get_buffer ().get_property ("text").decode ("string-escape")
        )
        self.edit_window.hide ()


    def on_edit_item (self, renderer, row, text, col):
        if text:
            self.treeview.model[row][col] = unicode (text.decode ("string-escape"))
            self.update_config ()


    def on_hide_edit (self, *args):
        self.edit_window.hide ()


    def on_move_item_up (self, widget):
        try:
            row = self.get_first_selected_row ()
            if row == None:
                row = 0
            if row < 1:
                self.treeview.model.move_before (self.treeview.model.get_iter (row), None)
            else:
                self.treeview.model.move_before (self.treeview.model.get_iter (row),
                                                 self.treeview.model.get_iter (row - 1))
            self.update_config ()
        except:
            pass


    def on_move_item_down (self, widget):
        try:
            row = self.get_first_selected_row ()
            if row == None:
                row = 0
            if row == len (self.treeview.model) - 1:
                self.treeview.model.move_after (self.treeview.model.get_iter (row), None)
            else:
                self.treeview.model.move_after (self.treeview.model.get_iter (row),
                                                self.treeview.model.get_iter (row + 1))
            self.update_config ()
        except:
            pass


    def on_key_press (self, widget, event, cancel=False):
        keyname = gtk.gdk.keyval_name (event.keyval)
        if keyname == 'Tab' or keyname == 'Escape':
            row, col = widget.get_cursor ()

            if not row:
                row = self.get_first_selected_row ()
            if not row:
                row = 0
            if isinstance (row, (list, tuple)):
                row = row[0]

            if not col:
                col = 0
            else:
                col = col.get_data ("id") + 1
            if col > len (self.treeview.cols) - 1:
                col = 0

            self.treeview.cols[col].renderer.stop_editing (cancel)

            if keyname == 'Tab':
                widget.set_cursor (row, self.treeview.cols[col], True)

            return True # cancel the event


    def on_window_keypress (self, widget, event):
        keyname = gtk.gdk.keyval_name (event.keyval)
        if keyname == 'Escape':
            if widget == self.window:
                gtk.main_quit ()
            else:
                if widget == self.pref_window:
                    self.on_hide_preferences ()
                elif widget == self.edit_window:
                    self.on_hide_edit ()
                else:
                    widget = widget.get_focus ()
                    if widget.get_name () == "GtkEntry":
                        self.on_key_press (self.treeview, event, True)


    def fetch_clipboard_info (self):
        self.clipboard.request_text (self.on_clipboard_text)
        return True


    def on_clipboard_text (self, clipboard, text, data):
        if self.need_paste:
            self.need_paste = False
            self.send_paste_keypress ()
        elif not text or text in self.clips or text == self.our_data:
            return
        else:
            self.our_data = text
            if len(self.clips) > self.options["clip_size"] - 1:
                if self.clips_ins > self.options["clip_size"] - 1:
                    self.clips[0] = text
                    self.clips_ins = 1
                else:
                    self.clips[self.clips_ins] = text
                    self.clips_ins += 1
            else:
                self.clips.append (text)
            self.populate_clip_buttons ()


    def on_profile_new (self, button):
        profile = None
        self.profile_entry.set_text ("")

        if self.profile_dialog.run () == gtk.RESPONSE_OK:
            profile = self.profile_entry.get_text ()
        self.profile_dialog.hide ()

        if profile:
            while profile == "profile" or profile == "Default":
                dialog = gtk.MessageDialog (self.window, 0, gtk.MESSAGE_ERROR,
                                            gtk.BUTTONS_OK,
                                            "Cannot create profile named 'profile' or 'Default'")
                dialog.set_position (gtk.WIN_POS_CENTER_ON_PARENT)
                dialog.set_transient_for (self.pref_window)
                dialog.run ()
                dialog.destroy ()

                self.profile_entry.set_text ("")
                if self.profile_dialog.run () == gtk.RESPONSE_OK:
                    profile = self.profile_entry.get_text ()
                else:
                    profile = None
                self.profile_dialog.hide ()
                if not profile:
                    return
            else:
#               if self.needs_save:
#                   dialog = gtk.MessageDialog (self.window, 0, gtk.MESSAGE_QUESTION,
#                                               gtk.BUTTONS_YES_NO,
#                                               "Save changes to %s?" % profile)
#                   if dialog.run () == gtk.RESPONSE_YES:
#                    self.update_config ()
#                   self.needs_save = False
#                   dialog.destroy ()

                self.config["profile"] = profile
                self.config[self.config["profile"]] = self.template
                self.config.write ()

                model = self.profile_combo.get_model ()
                model.append ((profile,))
                self.profile_combo.set_active (len (model) - 1)


    def on_profile_delete (self, button):
        profile = self.profile_combo.get_active_text ()
        if profile == "Default":
            dialog = gtk.MessageDialog(self.window, 0, gtk.MESSAGE_ERROR,
                                       gtk.BUTTONS_OK,
                                       "Cannot delete Default profile")
            dialog.set_position (gtk.WIN_POS_CENTER_ON_PARENT)
            dialog.set_transient_for (self.pref_window)
            dialog.run ()
            dialog.destroy ()
        else:
            dialog = gtk.MessageDialog(self.window, 0, gtk.MESSAGE_QUESTION,
                                       gtk.BUTTONS_YES_NO,
                                       "Permanently delete profile %s?" % profile)
            dialog.set_position (gtk.WIN_POS_CENTER_ON_PARENT)
            dialog.set_transient_for (self.pref_window)

            if dialog.run () == gtk.RESPONSE_YES:
                self.config["profile"] = "Default"
                del self.config[profile]
                self.config.write ()
                model = self.profile_combo.get_model ()
                for i in range (len (model)):
                    if model[i][0] == profile:
                        del model[i]
                self.profile_combo.set_active (0)

            dialog.destroy ()


    def on_profile_changed (self, combo, *args):
#         if self.needs_save:
#             dialog = gtk.MessageDialog (self.window, 0, gtk.MESSAGE_QUESTION,
#                                         gtk.BUTTONS_YES_NO,
#                                         "Save changes to %s?" % profile)
#             dialog.set_position (gtk.WIN_POS_CENTER_ON_PARENT)
#             dialog.set_transient_for (self.pref_window)
#             if dialog.run () == gtk.RESPONSE_YES:
#                 self.update_config ()
#             self.needs_save = False
#             dialog.destroy ()

        self.update_config ()

        self.window.move (self.options["x"], self.options["y"])
        if self.options.has_key ("always_ontop"):
            ontop = self.options.as_bool ("always_ontop")
        else:
            ontop = True
        self.window.set_keep_above (ontop)

        self.populate_tree ()
        self.populate_preferences ()

        self.populate_snip_buttons ()
        self.populate_clip_buttons ()

        gobject.timeout_add (100, self.size_move_window)


    def on_profile_activate (self, entry):
        self.profile_dialog.response (gtk.RESPONSE_OK)


    def on_snip_color_set (self, button, *args):
#        self.needs_save = True
        pass


    def on_clip_color_set (self, button, *args):
#        self.needs_save = True
        pass


    def on_column_toggled (self, button, *args):
#        self.needs_save = True
        pass


    def on_ontop_toggled (self, button, *args):
#        self.needs_save = True
        pass


    def on_initclip_toggled (self, button, *args):
#        self.needs_save = True
        pass


    def on_wrap_spin (self, button, *args):
#        self.needs_save = True
        pass


    def on_clip_spin (self, button, *args):
#        self.needs_save = True
        pass


    def on_delete_event (self, *args):
        self.options["x"], self.options["y"] = self.window.get_position ()
        self.config.write ()
        gtk.main_quit ()


if __name__ == "__main__":
    GPasteItIn ()


