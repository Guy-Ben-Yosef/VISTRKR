'''This file is for blah bla bla'''
import numpy as np


def lin_pix2ang(pix, total_pix_num, angle_of_view):
    """
    Converts pixel coordinates to angular coordinates using linear interpolation.
    
    Args:
    pix (int): The pixel coordinate to convert.
    total_pix_num (int): The total number of pixels.
    angle_of_view (float): The angle of view in degrees.
    
    Returns:
    float or None: The angular coordinate in degrees if pix >= 0, otherwise None.
    """
    return (0.5 - (pix + 1) / total_pix_num) * angle_of_view if pix >= 0 else None


def calculate_calibration_params(expected_angles, measured_angles):
    """
    Calculate calibration parameters from expected and measured angles.

    This function takes in two 1D arrays of expected and measured angles, and calculates the slope (m) and
    intercept (b) of the linear model fitted to the expected and measured angles at the minimum, maximum, and
    median angles. It also computes the coefficient of determination (R^2) to evaluate the goodness of fit of
    the linear model. Additionally, it creates a mask to exclude the median point from the non-calibrated points.

    Args:
    expected_angles (numpy.ndarray): A 1D array of expected angles.
    measured_angles (numpy.ndarray): A 1D array of measured angles.

    Returns:
    float: The slope (m) of the linear model.
    float: The intercept (b) of the linear model.
    float: The coefficient of determination (R^2).
    numpy.ndarray: A boolean mask indicating the non-calibrated points.
    """
    # Select the indices of the points at the minimum, maximum, and median angles
    index_min, index_max, index_median = (0, -1, len(expected_angles) // 2)

    # Select the expected and measured angles for the points at the minimum, maximum, and median angles
    expected_angles_points = [expected_angles[index_min], expected_angles[index_median], expected_angles[index_max]]
    measured_angles_points = [measured_angles[index_min], measured_angles[index_median], measured_angles[index_max]]

    # Fit a linear model to the data
    coef, residuals, _, _, _ = np.polyfit(expected_angles_points, measured_angles_points, deg=1, full=True)
    slope = coef[0]
    intercept = coef[1]
    residuals = residuals[0]

    # Compute R^2
    total_sum_of_squares = sum((measured_angles - np.mean(measured_angles))**2)
    r_squared = 1 - (residuals / total_sum_of_squares)

    # Create a mask to exclude the median point from the non-calibrated points
    mask_non_calibrated = np.arange(len(measured_angles)) != index_median
    mask_non_calibrated[0] = False
    mask_non_calibrated[-1] = False

    # Return the slope, intercept, R^2, and mask for the non-calibrated points
    return slope, intercept, r_squared, mask_non_calibrated




def foo(p_i_locations, data, base_locations, cam_data):
    # Initialize the result array with nan values
    result = np.zeros([4, len(p_i_locations)])
    result[:] = np.nan
    # Populate the final row of the result array with indices
    for i in range(result.shape[1]):
        result[-1, i] = i

    cam = cam_data['name']
    cam_data = data[cam]
    for i in range(result.shape[1]):  # Iterate different points
        point_name = f'p{i:02d}'  # Format the point name as a string
        if p_i_locations[point_name] is None:  # Skip the point if its location isn't available
            continue
        delta_x = p_i_locations[point_name][0] - base_locations[cam][0]    # Calculate the difference in x coordinates
        delta_y = p_i_locations[point_name][1] - base_locations[cam][1]    # Calculate the difference in y coordinates
        azimuth = np.rad2deg(np.arctan2(delta_y, delta_x)) - cam_data['a']  # Calculate the azimuth angle
        result[0, i] = azimuth  # Store the expected azimuth angle in the result array
        result[1, i] = lin_pix2ang(cam_data[point_name][0], cam_data['total_pix_num'], cam_data['AOV'])  # Store the measurements in the result array
