"""
This script monitors a directory for new FITS files matching a specified prefix,
reads the telemetry times from corresponding .txt files, and plots the timing
information in real-time using Bokeh.


There are two main processes:
1. A watchdog observer thread that detects new FITS files, reads the telemetry,
   and puts timing data into a shared queue.
2. A Bokeh periodic callback that processes the queue, updates global and rolling
   timing plots, and calculates efficiency metrics.
   
   
Plots in the Bokeh dashboard:
    - Global Exposure Timing
        Shows the measured delta(time) for each frame compared to the nominal
        exposure time (white dashed line). This includes any timing gap between
        cubes. A mismatch between the measured time from the exposure time
        indicates dropped frames in the cube or dropped frames before the
        beginning of the cube.
    - Recent Cubes
        Shows timing for frames in the most recent N cubes, with vertical
        lines marking cube boundaries. This excludes the gap between cubes
        (i.e. the inter-cube timing). A mismatch between the data from the
        exposure time indicates dropped frames within the cube.
    - Global Efficiency
        Shows the cumulative efficiency of the exposures over time. This
        includes all effects -- dropped frames within the cubes, dropped frames
        between cubes, and any other timing issues.
    - Efficiency per Cube
        Shows the efficiency of each cube individually, excluding the gap between
        cubes.
        
        
To Run:
    bokeh serve --show frame_monitor --args --data-dir ./data/ --file-prefix fake_frame --rolling-cubes 5 --max-frames-global 100_000
"""

import queue
import sys
import threading
from bokeh.plotting import curdoc, figure
from bokeh.models import ColumnDataSource, DataRange1d, Range1d
from bokeh.layouts import gridplot

from .config import parse_args
from .watcher import start_observer
from .processor import update

# Parse arguments (passed via --args)
CONFIG = parse_args(sys.argv[1:])

# Shared queue
data_queue = queue.Queue()

# Data sources
source_global = ColumnDataSource(dict(frame_index=[], measured_dt=[], nominal=[]))
source_global_eff = ColumnDataSource(dict(frame_index=[], efficiency=[]))
source_rolling = ColumnDataSource(dict(frame_index=[], measured_dt=[], nominal=[]))
source_cube_eff = ColumnDataSource(dict(frame_index=[], efficiency=[]))



# Create plots
from bokeh.plotting import figure   

p1 = figure(
    title=f"Global Exposure Timing (last ~{CONFIG.max_frames_global} frames)",
    x_axis_label="Frame Index",
    y_axis_label="Δt (seconds)",
    height=300, width=800,
    tools="pan,wheel_zoom,box_zoom,reset,save"
)
r1 = p1.line("frame_index", "measured_dt", source=source_global, line_width=1.5, color="#42A5F5")
p1.line("frame_index", "nominal", source=source_global, line_dash="dashed", color="white", line_alpha=0.7, line_width=2)
p1.y_range = DataRange1d(only_visible=True, renderers=[r1])
p1.x_range = Range1d(start=0, end=1)



p2 = figure(
    title=f"Recent {CONFIG.rolling_cubes} Cubes",
    x_axis_label="Frame Index",
    y_axis_label="Δt (seconds)",
    height=300, width=600,
    tools="pan,wheel_zoom,box_zoom,reset,save"
)
r2 = p2.line("frame_index", "measured_dt", source=source_rolling, line_width=1.5, color="#42A5F5")
p2.line("frame_index", "nominal", source=source_rolling, line_dash="dashed", color="white", line_alpha=0.7, line_width=2)
p2.y_range = DataRange1d(only_visible=True, renderers=[r2])
p2.x_range = Range1d(start=0, end=1)



p3 = figure(
    title="Global Efficiency (cumulative, rolling window)",
    x_axis_label="Frame Index", y_axis_label="Efficiency",
    height=250, width=800,
    tools="pan,wheel_zoom,box_zoom,reset,save"
)
r3 = p3.line("frame_index", "efficiency", source=source_global_eff, line_width=2, color="#42A5F5")
p3.y_range = DataRange1d(only_visible=True, renderers=[r3], bounds=(0, None))
p3.x_range = Range1d(start=0, end=1)



p4 = figure(
    title=f"Efficiency per Cube (last {CONFIG.rolling_cubes} cubes)",
    x_axis_label="Frame Index (cube start)", y_axis_label="Cube Efficiency",
    height=250, width=600,
    tools="pan,wheel_zoom,box_zoom,reset,save"
)
r4 = p4.line("frame_index", "efficiency", source=source_cube_eff, line_width=2, color="#42A5F5")
p4.circle("frame_index", "efficiency", source=source_cube_eff, size=8, color="#42A5F5", line_color="white")
p4.y_range = DataRange1d(only_visible=True, renderers=[r4], bounds=(0, None))
p4.x_range = Range1d(start=0, end=1)



# Setup Bokeh document
curdoc().add_root(gridplot([[p2, p1], [p4, p3]], sizing_mode="stretch_both"))
curdoc().title = f"{CONFIG.file_prefix} Timing Monitor"
curdoc().theme = "carbon"



# Periodic callback
curdoc().add_periodic_callback(
    lambda: update(
        data_queue,
        CONFIG,
        source_global,
        source_global_eff,
        source_rolling,
        source_cube_eff,
        p1, p2, p3, p4
    ),
    400  
)

# Start observer in background thread
threading.Thread(target=start_observer, args=(data_queue, CONFIG), daemon=True).start()