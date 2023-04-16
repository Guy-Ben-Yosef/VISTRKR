"""
This code bla bla bla...
"""
import numpy as np  # comment


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
    print_hi('PyCharm')
