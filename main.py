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
    number_of_measurements = len(pixels_by_camera[cameras_list[0]['name']])
    expected_angles = {}
    for camera in cameras_list:
        expected_angles_for_camera = []
        for pixel in pixels_by_camera[camera['name']]:
            expected_angles_for_camera.append(calib_functions.pixel2phi(pixel, camera))
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
    elif not isinstance(cameras_list, list):
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



if __name__ == '__main__':
    # Data arrangement
    from data.experiment_data import *
    calibration_data = {}
    calibration_data['points'] = list(p_i_locations.values())
    calibration_data['pixels'] = {'O': list(data_O.values()),
                                  'Dx': list(data_Dx.values()),
                                  'By': list(data_By.values())}

    cam_O = {'name': 'O', 'position': (0, 0), 'azimuth': 45}
    cam_Dx = {'name': 'Dx', 'position': (20, 0), 'azimuth': 135}
    cam_By = {'name': 'By', 'position': (0, 10), 'azimuth': 0}

    # Calibrate cameras
    cameras_data = calibrate_cameras([cam_O, cam_Dx, cam_By], calibration_data)

    foo = lambda x: 1.5 * np.cos(x / 1.2) + 1.2 * x

    p = sim_functions.generate_2d_points(foo, x_range=[2, 18], y_range=[2, 18], density=50)

    measurements = simulate_data(cameras_data[0], p, noise_std=20)
    points = estimate_position(cameras_data, measurements)

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()

    p = np.array(p)

    ax.plot(p[:, 0], p[:, 1], 'bo')
    ax.plot(points[:, 0], points[:, 1], 'rx')
    plt.show()
