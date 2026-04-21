# ITR UI2 — Development Roadmap

## Phase 1 — Local database + editing ✅
- [x] SQLite module (`db/database.py`) for persist/load/delete datasets
- [x] `st.data_editor()` for inline editing of Portfolio, Fundamentals, Targets
- [x] Save/load from database in sidebar
- [x] ExcelProvider rebuilt from edited DataFrames
- [x] `.gitignore` excludes `data/*.db`

## Phase 2 — Dockerized local version
- [ ] Create `Dockerfile` (Python base, install requirements, copy app)
- [ ] Create `docker-compose.yml` with volume mount for `data/` (SQLite persistence)
  ```yaml
  services:
    itr:
      build: .
      ports:
        - "8501:8501"
      volumes:
        - ./data:/app/data   # persists itr_data.db across container restarts
      environment:
        # No ITR_DEPLOYMENT env var needed — local is the safe default
  ```
- [ ] Users run `docker compose up` → app at `localhost:8501`
- [ ] No data leaves the user's machine
- [ ] Add usage instructions to README
- [ ] Test on clean machine (no pre-installed dependencies)

## Phase 3 — Dual deployment
- [ ] **Streamlit Cloud** (`main` branch) — demo/sample-data mode, no persistent DB
- [ ] **Docker** — full local mode with SQLite persistence and editing
- [ ] Add mode detection (cloud vs local) to toggle features appropriately
- [ ] Consider disabling file upload on cloud version (or adding disclaimers)
- [ ] README with deployment instructions for both modes

## UI / Results Presentation (before Phase 2)
- [ ] (Add specific changes here as they come up)
