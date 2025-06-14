# Backend API

This backend provides REST APIs and WebSocket connections for:

- **Track Management**: Recording, editing, and following GPS-based navigation tracks
- **Camera Integration**: Multi-camera system with OAK-D devices for depth sensing and RGB streaming
- **Point Cloud Processing**: 3D point cloud generation, alignment, and fusion from multiple cameras
- **Line Following**: Automated row-based farming operations with turn calibration

## Architecture

```
backend/
├── main.py                # FastAPI application entry point
├── config.py              # Configuration and global settings
├── routers/               # API route handlers
│   ├── tracks.py          # Track CRUD operations
│   ├── record.py          # Track recording functionality
│   ├── follow.py          # Track following and robot control
│   ├── linefollow.py      # Line-based navigation for farming rows
│   └── pointcloud.py      # Point cloud management APIs
├── cameraBackend/         # Camera and point cloud processing
│   ├── camera.py          # OAK-D camera interface
│   ├── oakManager.py      # Multi-camera coordination
│   ├── pointCloud.py      # Point cloud fusion and alignment
│   └── syncQueue.py       # Frame synchronization utilities
├── tracks/                # Stored navigation tracks (JSON)
├── lines/                 # Stored line navigation data (JSON)
├── calibration_data/      # Camera calibration files
└── pointcloud_data/       # Generated point cloud files
```

## Development Quickstart

### Hardware Requirements

- Farm-ng Amiga robot platform
- OAK-D cameras connected to Amiga (up to 3 supported)
- Network connectivity for camera communication

### Software Requirements

- Python 3.8+
- DepthAI SDK for OAK cameras
- farm-ng SDK for robot integration
- Access to farm-ng robot
- SSH perms to farm-ng robot

### Runing the Backend

```bash
# install dependencies
pip install fastapi uvicorn
pip install depthai opencv-python numpy
pip install open3d
pip install farm-ng-core farm-ng-track farm-ng-field_perimeter

# run server
python main.py

# test camera system
python test.py
# Use 'a' to align cameras, 's' to save point clouds
```

## Configuration

### Environment Setup

Key configuration variables in `config.py`:

```python
TRACKS_DIR = "./tracks/"              # Navigation track storage
LINES_DIR = "./lines/"                # Line navigation data
CALIBRATION_DATA_DIR = "./calibration_data/"  # Camera calibration
POINTCLOUD_DATA_DIR = "./pointcloud_data/"    # Point cloud exports
PORT = 8042                           # API server port
```

### Camera Configuration

Update camera IP addresses in `oakManager.py`:

```python
cameraIps = [
    "10.95.76.11",  # Camera 1
    "10.95.76.12",  # Camera 2
    "10.95.76.13"   # Camera 3
]
```

## API Reference

### Track Management

- `GET /list_tracks` - List all stored tracks
- `POST /delete_track/{track_name}` - Delete a track
- `POST /edit_track` - Rename a track
- `GET /get_track/{track_name}` - Retrieve track waypoints

### Recording & Following

- `POST /record/{track_name}` - Start recording a new track
- `POST /stop_recording` - Stop current recording
- `POST /follow/start/{track_name}` - Begin following a track
- `POST /follow/pause` - Pause track following
- `POST /follow/stop` - Stop track following
- `GET /follow/state` - Get follower status

### Line Navigation

- `POST /line/record/start/{track_name}` - Start line recording
- `POST /line/record/stop` - Stop line recording
- `POST /line/calibrate_turn/start` - Begin turn calibration
- `POST /line/calibrate_turn/end` - Complete turn calibration
- `POST /line/follow/{line_name}` - Start line following

### Point Cloud Operations

- `GET /pointcloud/save` - Export current point clouds
- `GET /pointcloud/align` - Align cameras using ICP
- `GET /pointcloud/reset` - Reset camera alignment

### Camera Streaming

- `GET http://{camera_ip}:5000/rgb` - MJPEG video stream

## Usage Examples

### Recording a Navigation Track

```python
import requests

# Start recording
response = requests.post("http://localhost:8042/record/field_perimeter")
print(response.json())  # {"message": "Recording started for track 'field_perimeter'."}

# Drive the robot along desired path...

# Stop recording
response = requests.post("http://localhost:8042/stop_recording")
print(response.json())  # {"message": "Recording stopped successfully."}
```

### Following a Track

```python
# Start following
response = requests.post("http://localhost:8042/follow/start/field_perimeter")
print(response.json())  # {"message": "Following track 'field_perimeter'."}

# Check status
response = requests.get("http://localhost:8042/follow/state")
print(response.json())  # {"controllable": true}

# Stop following
response = requests.post("http://localhost:8042/follow/stop")
```

### Line Following for Row Crops

```python
# Record a line (single row)
requests.post("http://localhost:8042/line/record/start/corn_row_1")
# Drive along one row...
requests.post("http://localhost:8042/line/record/stop")

# Calibrate turns
requests.post("http://localhost:8042/line/calibrate_turn/start")
# Make several turns to learn pattern...
requests.post("http://localhost:8042/line/calibrate_turn/end")

# Follow multiple rows
data = {"num_rows": 5, "first_turn_right": True}
requests.post("http://localhost:8042/line/follow/corn_row_1", json=data)
```

### Point Cloud Processing

```python
# Align cameras
requests.get("http://localhost:8042/pointcloud/align")

# Save point clouds
requests.get("http://localhost:8042/pointcloud/save")
```

## Data Formats

### Track Format (JSON)

```json
{
  "waypoints": [
    {
      "aFromB": {
        "rotation": {"unitQuaternion": {"real": 0.65, "imag": {"z": -0.75}}},
        "translation": {"x": 6484.18, "y": -5622.38}
      },
      "frameA": "world",
      "frameB": "robot",
      "tangentOfBInA": {
        "linearVelocity": {"x": 1.0},
        "angularVelocity": {"z": -0.005}
      }
    }
  ]
}
```

### Line Format (JSON)

```json
{
  "start": [6484.18, -5622.38, 0],
  "end": [6483.46, -5630.20, 0],
  "turn_length": 2.5
}
```

## Errors/Exceptions

### Camera Issues

- **Connection Failed**: Check camera IP addresses and network connectivity
- **Crash Dumps**: DepthAI crash dumps are stored in `.cache/depthai/crashdumps/`
- **Calibration Missing**: Run `mock_calibration.py` to generate test calibration data

### Track Following Problems

- **Robot Not Responding**: Verify farm-ng services are running and accessible such as the filter service and calibration.
- **Poor Navigation**: Check GPS signal quality and filter service status
- **Track Corruption**: Validate JSON format and waypoint data integrity

### Point Cloud Issues

- **Alignment Failure**: Ensure sufficient visual overlap between cameras
- **Performance**: Reduce point cloud density or processing frequency
- **Export Problems**: Check write permissions in pointcloud_data directory