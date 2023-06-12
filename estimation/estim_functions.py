"""
This module contains functions for estimating the position of an object using triangulation method.
"""

import numpy as np
import math
from calibration.calib_functions import calculate_expected_angles
import deprecation

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
    x_a, y_a = camera_a_data['position'][:2]
    az_a = camera_a_data['azimuth']
    x_b, y_b = camera_b_data['position'][:2]
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


@deprecation.deprecated(details="\nThis function is deprecated. Use calc_3D_error instead.")
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
    azimuth_a = calculate_expected_angles(camera_a_data, tuple(target_position))[0]
    azimuth_b = calculate_expected_angles(camera_b_data, tuple(target_position))[0]

    # Estimate object positions for each combination of expected azimuth angles
    pp = triangulation(camera_a_data, azimuth_a + delta, camera_b_data, azimuth_b + delta)
    mm = triangulation(camera_a_data, azimuth_a - delta, camera_b_data, azimuth_b - delta)
    pm = triangulation(camera_a_data, azimuth_a + delta, camera_b_data, azimuth_b - delta)
    mp = triangulation(camera_a_data, azimuth_a - delta, camera_b_data, azimuth_b + delta)

    # Compute error for each estimated position and store in array
    errors = np.linalg.norm(np.array([pp, mm, pm, mp]) - target_position[:2], axis=1)

    return max(errors)


def convert_angles_to_unit_vectors(angles_1, angles_2):
    """
    Convert angles to unit vectors.

    Given two sets of angles (azimuth and elevation), this function converts them to unit vectors
    representing the direction in three-dimensional space.

    Args:
        @param angles_1: (tuple) A tuple containing the azimuth and elevation angles of the first vector.
        @param angles_2: (tuple) A tuple containing the azimuth and elevation angles of the second vector.

    Returns:
        @return tuple: A tuple containing the unit vectors corresponding to the given angles.
            The first element is the unit vector for angles_1, and the second element is the unit vector for angles_2.
    """
    azimuth_1, elevation_1 = angles_1
    azimuth_2, elevation_2 = angles_2

    # Convert angles from degrees to radians
    azimuth_1_rad, elevation_1_rad = np.deg2rad(azimuth_1), np.deg2rad(elevation_1)
    azimuth_2_rad, elevation_2_rad = np.deg2rad(azimuth_2), np.deg2rad(elevation_2)

    # Compute the components of the unit vectors
    u1 = np.array([np.sin(azimuth_1_rad) * np.cos(elevation_1_rad),
                   np.cos(azimuth_1_rad) * np.cos(elevation_1_rad),
                   np.sin(elevation_1_rad)])

    u2 = np.array([np.sin(azimuth_2_rad) * np.cos(elevation_2_rad),
                   np.cos(azimuth_2_rad) * np.cos(elevation_2_rad),
                   np.sin(elevation_2_rad)])

    return u1, u2


def closest_point_between_lines(line1, line2):
    """
    Find the closest point between two lines.

    Given two lines defined by a point and a direction vector, this function calculates
    the closest point on the first line to the second line.

    Args:
        @param line1: (tuple) A tuple containing the point and direction vector of the first line.
            The point is a 3D coordinate, and the direction vector is a 3D vector.
        @param line2: (tuple) A tuple containing the point and direction vector of the second line.
            The point is a 3D coordinate, and the direction vector is a 3D vector.

    Returns:
        @return numpy.ndarray: The 3D coordinates of the closest point on the first line to the second line.

    Raises:
        @raise LinAlgError: If the system of linear equations is singular (i.e., the lines are parallel).
    """
    # Unpack the lines into variables
    point1, direction1 = line1
    point2, direction2 = line2

    # Raise LinAlgError if the system of linear equations is singular
    if np.linalg.norm(direction2 - direction1) < 1e-6:
        raise np.linalg.LinAlgError("The lines are parallel, or nearly parallel.")

    # Construct the matrix G
    G = np.zeros([6, 5])
    G[:3, :3] = np.eye(3)
    G[3:, :3] = np.eye(3)
    G[:3, 3] = -direction1
    G[3:, 4] = -direction2

    # Construct the vector d
    d = np.concatenate([point1, point2])

    # Calculate the parameters 'm' using least squares
    m = np.linalg.inv(G.T @ G) @ G.T @ d

    # Extract the coordinates of the closest point
    closest_point = m[:3]

    return closest_point


def weighted_estimation(points, weights):
    """
    Computes the weighted average of a set of points.
    @param points: (np.array) An array containing the points to be averaged.
    @param weights: (np.array) An array containing the weights of each point.
    @return: (np.array) The weighted average of the points.
    """
    return (points.T * weights).sum(axis=1) / weights.sum()
