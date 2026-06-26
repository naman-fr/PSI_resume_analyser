# ⚛️ Frontend Control Plane

This directory contains the React/Vite SPA serving as the primary User Interface.

## Tech Stack
*   **Core**: React 18, Vite.
*   **Styling**: Vanilla CSS, Glassmorphism, CSS Variables.
*   **3D Assets**: `react-three-fiber` and Three.js loading `.glb` objects.
*   **Icons**: `lucide-react`.

## Key Architectural Modules
*   `src/utils/behaviorTracker.js`: Continuously streams biometric telemetry (mouse velocity, typing flight times) to the backend for bot detection.
*   `src/components/VisionStreaming.jsx`: Integrates `OpenCV.js` directly in the browser to run Haar Cascades for multi-face detection without heavily loading the backend.
*   `src/components/InterviewRoom.jsx`: Hooks into the native browser Web Speech API for voice dictation and handles WebRTC streams.
*   `src/components/ConsentManager.jsx`: The AI Data Governance Center allowing granular privacy vector adjustments.

## Commands
*   `npm run dev`: Starts the local dev server.
*   `npm run build`: Bundles the application using Rollup for FastAPI static serving.
