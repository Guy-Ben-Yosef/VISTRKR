import numpy as np
from calibration import calib_functions
from estimation import estim_functions


def calibrate_cameras(cameras_data, calibration_data):
    """
    Calibrates a list of cameras using calibration data.

    @param cameras_data: (List[Dict]) A list of camera dictionaries, each containing camera data.
    @param calibration_data: (Dict) A dictionary containing calibration data, including pixel and point information.
    @return: List[Dict] A list of camera dictionaries, each updated with calibration information.
    """
    pixels = calibration_data['pixels']
    points = calibration_data['points']

    updated_cameras_data = []
    for camera in cameras_data:
        expected_angles = calib_functions.calculate_expected_angles(camera, points)
        camera['calibration'] = calib_functions.calculate_calibration_params(pixels[camera['name']], expected_angles)

        updated_cameras_data.append(camera)
    return updated_cameras_data


def estimate_position(cameras_data, measurements):
    """
    Estimates the position of a point using measurements from a list of cameras.
    @param cameras_data:
    @param measurements:
    @return:
    """
    # Calculate the expected angles for each camera
    expected_angles = []
    for camera in cameras_data:
        expected_angles.append(calib_functions.calculate_expected_angles(camera, measurements['pixels']))
    expected_angles = np.array(expected_angles)

    # Calculate the position estimate
    position_estimate = estim_functions.calculate_position_estimate(cameras_data, expected_angles)

    return position_estimate


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
    x, y = estimate_position(cameras_data, measurements)
