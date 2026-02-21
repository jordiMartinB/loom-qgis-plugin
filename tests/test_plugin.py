import unittest
from loom_qgis_plugin import loom_qgis_plugin

class TestLoomQGISPlugin(unittest.TestCase):

    def setUp(self):
        self.plugin = loom_qgis_plugin.LoomQGISPlugin()

    def test_plugin_initialization(self):
        self.assertIsNotNone(self.plugin)
        self.assertEqual(self.plugin.name, "Loom QGIS Plugin")

    def test_plugin_load(self):
        self.plugin.initGui()
        self.assertTrue(self.plugin.isLoaded)

    def test_plugin_unload(self):
        self.plugin.unload()
        self.assertFalse(self.plugin.isLoaded)

if __name__ == '__main__':
    unittest.main()