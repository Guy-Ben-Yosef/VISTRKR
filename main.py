import numpy as np
from calibration import calib_functions
from estimation import estim_functions



def calibrate_cameras(cameras_data, calibrationd_data):



if __name__ == '__main__':
    cam_a_dat = {'position': (1.72, 3.35), 'azimuth': 333}
    cam_b_dat = {'position': (11.22, -1.44), 'azimuth': 153.5}
    print(estim_functions.get_error(cam_a_dat, cam_b_dat, .5, np.array([8.9, -0.31])))
