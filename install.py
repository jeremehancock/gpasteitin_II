#!/usr/bin/env python

import os, glob, sys
from distutils.core import setup
import version

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


dfiles     = (["resources/gpasteitin.ui"])
scripts    = [os.path.join("scripts", "gpasteitin")]
data_files = [("/usr/share/gpasteitin", dfiles),
              ("/usr/share/pixmaps", ["resources/gpasteitin.png"]),
              ("/usr/share/applications", ["resources/gpasteitin.desktop"])]

setup(name             = "GPasteItIn II",
      version          = version.__VERSION__,
      description      = "Simple snippet / paste tool for GTK+",
      long_description = "Simple snippet / paste tool for GTK+",
      author           = "Jordan Callicoat... Modified by Jereme Hancock",
      author_email     = "jordan.callicoat@rackspace.com... jereme.hancock@rackspace.com",
      url              = "",
      download_url     = "",
      license          = "MIT",
      platforms        = ["POSIX", "OS X", "Windows"],
      keywords         = [],
      packages         = ["gpasteitin"],
      scripts          = scripts,
      data_files       = data_files,
      )
