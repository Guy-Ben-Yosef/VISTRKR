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


@deprecation.deprecated(details="\nThis function is deprecated. Use closest_point_between_lines instead.")
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
    """
    Perform triangulation by pairs of cameras.

    Args:
        @param: cameras_list (list): A list of dictionaries representing cameras.
                Each camera dictionary should have keys: 'name', 'azimuth', 'elevation', and 'position'.
        @param: angle_by_camera (dict): A dictionary mapping camera names to angles.
                The angles can be either an integer or a tuple of two elements representing azimuth and elevation.

    Returns:
        @return: numpy.ndarray: A 2D array representing the triangulated points.
                 Each row corresponds to a pair of cameras, and the columns represent the X, Y, and Z coordinates.
                 The last column stores the calculated 3D error for each pair of cameras.
    """
    # Determine the dimensions based on the type of angle values
    instance_val = list(angle_by_camera.values())[0]
    if isinstance(instance_val, int):
        dimensions = 2
    elif isinstance(instance_val, tuple) and len(instance_val) == 2:
        dimensions = 3
    else:
        raise TypeError("angle_by_camera values must be either int or tuple of two elements")

    # Initialize the result array with zeros
    result = np.zeros([math.comb(len(cameras_list), 2), dimensions + 1])
    running_index = 0

    # Perform triangulation for each pair of cameras
    for i in range(len(cameras_list) - 1):
        for j in range(i + 1, len(cameras_list)):
            camera_a = cameras_list[i]
            azimuth_a = angle_by_camera[camera_a['name']][0] + camera_a['azimuth']
            elevation_a = angle_by_camera[camera_a['name']][1] + camera_a['elevation']

            camera_b = cameras_list[j]
            azimuth_b = angle_by_camera[camera_b['name']][0] + camera_b['azimuth']
            elevation_b = angle_by_camera[camera_b['name']][1] + camera_b['elevation']

            direction_a, direction_b = convert_angles_to_unit_vectors((azimuth_a, elevation_a),
                                                                      (azimuth_b, elevation_b))

            point = closest_point_between_lines((camera_a['position'], direction_a),
                                                (camera_b['position'], direction_b))

            result[running_index, :dimensions] = point
            running_index += 1

    # Calculate the mean point
    point = np.mean(result[:, :dimensions], axis=0)

    running_index = 0

    # Calculate the 3D error for each pair of cameras
    for i in range(len(cameras_list) - 1):
        for j in range(i + 1, len(cameras_list)):
            camera_a = cameras_list[i]
            camera_b = cameras_list[j]
            result[running_index, dimensions] = calc_3d_error(camera_a, camera_b, delta=0.5, target_position=point)
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


def calc_3d_error(camera_a_data, camera_b_data, delta, target_position):
    """
    Calculates the maximum 3D error between two cameras and a target position.

    @param camera_a_data: (dict) Data for camera A, including 'azimuth', 'elevation', and 'position'.
    @param camera_b_data: (dict) Data for camera B, including 'azimuth', 'elevation', and 'position'.
    @param delta: (float) Delta value for calculating deviations.
    @param target_position: (tuple) Target position in 3D space as a tuple of (x, y, z) coordinates.
    @return: (float) Maximum 3D error between the two cameras and the target position.
    """
    target_position = tuple(target_position)

    # Calculate the expected azimuth and elevation for camera A based on camera data and target position
    azimuth_a, elevation_a = calculate_expected_angles(camera_a_data, target_position)
    azimuth_a += camera_a_data['azimuth']
    elevation_a += camera_a_data['elevation']

    # Calculate the expected azimuth and elevation for camera B based on camera data and target position
    azimuth_b, elevation_b = calculate_expected_angles(camera_b_data, target_position)
    azimuth_b += camera_b_data['azimuth']
    elevation_b += camera_b_data['elevation']

    deltas = [-delta, delta]
    combinations = 2 ** 4
    deviated_points = np.zeros([combinations, 3])

    i = 0
    for delta_azimuth_a in deltas:
        for delta_elevation_a in deltas:
            for delta_azimuth_b in deltas:
                for delta_elevation_b in deltas:
                    # Calculate the deviated azimuth and elevation for camera A and camera B
                    deviated_azimuth_a = azimuth_a + delta_azimuth_a
                    deviated_elevation_a = elevation_a + delta_elevation_a

                    deviated_azimuth_b = azimuth_b + delta_azimuth_b
                    deviated_elevation_b = elevation_b + delta_elevation_b

                    angles_a = (deviated_azimuth_a, deviated_elevation_a)
                    angles_b = (deviated_azimuth_b, deviated_elevation_b)

                    # Convert the deviated angles to unit vectors representing directions
                    direction_a, direction_b = convert_angles_to_unit_vectors(angles_a, angles_b)

                    line_a = (camera_a_data['position'], direction_a)
                    line_b = (camera_b_data['position'], direction_b)

                    # Find the closest point between the lines defined by camera A and camera B
                    deviated_points[i, :] = closest_point_between_lines(line_a, line_b)
                    i += 1

    # Calculate the errors as the Euclidean distance between each deviated point and the target position
    errors = np.linalg.norm(deviated_points - target_position, axis=1)

    # Return the maximum error among all deviations
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
    # Validate input
    if type(angles_1) != tuple or type(angles_2) != tuple:
        raise TypeError('Angles must be passed as tuples.')
    else:
        if len(angles_1) != 2 or len(angles_2) != 2:
            raise ValueError('Angles must be passed as tuples of length 2.')

    azimuth_1, elevation_1 = angles_1
    azimuth_2, elevation_2 = angles_2

    # Convert angles from degrees to radians
    azimuth_1_rad, elevation_1_rad = np.deg2rad(azimuth_1), np.deg2rad(elevation_1)
    azimuth_2_rad, elevation_2_rad = np.deg2rad(azimuth_2), np.deg2rad(elevation_2)

    # Compute the components of the unit vectors
    u1 = np.array([np.cos(azimuth_1_rad) * np.cos(elevation_1_rad),
                   np.sin(azimuth_1_rad) * np.cos(elevation_1_rad),
                   np.sin(elevation_1_rad)])

    u2 = np.array([np.cos(azimuth_2_rad) * np.cos(elevation_2_rad),
                   np.sin(azimuth_2_rad) * np.cos(elevation_2_rad),
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

    # Convert the points to numpy arrays, and add a zero to the end if necessary
    pre_proc = lambda x: np.array(x) if len(x) == 3 else np.array(list(x) + [0])

    point1 = pre_proc(point1)
    point2 = pre_proc(point2)
    direction1 = pre_proc(direction1)
    direction2 = pre_proc(direction2)

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
