# Export vers numpy/pandas/nifti/csv




SPACE_MNI = "mni"
SPACE_NATIVE = "native"


class OutputContext:
    """
    Groups all parameters needed to build pipeline output filenames.
    Instantiate in the main loop (run.py) and pass to save / get_*_path functions.

    Parameters
    ----------
    subject : str
        Subject identifier (e.g. '0008').
    condition : str
        ROI / stimulation condition name (e.g. 'fef', 'ips-left').
        Used in preprocessed filenames and mask names.
    mode : str
        'simulation' or 'optimization'.
    space : str
        'mni' or 'native'.
    roi_name : str
        ROI key as defined in config.yaml → target_generation.rois.
        Usually identical to *condition*; useful to distinguish the config key
        from the filename.
    base_name : str or None
        Stem of the source e-field file (e.g. 'sub-0008_scalar_MNI_magnE').
        Required for get_preproc_paths.  Set after find_efield_files.
    results_dir : Path or None
        Root results directory (config.paths.results_dir).
    simnibs_output : Path or None
        Root SimNIBS output directory (config.paths.simnibs_output).
    """

    def __init__(
        self,
        subject: str = "",
        condition: str = "",
        mode: str = "",
        space: str = SPACE_MNI,
        roi_name: str = "",
        base_name: str = "",
        results_dir: Optional[Path] = None,
        simnibs_output: Optional[Path] = None,
    ) -> None:
        self.subject = subject
        self.condition = condition
        self.mode = mode
        self.space = space
        self.roi_name = roi_name or condition  # default: same as condition
        self.base_name = base_name
        self.results_dir = results_dir
        self.simnibs_output = simnibs_output


def normalize_space(space: str) -> str:
    """Normalize and validate the working space value."""
    normalized = str(space).lower().strip()
    if normalized not in {SPACE_MNI, SPACE_NATIVE}:
        raise ValueError(
            f"Invalid 'space' parameter: {space}. Allowed values: {SPACE_MNI}, {SPACE_NATIVE}"
        )
    return normalized


def space_tag(space: str) -> str:
    """Return tagged space label used in output paths and file names."""
    return f"space-{normalize_space(space)}"




#########################

def check_output(path: Path, if_exists: str = "overwrite") -> bool:
    """Return True if the file should be written, False if it should be skipped.

    Parameters
    ----------
    path : Path
        Target output path.
    if_exists : str
        ``'overwrite'`` — always write (default).
        ``'skip'``      — silently skip if file exists.
        ``'error'``     — raise FileExistsError if file exists.
    """
    path = Path(path)
    if path.exists():
        if if_exists == "skip":
            logger.info(f"Skip (already exists): {path.name}")
            return False
        elif if_exists == "error":
            msg = f"Output already exists (if_exists='error'): {path}"
            logger.error(msg)
            raise FileExistsError(msg)
    return True


def save_nifti(
    img: nib.spatialimages.SpatialImage, output_path: Path, if_exists: str = "overwrite"
) -> None:
    """Save a NIfTI image to disk, creating parent directories as needed."""
    output_path = Path(output_path)
    if not check_output(output_path, if_exists):
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.to_filename(str(output_path))


def load_csvs(csv_paths: Iterable[Path]) -> pd.DataFrame:
    """Load and concatenate multiple CSV files into a single DataFrame.

    Parameters
    ----------
    csv_paths : Iterable[Path]
        Iterable of paths to CSV files

    Returns
    -------
    pd.DataFrame
        Concatenated DataFrame from all CSV files
    """
    frames = [pd.read_csv(p) for p in csv_paths]
    return pd.concat(frames, ignore_index=True)


def save_rows(rows: List[Dict], out_csv: Path, if_exists: str = "overwrite") -> None:
    """Save a list of row dicts to a CSV file, creating parent directories as needed.

    Parameters
    ----------
    rows :
        List of dicts, each representing one row (e.g. feature extraction output).
    out_csv :
        Destination CSV path.
    if_exists :
        ``'overwrite'`` (default), ``'skip'``, or ``'error'``.
    """
    out_csv = Path(out_csv)
    if not check_output(out_csv, if_exists):
        return
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)


def save_dataframe(
    df: pd.DataFrame, out_path: Path, if_exists: str = "overwrite", **to_csv_kwargs
) -> None:
    """Save a DataFrame to CSV, creating parent directories as needed."""
    out_path = Path(out_path)
    if not check_output(out_path, if_exists):
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, **to_csv_kwargs)


def save_ants_image(img: Any, out_path: Path, if_exists: str = "overwrite") -> None:
    """Save an ANTsPy image to disk, creating parent directories as needed."""
    import ants

    out_path = Path(out_path)
    if not check_output(out_path, if_exists):
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ants.image_write(img, str(out_path))


def save_figure(out_path: Path, if_exists: str = "overwrite", **savefig_kwargs) -> bool:
    """Save the current matplotlib figure to disk.

    Returns True if the figure was saved, False if skipped.
    Closes the figure in both cases.
    """
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    if not check_output(out_path, if_exists):
        logger.debug(f"  skip figure (exists): {out_path.name}")
        plt.close()
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, **savefig_kwargs)
    plt.close()
    return True
