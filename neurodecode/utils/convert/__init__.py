'''
Format conversion.

It supports converting:

- from .xdf | .gdf | .bdf | .eeg | .pickle files to mne.io.raw
- from mne.io.raw to .mat.
'''

from .convert2fif import any2fif, pcl2fif, edf2fif, bdf2fif, gdf2fif, xdf2fif, eeg2fif
from .fif2mat import fif2mat