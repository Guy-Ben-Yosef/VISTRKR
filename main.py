import numpy as np

import calibration.calib_functions
from calibration.save_camera_position import save_values
from calibration import calib_functions
from estimation import estim_functions


def test_calib():
    expected_angles = calib_functions.calculate_expected_angles(
        camera_data={'position': (0, 0), 'azimuth': 45}, points=[(1, 1), (4.8, 4), (5.32, 6.87), (7.84, 9.22)])
    pixels = [1.85, -2.92, 8.8, 6.23]
    m, b, R = calib_functions.calculate_calibration_params(
        measured_pixels=pixels, expected_angles=expected_angles, fit_degree=1)
    return m, b, R


def test_estim():
    camera_a_data = {'position': (20, 0), 'azimuth': 135}
    camera_b_data = {'position': (0, 0), 'azimuth': 45}

    import matplotlib.pyplot as plt

    deltas = np.arange(0, 20, 0.1)
    result = np.zeros(deltas.shape)
    for i, delta in enumerate(deltas):
        error = estim_functions.get_error(camera_a_data, camera_b_data, delta, np.array([10, 10]))
        result[i] = error

    fig, ax = plt.subplots()
    ax.plot(deltas, result)
    ax.set_xlabel("Delta")
    ax.set_ylabel("Error")
    plt.show()
    return result[result < 0.5][-1]


if __name__ == '__main__':
    cam_a_dat = {'position': (1.72, 3.35), 'azimuth': 333}
    cam_b_dat = {'position': (11.22, -1.44), 'azimuth': 153.5}
    print(estim_functions.get_error(cam_a_dat, cam_b_dat, .5, np.array([8.9, -0.31])))
