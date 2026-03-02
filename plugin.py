from qgis.core import QgsApplication

from loom_provider import LoomProvider


class LoomQGISPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        """Register the Loom processing provider with QGIS."""
        self.provider = LoomProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Remove the Loom processing provider from QGIS."""
        QgsApplication.processingRegistry().removeProvider(self.provider)
