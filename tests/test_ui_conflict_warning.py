import unittest
from unittest import mock

import main as app_main

class UIConflictWarningTests(unittest.TestCase):
    @mock.patch('main.detect_conflicting_services', return_value='Portmaster (PID: 9999)')
    @mock.patch('core.config_manager.load_config', return_value={'groups': {'Default': {}}, 'settings': {}})
    def test_about_tab_shows_compatibility_warning(self, mock_load, mock_detect):
        app = app_main.ProductivityApp()
        try:
            # Open settings which builds the About tab
            app.show_settings()

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
