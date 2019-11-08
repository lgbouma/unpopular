import numpy as np
import matplotlib.pyplot as plt
from astroquery.mast import Tesscut
from astropy.io import fits
import lightkurve as lk
import re


class TargetData(object):
    """Object containing the data and additional attributes used in the TESS CPM model.

    Args:
        path (str): path to file
        remove_bad (bool): If ``True``, remove the data points that have been flagged by the TESS team. Default is ``True``.
        verbose (bool): If ``True``, print statements containing information. Default is ``True``.

    """

    def __init__(self, path, remove_bad=True, verbose=True):
        self.file_path = path
        self.file_name = path.split("/")[-1]
        s = self.file_name.split("-")
        self.sector = s[1].strip("s").lstrip("0")
        self.camera = s[2]
        self.ccd = s[3][0]

        with fits.open(path, mode="readonly") as hdu:
            self.time = hdu[1].data["TIME"]
            self.fluxes = hdu[1].data["FLUX"]
            self.flux_errors = hdu[1].data["FLUX_ERR"]
            self.quality = hdu[1].data["QUALITY"]
            try:
                self.wcs_info = WCS(hdulist[2].header)
            except:
                if verbose == True:
                    print("WCS Info could not be retrieved")

        self.flagged_times = self.time[self.quality > 0]
        # If remove_bad is set to True, we'll remove the values with a nonzero entry in the quality array
        if remove_bad == True:
            bool_good = self.quality == 0
            if verbose == True:
                print(
                    f"Removing {np.sum(~bool_good)} bad data points "
                    "(out of {np.size(bool_good)}) using the TESS provided QUALITY array"
                )
            self.time = self.time[bool_good]
            self.fluxes = self.fluxes[bool_good]
            self.flux_errors = self.flux_errors[bool_good]

        # We're going to precompute the pixel lightcurve medians since it's used to set the predictor pixels
        # but never has to be recomputed. np.nanmedian is used to handle images containing NaN values.
        self.flux_medians = np.nanmedian(self.fluxes, axis=0)
        self.cutout_sidelength = self.fluxes[0].shape[0]
        self.flattened_flux_medians = self.flux_medians.reshape(
            self.cutout_sidelength ** 2
        )
        # We also rescale the fluxes to be divided by the median and centered about zero
        self.centered_scaled_fluxes = (self.fluxes / self.flux_medians) - 1
        self.flattened_centered_scaled_fluxes = self.centered_scaled_fluxes.reshape(
            self.time.shape[0], self.cutout_sidelength ** 2
        )

        self.centered_scaled_flux_errors = self.flux_errors / self.flux_medians