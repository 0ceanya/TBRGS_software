<<<<<<< HEAD
## Summary of test case scenario
tc_001 - impossible path routing
tc_002 - 
tc_003 -
tc_004 - 
tc_005 -
tc_006 - 
tc_007 -
tc_008 - 
tc_009 - 
tc_010 -
=======
# Test Cases

13 test cases covering route finding, algorithm comparison, travel time conversion, and error handling.

## Summary

| ID | Category | Description | Origin | Destination | Algorithm | k |
|----|----------|-------------|--------|-------------|-----------|---|
| tc_001 | route_finding | Full 325-sensor window snapshot (legacy) | 402365 | 401129 | -- | -- |
| tc_002 | route_finding | Adjacent sensors - 1-hop minimal route | 400030 | 400971 | A* | 5 |
| tc_003 | route_finding | Medium distance route (~10km) | 400343 | 400274 | A* | 5 |
| tc_004 | route_finding | Long distance (~26km), full network span | 400750 | 401507 | A* | 5 |
| tc_005 | route_finding | Single optimal route (k=1) | 402365 | 401129 | A* | 1 |
| tc_006 | algorithm_comparison | Uninformed: BFS | 401224 | 400952 | BFS | 5 |
| tc_007 | algorithm_comparison | Uninformed: DFS | 401224 | 400952 | DFS | 5 |
| tc_008 | algorithm_comparison | Informed: GBFS | 401224 | 400952 | GBFS | 5 |
| tc_009 | algorithm_comparison | Informed: CUS2 (BALA*) | 401224 | 400952 | CUS2 | 5 |
| tc_010 | route_finding | Maximum diversity (k=10) | 400715 | 402120 | A* | 10 |
| tc_011 | route_finding | Reverse direction of tc_001 | 401129 | 402365 | A* | 5 |
| tc_012 | travel_time | Flow-to-speed formula at key values | -- | -- | -- | -- |
| tc_013 | error_handling | Invalid sensors and bad parameters | -- | -- | -- | -- |

## Categories

### Route Finding (tc_001 to tc_005, tc_010, tc_011)
Tests the core route guidance pipeline across varying distances (adjacent, short, medium, long) and configurations (single route, multiple routes, reverse direction, maximum k).

### Algorithm Comparison (tc_006 to tc_009)
Same origin/destination pair (401224 -> 400952) tested with different search algorithms to enable direct comparison of route quality and path characteristics.

### Travel Time Conversion (tc_012)
Verifies the flow-to-speed quadratic formula at boundary values: zero flow, threshold (351), moderate traffic, heavy traffic, and capacity (1500 veh/hr).

### Error Handling (tc_013)
Verifies the system handles invalid inputs gracefully: nonexistent sensor IDs and same origin/destination.

## File Format

Each JSON test case contains:
```json
{
  "test_case_id": "tc_XXX",
  "description": "Human-readable description",
  "category": "route_finding | algorithm_comparison | travel_time | error_handling",
  "input": { ... },
  "expected_output": { ... }
}
```

## Running

Automated test validation via pytest:
```bash
python -m pytest tests/ -v
```

All test cases are also accessible via the web UI at `/testing`.
>>>>>>> c20f361 (Add main application logic, update requirements, and document test cases)
