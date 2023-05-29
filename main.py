import numpy as np
import math

from calibration import calib_functions
from estimation import estim_functions
from simulation import sim_functions


def calibrate_cameras(cameras_list, calibration_data):
    """
    Calibrates a list of cameras using calibration data.

    @param cameras_list: (List[Dict]) A list of camera dictionaries, each containing camera data.
    @param calibration_data: (Dict) A dictionary containing calibration data, including pixel and point information.
    @return: List[Dict] A list of camera dictionaries, each updated with calibration information.
    """
    pixels = calibration_data['pixels']
    points = calibration_data['points']

    updated_cameras_data = []
    for camera in cameras_list:
        expected_angles = calib_functions.calculate_expected_angles(camera, points)
        camera['calibration'] = calib_functions.calculate_calibration_params(pixels[camera['name']], expected_angles)

        updated_cameras_data.append(camera)
    return updated_cameras_data


def estimate_position(cameras_list, pixels_by_camera):
    if not isinstance(pixels_by_camera[cameras_list[0]['name']], list):
        number_of_measurements = 1
    else:
        number_of_measurements = len(pixels_by_camera[cameras_list[0]['name']])
    expected_angles = {}
    for camera in cameras_list:
        expected_angles_for_camera = []

        # TODO: Implement for single point/pixel/measurement as well
        for pixel in pixels_by_camera[camera['name']]:
            expected_angles_for_camera.append(calib_functions.pixel2phi(camera, pixel))
        expected_angles[camera['name']] = expected_angles_for_camera

    dimensions = 2
    points_weights_by_pairs = np.zeros([math.comb(len(cameras_list), 2), dimensions+1, number_of_measurements])
    for k in range(number_of_measurements):
        angle_by_camera = {}
        for m in range(len(cameras_list)):
            camera_name = cameras_list[m]['name']
            angle_by_camera[camera_name] = expected_angles[camera_name][k]
        points_weights_by_pairs[:, :, k] = estim_functions.triangulation_by_pairs(cameras_list, angle_by_camera)

    results = np.zeros([number_of_measurements, dimensions])
    for k in range(number_of_measurements):
        relevant_points = points_weights_by_pairs[:, :dimensions, k]
        relevant_weights = points_weights_by_pairs[:, dimensions, k]
        relevant_weights = 1 / relevant_weights
        relevant_weights = relevant_weights / np.linalg.norm(relevant_weights)
        results[k, :] = estim_functions.weighted_estimation(relevant_points, relevant_weights)

    return results


def simulate_data(cameras_list, points, noise_std):
    """
    Simulates measurements of 3D points in a 2D camera coordinate system with added Gaussian noise.

    @param cameras_list: (list) List of camera dictionaries, each containing camera parameters including intrinsic and
                                extrinsic parameters.
    @param points: (list or tuple) List of 3D point coordinates or a single tuple containing 3D point coordinates.
    @param noise_std: (float) Standard deviation of Gaussian noise to be added to the simulated measurements.
    @return: Dictionary containing the measurements for each camera in the cameras_list. The keys of the dictionary are
             the camera names, and the values are lists of integers representing the measured pixel coordinates in the
             camera image plane.
    """
    # Ensure that points is a list
    if not isinstance(points, list):
        points = [points]

    # Ensure that cameras_list is a list
    if not isinstance(cameras_list, list):
        cameras_list = [cameras_list]

    # Create an empty dictionary to store the measurements for each camera
    measurements = {}

    # Loop through each camera in the cameras_list
    for camera in cameras_list:
        # Create an empty list to store the measurements for this camera
        measurements_by_camera = []
        # Loop through each point in the points list
        for point in points:
            # Convert the 3D point to pixel coordinates in the camera image plane
            pixel = sim_functions.point2pixel(point, camera)
            # Add Gaussian noise to the pixel coordinates
            measurements_by_camera.append(sim_functions.add_white_gaussian_noise(pixel, noise_std))

        # Add the measurements for this camera to the measurements dictionary
        measurements[camera['name']] = measurements_by_camera

    return measurements


def simulate_calibration(cameras_list, calibration_points, angle_error_std=5, pixel_error_std=5):
    # Ensure that cameras_list is a list
    if not isinstance(cameras_list, list):
        cameras_list = [cameras_list]
    # Ensure that `calibration_points` is a list, if not raise an error
    if not isinstance(calibration_points, list):
        raise TypeError('`calibration_points` must be a list of points.')
    # Ensure that `calibration_points` contains at least 3 points
    if len(calibration_points) < 3:
        raise ValueError('At least 3 calibration points are required.')

    updated_cameras_data = []
    for camera in cameras_list:
        expected_angles = calib_functions.calculate_expected_angles(camera, calibration_points)
        angle_error = np.random.normal(0, angle_error_std)
        angles_with_deployment_error = (np.array(expected_angles) - angle_error).tolist()
        camera['true_azimuth'] = camera['azimuth'] + angle_error

        expected_pixels = sim_functions.calculate_expected_pixels(
            angles_with_deployment_error, camera['angle_of_view'], camera['resolution'], pixel_error_std)

        camera['calibration'] = calib_functions.calculate_calibration_params(expected_pixels, expected_angles)
        camera['calculated_azimuth'] = camera['azimuth'] + camera['calibration'][1] - camera['angle_of_view']/2
        updated_cameras_data.append(camera)

    return updated_cameras_data



if __name__ == '__main__':
    # Data arrangement
    from data.general import *

    simulate_calibration(cameras_data, [(1, 10.5), (10, 9.5), (15, 15), (19, 9)], 10)

    NUMBER_OF_POINTS = 150
    ERROR = 30  # pixel white gaussian noise STD

    foo = lambda x: 0.6 * (x - 5.8) ** 3 + 1.5 * (x - 5.8) ** 2 + -1.1 * x + 13

    # Generate points using the sim_functions module
    simulated_points = sim_functions.generate_2d_points(foo, x_range=[1, 19], y_range=[1, 19], density=NUMBER_OF_POINTS)

    # Simulate measurements using the cameras_data and generated points
    measurements = simulate_data(cameras_data, simulated_points, noise_std=ERROR)

    # Estimate the position of the points using cameras_data and measurements
    estimated_points = estimate_position(cameras_data, measurements)

    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots()
    #
    # p = np.array(p)
    #
    # ax.plot(p[:, 0], p[:, 1], 'bo')
    # ax.plot(points[:, 0], points[:, 1], 'rx')
    # plt.show()
