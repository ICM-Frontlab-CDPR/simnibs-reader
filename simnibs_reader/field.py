import numpy as np
import pandas as pd

class FieldExtractor:
    def __init__(self, mesh: MeshAccessor):
        self._mesh = mesh

    def get(self, field: str, tissue: int | str | None = None) -> np.ndarray:
        """
        Extrait un champ vectoriel ou scalaire, optionnellement
        restreint à un tissu.
        field: 'E', 'normE', 'J', 'normJ', 'v', ...
        """
        ...

    def to_dataframe(self, fields: list[str], tissue=None) -> pd.DataFrame:
        """Export pratique pour analyse statistique."""
        ...

    def percentile(self, field: str, p: float, tissue=None) -> float:
        vals = self.get(field, tissue)
        return np.percentile(vals, p)

    def focality(self, field: str, threshold_pct: float = 75) -> float:
        """Volume de tissu au-dessus du seuil (indicateur de focalité)."""
        ...