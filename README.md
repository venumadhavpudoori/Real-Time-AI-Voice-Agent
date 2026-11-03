# Real-Time AI Voice Agent (Restaurant Reservations)

A production-grade, voice-activated AI agent built for restaurant table reservations, live availability checking, dietary allergen safety, and graceful barge-in/interruption handling.

---

## 🏗️ Architecture & Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (Async), WebSockets, Pydantic V2, gTTS / Web Speech API.
- **Database**: PostgreSQL (with automatic zero-config SQLite fallback for instant local execution).
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, Web Audio API (FFT analyser) & Web Speech API.
- **Safety Guardrails**: PII Redaction (Luhn-tested credit cards, IDs), Severe Allergen Escalation (`SEVERE_ANAPHYLAXIS` kitchen alerts), and Prompt Injection interception.

```
Real-Time-AI-Voice-Agent/
├── docker-compose.yml               # PostgreSQL 16 container setup
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, lifespan & router mounting
│   │   ├── config.py                # Environment & guardrail threshold settings
│   │   ├── database.py              # Async SQLAlchemy engine & session manager
│   │   ├── models/                  # Tables, Reservations, MenuItems, SafetyAuditLogs
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── guardrails/
│   │   │   ├── sensitive_data.py    # PII masking (Credit Card Luhn check, SSN, PINs)
│   │   │   ├── allergen_safety.py   # Severe allergen & anaphylaxis detection
│   │   │   ├── prompt_safety.py     # Prompt injection & jailbreak defense
│   │   │   └── __init__.py          # Unified safety pipeline & audit logger
│   │   ├── services/
│   │   │   ├── agent_service.py     # Voice state machine & interruption engine
│   │   │   ├── tool_registry.py     # SQL integration tools (availability, bookings, menu)
│   │   │   ├── tts_service.py       # Base64 audio synthesis
│   │   │   └── stt_service.py       # Speech transcript cleaner
│   │   └── api/
│   │       ├── reservations.py      # REST CRUD for reservations
│   │       ├── tables.py            # REST table availability endpoints
│   │       ├── menu.py              # REST menu & dietary safety checker
│   │       ├── guardrails.py        # REST safety audit telemetry
│   │       └── websocket.py         # Bi-directional WebSocket /ws/voice-agent
│   ├── tests/
│   │   ├── test_guardrails.py       # PII, allergen & prompt injection tests
│   │   ├── test_tools.py            # SQL table check & booking transactions
│   │   └── test_api.py              # FastAPI endpoints tests
│   ├── init_db.sql                  # PostgreSQL schema & initial seed data
│   ├── seed_data.py                 # Async database seeder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VoiceVisualizer.jsx      # Glowing pulse orb & live canvas audio waveform
│   │   │   ├── VoiceController.jsx      # Mic controls, barge-in trigger, prompt chips
│   │   │   ├── ConversationFeed.jsx     # Live transcript, tool badges & safety alerts
│   │   │   ├── ReservationDashboard.jsx # Real-time PostgreSQL bookings registry
│   │   │   ├── TableAvailability.jsx    # Visual floor plan & availability tester
│   │   │   ├── MenuAllergenCatalog.jsx  # Menu items & dietary safety verification
│   │   │   └── GuardrailMonitor.jsx     # Security telemetry & audit log inspector
│   │   ├── hooks/
│   │   │   ├── useVoiceAgent.js         # WebSocket, speech recognition, barge-in hook
│   │   │   └── useAudioVisualizer.js    # Web Audio API microphone stream analyzer
│   │   ├── services/api.js              # Axios REST client
│   │   ├── App.jsx                      # Main UI layout & keyboard shortcuts
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
```

---

## 🚀 Quick Start Guide

### 1. Database Setup (PostgreSQL)

You can launch a PostgreSQL instance with Docker:
```bash
docker compose up -d
```
*Note: If PostgreSQL is not running, the backend automatically falls back to an embedded SQLite database (`sqlite+aiosqlite:///./restaurant.db`) so the application runs immediately without any configuration!*

---

### 2. Backend Setup & Run

1. Navigate to the `backend` folder:
```bash
cd backend
```

2. (Optional) Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables (optional):
```bash
copy .env.example .env
```
*(If `OPENAI_API_KEY` is not provided, the agent uses its high-fidelity built-in NLP & Slot-Filling Engine with complete offline capability.)*

5. Run the FastAPI development server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- WebSocket Endpoint: `ws://localhost:8000/ws/voice-agent`

---

### 3. Frontend Setup & Run

1. Open a separate terminal and navigate to `frontend`:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start Vite development server:
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser (preferably Google Chrome or Edge for full Web Speech API audio support).

---

## 🛡️ Safety Guardrails & Graceful Interruption

### 1. Sensitive Data Guardrail (`sensitive_data.py`)
- **Credit Card Numbers**: Validates sequences against the Luhn algorithm and automatically redacts them as `[CARD_REDACTED_*XXXX]`.
- **National IDs & SSNs**: Intercepts sensitive identity numbers.
- **CVVs & PINs**: Masks security codes to prevent accidental recording in database logs.

### 2. Dietary & Severe Allergen Guardrail (`allergen_safety.py`)
- **Allergen Taxonomy**: Monitors Big 9 allergens (peanuts, tree nuts, dairy, gluten, shellfish, fish, eggs, soy, sesame).
- **Severity Classification**: Detects keywords like `severe`, `anaphylaxis`, `epipen`, and `life-threatening`.
- **Automatic Kitchen Escalation**:
  - Automatically flags reservations with `allergy_level='SEVERE_ANAPHYLAXIS'`.
  - Dispatches a mandatory kitchen preparation alert for cookware sanitization and manager sign-off.
  - Injects a food safety disclaimer directly into the voice response to warn customers about cross-contamination.

### 3. Prompt Injection Defense (`prompt_safety.py`)
- Intercepts adversarial spoken phrases (e.g., "ignore all previous instructions", "drop table", "leak customer numbers").
- Neutralizes malicious prompts, logs an audit entry, and politely redirects the dialogue back to restaurant hospitality.

### 4. Interruption & Barge-in Handling
- When the agent is speaking:
  - If user begins speaking (voice activity detection or interim transcript) or hits **Spacebar / Escape / "Barge In" button**:
    1. Browser instantly cancels audio playback via `speechSynthesis.cancel()` and clears the audio element.
    2. Frontend dispatches `{ "type": "interrupt" }` over the WebSocket.
    3. Backend aborts ongoing speech synthesis, transitions session state to `INTERRUPTED`, logs the event, and re-engages `LISTENING` mode without losing context!

---

## 🧪 Running Automated Tests

Run the backend test suite:
```bash
python -m pytest backend/tests -v
```

All 12 unit and integration tests verify:
- ✅ PII Luhn algorithm validation & credit card redaction
- ✅ Severe allergen detection & kitchen safety escalation
- ✅ Prompt injection blocking & safe redirection
- ✅ SQL table availability queries
- ✅ ACID reservation booking transactions & cancellations
- ✅ FastAPI health, menu, tables, and guardrail endpoints
