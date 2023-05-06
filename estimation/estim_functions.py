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


def triangulation(camera_a_position, camera_a_azimuth, camera_b_position, camera_b_azimuth):
    """
    Estimates the position of an object using triangulation method.
    @param camera_a_position: (tuple) X and Y coordinates of camera A.
    @param camera_a_azimuth: (float) Azimuth angle of camera A in degrees.
    @param camera_b_position: (tuple) X and Y coordinates of camera B.
    @param camera_b_azimuth: (float) Azimuth angle of camera B in degrees.
    @return: (numpy array) Estimated X and Y coordinates of the object.
    """

    # Get camera positions
    x_a = camera_a_position[0]
    y_a = camera_a_position[1]
    x_b = camera_b_position[0]
    y_b = camera_b_position[1]

    # Calculate the tangent of the azimuth angles
    tan_phi_a = tand(camera_a_azimuth)
    tan_phi_b = tand(camera_b_azimuth)

    # Calculate the estimated X and Y coordinates of the object
    x = 1 / (tan_phi_a - tan_phi_b) * (x_a * tan_phi_a - x_b * tan_phi_b - (y_a - y_b))
    y = tan_phi_a * (x - x_a) + y_a
    return np.array([x, y])


def get_error(camera_a_position, azimuth_a, camera_b_position, azimuth_b, delta, target_position):
    """
    Computes the maximum error for an estimated position of an object.

    @param camera_a_position: (tuple) X and Y coordinates of camera A.
    @param azimuth_a: (float) Expected azimuth angle of camera A in degrees.
    @param camera_b_position: (tuple) X and Y coordinates of camera B.
    @param azimuth_b: (float) Expected azimuth angle of camera B in degrees.
    @param delta: (float) Incremental value used to compute the error.
    @param target_position: (numpy.array) True X and Y coordinates of the object.
    @return: (float) Maximum error for the estimated position of the object.
    """
    # Estimate object positions for each combination of expected azimuth angles
    pp = triangulation(camera_a_position, azimuth_a + delta, camera_b_position, azimuth_b + delta)
    mm = triangulation(camera_a_position, azimuth_a - delta, camera_b_position, azimuth_b - delta)
    pm = triangulation(camera_a_position, azimuth_a + delta, camera_b_position, azimuth_b - delta)
    mp = triangulation(camera_a_position, azimuth_a - delta, camera_b_position, azimuth_b + delta)

    # Compute error for each estimated position and store in array
    errors = np.linalg.norm(np.array([pp, mm, pm, mp]) - target_position, axis=1)

    return max(errors)
