import numpy as np
from calibration.save_camera_position import save_values
from calibration import calib_functions


def test():
    expected_angles = calib_functions.calculate_expected_angles(
        camera_position=[0, 0], points=[(1, 1), (4.8, 4), (5.32, 6.87), (7.84, 9.22)], camera_azimuth=45)
    pixels = [1.85, -2.92, 8.8, 6.23]
    m, b, R = calib_functions.calculate_calibration_params(
        measured_pixels=pixels, expected_angles=expected_angles, fit_degree=1)
    return m, b, R


if __name__ == '__main__':
    print(test())