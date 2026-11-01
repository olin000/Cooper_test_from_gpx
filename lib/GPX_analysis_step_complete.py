import logging
import gpxpy
import numpy as np
import plotly.graph_objects as go

logger = logging.getLogger('db')


def calculate_cooper_test(gpx_file_input):
    """
    Parses a GPX file and computes the rolling 12-minute Cooper test performance.

    Args:
        gpx_file_input: file object, file-like object, or string containing GPX data.

    Returns:
        tuple: (result_dict, error_message)
               If successful, (result_dict, None)
               If failed, (None, error_message)
    """
    # Read GPX content
    try:
        if hasattr(gpx_file_input, 'read'):
            content = gpx_file_input.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
        elif isinstance(gpx_file_input, bytes):
            content = gpx_file_input.decode('utf-8', errors='replace')
        elif isinstance(gpx_file_input, str):
            content = gpx_file_input
        else:
            return None, "Invalid file input type."

        gpx = gpxpy.parse(content)
    except Exception as e:
        logger.exception("Failed to parse GPX file")
        return None, f"Could not parse GPX file: {str(e)}"

    # Collect all GPS points across all tracks, segments, and routes
    points = []
    if gpx.tracks:
        for track in gpx.tracks:
            for segment in track.segments:
                for p in segment.points:
                    if p.time is not None and p.latitude is not None and p.longitude is not None:
                        points.append((p.time, p.latitude, p.longitude, p.elevation))

    if not points and gpx.routes:
        for route in gpx.routes:
            for p in route.points:
                if p.time is not None and p.latitude is not None and p.longitude is not None:
                    points.append((p.time, p.latitude, p.longitude, p.elevation))

    if len(points) < 2:
        return None, "Not enough GPS trackpoints with valid timestamps found in the file."

    # Sort strictly by timestamp
    points.sort(key=lambda x: x[0])

    # Convert timestamps to elapsed seconds from start
    t0 = points[0][0]
    times_sec = np.array([(p[0] - t0).total_seconds() for p in points], dtype=np.float64)
    lats = np.array([p[1] for p in points], dtype=np.float64)
    lons = np.array([p[2] for p in points], dtype=np.float64)
    elevations = np.array([p[3] if p[3] is not None else np.nan for p in points], dtype=np.float64)

    # Filter out duplicate or out-of-order timestamps
    time_diffs = np.diff(times_sec)
    valid_mask = np.insert(time_diffs > 0, 0, True)
    if not np.all(valid_mask):
        times_sec = times_sec[valid_mask]
        lats = lats[valid_mask]
        lons = lons[valid_mask]
        elevations = elevations[valid_mask]

    total_duration = times_sec[-1] - times_sec[0]
    if total_duration < 720:
        mins = int(total_duration // 60)
        secs = int(total_duration % 60)
        return None, (
            f"Activity duration ({mins}m {secs}s) is shorter than the required 12 minutes (720s) "
            "for a Cooper test."
        )

    # Vectorized Haversine distance
    lat_rad = np.radians(lats)
    lon_rad = np.radians(lons)
    dlat = np.diff(lat_rad)
    dlon = np.diff(lon_rad)

    a = (np.sin(dlat / 2.0) ** 2 +
         np.cos(lat_rad[:-1]) * np.cos(lat_rad[1:]) * np.sin(dlon / 2.0) ** 2)
    a = np.clip(a, 0.0, 1.0)
    d2d = 2.0 * 6371000.0 * np.arcsin(np.sqrt(a))

    # 3D Distance if elevation data exists
    if np.all(np.isnan(elevations)):
        d3d = d2d
    else:
        d_alt = np.diff(elevations)
        d_alt = np.nan_to_num(d_alt, nan=0.0)
        d3d = np.sqrt(d2d ** 2 + d_alt ** 2)

    # Cumulative distance at recorded points
    cum_dist = np.insert(np.cumsum(d3d), 0, 0.0)

    # Resample to 1-second intervals via linear interpolation
    total_seconds = int(np.floor(total_duration))
    second_grid = np.arange(0, total_seconds + 1)
    dist_1s = np.interp(second_grid, times_sec, cum_dist)

    # 720-second (12-minute) rolling distance
    cooper_dist = dist_1s[720:] - dist_1s[:-720]
    if len(cooper_dist) == 0:
        return None, "Unable to calculate 12-minute window distance."

    cumulative_max = np.maximum.accumulate(cooper_dist)
    max_value = float(np.max(cooper_dist))
    best_idx = int(np.argmax(cooper_dist))

    # VO2max estimation: Cooper formula
    vo2max = (max_value - 504.9) / 44.73

    min_value = float(np.min(cooper_dist[cooper_dist > 0])) if np.any(cooper_dist > 0) else 0.0
    min_axis = max(min_value * 0.98, 0.0)
    max_axis = max_value * 1.02

    # Plotly traces
    x = np.arange(len(cooper_dist))
    bar_trace = go.Bar(
        x=x,
        y=cooper_dist,
        marker=dict(color='steelblue', line=dict(width=0)),
        name='Trials'
    )
    line_trace = go.Scatter(
        x=x,
        y=cumulative_max,
        mode='lines',
        line=dict(color='red', width=2),
        name='Maximum'
    )

    layout = go.Layout(
        xaxis=dict(title='12-minute Window Starting Second (Trial)'),
        yaxis=dict(title='Cooper test distance (m)', range=[min_axis, max_axis]),
        legend=dict(x=0.75, y=1.15, traceorder='reversed'),
        bargap=0,
        bargroupgap=0,
        title=f"Fastest 12m: {round(max_value, 1)} m | Estimated VO2max: {round(vo2max, 1)} ml/kg/min",
        template='plotly_white',
        autosize=True
    )

    text_annotation = go.layout.Annotation(
        x=best_idx,
        y=max_value,
        text=f"{round(max_value, 1)} m",
        showarrow=True,
        arrowhead=2,
        font=dict(color='blue', size=12)
    )
    layout.annotations = [text_annotation]

    fig = go.Figure(data=[bar_trace, line_trace], layout=layout)
    fig.update_traces(marker_line_width=0)

    # Use CDN for plotlyjs to keep response small and fast
    chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

    return {
        'chart': chart_html,
        'max_value': round(max_value, 1),
        'vo2max': round(vo2max, 1),
        'best_start_second': best_idx,
        'total_distance': round(float(cum_dist[-1]), 1),
        'total_duration_sec': int(total_duration),
    }, None


def readgpx(gpxfile):
    """
    Backward-compatible wrapper for legacy callers.
    """
    result, error_msg = calculate_cooper_test(gpxfile)
    if error_msg:
        return None, False
    return result, True
