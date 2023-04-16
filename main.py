import numpy as np  # comment


def print_hi(name):
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
