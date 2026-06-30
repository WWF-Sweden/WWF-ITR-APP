# Use the WWF ITR Tool with your browser

A Streamlit web application for analyzing portfolio alignment with climate goals using the [CDP-WWF Temperature Scoring Methodology](https://wwfint.awsassets.panda.org/downloads/cdp-wwf-temperature-scoring-methodology---september-2024.pdf).

## Features

- **Temperature scoring** — Calculate implied temperature rise (ITR) for portfolio companies across scopes (S1, S2, S1+S2, S3) and time frames (short, mid, long)
- **Portfolio coverage** — Measure the share of portfolio assets with validated science-based targets (SBTi)
- **Scenario analysis** — Model the impact of engagement strategies and target improvements
- **Data editing** — Edit portfolio, company fundamentals, and targets inline via the UI

## Running the Application with Docker

The recommended way to run this application is with Docker. This method ensures you have the correct environment and dependencies without needing to install Python or other packages on your system. Your data remains on your local machine.

**Prerequisites:**
*   Docker must be installed and running on your system. You can download it from the [official Docker website](https://www.docker.com/products/docker-desktop/).

**Instructions:**

1.  **Create a `docker-compose.yml` file:**
    Create a new file named `docker-compose.yml` in the root of this project and add the following content:

    ```yaml
    services:
      itr:
        image: ghcr.io/wwf-sweden/wwf-itr-app:latest
        ports:
          - "8501:8501"
        volumes:
          - ./data:/app/data
    ```

2.  **Start the application:**
    Open a terminal, navigate to the project directory, and run the following command:

    ```bash
    docker compose up
    ```
    This command will pull the latest application image from the GitHub Container Registry and start it.

3.  **Access the application:**
    Once the container is running, open your web browser and go to:
    [http://localhost:8501](http://localhost:8501)

Your portfolio data will be saved in the `data` directory on your local machine, so it will be preserved even if you stop and restart the container.

### Data Persistence with Docker

By default, when you run the application using `docker compose up`, the SQLite database is stored inside the running container. This data will persist if you stop the container (with `docker compose stop` or `Ctrl+C`) and restart it later (`docker compose start`).

However, the data will be **lost** if you remove the container, which happens when you run `docker compose down`.

To ensure your saved datasets are not lost when you rebuild or remove the container, you should use a Docker volume to store the database file on your host machine.

#### Using a Named Volume

You can configure a **named volume** in your `docker-compose.yml` file. This is the recommended approach for robust data persistence.

1.  Create or edit a `docker-compose.yml` file in the root of the project with the following content:

    ```yaml
    version: '3.8'

    services:
      app:
        build: .
        ports:
          - "8501:8501"
        volumes:
          - itr_data:/app/data

    volumes:
      itr_data:
    ```

2.  Run the application using Docker Compose:

    ```bash
    docker compose up --build
    ```

Now, the `data` directory inside the container (where `itr_data.db` is stored) is mapped to a Docker-managed volume named `itr_data` on your host machine. This volume will persist even if you run `docker compose down`, keeping your database safe.


## Getting Started - local install

### Prerequisites

- Python 3.10+

### Installation

```bash
git clone https://github.com/WWF-Sweden/WWF-ITR-APP.git
cd WWF-ITR-UI
pip install -r requirements.txt
```

### Running the app

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

## Data Requirements

The tool expects two data sources:

| File | Format | Description |
|------|--------|-------------|
| Provider data | Excel (`.xlsx`) | Company fundamentals and emission reduction targets (sheets: `fundamental_data`, `target_data`) |
| Portfolio | CSV or Excel | Holdings with at minimum `company_id`, `company_name`, and `investment_value` columns |

See the [data requirements documentation](https://wwf-sweden.github.io/ITR-tool/DataRequirements.html) for full column specifications.

You can also use the built-in **Sample Data** option to explore the tool without uploading files.

## Methodology

This tool implements the CDP-WWF Temperature Scoring Methodology v1.5. For a detailed walkthrough, see the [Analysis Example Notebook](https://colab.research.google.com/github/WWF-Sweden/ITR-tool/blob/main/examples/1_analysis_example.ipynb).

The underlying scoring engine is the open-source [`wwf-itr`](https://github.com/WWF-Sweden/ITR-tool) Python package.

## Project Structure

```
app.py                  # Main Streamlit application
requirements.txt
assets/                 # CSS and images
data/                   # Sample data files
db/
    database.py         # SQLite persistence layer
utils/
    data_loader.py      # File loading, validation, and cleaning
    data_source.py      # Data source selection UI
    scoring.py          # Temperature score calculations
    scenarios.py        # Scenario and engagement analysis
    visualization.py    # Plotly charts
```

## Deployment

### Local / Docker (recommended for real data)

All computation runs on the user's own machine. No data is sent externally. SQLite persistence works as intended. See [TODO.md](TODO.md) for the planned Docker setup.

### Streamlit Cloud (demo / sample data only)

The app can be deployed to [Streamlit Cloud](https://streamlit.io/cloud) for demonstration purposes using the built-in sample data. File upload is technically possible but **not recommended for sensitive portfolio data**, as uploaded files are processed on Streamlit's servers (US-based, AWS).

**Important — required secret:** When deploying to Streamlit Cloud, add the following to the app's secrets (Streamlit Cloud dashboard → your app → **Settings** → **Secrets**):

```toml
ITR_DEPLOYMENT = "cloud"
```

This activates a warning in the UI that informs users their uploaded data will be processed on external servers. Without this secret, the app assumes it is running locally and no warning is shown.

## License

See [LICENSE](LICENSE).

---

*© WWF Sweden, 2026. Results are for informational purposes only and should not be considered financial or investment advice.*
