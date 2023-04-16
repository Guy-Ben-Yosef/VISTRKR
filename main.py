import numpy as np

from calibration.save_camera_position import save_values
# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    a = np.array([1, 2, 3])
    print(a)
    print(f'Bye, {name}')  # Press Ctrl+F8 to toggle the breakpoint.

    b = np.array([4, 5, 6])
    print(b)

    c = np.array([7, 8, 9])
    print(c)

    d = np.array([10, 11, 12])
    print(a, b, c, d)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parameters = {'name': 'try1',
                  'value': 3}
    save_values(parameters)

