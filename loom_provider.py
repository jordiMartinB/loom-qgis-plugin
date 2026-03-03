from qgis.core import QgsProcessingProvider

from loom_algorithms import (
    BuildGraphAlgorithm,
    RunTopoAlgorithm,
    RunLoomAlgorithm,
    RunOctiAlgorithm,
)


class LoomProvider(QgsProcessingProvider):
    """QGIS Processing provider that exposes the loom pipeline stages."""

    def id(self) -> str:
        return "loom"

    def name(self) -> str:
        return "Loom"

    def longName(self) -> str:
        return "Loom Transit Map Tools"

    def loadAlgorithms(self):
        for algo_cls in (
            BuildGraphAlgorithm,
            RunTopoAlgorithm,
            RunLoomAlgorithm,
            RunOctiAlgorithm,
        ):
            self.addAlgorithm(algo_cls())
