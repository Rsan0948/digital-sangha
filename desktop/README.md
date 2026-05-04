# Desktop Mode (optional)

This adds a second app mode that launches as a desktop window and auto-starts the backend.

## Keep current workflow
Your current workflow stays the same:
- Backend: `python backend/main.py`
- Frontend: `cd frontend && npm run dev`

## Desktop workflow
1. Install desktop dependencies:
   - `cd desktop`
   - `npm install`
2. Launch desktop app:
   - `npm run start`

The desktop launcher will:
- Build the frontend (`frontend/dist`)
- Start backend server automatically on `http://127.0.0.1:8000`
- Open an Electron window

## Notes
- Backend Python deps still need to be installed once (`pip install -r backend/requirements.txt`).
- Preferred Python is `./.venv/bin/python` (or `./.venv/Scripts/python.exe` on Windows).
