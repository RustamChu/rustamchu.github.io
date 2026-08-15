"""Recursive shadowcasting field of view.

The map is swept in eight octants; each recursion narrows the visible slope
range around obstacles. It is O(visible tiles) rather than O(rays x steps),
which is why it stays fast even with a large torch radius, and unlike naive
ray casting it never leaves "pinhole" artefacts behind wall corners.
"""

# octant transformation matrices: xx, xy, yx, yy
_MULT = (
    (1, 0, 0, -1, -1, 0, 0, 1),
    (0, 1, -1, 0, 0, -1, 1, 0),
    (0, 1, 1, 0, 0, -1, -1, 0),
    (1, 0, 0, 1, -1, 0, 0, -1),
)


def compute_fov(blocks_sight, mark_visible, ox, oy, radius):
    """blocks_sight(x, y) -> bool, mark_visible(x, y, distance_squared)."""
    mark_visible(ox, oy, 0)
    for octant in range(8):
        _cast(blocks_sight, mark_visible, ox, oy, 1, 1.0, 0.0, radius,
              _MULT[0][octant], _MULT[1][octant],
              _MULT[2][octant], _MULT[3][octant])


def _cast(blocks_sight, mark_visible, cx, cy, row, start, end, radius,
          xx, xy, yx, yy):
    if start < end:
        return
    radius_sq = radius * radius

    for j in range(row, radius + 1):
        dx, dy = -j - 1, -j
        blocked = False
        new_start = start

        while dx <= 0:
            dx += 1
            x = cx + dx * xx + dy * xy
            y = cy + dx * yx + dy * yy

            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)

            if start < r_slope:
                continue
            if end > l_slope:
                break

            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius_sq:
                mark_visible(x, y, dist_sq)

            if blocked:
                if blocks_sight(x, y):
                    new_start = r_slope
                    continue
                blocked = False
                start = new_start
            elif blocks_sight(x, y) and j < radius:
                blocked = True
                _cast(blocks_sight, mark_visible, cx, cy, j + 1,
                      start, l_slope, radius, xx, xy, yx, yy)
                new_start = r_slope

        if blocked:
            break
