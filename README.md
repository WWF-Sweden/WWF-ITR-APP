# Use the WWF ITR Tool with your browser

A Streamlit web application for analyzing portfolio alignment with
climate goals using the [CDP-WWF Temperature Scoring
Methodology](https://wwfint.awsassets.panda.org/downloads/cdp-wwf-temperature-scoring-methodology---september-2024.pdf).


## Try the App Online — No Installation Required

The easiest way to explore the WWF ITR Tool is to use our online demo, hosted on Streamlit Community Cloud.

**[🚀 Launch the WWF ITR App](https://wwf-itr.streamlit.app/)**

No installation, Docker setup, or Python environment is required. Simply open the app in your browser and select **Sample Data** to explore its features, calculate portfolio temperature scores, and experiment with different scenarios.

**Data privacy:** The online version is intended for demonstration and testing with sample or publicly available data. Do not upload confidential, sensitive, or proprietary portfolio information, as uploaded data is processed on external cloud servers.

**Working with your own data?** We recommend running the application locally using Docker, where your application data remains on your own computer. See [Running the Application with Docker](#running-the-application-with-docker) below.


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

## Local data and privacy

The supported setup for confidential data is one user per local installation,
with a separate data directory. This app does not provide user accounts or
dataset permissions for a shared server installation. Other accounts and
processes on the same computer may still be able to access local data;
follow your organization's rules for device access, disk encryption and backups.

Uploaded provider workbooks, portfolios and pre-scored files are read in memory
without creating application-managed temporary disk copies. Only the required
`fundamental_data` and `target_data` sheets are read from provider uploads.
Provider reconstruction for calculations also takes place in memory.
Analysis data and results are not stored in global Streamlit caches; the
current session retains loaded data and may reuse its own calculation results.
Repeated what-if scenarios can reuse up to three results in that session,
with a total budget of 32 MiB of serialized result data. This is not a limit
on the app's total memory use. The key includes the complete provider data,
portfolio, scenario settings and CTA contents. Least recently used results
are evicted; a result larger than the budget is calculated without caching.
The cache stays in memory and is cleared by **Clear loaded data / Change source**
or normal session disposal. Closing a tab may not dispose of the session immediately.
Streamlit usage statistics are disabled in the supplied configuration.

Use **Clear loaded data / Change source** to release this session's loaded data,
results and uploads. This does not delete datasets explicitly saved to SQLite
or files already downloaded through your browser. It does not securely erase
process memory. Stop the app/container to end the running process; closing a
browser tab alone does not guarantee immediate session disposal.

Custom CTA uploads still require a temporary file for the calculation package.
They use a session-owned temporary directory, removed when the upload is
replaced, removed or cleared, or when the session owner is normally released.
Abrupt process termination can leave these temporary files behind. Updating
does not remove temporary upload files left by earlier versions. Database
files, browser downloads, backups and operating-system swap are separate from
the application's in-memory upload handling.

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
      - "127.0.0.1:8501:8501"
    volumes:
      - ./data:/app/data
```

The port mapping binds the app to your computer's loopback address, so it
is available locally rather than through your computer's LAN or Wi-Fi address.
Use Docker Engine 28.0.0 or later: older versions have a known issue that can
allow other devices on the same network segment to reach ports published to
localhost ([Docker documentation](https://docs.docker.com/engine/network/port-publishing/)).

The Docker image sets `ITR_DEPLOYMENT=local`, enabling the dataset database.
With the volume mapping above, saved datasets are stored in
`./data/itr_data.db` on your computer and remain available when the container
is replaced.

Keep the port mapping `"127.0.0.1:8501:8501"` for local use. The image's
local mode does not provide authentication or separate datasets by user.
Publishing this image on a shared or public server would require additional
access controls, or disabling the dataset database.

After starting the app, run `docker compose ps` and verify that the
published port is shown as `127.0.0.1:8501->8501/tcp`.

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

CTA downloads are stored in `/app/data/cta/current-Companies-Taking-Action.xlsx`
and persist through this same volume. The app uses cached CTA data for up to
one week, then attempts a new download. **Update CTA from SBTi** forces an
update; a failed or invalid download preserves the previous file. **Offline
mode** uses cached or bundled data without downloading. The sidebar displays
the actual CTA file and its modification time, and warns when bundled data is used.

Users can also select **Upload custom file** and upload a CTA Excel file in
Docker or Streamlit Cloud. Uploaded files never require a download and are
kept for the active session; replacing or removing an upload deletes its previous
temporary file. Missing or invalid CTA data is reported as an error rather than
zero portfolio coverage. Outside Docker, the default cache is `data/cta`; set
`ITR_CTA_PATH` to override it. Streamlit Cloud storage should be treated as
temporary across app restarts.

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

To enable saving and loading datasets on your own computer:

**macOS / Linux**

```bash
ITR_DEPLOYMENT=local streamlit run app.py
```

**Windows PowerShell**

```powershell
$env:ITR_DEPLOYMENT = "local"
streamlit run app.py
```

The app will be available at <http://localhost:8501>.

The repository's `.streamlit/config.toml` defaults to listening on
`127.0.0.1`. Run the command from the repository root so this configuration
is loaded. Streamlit environment variables and command-line flags can
override this setting.

Without `ITR_DEPLOYMENT=local`, the app runs in demo mode. The dataset
database is disabled, but sample data, file uploads, calculations, editing
and exports remain available. Upload warnings are shown in demo mode.

`ITR_DEPLOYMENT=local` enables database access; it does not verify that
the app is running locally or provide authentication. Enable it only for
an installation you control and have restricted to authorised users.

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

### Streamlit Community Cloud (demo)

The app can be deployed to
[Streamlit Community Cloud](https://streamlit.io/cloud)
for demonstration purposes.

No deployment-mode secret is required. Unless `ITR_DEPLOYMENT=local`
is explicitly set, the dataset database is disabled and upload warnings
are shown.

Do not set `ITR_DEPLOYMENT=local` in Community Cloud. An existing
`ITR_DEPLOYMENT = "cloud"` secret also leaves the database disabled
and can be removed.

Sample data, uploads, calculations, editing and exports remain available.
Uploaded data is processed on Streamlit Community Cloud servers in the
United States. Use a local installation for sensitive or confidential data.

Disabling the dataset database blocks the app's database operations.
It does not mean that uploaded data is never processed, cached, or held
temporarily on the server.

Before deploying changes to the public demo, verify startup and access
in a separate test deployment, including compatibility with the
`server.address` setting in `.streamlit/config.toml`.

Disabling database access does not delete an existing database file.
If previous deployments stored datasets, handle their removal explicitly
and verify the result. Do not rely on an app reboot as proof of deletion.

## Updating the WWF-ITR dependency

Dependabot checks PyPI for new published releases of `WWF-ITR` on weekdays
at 08:00 Europe/Stockholm. It monitors only this dependency and opens a PR
updating the exact version in `requirements.txt`. Changes in the ITR-tool
repository alone do not trigger a dependency update.

The PR runs the app's CTA integration tests with the proposed package version.
Review and merge the PR to `main` to publish a new image to
`ghcr.io/wwf-sweden/wwf-itr-app:latest`. The publishing workflow also runs the
tests and only builds and pushes the image if they pass. There is no automatic
merge. Configure a branch protection rule requiring the CTA integration test
check if failed tests should prevent merging.

These workflows and the Dependabot configuration take effect after they are
merged to the repository's default branch. No cross-repository token or
notification from ITR-tool is needed.

To update an existing Docker installation after the image has been published:

```sh
docker compose up -d --pull always
```

## License

See [LICENSE](LICENSE).

------------------------------------------------------------------------

*© WWF Sweden, 2026. Results are for informational purposes only and
should not be considered financial or investment advice.*
