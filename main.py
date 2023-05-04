import numpy as np
from calibration.save_camera_position import save_values
from calibration import calib_functions


def test():
    expected_angles = calib_functions.calculate_expected_angles(camera_position=[0, 0], points=[[1, 2], [1/2, 1/3]], camera_azimuth=45)
    pixels = [2000, 3000]
    calib_functions.calculate_calibration_params(measured_pixels=pixels, expected_angles=expected_angles, fit_degree=1)
    return expected_angles


if __name__ == '__main__':
    print(test())