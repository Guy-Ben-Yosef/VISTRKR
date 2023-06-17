from calibration.calib_functions import *
from numpy.random import normal


def add_white_gaussian_noise(pixel, std):
    """
    Adds white Gaussian noise to a pixel value.

    @param pixel: (int) The pixel value to add noise to.
    @param std: (float) The standard deviation of the noise.
    @return: (int) The pixel value with added noise.
    """
    if isinstance(pixel, int):
        s = normal(0, std)
        return int(pixel + s)
    elif isinstance(pixel, tuple) and len(pixel) == 2:
        return add_white_gaussian_noise(pixel[0], std), add_white_gaussian_noise(pixel[1], std)
    else: # Raise an error if the pixel is not an integer or tuple of length 2
        raise TypeError("pixel must be an integer or tuple of length 2.")


def point2pixel(point, camera_data):
    """
    Converts a point to a pixel value for a given camera.

    @param point: (tuple of floats) A tuple containing the (x, y) coordinates of the point.
    @param camera_data: (dict) A dictionary containing the position, azimuth angle in degrees and calibration data of
           the camera.
    @return: (tuple) The pixel values representation of the point.
    """
    camera_position = camera_data['position']
    camera_azimuth = camera_data['azimuth']
    camera_elevation = camera_data['elevation']

    expected_azimuth, expected_elevation = calculate_expected_angles(camera_data, point)

    pixel_horizontal = phi2pixel(expected_azimuth, camera_data['calibration']['azimuth'])
    pixel_vertical = phi2pixel(expected_elevation, camera_data['calibration']['elevation'])

    return pixel_horizontal, pixel_vertical


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


def generate_3d_points(function, x_range, y_range, z_range, density):
    """
    Generate a list of 3D points on a space using a given function.

    @param function: (callable) The function f(x) that defines the y-coordinate of the points.
                                It should take a NumPy array of x-values as input and return
                                a NumPy array of corresponding y-values.
    @param x_range: (tuple) The range of x-values (x_min, x_max) for generating points.
    @param y_range: (tuple) The range of y-values (y_min, y_max) to filter the points.
    @param z_range: (tuple) The range of z-values (z_min, z_max) for generating points.
    @param density: (int) The number of points to generate between x_min and x_max.
    @return: (list) A list of generated points as tuples (x, y).
    """
    # Generate the x-coordinates
    x_values = np.linspace(x_range[0], x_range[1], density)

    # Evaluate the function at each x-coordinate to get the y-coordinates
    y_values = function(x_values)

    z_values = np.linspace(z_range[0], z_range[1], density)

    # Create a mask to filter out points outside the y-range
    mask = (y_range[0] <= y_values) & (y_values <= y_range[1])

    # Filter the x and y values based on the mask
    x_filtered = x_values[mask]
    y_filtered = y_values[mask]
    z_filtered = z_values[mask]

    # Create a list to store the generated points
    points = []

    # Iterate over the filtered values and add them as tuples to the points list
    for i in range(len(x_filtered)):
        points.append((x_filtered[i], y_filtered[i], z_filtered[i]))

    return points


def calculate_expected_pixels(expected_angles, angle_of_view, image_size, std):
    """
    Calculate the expected pixel positions on an image given the expected angles.

    @param expected_angles: (tuple of floats or lists) The expected angles in degrees. If a single angles is provided,
                            it will be converted to a lists.
    @param angle_of_view: (float) The camera's angle of view in degrees.
    @param image_size: (tuple) The size of the image in pixels (width, height).
    @param std: (float) The standard deviation of the white Gaussian noise to add to the pixel values.
    @return: (numpy.ndarray) An array containing the expected pixel positions.

    Note:
    The function assumes a centered perspective projection where the
    horizontal field of view is symmetric around the camera's forward
    direction.
    """
    # Ensure that the expected angles is lists
    for k in range(2):
        if not isinstance(expected_angles[k], list):
            expected_angles[k] = [expected_angles[k]]
    expected_azimuths, expected_elevations = expected_angles  # Unpack the expected angles
    if len(expected_azimuths) != len(expected_elevations):
        raise ValueError('The number of azimuths and elevations must be equal.')

    n = len(expected_azimuths)

    horizontal_pixels_number = image_size[0]
    vertical_pixels_number = image_size[1]

    expected_pixels = np.zeros([n, 2])

    # Calculate the expected pixel positions for each angle
    for i in range(n):
        azimuth = expected_azimuths[i]
        elevation = expected_elevations[i]

        # Convert angle to pixel position
        pixel_horizontal = round((0.5 - azimuth/angle_of_view) * (horizontal_pixels_number - 1))
        pixel_vertical = round((0.5 - elevation / angle_of_view) * (vertical_pixels_number - 1))

        expected_pixels[i, 0] = add_white_gaussian_noise(pixel_horizontal, std)
        expected_pixels[i, 1] = add_white_gaussian_noise(pixel_vertical, std)

    return expected_pixels


def generate_calibration_points(x_limits, y_limits, z_limits, number_of_points):
    """
    Generate a list of 3D points on a space using a given function.
    @param x_limits: (list or tuple) The range of x-values (x_min, x_max) for generating points.
    @param y_limits: (list or tuple) The range of y-values (y_min, y_max) for generating points.
    @param z_limits: (list or tuple) The range of z-values (z_min, z_max) for generating points.
    @param number_of_points: (int) The number of points to generate between x_min and x_max.
    @return: (list of tuples) A list of generated points as tuples (x, y, z).
    """
    random_x_values = np.random.uniform(x_limits[0], x_limits[1], number_of_points)
    random_y_values = np.random.uniform(y_limits[0], y_limits[1], number_of_points)
    random_z_values = np.random.uniform(z_limits[0], z_limits[1], number_of_points)

    result = []
    for i in range(number_of_points):
        result.append((random_x_values[i], random_y_values[i], random_z_values[i]))

    return result
