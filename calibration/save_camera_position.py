# DroNet-2023
# This function will save calibration values of a specific camera

import json, os

def save_values(parameters) -> None:
    output_directory = 'data'
   
    # Create the directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Set the path 
    output_file_path = os.path.join(output_directory, 'parameters.json')

    # 'w' for write mode
    with open(output_file_path, 'w', encoding='utf-8') as f:        
        json.dump(parameters, f)

