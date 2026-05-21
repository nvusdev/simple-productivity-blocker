import unittest
from unittest import mock

import main as app_main


class ImmediateThread:
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        self.target = target
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}
        self.daemon = daemon

    def start(self):
        if self.target:
            self.target(*self.args, **self.kwargs)

    def join(self, timeout=None):
        pass

    def is_alive(self):
        return False

class UIConflictWarningTests(unittest.TestCase):
    @mock.patch('main.detect_conflicting_services', return_value='Portmaster (PID: 9999)')
    @mock.patch('core.config_manager.load_config', return_value={'groups': {'Default': {}}, 'settings': {}})
    def test_about_tab_shows_compatibility_warning(self, mock_load, mock_detect):
        with mock.patch('main.threading.Thread', ImmediateThread):
            app = app_main.ProductivityApp()
            try:
                # Open settings which builds the About tab
                app.show_settings()
                app.update()

                # Traverse widgets to find any label with the compatibility text
                found = False

                def walk(w):
                    nonlocal found
                    for child in w.winfo_children():
                        try:
                            txt = child.cget('text')
                            if isinstance(txt, str) and 'Compatibility mode active' in txt:
                                found = True
                                return
                        except Exception:
                            pass
                        walk(child)

                walk(app)
                self.assertTrue(found, 'Compatibility warning label not found in About tab')
            finally:
                app.destroy()

if __name__ == '__main__':
    unittest.main()
