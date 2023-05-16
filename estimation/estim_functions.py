"""
This module contains functions for estimating the position of an object using triangulation method.
"""

import numpy as np
import math
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


def triangulation_by_pairs(cameras_list, angle_by_camera):
    result = np.zeros([math.comb(len(cameras_list), 2), 3])
    running_index = 0
    for i in range(len(cameras_list) - 1):
        for j in range(i + 1, len(cameras_list)):
            camera_a = cameras_list[i]
            camera_b = cameras_list[j]
            sight_angle_a = angle_by_camera[camera_a['name']]
            sight_angle_b = angle_by_camera[camera_b['name']]
            point = triangulation(camera_a, sight_angle_a, camera_b, sight_angle_b)
            result[running_index, :2] = point
            running_index += 1
    point = np.mean(result[:, :2], axis=0)

    running_index = 0
    for i in range(len(cameras_list) - 1):
        for j in range(i + 1, len(cameras_list)):
            camera_a = cameras_list[i]
            camera_b = cameras_list[j]
            result[running_index, 2] = get_error(camera_a, camera_b, delta=0.5, target_position=point)
            running_index += 1
    return result


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
    azimuth_a = calculate_expected_angles(camera_a_data, tuple(target_position))
    azimuth_b = calculate_expected_angles(camera_b_data, tuple(target_position))

    # Estimate object positions for each combination of expected azimuth angles
    pp = triangulation(camera_a_data, azimuth_a + delta, camera_b_data, azimuth_b + delta)
    mm = triangulation(camera_a_data, azimuth_a - delta, camera_b_data, azimuth_b - delta)
    pm = triangulation(camera_a_data, azimuth_a + delta, camera_b_data, azimuth_b - delta)
    mp = triangulation(camera_a_data, azimuth_a - delta, camera_b_data, azimuth_b + delta)

    # Compute error for each estimated position and store in array
    errors = np.linalg.norm(np.array([pp, mm, pm, mp]) - target_position, axis=1)

    return max(errors)


def closest_point_between_two_lines(L1, L2):
    """
    Computes the point in 3D space that is closest to two infinite lines.

    Parameters
    ----------
    L1 : tuple
        A tuple of two numpy arrays representing the first line in 3D space:
        - The first array (shape 3,) represents a point `p1` on the line.
        - The second array (shape 3,) represents a direction vector `v1` of the line.
    L2 : tuple
        A tuple of two numpy arrays representing the second line in 3D space:
        - The first array (shape 3,) represents a point `p2` on the line.
        - The second array (shape 3,) represents a direction vector `v2` of the line.

    Returns
    -------
    result : numpy array
        The coordinates of the point in 3D space that is closest to both lines.

    Raises
    ------
    LinAlgError
        If the system of linear equations is singular (i.e., the lines are parallel).
    """
    p1, v1 = (L1[0], L1[1])
    p2, v2 = (L2[0], L2[1])
    # Compute the vector connecting the lines
    v3 = np.cross(v1, v2)

    # Compute the parameter values for the point on line 1 closest to line 2
    p_vec = np.array([(p2[i] - p1[i]) for i in range(3)])
    v_mat = np.array([v1, -v2, v3])
    lambdas = np.dot(p_vec, np.linalg.inv(v_mat.T))

    # Compute the coordinates of the closest point on line 1
    return (p1 + lambdas[0] * v1 + p2 + lambdas[1] * v2) / 2


def weighted_estimation(points, weights):
    """
    Computes the weighted average of a set of points.
    @param points: (np.array) An array containing the points to be averaged.
    @param weights: (np.array) An array containing the weights of each point.
    @return: (np.array) The weighted average of the points.
    """
    return (points.T * weights).sum(axis=1) / weights.sum()
