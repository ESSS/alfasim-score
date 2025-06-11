import numpy as np


# FIXME type annotate
def numeric_difference_1d(
    values: np.ndarray[tuple[int], np.dtype[float]],
    coords: np.ndarray[tuple[int], np.dtype[float]],
    tolerance: float = 1e-12,
) -> np.ndarray[tuple[int], np.dtype[float]]:
    """
    Calculates the derivative of values with respect to coords using central difference.
    Handles edge points with forward/backward differences.

    Args:
        values (np.ndarray): 1D array of function values.
        coords (np.ndarray): 1D array of coordinates.
        tolerance (float): Small value to check for near-zero coordinate differences.

    Returns:
        np.ndarray: 1D array of derivatives. Returns NaN where derivative cannot be computed
                    due to insufficient points or zero coordinate difference.
    """
    n = len(values)
    d_values_d_coords = np.full_like(values, np.nan, dtype=float)

    if n < 2:
        # Cannot compute derivative if less than 2 points
        return d_values_d_coords

    # Forward difference for the first point (i=0)
    delta_coord_fwd = coords[1] - coords[0]
    if abs(delta_coord_fwd) > tolerance:
        d_values_d_coords[0] = (values[1] - values[0]) / delta_coord_fwd
    # else: remains NaN

    # Central difference for internal points (i=1 to n-2)
    for i in range(1, n - 1):
        delta_coord_central = coords[i + 1] - coords[i - 1]
        if abs(delta_coord_central) > tolerance:
            d_values_d_coords[i] = (values[i + 1] - values[i - 1]) / delta_coord_central
        # else: remains NaN

    # Backward difference for the last point (i=n-1)
    delta_coord_bwd = coords[n - 1] - coords[n - 2]
    if abs(delta_coord_bwd) > tolerance:
        d_values_d_coords[n - 1] = (values[n - 1] - values[n - 2]) / delta_coord_bwd
    # else: remains NaN

    return d_values_d_coords
