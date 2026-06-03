import meshio
import numpy as np

class MeshAccessor:
    TISSUE_TAGS = {
        1: "white_matter",
        2: "gray_matter",
        3: "csf",
        4: "skull",
        5: "scalp",
        6: "eye",
    }

    def __init__(self, raw_mesh):
        self._raw = raw_mesh  # objet meshio.Mesh ou simnibs.Msh

    def get_tissue(self, label: int | str) -> "MeshAccessor":
        """Retourne un sous-mesh filtré par tissu."""
        ...

    def nodes(self) -> np.ndarray:          # (N, 3)
        ...

    def elements(self) -> np.ndarray:       # (M, 4) pour tetra
        ...

    def element_data(self) -> dict[str, np.ndarray]:
        """Tous les champs disponibles (E, normE, J...)."""
        ...