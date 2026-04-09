# LSTM Model Placeholder

Drop the trained LSTM model file here as `best_model.pt`.

## Integration Steps

1. Place `best_model.pt` in this directory
2. Edit `src/prediction/lstm_provider.py`:
   - Implement the LSTM model class matching your training architecture
   - Fill in the `predict()` method to load the model and run inference
3. The system will automatically detect it via `is_available()`

## Expected Interface

The provider must return `PredictionResult` objects with:
- `sensor_flows`: dict mapping sensor_id -> predicted flow (veh/hr)
- `timestep_minutes`: prediction horizon (5, 10, 15, ...)
- `model_name`: "lstm"
