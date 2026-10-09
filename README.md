# Use the WWF ITR Tool with your browser

A Streamlit web application for analyzing portfolio alignment with
climate goals using the [CDP-WWF Temperature Scoring
Methodology](https://wwfint.awsassets.panda.org/downloads/cdp-wwf-temperature-scoring-methodology---september-2024.pdf).

## Features

-   **Temperature scoring** --- Calculate implied temperature rise (ITR)
    for portfolio companies across scopes (S1, S2, S1+S2, S3) and time
    frames (short, mid, long)
-   **Portfolio coverage** --- Measure the share of portfolio assets
    with validated science-based targets (SBTi)
-   **Scenario analysis** --- Model the impact of engagement strategies
    and target improvements
-   **Data editing** --- Edit portfolio, company fundamentals, and
    targets inline via the UI

## Running the Application with Docker

The recommended way to run this application is with Docker. This method
ensures you have the correct environment and dependencies without
needing to install Python or other packages on your system.

The application runs locally on your computer, and application data is
stored locally.

### Prerequisites

Docker must be installed and running on your system.

Installation instructions:

-   **Windows:** [Install Docker Desktop on
    Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
-   **macOS:** [Install Docker Desktop on
    Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
-   **Linux:** [Install Docker
    Engine](https://docs.docker.com/engine/install/)

Docker Desktop includes Docker Compose.

You can verify your installation by running:

``` bash
docker --version
docker compose version
```

### Starting the Application

**1. Create a directory for the application**

Create a directory on your computer where you want to run the
application.

You do not need to clone the GitHub repository to run the application
using Docker.

**2. Create a `docker-compose.yml` file**

Inside your directory, create a file named `docker-compose.yml` with the
following content:

``` yaml
services:
  itr:
    image: ghcr.io/wwf-sweden/wwf-itr-app:latest
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
```

**3. Start the application**

Open a terminal, navigate to the directory containing
`docker-compose.yml`, and run:

``` bash
docker compose up -d --pull always
```

This command:

-   Checks for the latest application image on GitHub Container Registry
    (GHCR).
-   Downloads the image or any updated layers if necessary.
-   Starts the application in the background.

If the image has not changed, Docker reuses the existing image layers.

**4. Access the application**

Once the container is running, open your web browser and go to:

<http://localhost:8501>

### Stopping the Application

To stop the application and remove its container, run:

``` bash
docker compose down
```

Your application data will remain in the local `data` directory.

### Starting the Application Again

To restart the application at a later time, simply run:

``` bash
docker compose up -d --pull always
```

This also checks whether a newer version of the application is
available.

### Viewing Logs

If you encounter problems or want to inspect application logs, run:

``` bash
docker compose logs -f itr
```

Press `Ctrl+C` to stop following the logs.

To check whether the application is running:

``` bash
docker compose ps
```

### Data Persistence with Docker

The Docker Compose configuration includes the following volume mapping:

``` yaml
volumes:
  - ./data:/app/data
```

This maps the application's `/app/data` directory inside the container
to the `data` directory on your local machine.

The application's SQLite database and other data stored in this
directory will therefore persist even if you:

-   Stop the application.
-   Remove the Docker container using `docker compose down`.
-   Update the application to a newer Docker image.

**Important:** Do not delete the local `data` directory if you want to
preserve your saved data.

You may also want to back up this directory periodically.

### Updating the Application

The application is distributed through GitHub Container Registry:

`ghcr.io/wwf-sweden/wwf-itr-app:latest`

To check for updates and start the latest published version, run:

``` bash
docker compose up -d --pull always
```

There is no need to manually download or rebuild the Docker image.

------------------------------------------------------------------------

## Getting Started --- Local Installation

For developers who want to modify the application or run it directly
with Python, the following installation method can be used.

### Prerequisites

-   Python 3.10+

### Installation

Clone the repository:

``` bash
git clone https://github.com/WWF-Sweden/WWF-ITR-APP.git
cd WWF-ITR-APP
```

Install the required dependencies:

``` bash
pip install -r requirements.txt
```

### Running the App

``` bash
streamlit run app.py
```

The app will be available at <http://localhost:8501>.

------------------------------------------------------------------------

## Data Requirements

The tool expects two data sources:

  ------------------------------------------------------------------------
  File            Format                Description
  --------------- --------------------- ----------------------------------
  Provider data   Excel (`.xlsx`)       Company fundamentals and emission
                                        reduction targets (sheets:
                                        `fundamental_data`, `target_data`)

  Portfolio       CSV or Excel          Holdings with at minimum
                                        `company_id`, `company_name`, and
                                        `investment_value` columns
  ------------------------------------------------------------------------

See the [data requirements
documentation](https://wwf-sweden.github.io/ITR-tool/DataRequirements.html)
for full column specifications.

You can also use the built-in **Sample Data** option to explore the tool
without uploading files.

## Methodology

This tool implements the CDP-WWF Temperature Scoring Methodology v1.5.
For a detailed walkthrough, see the [Analysis Example
Notebook](https://colab.research.google.com/github/WWF-Sweden/ITR-tool/blob/main/examples/1_analysis_example.ipynb).

The underlying scoring engine is the open-source
[`wwf-itr`](https://github.com/WWF-Sweden/ITR-tool) Python package.

## Project Structure

``` text
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

The recommended deployment method is to run the application locally
using Docker.

All application calculations run on the user's own machine, and
application data is stored locally.

See [Running the Application with
Docker](#running-the-application-with-docker) for installation and usage
instructions.

### Streamlit Cloud (demo / sample data only)

The app can be deployed to [Streamlit Cloud](https://streamlit.io/cloud)
for demonstration purposes using the built-in sample data.

File upload is technically possible but **not recommended for sensitive
portfolio data**, as uploaded files are processed on Streamlit's servers
(US-based, AWS).

**Important --- required secret:** When deploying to Streamlit Cloud,
add the following to the app's secrets (Streamlit Cloud dashboard → your
app → **Settings** → **Secrets**):

``` toml
ITR_DEPLOYMENT = "cloud"
```

This activates a warning in the UI that informs users their uploaded
data will be processed on external servers.

Without this secret, the app assumes it is running locally and no
warning is shown.

## License

See [LICENSE](LICENSE).

------------------------------------------------------------------------

*© WWF Sweden, 2026. Results are for informational purposes only and
should not be considered financial or investment advice.*
