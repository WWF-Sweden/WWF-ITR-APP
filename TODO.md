# ITR UI2 — Development Roadmap

## Phase 1 — Local database + editing ✅
- [x] SQLite module (`db/database.py`) for persist/load/delete datasets
- [x] `st.data_editor()` for inline editing of Portfolio, Fundamentals, Targets
- [x] Save/load from database in sidebar
- [x] ExcelProvider rebuilt from edited DataFrames
- [x] `.gitignore` excludes `data/*.db`

## Phase 2 — Dockerized local version
- [ ] Create `Dockerfile` (Python base, install requirements, copy app)
- [ ] Create `docker-compose.yml` using pre-built image from ghcr.io
  ```yaml
  services:
    itr:
      image: ghcr.io/wwf-sweden/wwf-itr-app:latest
      ports:
        - "8501:8501"
      volumes:
        - ./data:/app/data   # persists itr_data.db across container restarts
      # No ITR_DEPLOYMENT env var needed — local is the safe default
  ```
- [ ] GitHub Actions workflow (`.github/workflows/docker-publish.yml`) already drafted —
      triggers on `workflow_dispatch` and `v*` tags (not on every push to main)
- [ ] Set the ghcr.io package visibility to **public** so users can pull without a token
      (GitHub → your repo → Packages → wwf-itr-app → Package settings → Change visibility)
- [ ] Users run `docker compose up` → app at `localhost:8501` (no local build needed)
- [ ] No data leaves the user's machine
- [ ] Add usage instructions to README (pull image, run compose, open browser)
- [ ] Test on clean machine (Docker only, no pre-installed Python/dependencies)

## Phase 3 — Dual deployment
- [ ] **Streamlit Cloud** (`main` branch) — demo/sample-data mode, no persistent DB
- [ ] **Docker** — full local mode with SQLite persistence and editing
- [ ] Add mode detection (cloud vs local) to toggle features appropriately
- [ ] Consider disabling file upload on cloud version (or adding disclaimers)
- [ ] README with deployment instructions for both modes

## UI / Results Presentation (before Phase 2)
- [ ] (Add specific changes here as they come up)
