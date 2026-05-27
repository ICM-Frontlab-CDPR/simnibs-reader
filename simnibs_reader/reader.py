from pathlib import Path
from .loader import SimNIBSLoader
from .mesh import MeshAccessor
from .fields import FieldExtractor
from .roi import ROIExtractor

class SimNIBSReader:
    def __init__(self, sim_dir: str | Path):
        self.sim_dir = Path(sim_dir)
        self._loader = SimNIBSLoader(self.sim_dir)
        
        # Chargement lazy : le maillage n'est parsé qu'à la demande
        self._mesh = None

    @property
    def mesh(self) -> MeshAccessor:
        if self._mesh is None:
            raw = self._loader.load_main_mesh()
            self._mesh = MeshAccessor(raw)
        return self._mesh

    @property
    def fields(self) -> FieldExtractor:
        return FieldExtractor(self.mesh)

    @property
    def roi(self) -> ROIExtractor:
        return ROIExtractor(self.mesh)

    def summary(self) -> dict:
        """Résumé rapide : champs disponibles, tissus, nb éléments."""
        return self._loader.parse_summary()     