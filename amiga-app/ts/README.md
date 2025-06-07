## Summary

React-based web application for controlling and monitoring the Farm-ng Amiga autonomous farming robot. This frontend provides an interface for track management, navigation control, and crop yield data visualization.

Application serves as the primary user interface for the Farm-ng Amiga robot navigation system. It enables operators to create navigation tracks, control autonomous movement, and monitor agricultural data through a web-based dashboard.

## Tech Stack

- **React 18** with TypeScript for type-safe component development
- **Material-UI (MUI) v6** for consistent UI components and styling
- **React Router v7** for client-side navigation
- **Emotion** for CSS-in-JS styling
- **Vite** as the build tool and development server
- **ESLint** and **Prettier** for code quality and formatting

## Architecture

- **Pages**: Top-level route components that compose the main application views
- **Components**: Reusable UI components with specific functionality
- **Utils**: Utility functions and mathematical operations
- **API Integration**: REST API calls and WebSocket connections to the robot backend
## Project Structure

```
amiga-app/ts/
├── public/
├── src/
│   ├── components/             # Reusable UI components
│   │   ├── BackButton.tsx      # Navigation back functionality
│   │   ├── CameraFeed.tsx      # Live camera streaming display
│   │   ├── ExitButton.tsx      # Farm-ng app exit integration
│   │   ├── TrackCreateMenu.tsx # Track creation interface
│   │   ├── TrackRunMenu.tsx    # Navigation control interface
│   │   ├── TrackSelectMenu.tsx # Track management and selection
│   │   ├── TrackYieldInfo.tsx  # Yield data display component
│   │   └── TrackYieldSelect.tsx # Yield run selection interface
│   ├── pages/                  # Main application screens
│   │   ├── Home.tsx           # Landing page with navigation
│   │   ├── TrackSelect.tsx    # Track management screen
│   │   └── ViewCropYield.tsx  # Crop yield visualization
│   ├── utils/                 # Utility functions
│   │   └── Vec2.ts           # 2D vector mathematics library
│   ├── icons/                # Static assets
│   │   └── direction-arrow.png # Navigation arrow icon
│   ├── App.css              # Global application styles
│   ├── App.tsx              # Main application component
│   ├── index.css            # Additional CSS imports
│   ├── main.tsx             # Application entry point
│   ├── theme.tsx            # Material-UI theme configuration
│   └── vite-env.d.ts        # Vite TypeScript definitions
├── .env                     # Environment configuration
├── .gitignore              # Git exclusion rules
├── index.html              # HTML template
├── package.json            # Dependencies and scripts
├── package-lock.json       # Dependency lock file
├── tsconfig.json           # TypeScript configuration
├── tsconfig.node.json      # Node.js TypeScript config
└── vite.config.ts          # Vite build configuration
```

### Config Files

#### `package.json`

Defines project dependencies and build scripts. Key dependencies include React ecosystem packages, Material-UI components, and development tools for TypeScript compilation and linting.

#### `tsconfig.json` / `tsconfig.node.json`

TypeScript compiler configuration for both application code and Node.js tooling. Configures strict type checking, ES2020 target, and React JSX transform.

#### `vite.config.ts`

Vite build tool configuration enabling React plugin support and development server settings.

#### `.env`

Environment configuration file containing the backend API URL (`VITE_API_URL = "http://localhost:8042"`).

#### `.gitignore`

Git exclusion rules for node_modules, build artifacts, and environment files.

### Application Entry Points

#### `index.html`

Base HTML template with root div element and script reference to the main TypeScript entry point.

#### `src/main.tsx`

Application bootstrap file that initializes React, applies Material-UI theming with `CssBaseline`, and mounts the root App component.

#### `src/App.tsx`

Main application component implementing React Router with three primary routes:

- `/` - Home page
- `/TrackSelect` - Track management interface
- `/ViewCropYield` - Crop yield data visualization

### Styling and Theming

#### `src/App.css`

Global CSS styles defining body margins, overflow settings, and navigation button styling with specific dimensions and border radius.

#### `src/theme.tsx`

Material-UI theme configuration defining the application color palette:

- Primary color: Light blue (`#6feafc`) with black contrast text
- Secondary color: Dark blue (`#0055AA`) with white contrast text
- Light mode with white background

#### `src/index.css`

Additional CSS imports (currently minimal).

### Page Components

#### `src/pages/Home.tsx`

Landing page component featuring:

- Application title "NavLogger"
- Exit button for farm-ng app integration
- Two primary navigation buttons routing to Track Select and View Crop Yield pages
- Material-UI Grid layout with centered content

#### `src/pages/TrackSelect.tsx`

Primary track management interface containing:

- Multi-camera feed with tabbed interface (left, center, right cameras)
- Three operational modes: Add New Track, Select Track, Run Track
- Dynamic menu system based on selected mode
- Track listing and current track display
- Integration with camera feeds and real-time robot data

#### `src/pages/ViewCropYield.tsx`

Crop yield visualization page with:

- Track run selection interface
- Yield data display showing date, total yield, and path length
- Grid layout for organized data presentation
- Dummy data implementation for demonstration purposes

### Reusable Components

#### `src/components/BackButton.tsx`

Navigation component using React Router's `useNavigate` hook to implement browser-style back functionality with Material-UI Button styling.

#### `src/components/ExitButton.tsx`

System integration component that:

- Fetches current app information from farm-ng system API
- Implements clean app shutdown via systemctl API calls
- Redirects to farm-ng app launcher upon successful exit
- Handles service lifecycle management

#### `src/components/CameraFeed.tsx`

Live camera streaming component that:

- Maps camera orientation strings to IP addresses
- Displays live video feeds from robot cameras at specific network endpoints
- Provides error handling for camera connectivity issues

#### `src/components/TrackCreateMenu.tsx`

Track creation interface featuring:

- Track type selection (line vs standard tracks)
- Track name input with validation
- Real-time track recording controls
- Turn calibration functionality for line tracks
- API integration for track recording lifecycle management

#### `src/components/TrackRunMenu.tsx`

Navigation control interface providing:

- Real-time robot positioning via WebSocket connection
- Distance and directional guidance to track starting points
- Track following controls (start, pause, resume)
- Visual feedback with directional arrow indicators
- Live position data processing and display

#### `src/components/TrackSelectMenu.tsx`

Track management component offering:

- Track listing with selection functionality
- Inline editing capabilities for track renaming
- Delete operations with confirmation
- API integration for track CRUD operations
- Error handling for duplicate names and validation

#### `src/components/TrackYieldSelect.tsx`

Yield data selection interface with:

- List-based track run selection
- Highlighting of currently selected runs
- Clean Material-UI list component integration

#### `src/components/TrackYieldInfo.tsx`

Data display component showing:

- Formatted yield information in bordered containers
- Date, total yield (grams), and path length (meters) display
- Responsive layout with Material-UI Box components

### Utility Functions

#### `src/utils/Vec2.ts`

2D vector mathematics library providing:

- Vector arithmetic operations (add, subtract, multiply, divide)
- Geometric calculations (magnitude, normalization, dot product, cross product)
- Polar coordinate conversions
- Distance calculations between points
- Interpolation and averaging functions
- Specialized operations for robot positioning calculations

#### `src/vite-env.d.ts`

TypeScript environment definitions for Vite build tool integration.

## API Integration

The frontend communicates with the robot backend through:

### REST Endpoints

- Track management (create, read, update, delete)
- Navigation control (start, pause, resume, stop)
- System integration (app lifecycle management)

### WebSocket Connections

- Real-time robot pose data via `/filter_data` endpoint
- Live position updates for navigation feedback

### Camera Streams

- HTTP endpoints for live video feeds from robot camera array
- IP-based camera addressing for multi-camera support

## Development Workflow

1. **Environment Setup**: Configure `.env` file with appropriate API endpoint
2. **Development Server**: Use `npm run dev` for hot-reload development
3. **Type Checking**: TypeScript strict mode ensures type safety
4. **Code Quality**: ESLint and Prettier maintain consistent code standards
5. **Build Process**: Vite optimizes for production deployment

## System Integration

The application integrates with the broader farm ng through:

- Service lifecycle management via systemctl APIs
- Port-based app identification and routing
- Clean shutdown procedures for system stability
- Integration with farm-ng app launcher infrastructure
