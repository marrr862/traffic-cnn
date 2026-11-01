"""Windowed statistics on the video's time axis."""
import math


def flow_windows(events, frames, fps, interval_seconds=10):
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('FPS must be finite and positive')
    if not math.isfinite(interval_seconds) or interval_seconds <= 0:
        raise ValueError('Interval must be finite and positive')
    if not frames:
        raise ValueError('Frame statistics must not be empty')
    duration = len(frames) / fps
    windows = []
    for index in range(math.ceil(duration / interval_seconds)):
        start = index * interval_seconds
        end = min(duration, start + interval_seconds)
        windows.append(dict(start_seconds=start, end_seconds=end, duration_seconds=end-start,
                            crossings=0, negative_to_positive=0, positive_to_negative=0,
                            mean_visible_tracked_vehicles=0, peak_visible_tracked_vehicles=0,
                            event_rate_per_hour=0, frame_count=0))
    density_sums = [0.0] * len(windows)
    density_frames = [0] * len(windows)
    speeds = [[] for _ in windows]
    for frame in frames:
        index = min(int((frame['frame']/fps) / interval_seconds), len(windows)-1)
        window = windows[index]
        visible = frame['visible_tracked_vehicles']
        window['frame_count'] += 1
        window['mean_visible_tracked_vehicles'] += visible
        window['peak_visible_tracked_vehicles'] = max(window['peak_visible_tracked_vehicles'], visible)
        value = frame.get('density_per_km')
        if value is not None and value == value and value != '':
            density_sums[index] += float(value)
            density_frames[index] += 1
    for event in events:
        timestamp = event['frame'] / fps
        if not 0 <= timestamp < duration:
            raise ValueError('Event frame is outside the video')
        direction = event['direction']
        if direction not in ('negative_to_positive', 'positive_to_negative'):
            raise ValueError('Unknown crossing direction')
        index = min(int(timestamp / interval_seconds), len(windows)-1)
        window = windows[index]
        window['crossings'] += 1
        window[direction] += 1
        speed = event.get('speed_kmh')
        try:
            speed = float(speed)
        except (TypeError, ValueError):
            speed = None
        if speed is not None and speed > 0 and math.isfinite(speed):
            speeds[index].append(speed)
    calibrated = any(density_frames)
    for i, window in enumerate(windows):
        count = window['frame_count']
        window['mean_visible_tracked_vehicles'] = window['mean_visible_tracked_vehicles']/count if count else 0
        window['event_rate_per_hour'] = window['crossings'] * 3600 / window['duration_seconds']
        if calibrated or any(speeds):
            window['mean_speed_kmh'] = sum(speeds[i])/len(speeds[i]) if speeds[i] else None
            window['space_mean_speed_kmh'] = len(speeds[i])/sum(1/s for s in speeds[i]) if speeds[i] else None
            window['mean_density_per_km'] = density_sums[i]/density_frames[i] if density_frames[i] else None
    return windows
