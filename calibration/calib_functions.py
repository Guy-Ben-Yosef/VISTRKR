"""Calibration related functions library"""
import warnings
import numpy as np

def calculate_expected_angles(camera_position, points, camera_azimuth):
    """
    Calculates the expected azimuth angles for a set of points relative to a camera position and azimuth angle.

    @param camera_position: tuple of floats
        The (x, y) coordinates of the camera position.
    @param points: array-like
        A list or array of (x, y) coordinate pairs for the points of interest.
    @param camera_azimuth: float
        The azimuth angle (in degrees) of the camera.
    @return: list of floats
        A list of expected azimuth angles (in degrees) for the given points relative to the camera position and azimuth angle.
    """
    # Check that each point in points is a tuple of length 2
    if any(not isinstance(p, tuple) or len(p) != 2 for p in points):
        raise TypeError("Each point in points must be a tuple of length 2.")

    expected_angles = []
    for point in points:
        x = point[0]
        y = point[1]
        delta_x = x - camera_position[0]  # Calculate the difference in x coordinates
        delta_y = y - camera_position[1]  # Calculate the difference in y coordinates
        azimuth = np.rad2deg(np.arctan2(delta_y, delta_x)) - camera_azimuth  # Calculate the azimuth angle
        expected_angles.append(azimuth)

    return expected_angles


def calculate_calibration_params(measured_pixels, expected_angles, fit_degree=1):
    """
   Calculates the calibration parameters for converting measured pixel values to expected angle values.

    @param measured_pixels: array-like
        A one-dimensional array containing measured pixel values.
    @param expected_angles: array-like
        A one-dimensional array containing expected angle values.
    @param fit_degree: int
        An integer indicating the degree of polynomial fit to use.
    @return: tuple of floats
        The slope, intercept, and R^2 value for the fitted polynomial.
    """

    # Check that the input arrays have the same length
    if len(measured_pixels) != len(expected_angles):
        raise ValueError("measured_pixels and expected_angles must have the same number of elements.")

    # Fit a polynomial to the measured pixel values and expected angle values
    coefficients, residuals, _, _, _, = np.polyfit(measured_pixels, expected_angles, deg=fit_degree, full=True)
    slope = coefficients[0]
    intercept = coefficients[1]
    residuals = residuals[0]

    # Compute R^2
    total_sum_of_squares = sum((expected_angles - np.mean(expected_angles)) ** 2)
    r_squared = 1 - (residuals / total_sum_of_squares)

    # Warn if R^2 value is too small
    if r_squared < 0.95:
        warnings.warn(f"too small residual (R^2 = {r_squared:0.3f})")

    return slope, intercept, r_squared
