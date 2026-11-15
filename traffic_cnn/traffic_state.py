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


# HCM treats trucks and buses together as heavy vehicles. The detector separates them well on road
# cameras (about 2% confusion on MIO-TCD) but not on unfamiliar vehicles such as a European box truck
# seen head-on, so counts are also reported by group, where that confusion does not matter.
VEHICLE_GROUPS = {'car': 'light', 'van': 'light', 'truck': 'heavy', 'bus': 'heavy', 'motorcycle': 'motorcycle'}


def vehicle_groups(by_class):
    """Counts per group (light, heavy, motorcycle; unknown class names go to other) and the heavy-vehicle share."""
    groups = {'light': 0, 'heavy': 0, 'motorcycle': 0}
    for name, count in by_class.items():
        group = VEHICLE_GROUPS.get(name, 'other')
        groups[group] = groups.get(group, 0) + count
    total = sum(groups.values())
    return groups, (groups['heavy'] / total if total else None)


# HCM 6th ed. passenger-car equivalent of a heavy vehicle on level terrain (E_T); cars, vans and motorcycles count as 1.
HEAVY_VEHICLE_PCE = 2.0


def directional_los(observations, frames, length_m, lanes, min_share=0.1):
    """HCM-style level of service per travel direction.

    observations: (frame, direction, vehicle_class) for every vehicle seen inside the zone. Density is in
    passenger cars per km per lane: heavy vehicles weigh HEAVY_VEHICLE_PCE, and each direction has its own
    lanes (split evenly between the directions that carry at least min_share of the observations; a zone
    on one carriageway gets all lanes for its single direction). Returns the per-direction results and the
    worst grade. An indication only: HCM grades a 15-minute period, not a short video.
    """
    if frames <= 0 or length_m <= 0 or not lanes:
        return None
    totals, weights = {}, {}
    for _, direction, vehicle_class in observations:
        totals[direction] = totals.get(direction, 0) + 1
        weights[direction] = weights.get(direction, 0.0) + (HEAVY_VEHICLE_PCE if VEHICLE_GROUPS.get(vehicle_class) == 'heavy' else 1.0)
    seen = sum(totals.values())
    if not seen:
        return None
    main = [d for d in totals if totals[d] >= min_share*seen]
    lanes_each = lanes/len(main)
    result = {}
    for direction in sorted(totals):
        if direction not in main:
            result[direction] = dict(share=totals[direction]/seen, lanes=None, level_of_service=None)
            continue
        per_lane = weights[direction]/frames/(length_m/1000)/lanes_each
        result[direction] = dict(share=totals[direction]/seen, lanes=lanes_each, mean_pc_density_per_km_per_lane=per_lane,
                                 level_of_service=level_of_service(per_lane))
    worst = max((r for r in result.values() if r['level_of_service']), key=lambda r: r['mean_pc_density_per_km_per_lane'])
    return dict(by_direction=result, level_of_service=worst['level_of_service'], heavy_vehicle_pce=HEAVY_VEHICLE_PCE)


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
