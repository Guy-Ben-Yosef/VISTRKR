"""Calibration related functions library"""
import warnings
import numpy as np


def normalize_angle(x):
    """
    Normalizes an angle to the range [-180, 180).
    @param x: Angle in degrees
    @return: Normalized angle in degrees
    """
    return (x + 180) % 360 - 180


def calculate_expected_angles(camera_data, points):
    """
    Calculates the expected azimuth and elevation angles for a set of points relative to a camera position and
    orientation.

    @param camera_data: (dict) A dictionary containing the position and orientation in degrees of the camera.
    @param points: (array-like) A list or array of (x, y, z) coordinates for the points of interest.
    @return: (list of floats) A list of expected azimuth and elevation angles (in degrees) for the given points relative
             to the camera position and orientation.
    """
    if not isinstance(points, list):
        points = [points]
    # Check that each point in points is a tuple of length 2
    if any(not isinstance(p, tuple) or (len(p) != 2 and len(p) != 3) for p in points):
        raise TypeError("Each point in points must be a tuple of length 2 or 3.")

    camera_position = camera_data['position']
    camera_azimuth = camera_data['azimuth']
    camera_elevation = camera_data['elevation']

    expected_azimuths = []
    expected_elevations = []
    for point in points:
        x = point[0]
        y = point[1]
        z = 0 if len(point) == 2 else point[2]  # Set z to 0 if it is not provided
        delta_x = x - camera_position[0]  # Calculate the difference in x coordinates
        delta_y = y - camera_position[1]  # Calculate the difference in y coordinates
        delta_z = z - camera_position[2]  # Calculate the difference in z coordinates

        # Calculate the azimuth angle:
        azimuth = np.rad2deg(np.arctan2(delta_y, delta_x)) - camera_azimuth

        # Calculate the elevation angle:
        elevation = np.rad2deg(np.arctan2(delta_z, np.sqrt(delta_x ** 2 + delta_y ** 2))) - camera_elevation

        # Append the calculated angles to the list of expected angles
        expected_azimuths.append(normalize_angle(azimuth))
        expected_elevations.append(normalize_angle(elevation))

    long_return = (expected_azimuths, expected_elevations)
    short_return = (expected_azimuths[0], expected_elevations[0])
    return long_return if len(expected_azimuths) > 1 else short_return


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


def pixel2phi(calibration_data, pixel):
    """
    Converts a pixel coordinate to a corresponding angles in degrees, using calibration parameters of a camera.

    @param calibration_data: (tuple or dictionary) A tuple containing the slope, intercept, and R^2 value of the or a
                             dictionary containing the azimuth and elevation calibration parameters of the camera.
    @param pixel: (int or tuple of 2 ints) The pixel coordinate to convert to an angle.
    @return: Angle or angles in degrees corresponding to the given pixel coordinate.
    """
    if isinstance(pixel, int):
        # Extract the calibration parameters for the camera
        slope, intercept, _ = calibration_data

        # Convert the pixel coordinate to an angle using the slope and intercept
        phi = slope * pixel + intercept

        return phi
    elif isinstance(pixel, tuple) and len(pixel) == 2:
        return pixel2phi(calibration_data['azimuth'], pixel[0]), pixel2phi(calibration_data['elevation'], pixel[1])
    else:
        raise TypeError("pixel must be an integer or tuple of length 2.")

