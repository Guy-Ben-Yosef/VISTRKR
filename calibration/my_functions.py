import numpy as np


def lin_pix2ang(pix):
    # Convert pixel value to angle in degrees
    return (0.5 - (pix+1)/4608)*155 if pix>=0 else None


def get_calib_params(result, round=1):
    # Print the current round number
    print(f'Calibration done by round {round}')
    
    # Extract the vector of angles for the current round
    phi_vec = result[round, :]
    
    # Select the indices of the points at the minimum, maximum, and median angles
    i_min = 0 ; i_max = -1 ; i_med = len(phi_vec)//2
    
    # Select the expected and measured angles for the points at the minimum, maximum, and median angles
    poly_x = [result[0, i_min], result[0, i_med], result[0, i_max]]
    poly_y = [phi_vec[i_min], phi_vec[i_med], phi_vec[i_max]]
    
    # Fit a linear model to the data
    coef,  R2, _, _, _ = np.polyfit(poly_x, poly_y, deg=1, full=True)
    m = coef[0] ; b = coef[1] ; R2 = R2[0]
    
    # Create a mask to exclude the median point from the non-calibrated points
    mask_non_calib = np.arange(len(phi_vec)) != i_med
    mask_non_calib[0] = False ; mask_non_calib[-1] = False
    
    # Return the slope and intercept of the linear model and the mask for the non-calibrated points
    return m, b, R2, mask_non_calib
    

def tand(x):
    return np.tan(np.deg2rad(x))


def use_By_O(phi_By, phi_O):
    x = 10/(tand(phi_O + 45) - tand(phi_By))
    y = 10/(tand(phi_O + 45) - tand(phi_By))*tand(phi_By) + 10
    return np.array([x,y])


def use_By_Dx(phi_By, phi_Dx):
    x = (10 + 20*tand(phi_Dx + 135))/(tand(phi_Dx + 135) - tand(phi_By))
    y = (10 + 20*tand(phi_Dx + 135))/(tand(phi_Dx + 135) - tand(phi_By))*tand(phi_By) + 10
    return np.array([x,y])


def use_Dx_O(phi_Dx, phi_O):
    x = (20*tand(phi_Dx + 135))/(tand(phi_Dx + 135) - tand(phi_O + 45))
    y = (20*tand(phi_Dx + 135))/(tand(phi_Dx + 135) - tand(phi_O + 45))*tand(phi_O + 45)
    return np.array([x,y])
    
    
def get_error(use_A_B, expected_A, expected_B, delta, true_pos):
    pp = np.sqrt(sum((use_A_B(expected_A + delta, expected_B + delta) - true_pos)**2))
    mm = np.sqrt(sum((use_A_B(expected_A - delta, expected_B - delta) - true_pos)**2))
    pm = np.sqrt(sum((use_A_B(expected_A + delta, expected_B - delta) - true_pos)**2))
    mp = np.sqrt(sum((use_A_B(expected_A - delta, expected_B + delta) - true_pos)**2))
    return max([pp, mm, pm, mp])


def generate_circle(center, radius):
    theta = np.linspace(0,2*np.pi, 200)
    return center[0] + radius*np.cos(theta), center[1] + radius*np.sin(theta)