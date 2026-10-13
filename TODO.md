# ITR UI2 — Remaining Tasks

## Docker verification

- [ ] Verify that `ghcr.io/wwf-sweden/wwf-itr-app:latest` is publicly accessible
      and can be pulled without authentication.
- [ ] Test the README’s Docker Compose instructions on a clean machine with
      Docker only (no pre-installed Python or application dependencies).
      Confirm that the app starts at `localhost:8501` and saved datasets persist
      after the container is removed and recreated.

## Streamlit Cloud

- [ ] Decide whether cloud mode should disable database save/load operations.
      Currently, cloud mode allows uploads, editing, and database operations;
      upload warnings are shown, and cloud storage is temporary across restarts.
      If this behavior is intentional, retire the original sample-only,
      no-database requirement. Otherwise, implement the restrictions and update
      the README to match.
