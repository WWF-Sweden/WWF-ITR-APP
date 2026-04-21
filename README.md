# Use the WWF ITR Tool with your browser

A Streamlit web application for analyzing portfolio alignment with climate goals using the [CDP-WWF Temperature Scoring Methodology](https://wwfint.awsassets.panda.org/downloads/cdp-wwf-temperature-scoring-methodology---september-2024.pdf).

## Features

- **Temperature scoring** — Calculate implied temperature rise (ITR) for portfolio companies across scopes (S1, S2, S1+S2, S3) and time frames (short, mid, long)
- **Portfolio coverage** — Measure the share of portfolio assets with validated science-based targets (SBTi)
- **Scenario analysis** — Model the impact of engagement strategies and target improvements
- **Data editing** — Edit portfolio, company fundamentals, and targets inline via the UI
- **Local persistence** — Save and reload datasets using a local SQLite database
- **Sample data** — Built-in example dataset for quick exploration

## Getting Started

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

**Important — required environment variable:** When deploying to Streamlit Cloud, set the following environment variable in the app's settings (Streamlit Cloud dashboard → your app → **Settings** → **Environment variables**):

```
ITR_DEPLOYMENT=cloud
```

This activates a warning in the UI that informs users their uploaded data will be processed on external servers. Without this variable, the app assumes it is running locally and no warning is shown.

## License

See [LICENSE](LICENSE).

---

*© WWF Sweden, 2026. Results are for informational purposes only and should not be considered financial or investment advice.*
