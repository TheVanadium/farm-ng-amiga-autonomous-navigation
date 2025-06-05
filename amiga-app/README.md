# Project Summary

- **Multi-Camera 3D Scanning**: Three OAK-D ToF cameras capture aligned point clouds of crop fields
- **Automated Navigation**: Line following for systematic crop row traversal and custom track recording/playback
- **Real time Processing**: Live camera feeds, point cloud generation, and robot position tracking
- **Crop Analysis**: Volume estimation from point cloud data with yield calculations
- **Web UI**: React based UI for camera control, track management, and data visualization

The robot can navigate predefined paths or follow crop rows while automatically capturing 3D data, allowing automated yield estimation of a field.

# Repository Structure

### Main Directories

- **`backend/`** 
	- Python FastAPI server that manages cameras, processes point clouds, and provides REST API for robot control and data management
- **`ts/`** 
	- React TypeScript frontend providing web interface for track management, live camera feeds, and crop yield visualization

### Data Directories

- **`tracks/`** - Stored navigation tracks as JSON files containing waypoint sequences for robot movement
- **`lines/`** - Line track configurations for systematic crop row navigation with start/end points and turn calibration data
- **`calibration_data/`** - Camera calibration matrices and alignment transformations for accurate point cloud fusion
- **`pointcloud_data/`** - Captured 3D point cloud files organized by line, row, and capture sequence for crop analysis

### Configuration & Setup

- **`build.sh`** - Build script for setting up Python environment and compiling frontend
- **`install.sh`** - Installation script for Amiga system integration
- **`manifest.json`** - Amiga app configuration and service registration
- **`requirements.txt`** - Python dependencies
- **`config.json`** - Amiga service connection configuration

## System Overview

The system follows a client-server architecture:
- Backend handles camera management, point cloud processing, robot communication, and data storage through a FastAPI server with WebSocket support for real-time updates.
- Frontend provides an intuitive web interface for operators to create navigation paths, monitor live camera feeds, control robot movement, and view crop analysis results.
- Hardware Integration connects three OAK-D cameras positioned at different angles to capture comprehensive 3D data while the robot navigates through crop fields.

## Quick Start

1. Build the application: `./build.sh`
2. Install on Amiga: `./install.sh`
3. Access the web interface through the Amiga's app launcher
4. Calibrate cameras and create navigation tracks
5. Execute scanning runs and analyze results

## Further Documentation

For specific setup, development, and operation instructions:

- See `backend/README.md` for API documentation and camera setup
- See `ts/README.md` for frontend development and UI components
