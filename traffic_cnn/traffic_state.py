"""Macroscopic traffic characteristics: density, level of service, q = k·v."""
import math

# HCM basic freeway segment density thresholds, passenger cars per km per lane
# (11, 18, 26, 35, 45 pc/mi/ln converted and rounded).
LOS_THRESHOLDS = [(7, 'A'), (11, 'B'), (16, 'C'), (22, 'D'), (28, 'E')]
LOS_DESCRIPTION = {
    'A': 'Ազատ երթևեկություն', 'B': 'Մոտ ազատ երթևեկություն', 'C': 'Կայուն հոսք',
    'D': 'Մոտ անկայուն հոսք', 'E': 'Թողունակության սահման', 'F': 'Խցանում',
}


def level_of_service(density_per_lane):
    if density_per_lane is None or not math.isfinite(density_per_lane) or density_per_lane < 0:
        return None
    for limit, grade in LOS_THRESHOLDS:
        if density_per_lane <= limit:
            return grade
    return 'F'


def density(vehicles_in_zone, length_m, lanes=None):
    """Vehicles per km (and per km per lane when the lane count is known)."""
    if length_m <= 0:
        raise ValueError('Zone length must be positive')
    k = vehicles_in_zone / (length_m / 1000)
    return k, (k / lanes if lanes else None)


def fundamental_check(flow_per_hour, density_per_km, space_mean_kmh):
    """Compare measured flow q with k·v_s (fundamental relation of traffic flow)."""
    if density_per_km is None or space_mean_kmh is None:
        return None
    predicted = density_per_km * space_mean_kmh
    return dict(measured_flow_per_hour=flow_per_hour, density_times_speed=predicted,
                relative_difference=(flow_per_hour - predicted) / predicted if predicted else None)


# Above the HCM basic freeway segment capacity (about 2400 pc/h/ln); a higher measured
# flow means an accelerated video, a duplicate-counting tracker or a wrong lane count.
MAX_FLOW_PER_LANE = 2400


def plausibility_issues(median_kmh=None, rejected=0, rejected_share=0.0, flow_per_lane=None, fundamental=None):
    """Reasons why measured speed or flow are physically implausible (empty list when none)."""
    issues = []
    if median_kmh is not None and median_kmh > 160:
        issues.append('median_speed_above_160')
    if rejected >= 10 and rejected_share > 0.3:
        issues.append('speeds_above_250')
    if flow_per_lane is not None and flow_per_lane > MAX_FLOW_PER_LANE:
        issues.append('flow_above_lane_capacity')
    if fundamental and fundamental.get('density_times_speed') and fundamental['measured_flow_per_hour'] > 0:
        ratio = fundamental['measured_flow_per_hour']/fundamental['density_times_speed']
        if not 0.5 <= ratio <= 2:
            issues.append('flow_density_speed_mismatch')
    return issues
