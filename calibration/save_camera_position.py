""""
 DroNet-2023
"""

import json
import os

def save_values(parameters) -> None:
    """
    function that gets parameters type .... 
    saving file in json type for each camera.
    """
    output_directory = 'data'

    # Create the directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Set the path
    output_file_path = os.path.join(output_directory, 'parameters.json')

    # 'w' for write mode
    with open(output_file_path, 'w', encoding='utf-8') as form:
        json.dump(parameters, form)
