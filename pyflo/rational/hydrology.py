"""Classes for performing rational method basin hydrology analysis.

:copyright: 2016, See AUTHORS for more details.
:license: GNU General Public License, See LICENSE for more details.

"""

import math
from typing import List, Tuple

from scipy import interpolate

from pyflo import distributions, constants, basins


class Basin(basins.Basin):

    def __init__(self, tc, area=0.0, c=0.0, **kwargs):
        """A watershed draining to a node with hydrology attributes, dimensions, and methods.

        Args:
            tc (float): The estimated time of concentration, in :math:`minutes`.
            area (float): The delineated region concentrating to a point, in :math:`acres`.
            c (float): The runoff coefficient; A ratio between 0.0 and 1.0.

        """
        super(Basin, self).__init__(area)
        self.tc = tc
        self.c = c
        shapes = kwargs.pop('shapes', [])
        if shapes:
            self.add_shapes(shapes)

    @property
    def runoff_area(self):
        return self.area * self.c

    def add_shapes(self, shapes):
        """Takes a list of (area, c) tuples, adding to self.area and weighting a new self.c

        Args:
            shapes (List[Tuple[float, float]]): A list of (area, c) pairs.

        """
        a_shp = sum(shp[0] for shp in shapes)
        c_shp = sum(shp[0] * shp[1] for shp in shapes) / a_shp
        a_tot = self.area + a_shp
        self.c = (self.area*self.c + a_shp*c_shp) / a_tot
        self.area = a_tot

    def flood_data(self, rain_dist, interval):
        """Generate pairs of basin runoff flow generated from rainfall over time.

        Args:
            rain_dist (distributions.Distribution): The hydrograph with scaled rainfall data.
            interval (float): The amount of time the output will increment by.

        Yields:
            Tuple[float, float]: The next pair of time and runoff flow generated from rainfall.

        """
        data_rainfall = rain_dist.data
        duration = data_rainfall[-1][0]
        time_steps = math.ceil(duration / interval)
        x_col, y_col = zip(*data_rainfall)
        fill_value = y_col[0], y_col[-1]
        y_interp = interpolate.interp1d(x_col, y_col, bounds_error=False, fill_value=fill_value)
        x_new = [step * interval for step in range(time_steps + 1)]
        y_new = y_interp(x_new)
        for time, rainfall in zip(x_new, y_new):
            intensity = rainfall / time
            flow = intensity * self.runoff_area * constants.K_RATIONAL
            yield time, flow

    def flood_hydrograph(self, rain_dist, interval):
        """Get a composite hydrograph of basin runoff generated from rainfall over time.

        Args:
            rain_dist (distributions.Distribution): The hydrograph with scaled rainfall data.
            interval (float): The amount of time the output will increment by.

        Returns:
            distributions.Distribution: The composite hydrograph of runoff flow generated from
                rainfall.

        """
        pairs = self.flood_data(rain_dist, interval)
        hydrograph = distributions.Distribution(list(pairs))
        return hydrograph
