"""A* pathfinding on the dungeon grid, with eight-way movement.

Monsters use this to walk around corners and pillars instead of grinding into
the nearest wall. Other actors count as soft obstacles: passing through them
is allowed but expensive, so a crowd shuffles around itself instead of
deadlocking in a corridor.
"""
import heapq

# eight neighbours; diagonals cost slightly more so paths look natural
_NEIGHBOURS = (
    (1, 0, 10), (-1, 0, 10), (0, 1, 10), (0, -1, 10),
    (1, 1, 14), (1, -1, 14), (-1, 1, 14), (-1, -1, 14),
)

SOFT_BLOCK_COST = 100   # extra cost for stepping onto another actor


def _heuristic(x1, y1, x2, y2):
    """Octile distance - admissible for eight-way movement."""
    dx, dy = abs(x1 - x2), abs(y1 - y2)
    return 10 * (dx + dy) - 6 * min(dx, dy)


def astar(walkable, start, goal, extra_cost=None, max_nodes=4000):
    """Return the list of steps from start (exclusive) to goal (inclusive).

    walkable(x, y) -> bool; extra_cost(x, y) -> int adds a soft penalty.
    Returns [] when no route exists or the search budget runs out.
    """
    if start == goal:
        return []

    open_heap = [(0, start)]
    came_from = {}
    cost_so_far = {start: 0}
    expanded = 0

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            break

        expanded += 1
        if expanded > max_nodes:
            return []

        cx, cy = current
        for dx, dy, step in _NEIGHBOURS:
            nx, ny = cx + dx, cy + dy
            neighbour = (nx, ny)
            # the goal itself is always enterable - that is where we attack
            if neighbour != goal and not walkable(nx, ny):
                continue
            new_cost = cost_so_far[current] + step
            if extra_cost is not None and neighbour != goal:
                new_cost += extra_cost(nx, ny)
            if neighbour not in cost_so_far or new_cost < cost_so_far[neighbour]:
                cost_so_far[neighbour] = new_cost
                priority = new_cost + _heuristic(nx, ny, goal[0], goal[1])
                heapq.heappush(open_heap, (priority, neighbour))
                came_from[neighbour] = current

    if goal not in came_from:
        return []

    path = []
    node = goal
    while node != start:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path
