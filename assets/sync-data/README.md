# Sync Data Samples
# TODO: Add sample sync data patterns for testing

This directory will contain:

- JSON files with sync patterns for sample videos
- Templates for creating new sync data
- Testing patterns for development
- Calibration data for different experience types

Sample sync data structure:
```json
{
  "video_id": "sample_001",
  "duration": 60.0,
  "sync_events": [
    {
      "time": 5.2,
      "type": "vibration",
      "intensity": 0.8,
      "duration": 500
    }
  ]
}
```

Experience types:
- vibration: Motor control patterns
- scent: Fragrance release timing
- temperature: Heating/cooling cycles
- wind: Fan control patterns