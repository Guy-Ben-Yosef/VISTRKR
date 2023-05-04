"""header"""

import numpy as np
import pandas as pd
from numpy import tan, rad2deg, deg2rad, array, zeros, sqrt

def tand(x):
    return np.tan(np.deg2rad(x))


def use_By_O(phi_By, phi_O):
    x = 10/(tand(phi_O + 45) - tand(phi_By))
    y = 10/(tand(phi_O + 45) - tand(phi_By))*tand(phi_By) + 10
    return np.array([x,y])


def get_error(use_A_B, expected_A, expected_B, delta, true_pos):
    pp = np.sqrt(sum((use_A_B(expected_A + delta, expected_B + delta) - true_pos)**2))
    mm = np.sqrt(sum((use_A_B(expected_A - delta, expected_B - delta) - true_pos)**2))
    pm = np.sqrt(sum((use_A_B(expected_A + delta, expected_B - delta) - true_pos)**2))
    mp = np.sqrt(sum((use_A_B(expected_A - delta, expected_B + delta) - true_pos)**2))
    return max([pp, mm, pm, mp])


def calc_errors():
    pass
