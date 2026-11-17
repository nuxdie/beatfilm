import gi
gi.require_version('Gtk','3.0'); gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk
t=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text(); print(t or "")
