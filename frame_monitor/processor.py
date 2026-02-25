import numpy as np
from bokeh.models import Span


# Shared global state
global_index = 0
total_nominal = 0.0
total_measured = 0.0
cube_count = 0
is_first_cube = True
cube_boundaries = []  # list of start frame_index for each cube
cube_frame_counts = []  # number of frames (including gap row) per cube


def update(data_queue, config, source_global, source_global_eff, source_rolling, source_cube_eff, p1, p2, p3, p4):
    global global_index, total_nominal, total_measured, cube_count, is_first_cube, cube_boundaries, cube_frame_counts

    while not data_queue.empty():
        gap, intra_dts, exptime, num_frames = data_queue.get()
        if num_frames == 0:
            continue

        plot_dt = np.insert(intra_dts, 0, gap)
        n_plot = len(plot_dt)
        assert n_plot == num_frames, f"plot_dt length mismatch: {n_plot} vs {num_frames}"

        start_index = global_index
        frame_idx = np.arange(start_index, start_index + n_plot)
        nominal = np.full(n_plot, exptime)

        # Hide gap marker on first cube
        if is_first_cube:
            plot_dt[0] = 0.0
            is_first_cube = False

        # Accumulate global, include gaps
        global_index += num_frames
        total_nominal += num_frames * exptime
        total_measured += np.sum(plot_dt)
        cumulative_eff = total_nominal / total_measured if total_measured > 1e-9 else 1.0

        # ── Global plots ───────────────────────────────────────────────
        new_global_data = {
            'frame_index': frame_idx.tolist(),
            'measured_dt': plot_dt.tolist(),
            'nominal': nominal.tolist()
        }
        source_global.stream(new_global_data, rollover=None)

        new_eff_data = {
            'frame_index': frame_idx.tolist(),
            'efficiency': np.full(n_plot, cumulative_eff).tolist()
        }
        source_global_eff.stream(new_eff_data, rollover=None)

        # Manual truncate global sources
        for src, max_len in [(source_global, config.max_frames_global), (source_global_eff, config.max_frames_global)]:
            current_len = len(src.data['frame_index'])
            if current_len > max_len:
                src.data = {k: v[-max_len:] for k, v in src.data.items()}

        p1.x_range.start = max(0, global_index - config.max_frames_global)
        p1.x_range.end = global_index + 5
        p3.x_range.start = max(0, global_index - config.max_frames_global)
        p3.x_range.end = global_index + 5

        # ── Rolling cubes and per-cube eff (excludes cube gap) ────────────
        source_rolling.stream(new_global_data, rollover=None)

        cube_count += 1
        cube_boundaries.append(start_index)
        cube_frame_counts.append(n_plot)

        vline = Span(location=start_index, dimension='height',
                     line_color='tomato', line_alpha=0.5, line_dash='dotted', line_width=2)
        p2.add_layout(vline)

        # Per-cube efficiency excluding gap
        intra_sum = np.sum(intra_dts) + exptime
        cube_eff = (num_frames * exptime) / intra_sum if intra_sum > 1e-9 else 1.0
        source_cube_eff.stream(
            {'frame_index': [start_index], 'efficiency': [cube_eff]},
            rollover=config.rolling_cubes
        )

        print(f"Cube {cube_count:3d} eff = {cube_eff:6.4f} | global eff = {cumulative_eff:6.4f}")

        # Truncate rolling data by whole cubes
        if cube_count > config.rolling_cubes:
            keep_n = sum(cube_frame_counts[-config.rolling_cubes:])
            new_data = {k: source_rolling.data[k][-keep_n:] for k in source_rolling.data}
            source_rolling.data = new_data

            # Drop old metadata
            cube_boundaries = cube_boundaries[-config.rolling_cubes:]
            cube_frame_counts = cube_frame_counts[-config.rolling_cubes:]

        # Adjust x-ranges
        left = cube_boundaries[0] if cube_boundaries else 0
        p2.x_range.start = left
        p2.x_range.end = global_index + 5
        p4.x_range.start = left
        p4.x_range.end = global_index + 5