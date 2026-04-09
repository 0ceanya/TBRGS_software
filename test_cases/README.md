# TBRGS Traffic Prediction Test Cases

Comprehensive test suite for validating deep LSTM traffic flow prediction models across diverse real-world scenarios. Each test case is drawn from the PEMS-BAY dataset with careful selection to capture distinct network characteristics.

**Web app:** the route page does not load the full `window` time series from disk, but you can pick each **`tc_*.json` example** from the **PEMS fixture** dropdown: `GET /api/test-cases` scans these files and returns `sensor_id_start`, `sensor_id_end`, and a suggested clock time from the README matrix. Separate **demo presets** are at `GET /api/scenarios`. Offline training/eval still uses the complete JSON.

## Dataset Background

**Source**: PEMS-BAY (California Bay Area traffic, Jan-Jun 2017)
- **Sensors**: 325 sensors across Bay Area highway network
- **Features per sensor**: Flow (veh/hr), Speed (mph), Time-of-day (fractional 0-1 scale)
- **Temporal granularity**: 5-minute intervals (12 steps = 60 minutes)
- **Speed range**: 14.1 - 72.7 mph (varies by location/traffic)
- **Flow range**: 580 - 1500 veh/hr (varies by road type)

Each test case selects 14-16 representative sensors on a potential route, mixing slow (congested), fast (free-flowing), and medium-speed links to create realistic prediction challenges.

## Test Case Matrix

| Case | Scenario | Avg Speed | Speed Range | Heterogeneity | Time Window | Key Challenge |
|------|----------|-----------|-------------|----------------|---------|-----------------|
| tc_001 | Edge Case | ~69 | High | Reference | - | Routing impossibility |
| tc_002 | Bottleneck Incident | 59.9 | 57.7 | **Extreme** | 10:00 AM | Incident handling |
| tc_003 | Network Congestion | 56.3 | 43.0 | High | 1:54 PM | System-wide stress |
| tc_004 | Clearing Trend | 59.7 | 39.6 | High | 5:32 PM | Temporal recovery |
| tc_005 | Free Flow | 67.2 | 15.0 | Low | 6:00 AM | Baseline accuracy |
| tc_006 | Urban-Highway Mix | 58.5 | 41.5 | High | 4:16 PM | Multi-class prediction |
| tc_007 | Congestion Building | 62.4 | 29.9 | Moderate | 9:07 AM | Onset detection |
| tc_008 | Evening Mixed | 64.6 | 35.2 | High | 7:41 PM | Post-peak patterns |
| tc_009 | Moderate Change | 66.7 | 17.3 | Moderate | 10:48 AM | Fine-grained accuracy |
| tc_010 | Uniform Network | 66.6 | 13.5 | Low | 1:12 PM | Homogeneous baseline |

## Scenario Details


### tc_001: Impossible Routing Scenario (Reference)
- **Purpose**: Edge case validation
- **Route**: Connects sensor 402365 → 401129 (reference routing scenario)  
- **Sensors**: 14 sensors spanning diverse speed classes
- **Characteristics**: Real mixed conditions with high variability
- **Model challenge**: Handle routing impossibility detection and fallback

### tc_002: Bottleneck Incident - Extreme Heterogeneity
- **Purpose**: Extreme network heterogeneity with localized incident
- **Source data**: Sample 24000 (highest dataset heterogeneity: 57.7 mph range)
- **Time window**: 10:00 AM (morning rush building)
- **Characteristics**:
  - 1 severely bottlenecked sensor (14.1 mph avg) - incident location
  - ~5 medium-speed sensors (40-50 mph)
  - ~8 free-flowing sensors (70+ mph)
- **Speed range**: 14.1 - 71.8 mph
- **Model challenge**: Predict through extreme variance; identify incident impact vs. normal flow

### tc_003: Network-wide Congestion - Multiple Bottlenecks
- **Purpose**: System-wide congestion with multiple problem areas
- **Source data**: Sample 12000 (43.0 mph heterogeneity range)
- **Time window**: 1:54 PM (midday peak)
- **Characteristics**:
  - Multiple sensors severely congested (28-40 mph)
  - Scattered free-flowing links (70+ mph)
  - No single dominant incident - distributed congestion
- **Speed range**: 28.2 - 71.2 mph
- **Model challenge**: Predict under system-wide stress; handle multi-source congestion

### tc_004: Congestion Clearing Trend  
- **Purpose**: Temporal recovery pattern detection
- **Source data**: Sample 8000 (improving trend: 62.9→65.8 mph over hour)
- **Time window**: 5:32 PM (evening rush clearing)
- **Characteristics**:
  - Speeds improve from start to finish
  - Mixed congestion transitioning away
  - Network moving from peak to off-peak
- **Speed range**: 31.5 - 71.1 mph
- **Model challenge**: Predict recovery trajectories; anticipate congestion clearing

### tc_005: Baseline Free-Flow Conditions
- **Purpose**: Normal operation baseline
- **Source data**: Sample 0 (homogeneous, low-variance conditions)
- **Time window**: 6:00 AM (early morning light traffic)
- **Characteristics**:
  - Relatively uniform network (57-72 mph)
  - Most sensors free-flowing (>65 mph)
  - Minimal congestion
- **Speed range**: 57.4 - 72.4 mph (lowest heterogeneity)
- **Model challenge**: Achieve high accuracy on baseline/normal conditions

### tc_006: Mixed Urban-Highway Network
- **Purpose**: Multi-class speed prediction
- **Source data**: Sample 16000 (distinct speed class mix)
- **Time window**: 4:16 PM (late afternoon)
- **Characteristics**:
  - Distinct link types: urban (30-50 mph), arterial (50-65 mph), highway (70+ mph)
  - Tests per-link-type speed prediction
  - Medium heterogeneity (41.5 mph range)
- **Speed range**: 30.7 - 72.2 mph
- **Model challenge**: Distinguish speed classes; predict appropriate speeds per infrastructure type

### tc_007: Rapid Congestion Building
- **Purpose**: Congestion onset and buildup detection
- **Source data**: Sample 20000 (building congestion trend)
- **Time window**: 9:07 AM (early morning rush building)
- **Characteristics**:
  - Network transitioning from light → peak congestion
  - Multiple sensors entering congestion state progressively
- **Speed range**: 41.9 - 71.8 mph
- **Model challenge**: Anticipate congestion onset; predict speed degradation

### tc_008: Heterogeneous Evening Conditions
- **Purpose**: Complex multi-pattern evening scenario
- **Source data**: Sample 28000 (mixed post-peak conditions)
- **Time window**: 7:41 PM (evening wind-down)
- **Characteristics**:
  - Residual congestion from earlier peak
  - Some links recovering, others still slow
  - Complex spatial patterns with high variance
- **Speed range**: 37.2 - 72.4 mph
- **Model challenge**: Handle complex post-peak conditions; mixed recovery patterns

### tc_009: Moderate Congestion with Gradual Change
- **Purpose**: Fine-grained speed prediction
- **Source data**: Sample 4000 (moderate heterogeneity, subtle evolution)
- **Time window**: 10:48 AM (mid-morning)
- **Characteristics**:
  - Moderate speed variance (17.3 mph range)
  - Stable conditions throughout interval
  - Subtle temporal evolution (not dramatic)
- **Speed range**: 57.9 - 75.2 mph
- **Model challenge**: Precise prediction without major events; maintain accuracy on stability

### tc_010: Light Heterogeneity - Mostly Uniform Flow
- **Purpose**: Homogeneous network baseline
- **Source data**: Sample 32000 (lowest selected heterogeneity)
- **Time window**: 1:12 PM (midday)
- **Characteristics**:
  - Narrow speed distribution (58-72 mph)
  - Minimal spatial variance  
  - Most sensors in 65-72 mph range
- **Speed range**: 58.2 - 71.7 mph
- **Model challenge**: High-accuracy prediction on homogeneous/uniform networks

## Data Format

Each JSON test case contains:
```json
{
  "sensor_id_start": "40XXXX",
  "sensor_id_end": "40XXXX",
  "scenario": "Scenario description",
  "window": {
    "40XXXX": [
      {
        "step": 1,
        "time_of_day": 0.42,
        "speed": 71.4,
        "flow": 815.3
      },
      ...
    ],
    ...
  }
}
```

**Field definitions**:
- `sensor_id_start/end`: Route endpoints for context (may not be in window list)
- `scenario`: Plain-language scenario description
- `window`: Dict of sensors on the route/network
  - `step`: 1-12 (sequential 5-minute intervals)
  - `time_of_day`: Fractional hours (0.0 = midnight, 0.5 = noon, 1.0 = next midnight)
  - `speed`: Miles per hour (realistic range: 14-72 mph)
  - `flow`: Vehicles per hour (realistic range: 580-1500 veh/hr)

## Data Characteristics

- **Window**: 12 timesteps = 1 hour, 5-minute intervals
- **Sensors per case**: 14-16 (variable like real routes)
- **Features per sensor/timestep**: flow, speed, time_of_day
- **Data source**: PEMS-BAY dataset (California Bay Area, Jan-Jun 2017)
- **Data quality**: Real sensor measurements, scaled to real-world units

## Generation Method

Test cases were generated through data-driven analysis:

1. **Dataset Analysis**: Analyzed all 41,674 training samples for heterogeneity patterns
2. **Sample Selection**: Ranked by speed variance to identify diverse network states
   - Sample 24000: Highest variance (57.7 mph range) - bottleneck scenario
   - Sample 12000: High variance (43.0 mph range) - system congestion
   - Sample 8000: Clearing trend detected - recovery scenario
   - Sample 0, 32000: Low variance (14-15 mph range) - baseline conditions
3. **Sensor Mixing**: Within each sample, selected sensors representing:
   - ~1/3 slow/congested sensors (<40 mph)
   - ~1/3 medium-speed sensors (50-65 mph)
   - ~1/3 fast/free-flowing sensors (70+ mph)
4. **De-normalization**: Inverse-scaled normalized dataset values to real-world units
5. **Time Assignment**: Assigned realistic time-of-day windows (6 AM - 8 PM) consistent with scenario traffic patterns
6. **Reproducibility**: Fixed `np.random.seed(42)` ensures deterministic sensor selection

## Validation Tips

When testing prediction models:
- **tc_001**: Should detect routing issue gracefully
- **tc_002**: Expect highest errors on sensor 400006 (severe bottleneck)
- **tc_003**: Watch for over-smoothing on multi-bottleneck scenario
- **tc_004**: Verify model captures improving trend (not static average)
- **tc_005**: Should achieve best overall accuracy (baseline)
- **tc_006**: Check per-class predictions separately (urban vs highway)
- **tc_007**: Model should not predict recovery when congestion is building
- **tc_008**: Complex case - expect moderate accuracy
- **tc_009**: Should achieve high accuracy (moderate, stable conditions)
- **tc_010**: Should achieve near-baseline accuracy (uniform network)
