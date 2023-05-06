"""
This module contains functions for estimating the position of an object using triangulation method.
"""

import numpy as np
import pandas as pd
from numpy import tan, rad2deg, deg2rad, array, zeros, sqrt


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


def get_error(camera_a_position, camera_b_position, delta, target_position):
    """
    Computes the maximum error for an estimated position of an object.

    @param camera_a_position: (tuple) X and Y coordinates of camera A.
    @param camera_b_position: (tuple) X and Y coordinates of camera B.
    @param delta: (float) Incremental value used to compute the error.
    @param target_position: (numpy.array) True X and Y coordinates of the object.
    @return: (float) Maximum error for the estimated position of the object.
    """

    azimuth_a = 3  # Expected azimuth angle of camera A in degrees.
    azimuth_b = 3  # ...                          ... B ...


    # Estimate object positions for each combination of expected azimuth angles
    pp = triangulation(camera_a_position, azimuth_a + delta, camera_b_position, azimuth_b + delta)
    mm = triangulation(camera_a_position, azimuth_a - delta, camera_b_position, azimuth_b - delta)
    pm = triangulation(camera_a_position, azimuth_a + delta, camera_b_position, azimuth_b - delta)
    mp = triangulation(camera_a_position, azimuth_a - delta, camera_b_position, azimuth_b + delta)

    # Compute error for each estimated position and store in array
    errors = np.linalg.norm(np.array([pp, mm, pm, mp]) - target_position, axis=1)

    return max(errors)
