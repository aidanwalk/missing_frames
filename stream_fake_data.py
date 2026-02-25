"""
Generates a bunch of fake FITS files every few seconds to test the 
frame_monitor.py script.

"""

import os
import time
from astropy.io import fits
import numpy as np


if __name__ == "__main__":
    FRATE = 5                   # frame rate in Hz
    CUBE_SIZE = 10              # Number of frames in each datacube
    RATE = 1.0 / FRATE          # time interval between frames in seconds
    SAVE_DIR = "./data/"        # Directory to save the files to 
    
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    
    while True:
        timestamp = time.time()
        filename = os.path.join(SAVE_DIR, f"fake_frame_{timestamp}.fits")
        
        # Generate frames and telemetry individually to simulate real conditions
        data = []
        telemetry_times = []
        while len(data) < CUBE_SIZE:
            # Drop frames randomly to simulate missing frames
            if np.random.rand() < 0.1:  # 10% chance to drop a frame
                time.sleep(RATE)  # Still wait for the time interval
                continue
            
            image = np.random.rand(10, 10)  # Example 10x10 image data
            frame_time = time.time()
            telemetry_time = frame_time + np.random.normal(0, RATE/10)  # Add some jitter to telemetry time
            data.append(image)
            telemetry_times.append(telemetry_time)
            time.sleep(RATE)  # Simulate time delay between frames
        
        
        data = np.array(data)  # Shape (CUBE_SIZE, 10, 10)
        
        tel_array = np.zeros((CUBE_SIZE, 5))  # Assuming 5 telemetry columns
        tel_array[:, 4] = telemetry_times  # First column is the timestamps
        
        # Create a FITS file with the random data and an exposure time in the header
        hdu = fits.PrimaryHDU(data)
        hdu.header['EXPTIME'] = RATE  # Example exposure time in seconds
        hdu.writeto(filename, overwrite=True)
        
        # Create the telemetry file with the corresponding times
        telemetry_filename = f"./data/fake_frame_{timestamp}.txt"
        np.savetxt(telemetry_filename, tel_array)
        
        print(f"Generated new fake frame: {filename}")
        # Wait a bit before generating the next cube to simulate between-cube gaps
        time.sleep(0.5)  