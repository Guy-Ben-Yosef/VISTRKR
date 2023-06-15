import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def plot_filled_sector(center, azimuth, radius, AOV, ax, sector_color='blue'):
    start_angle = azimuth - int(AOV/2)
    end_angle = azimuth + int(AOV/2)

    # Create a Wedge patch to represent the sector
    sector = patches.Wedge(center, radius, start_angle, end_angle, fc=sector_color)

    # Add the sector patch to the plot
    ax.add_patch(sector)
    ax.plot(center[0], center[1], 'r.', markersize=10)
