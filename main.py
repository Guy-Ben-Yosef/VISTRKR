import numpy as np
import math
import os
import xml.etree.ElementTree as ET

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
    """
    Estimate the position using triangulation based on camera pixels.

    Args:
        @param: cameras_list (list): A list of dictionaries representing cameras.
                Each camera dictionary should have keys: 'name', 'calibration'.
        @param: pixels_by_camera (dict): A dictionary mapping camera names to pixel values.
                The pixel values can be either a single pixel or a list of pixels.

    Returns:
        @return: numpy.ndarray: A 2D array representing the estimated positions.
                 Each row corresponds to a measurement, and the columns represent the X, Y, and Z coordinates.
    """
    # Determine the number of measurements
    if not isinstance(pixels_by_camera[cameras_list[0]['name']], list):
        number_of_measurements = 1
    else:
        number_of_measurements = len(pixels_by_camera[cameras_list[0]['name']])

    expected_angles = {}

    # Calculate the expected angles for each camera
    for camera in cameras_list:
        expected_angles_for_camera = []

        # Validate that the pixel is iterable
        if not isinstance(pixels_by_camera[camera['name']], list):
            pixels_by_camera[camera['name']] = [pixels_by_camera[camera['name']]]

        for pixel in pixels_by_camera[camera['name']]:
            expected_angles_for_camera.append(calib_functions.pixel2phi(camera['calibration'], pixel))

        expected_angles[camera['name']] = expected_angles_for_camera

    pixel_dim = len(pixels_by_camera[camera['name']][0])
    dimensions = pixel_dim + 1  # Recall that a 2D image represents 3D space

    # Initialize the array to store points and weights for each pair of cameras
    points_weights_by_pairs = np.zeros([math.comb(len(cameras_list), 2), dimensions + 1, number_of_measurements])

    # Perform triangulation for each measurement
    for k in range(number_of_measurements):
        angle_by_camera = {}
        for m in range(len(cameras_list)):
            camera_name = cameras_list[m]['name']
            angle_by_camera[camera_name] = expected_angles[camera_name][k]

        points_weights_by_pairs[:, :, k] = estim_functions.triangulation_by_pairs(cameras_list, angle_by_camera)

    # Perform weighted estimation for each measurement
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
    if not (isinstance(calibration_points, list) or isinstance(calibration_points, np.ndarray)):
        raise TypeError('`calibration_points` must be an array of points.')
    # Ensure that `calibration_points` contains at least 3 points
    if len(calibration_points) < 3:
        raise ValueError('At least 3 calibration points are required.')

    updated_cameras_data = []
    for camera in cameras_list:
        expected_azimuths, expected_elevations = calib_functions.calculate_expected_angles(camera, calibration_points)

        azimuth_error = np.random.normal(0, angle_error_std)
        elevation_error = np.random.normal(0, angle_error_std)

        camera['simulated_azimuth'] = camera['azimuth'] + azimuth_error
        camera['simulated_elevation'] = camera['elevation'] + elevation_error

        azimuths_with_deployment_error = (np.array(expected_azimuths) - azimuth_error).tolist()
        elevations_with_deployment_error = (np.array(expected_elevations) - elevation_error).tolist()

        expected_pixels = sim_functions.calculate_expected_pixels(
            (azimuths_with_deployment_error, elevations_with_deployment_error),
            camera['angle_of_view'], camera['resolution'], pixel_error_std)

        camera['calibration'] = {}
        camera['calibration']['azimuth'] = calib_functions.calculate_calibration_params(
            expected_pixels[:, 0], expected_azimuths)
        camera['calibration']['elevation'] = calib_functions.calculate_calibration_params(
            expected_pixels[:, 1], expected_elevations)

        camera['calculated_azimuth'] = camera['azimuth'] + \
                                       camera['calibration']['azimuth'][1] - camera['angle_of_view'] / 2
        camera['calculated_elevation'] = camera['elevation'] + \
                                         camera['calibration']['elevation'][1] - camera['angle_of_view'] / 2

        updated_cameras_data.append(camera)

    return updated_cameras_data


def write_cameras_data_to_xml(cameras_data_list, filename):
    """
    Writes a list of camera dictionaries to an XML file.
    @param cameras_data_list: (list) List of camera dictionaries, each containing camera parameters
    @param filename: (string) Name of the XML file to be written
    """
    root = ET.Element('cameras_data')
    root.text = '\n'

    for camera in cameras_data_list:
        camera_elem = ET.SubElement(root, 'camera')
        camera_elem.text = '\n\t'
        camera_elem.tail = '\n\t'

        id = ET.SubElement(camera_elem, 'ID')
        id.text = camera['name']
        id.tail = '\n\t\t'

        position_elem = ET.SubElement(camera_elem, 'position')
        position_elem.text = ','.join(str(coord) for coord in camera['position'])
        position_elem.tail = '\n\t\t'

        azimuth_elem = ET.SubElement(camera_elem, 'azimuth')
        azimuth_elem.text = str(camera['azimuth'])
        azimuth_elem.tail = '\n\t\t'

        elevation_elem = ET.SubElement(camera_elem, 'elevation')
        elevation_elem.text = str(camera['elevation'])
        elevation_elem.tail = '\n\t\t'

        angle_of_view_elem = ET.SubElement(camera_elem, 'angle_of_view')
        angle_of_view_elem.text = str(camera['angle_of_view'])
        angle_of_view_elem.tail = '\n\t\t'

        resolution_elem = ET.SubElement(camera_elem, 'resolution')
        resolution_elem.text = ','.join(str(res) for res in camera['resolution'])
        resolution_elem.tail = '\n\t\t'

        # Save simulated azimuth and elevation only if they exist
        if 'simulated_azimuth' in camera:
            simulated_azimuth_elem = ET.SubElement(camera_elem, 'simulated_azimuth')
            simulated_azimuth_elem.text = str(camera['simulated_azimuth'])
            simulated_azimuth_elem.tail = '\n\t\t'
        if 'simulated_elevation' in camera:
            simulated_elevation_elem = ET.SubElement(camera_elem, 'simulated_elevation')
            simulated_elevation_elem.text = str(camera['simulated_elevation'])
            simulated_elevation_elem.tail = '\n\t\t'

        # Save calibration parameters only if they exist
        if 'calibration' in camera:
            calibration_elem = ET.SubElement(camera_elem, 'calibration')
            calibration_elem.text = '\n\t\t\t'
            calibration_elem.tail = '\n\t\t'

            azimuth_calibration_elem = ET.SubElement(calibration_elem, 'azimuth')
            azimuth_calibration_elem.text = ','.join(str(val) for val in camera['calibration']['azimuth'])
            azimuth_calibration_elem.tail = '\n\t\t\t'

            elevation_calibration_elem = ET.SubElement(calibration_elem, 'elevation')
            elevation_calibration_elem.text = ','.join(str(val) for val in camera['calibration']['elevation'])
            elevation_calibration_elem.tail = '\n\t\t\t'

    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)


def read_cameras_data_from_xml(filename):
    """
    Reads camera data from an XML file and returns a list of camera dictionaries.
    @param filename: (string) Name of the XML file to be read
    @return: (list) List of camera dictionaries
    """
    tree = ET.parse(filename)
    root = tree.getroot()

    cameras_data_list = []

    for camera_elem in root.findall('camera'):
        camera_dict = {}

        camera_dict['name'] = camera_elem.find('ID').text

        position_text = camera_elem.find('position').text
        camera_dict['position'] = tuple([float(coord) for coord in position_text.split(',')])

        camera_dict['azimuth'] = float(camera_elem.find('azimuth').text)
        camera_dict['elevation'] = float(camera_elem.find('elevation').text)
        camera_dict['angle_of_view'] = float(camera_elem.find('angle_of_view').text)

        resolution_text = camera_elem.find('resolution').text
        camera_dict['resolution'] = tuple([int(res) for res in resolution_text.split(',')])

        # Read simulated azimuth and elevation only if they exist
        if camera_elem.find('simulated_azimuth') is not None and camera_elem.find('simulated_elevation') is not None:
            camera_dict['simulated_azimuth'] = float(camera_elem.find('simulated_azimuth').text)
            camera_dict['simulated_elevation'] = float(camera_elem.find('simulated_elevation').text)

        # Read calibration parameters only if they exist
        if camera_elem.find('calibration') is not None:
            calibration_dict = {}
            calibration_elem = camera_elem.find('calibration')

            azimuth_calib_text = calibration_elem.find('azimuth').text
            calibration_dict['azimuth'] = [float(val) for val in azimuth_calib_text.split(',')]

            elevation_calib_text = calibration_elem.find('elevation').text
            calibration_dict['elevation'] = [float(val) for val in elevation_calib_text.split(',')]

            camera_dict['calibration'] = calibration_dict

        cameras_data_list.append(camera_dict)

    return cameras_data_list


if __name__ == '__main__':
    from data.general import *
    # calibration_points = [(10, 8, 0), (5, 5, 5*np.sqrt(2)), (10, 12, 10)]
    cameras_data = simulate_calibration(cameras_data, calibration_points, angle_error_std=10, pixel_error_std=30)

    # Get the current path and go to sub-folder named 'data'
    p = os.path.join(os.getcwd(), 'data', 'cameras_data.xml')

    # Write the cameras data to an XML file
    write_cameras_data_to_xml(cameras_data, p)

    N = 60
    rounds = 2
    max_z = 5
    t = np.linspace(0, rounds * 2 * np.pi, N)
    x = np.cos(t)
    y = np.sin(t)
    z = np.linspace(0, max_z, N)
    points = np.stack((x, y, z), axis=1)
    points_as_list = []
    for i in range(points.shape[0]):
        points_as_list.append(tuple(points[i, :]))
    measurements_by_camera = simulate_data(cameras_data, points_as_list, noise_std=20)
    ps = estimate_position(cameras_data, measurements_by_camera)

    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    for point in points_as_list:
        ax.scatter(point[0], point[1], point[2], marker='*', c='b')
    for point in ps:
        ax.scatter(point[0], point[1], point[2], marker='s', c='r')

    fig.show()
