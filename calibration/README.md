# Calibration Algorithm of a Single Camera

<p align="center">
  <img src="https://github.com/theguyben/VISTRKR/assets/64026118/08642094-e6b2-4802-8a24-e8f62201b5f7" />
</p>

# Calibration Functions
This Python file contains a library of functions related to calibration. The functions provided are summarized below:

## `calculate_expected_angles`
This function calculates the expected azimuth angles for a set of points relative to a camera position and azimuth angle. It takes two parameters:
- `camera_data`: A dictionary containing the position and azimuth angle in degrees of the camera.
- `points`: A list or array of $(x, y)$ coordinate pairs for the points of interest.
The function returns a list of expected azimuth angles (in degrees) for the given points relative to the camera position and azimuth angle.

## `calculate_calibration_params`
This function calculates the calibration parameters for converting measured pixel values to expected angle values. It takes three parameters:
- `measured_pixels`: A one-dimensional array containing measured pixel values.
- `expected_angles`: A one-dimensional array containing expected angle values.
- `fit_degree` (optional): An integer indicating the degree of polynomial fit to use. The default value is 1.
The function returns a tuple of floats representing the slope, intercept, and R^2 value for the fitted polynomial.

## `pixel2phi`
This function converts a pixel coordinate to a corresponding angle in degrees using calibration parameters of a camera. It takes two parameters:
- `pixel`: A float representing the pixel coordinate to be converted to an angle.
- `camera_data`: A dictionary containing camera calibration parameters, including slope and intercept.
The function returns the angle in radians corresponding to the input pixel coordinate, using the slope and intercept calibration parameters of the camera.
