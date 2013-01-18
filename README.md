gpasteitin_II
=====

Installation
-----------

    1. Download the gpasteitin_II package.
    2. Extract the gpasteitin_II package.
    3. Open Terminal and cd into the gpasteitin_II-master folder 
    4. Run this command: sudo ./install.py install --record install_log

Usage
-----
    
    Start from Gnome Menu -> Accessories, or run "gpasteitin" command from terminal.

Uninstallation
------------

    1. Open Terminal and cd into the gpasteitin_II folder
    2. Run this command: cat install_log | sudo xargs rm -rf
    
Run without Installation
------------

    1. Open Terminal and cd into the gpasteitin_II folder
    2. Run this command: ./gpasteitin/gpasteitin.py
    
    
Credits:
------------

    This is merely a repackaging of the gpasteitin application available
    here. http://code.google.com/p/gpasteitin/
    
    I appreciate all the hard work that went into this application. I only wanted 
    to repackage it so that the installer would be a bit easier to work with so 
    that missing packages are recognized and reported.
