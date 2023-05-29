from calibration.calib_functions import *
from numpy.random import normal


def add_white_gaussian_noise(pixel, std):
    """
    Adds white Gaussian noise to a pixel value.

    @param pixel: (int) The pixel value to add noise to.
    @param std: (float) The standard deviation of the noise.
    @return: (int) The pixel value with added noise.
    """
    s = normal(0, std)
    return int(pixel + s)


def point2pixel(point, camera_data):
    """
    Converts a point to a pixel value for a given camera.

    @param point: (tuple of floats) A tuple containing the (x, y) coordinates of the point.
    @param camera_data: (dict) A dictionary containing the position, azimuth angle in degrees and calibration data of
           the camera.
    @return: (int) The pixel value representation of the point.
    """
    camera_position = camera_data['position']
    camera_azimuth = camera_data['azimuth']

    x, y = point

    phi = calculate_expected_angles(camera_data, point)

    pixel = phi2pixel(phi, camera_data['calibration'])

    return pixel


def phi2pixel(phi, calibration_data):
    """
    Converts an azimuth angle to a pixel value for a given camera.

    @param phi: (float) The azimuth angle in degrees.
    @param calibration_data: (tuple) A tuple containing the slope and intercept of the calibration data.
    @return: (int) The pixel value representation of the azimuth angle.
    """
    slope = calibration_data[0]
    intercept = calibration_data[1]

    pixel = round((phi - intercept) / slope)
    return pixel


def generate_2d_points(function, x_range, y_range, density):
    """
    Generate a list of 2D points on a plane using a given function.

    @param function: (callable) The function f(x) that defines the y-coordinate of the points.
                                It should take a NumPy array of x-values as input and return
                                a NumPy array of corresponding y-values.
    @param x_range: (tuple) The range of x-values (x_min, x_max) for generating points.
    @param y_range: (tuple) The range of y-values (y_min, y_max) to filter the points.
    @param density: (int) The number of points to generate between x_min and x_max.
    @return: (list) A list of generated points as tuples (x, y).
    """
    # Generate the x-coordinates
    x_values = np.linspace(x_range[0], x_range[1], density)

    # Evaluate the function at each x-coordinate to get the y-coordinates
    y_values = function(x_values)

    # Create a mask to filter out points outside the y-range
    mask = (y_range[0] <= y_values) & (y_values <= y_range[1])

    # Filter the x and y values based on the mask
    x_filtered = x_values[mask]
    y_filtered = y_values[mask]

    # Create a list to store the generated points
    points = []

    # Iterate over the filtered values and add them as tuples to the points list
    for i in range(len(x_filtered)):
        points.append((x_filtered[i], y_filtered[i]))

    return points


def calculate_expected_pixels(expected_angles, angle_of_view, image_size):
    """
    Calculate the expected pixel positions on an image given the expected angles.

    @param expected_angles: (float or list) The expected angles in degrees. If a single angle is provided, it will be
                            converted to a list.
    @param angle_of_view: (float) The camera's angle of view in degrees.
    @param image_size: (tuple) The size of the image in pixels (width, height).
    @return: (numpy.ndarray) An array containing the expected pixel positions.

    Note:
    The function assumes a centered perspective projection where the
    horizontal field of view is symmetric around the camera's forward
    direction.
    """
    # Ensure that expected_angles is a list
    if not isinstance(expected_angles, list):
        expected_angles = [expected_angles]

    horizontal_pixels_number = image_size[0]
    vertical_pixels_number = image_size[1]

    expected_pixels = np.zeros(len(expected_angles))

    # Calculate the expected pixel positions for each angle
    for i, angle in enumerate(expected_angles):
        # Convert angle to pixel position
        pixel = round((0.5 - angle/angle_of_view) * (horizontal_pixels_number - 1))
        expected_pixels[i] = pixel

    return expected_pixels
