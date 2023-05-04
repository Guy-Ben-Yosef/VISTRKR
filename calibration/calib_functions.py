"""Calibration related functions library"""
import warnings
import numpy as np


def calculate_expected_angles(camera_position, points, camera_azimuth):
    expected_angles = []
    for point in points:
        x = point[0]
        y = point[1]
        delta_x = x - camera_position[0]  # Calculate the difference in x coordinates
        delta_y = y - camera_position[1]  # Calculate the difference in y coordinates
        azimuth = np.rad2deg(np.arctan2(delta_y, delta_x)) - camera_azimuth  # Calculate the azimuth angle
        expected_angles.append(azimuth)
    return expected_angles


def calculate_calibration_params(measured_pixels, expected_angles, fit_degree):
    coefficients, residuals, _, _, _, = np.polyfit(measured_pixels, expected_angles, deg=fit_degree, full=True)
    slope = coefficients[0]
    intercept = coefficients[1]
    residuals = residuals[0]

    # Compute R^2
    total_sum_of_squares = sum((expected_angles - np.mean(expected_angles)) ** 2)
    r_squared = 1 - (residuals / total_sum_of_squares)

    if r_squared < 0.95:
        warnings.warn(f"Too small residual (R^2 = {r_squared:0.3f})")

    # Return the slope, intercept, R^2, and mask for the non-calibrated points
    return slope, intercept, r_squared
