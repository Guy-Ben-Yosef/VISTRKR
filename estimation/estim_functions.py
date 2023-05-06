"""
This module contains functions for estimating the position of an object using triangulation method.
"""

import numpy as np
from calibration.calib_functions import calculate_expected_angles


def tand(x):
    """
    Calculates the tangent of an angle in degrees.
    @param x : (float) Angle in degrees
    @return: (float) Tangent of the angle
    """
    return np.tan(np.deg2rad(x))


def triangulation(camera_a_data, sight_angle_a, camera_b_data, sight_angle_b):
    """
    Computes the estimated X and Y coordinates of an object using triangulation method.
    @param camera_a_data: (dict) A dictionary containing the position and azimuth angle of camera A.
    @param sight_angle_a: (float) The sight angle of camera A to the object in degrees.
    @param camera_b_data: (dict) A dictionary containing the position and azimuth angle of camera B.
    @param sight_angle_b: (float) The sight angle of camera B to the object in degrees.
    @return: (numpy.ndarray) An array containing the estimated X and Y coordinates of the object.
    """
    # Rearrange data
    x_a, y_a = camera_a_data['position']
    az_a = camera_a_data['azimuth']
    x_b, y_b = camera_b_data['position']
    az_b = camera_b_data['azimuth']

    # Calculate the tangent of the azimuth angles
    tan_phi_a = tand(az_a + sight_angle_a)
    tan_phi_b = tand(az_b + sight_angle_b)

    # Calculate the estimated X and Y coordinates of the object
    x = 1 / (tan_phi_a - tan_phi_b) * (x_a * tan_phi_a - x_b * tan_phi_b - (y_a - y_b))
    y = tan_phi_a * (x - x_a) + y_a
    return np.array([x, y])


def get_error(camera_a_data, camera_b_data, delta, target_position):
    """
    Computes the maximum error for an estimated position of an object.

    @param camera_a_data: (dict) A dictionary containing the position and azimuth angle of camera A.
    @param camera_b_data: (dict) A dictionary containing the position and azimuth angle of camera B.
    @param delta: (float) Incremental value used to compute the error.
    @param target_position: (numpy.array) True X and Y coordinates of the object.
    @return: (float) Maximum error for the estimated position of the object.
    """

    # Expected azimuth angle of cameras A and B in degrees.
    azimuth_a = camera_a_data['azimuth'] + calculate_expected_angles(camera_a_data, tuple(target_position))
    azimuth_b = camera_b_data['azimuth'] + calculate_expected_angles(camera_b_data, tuple(target_position))

    # Estimate object positions for each combination of expected azimuth angles
    pp = triangulation(camera_a_data, + delta, camera_b_data, + delta)
    mm = triangulation(camera_a_data, - delta, camera_b_data, - delta)
    pm = triangulation(camera_a_data, + delta, camera_b_data, - delta)
    mp = triangulation(camera_a_data, - delta, camera_b_data, + delta)

    # Compute error for each estimated position and store in array
    errors = np.linalg.norm(np.array([pp, mm, pm, mp]) - target_position, axis=1)

    return max(errors)


def weighted_estimation(points, weights):
    """
    Computes the weighted average of a set of points.
    @param points: (np.array) An array containing the points to be averaged.
    @param weights: (np.array) An array containing the weights of each point.
    @return: (np.array) The weighted average of the points.
    """
    return (points.T * weights).sum(axis=1) / weights.sum()
