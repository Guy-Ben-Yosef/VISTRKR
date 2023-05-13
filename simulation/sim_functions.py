from calibration.calib_functions import *


def point2pixel(point, camera_data):
    """
    Converts a point to a pixel value for a given camera.

    @param point: (tuple of floats) A tuple containing the (x, y) coordinates of the point.
    @param camera_data: (dict) A dictionary containing the position, azimuth angle in degrees and calibration data of
           the camera.
    @return: (int) The pixel value representation of the point.
    """
    camera_position = camera_data['position']
    camera_azimuth = camera_data['azimuth']

    x, y = point

    phi = calculate_expected_angles(camera_data, point)

    pixel = phi2pixel(phi, camera_data['calibration'])

    return pixel


def phi2pixel(phi, calibration_data):
    """
    Converts an azimuth angle to a pixel value for a given camera.

    @param phi: (float) The azimuth angle in degrees.
    @param calibration_data: (tuple) A tuple containing the slope and intercept of the calibration data.
    @return: (int) The pixel value representation of the azimuth angle.
    """
    slope = calibration_data[0]
    intercept = calibration_data[1]

    pixel = round((phi - intercept) / slope)
    return pixel
