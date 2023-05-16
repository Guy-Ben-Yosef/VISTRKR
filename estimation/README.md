# Object Position Estimation
This Python file contains functions for estimating the position of an object using the triangulation method. The functions provided are summarized below:

## `tand`
This function calculates the tangent of an angle in degrees. It takes one parameter:
- `x`: A float representing the angle in degrees.
The function returns the tangent of the angle.

## `triangulation`
This function computes the estimated $x$ and $y$ coordinates of an object using the triangulation method. It takes four parameters:
- `camera_a_data`: A dictionary containing the position and azimuth angle of camera A.
- `sight_angle_a`: A float representing the sight angle of camera A to the object in degrees.
- `camera_b_data`: A dictionary containing the position and azimuth angle of camera B.
- `sight_angle_b`: A float representing the sight angle of camera B to the object in degrees.
The function returns a numpy array containing the estimated $x$ and $y$ coordinates of the object.

## `triangulation_by_pairs`
This function performs triangulation for pairs of cameras and returns the result as a numpy array. It takes two parameters:
- `cameras_list`: A list of camera dictionaries, each containing the position and azimuth angle of a camera.
- `angle_by_camera`: A dictionary mapping camera names to sight angles in degrees.
The function returns a numpy array with the estimated $x$ and $y$ coordinates of the object for each camera pair, along with the maximum error for each estimated position.

## `get_error`
This function computes the maximum error for an estimated position of an object. It takes four parameters:
- `camera_a_data`: A dictionary containing the position and azimuth angle of camera A.
- `camera_b_data`: A dictionary containing the position and azimuth angle of camera B.
- `delta`: A float representing the incremental value used to compute the error.
- `target_position`: A numpy array representing the true X and Y coordinates of the object.
The function returns the maximum error for the estimated position of the object.

## `weighted_estimation`
This function computes the weighted average of a set of points. It takes two parameters:

- `points`: A numpy array containing the points to be averaged.
- `weights`: A numpy array containing the weights of each point.
The function returns the weighted average of the points.
