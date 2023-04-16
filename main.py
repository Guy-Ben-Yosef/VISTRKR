import numpy as np
from calibration.save_camera_position import save_values

# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    """
    Prints a greeting and arrays using NumPy.
    Args:
        name (str): The name to include in the greeting.
    Returns:
        None: This function does not return any value.
    Raises:
        N/A
    Example:
        >>> print_hi("Alice")
        [1 2 3]
        Bye, Alice
        [4 5 6]
        [7 8 9]
        [10 11 12]
        [1 2 3] [4 5 6] [7 8 9] [10 11 12]
    """
    first = np.array([1, 2, 3])
    print(first)
    print(f'Bye, {name}')

    second = np.array([4, 5, 6])
    print(second)

    third = np.array([7, 8, 9])
    print(third)

    fourth = np.array([10, 11, 12])
    print(first, second, third, fourth)


if __name__ == '__main__':
    parameters = {'name': 'try1',
                  'value': 3}
    save_values(parameters)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
