from pathlib import Path

import mne

from ..io._file_dir import get_file_list, make_dirs
from ... import logger


def set_montage(inst, montage, **kwargs):
    """
    Set EEG sensor configuration and head digitization.

    Parameters
    ----------
    inst : mne.io.Raw | mne.io.RawArray | mne.Epochs | mne.Evoked
        MNE instance of Raw | Epochs | Evoked.
    montage : str | DigMontage
        Montage to used, e.g. 'standard_1020'.
    **kwargs : Additional arguments are passed to inst.set_montage()
        c.f. https://mne.tools/stable/generated/mne.io.Raw.html#mne.io.Raw.set_montage
    """
    inst.set_montage(montage, **kwargs)


def dir_set_montage(fif_dir, recursive, montage,
                    out_dir=None, overwrite=False, **kwargs):
    """
    Change the channel names of all raw fif files in a given directory.
    The file name must respect MNE convention and end with '-raw.fif'.

    https://mne.tools/stable/generated/mne.io.Raw.html#mne.io.Raw.set_montage

    Parameters
    ----------
    fif_dir : str
        Path to the directory containing fif files.
    recursive : bool
        If True, search recursively.
    montage : str | DigMontage
        Montage to used, e.g. 'standard_1020'.
    out_dir : str | None
        Path to the output directory. If None, the directory
        'fif_dir/with_montage' is used.
    overwrite : bool
        If True, overwrite previously corrected files.
    """
    fif_dir = Path(fif_dir)
    if not fif_dir.exists():
        logger.error(f"Directory '{fif_dir}' not found.")
        raise IOError
    if not fif_dir.is_dir():
        logger.error(f"'{fif_dir}' is not a directory.")
        raise IOError

    if out_dir is None:
        out_dir = 'with_montage'
        if not (fif_dir / out_dir).is_dir():
            make_dirs(fif_dir / out_dir)
    else:
        out_dir = Path(out_dir)
        if not out_dir.is_dir():
            make_dirs(out_dir)

    for fif_file in get_file_list(fif_dir, fullpath=True, recursive=recursive):
        fif_file = Path(fif_file)

        if fif_file.suffix != '.fif':
            continue
        if not fif_file.stem.endswith('-raw'):
            continue

        raw = mne.io.read_raw(fif_file, preload=True)
        set_montage(raw, montage, **kwargs)

        relative = fif_file.relative_to(fif_dir).parent
        if not (fif_dir / out_dir / relative).is_dir():
            make_dirs(fif_dir / out_dir / relative)

        logger.info(
            f"Exporting to '{fif_dir / out_dir / relative / fif_file.name}'")
        try:
            raw.save(fif_dir / out_dir / relative / fif_file.name,
                     overwrite=overwrite)
        except FileExistsError:
            logger.warning(
                f'The corrected file already exist for {fif_file.name}. '
                'Use overwrite=True to force overwriting.')
