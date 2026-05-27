class ROIExtractor:
    def __init__(self, mesh: MeshAccessor):
        self._mesh = mesh

    def from_sphere(self, center: tuple, radius_mm: float) -> np.ndarray:
        """Masque sphérique centré sur des coordonnées MNI/subject."""
        ...

    def from_atlas_label(self, atlas: str, region: str) -> np.ndarray:
        """
        Ex: atlas='DKT', region='superiorfrontal'
        Nécessite que le maillage ait des labels atlas.
        """
        ...

    def from_tissue(self, label: int) -> np.ndarray:
        """Simple masque par tag de tissu."""
        ...