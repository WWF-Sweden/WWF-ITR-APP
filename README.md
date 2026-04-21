# WWF ITR Tool

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
git clone https://github.com/YOUR_ORG/WWF-ITR-UI.git
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

## License

See [LICENSE](LICENSE).

---

*© WWF Sweden, 2026. Results are for informational purposes only and should not be considered financial or investment advice.*
