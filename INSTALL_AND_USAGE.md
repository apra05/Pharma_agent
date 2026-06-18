# 🚀 Installation and Usage Guide

This guide will help you set up and run the **Pharma Agent** application locally.

# 📑 Table of Contents

- [📋 Prerequisites](#-prerequisites)
- [🎯 Getting Started](#-getting-started)
- [📁 Project Structure](#-project-structure)
- [🏗️ Set Up Your Local Infrastructure](#-set-up-your-local-infrastructure)
- [⚡️ Running the Application](#️-running-the-application)
- [🔧 Developer Commands](#-developer-commands)

---

# 📋 Prerequisites

## Local Tools

Ensure you have the following tools installed on your local machine:

| Tool | Version | Purpose | Installation Link |
|------|---------|---------|------------------|
| Python | 3.11 | Programming language runtime | [Download](https://www.python.org/downloads/) |
| uv | ≥ 0.4.30 | Python package installer and virtual environment manager | [Download](https://github.com/astral-sh/uv) |
| GNU Make | ≥ 3.81 | Build automation tool | [Download](https://www.gnu.org/software/make/) |
| Git | ≥ 2.44.0 | Version control | [Download](https://git-scm.com/downloads) |
| Docker | ≥ 27.4.0 | Containerization platform | [Download](https://www.docker.com/get-started/) |

<details>
<summary><b>📌 Windows Users Command Line configuration (Click to expand)</b></summary>

If you are using Windows, we recommend installing WSL or using PowerShell with a configured path to GNU Make (e.g., GnuWin32).
To temporarily add GnuWin32 `bin` to your current PowerShell session's `PATH`:
```powershell
$env:PATH += ";C:\Program Files (x86)\GnuWin32\bin"
```
</details>

## Cloud Services

Pharma Agent integrates with the following services. Add the corresponding credentials to your `.env` file:

| Service | Purpose | Cost | Environment Variable | Setup Guide |
|---------|---------|------|---------------------|-------------|
| [Groq](https://console.groq.com) | High-speed LLM inference | Free tier available | `GROQ_API_KEY` | [Quick Start](https://console.groq.com/keys) |
| [Opik](https://www.comet.com/site/products/opik/) | LLMOps Tracking & Evaluation | Free tier | `COMET_API_KEY` | [Quick Start](https://www.comet.com/docs/v2/guides/opik-interface/) |
| [OpenAI](https://platform.openai.com) | LLM-as-a-judge for evaluation | Pay-per-use | `OPENAI_API_KEY` | [Quick Start](https://platform.openai.com/docs/quickstart) |

When running locally, the database and API default values will connect to the Docker network. You do not need to change the MongoDB environment variables for local testing.

---

# 🎯 Getting Started

## 1. Clone the Repository

Clone the project and enter the repository folder:
```bash
git clone https://github.com/apra05/Pharma_agent.git
cd Pharma_agent
```

## 2. Install Python Dependencies

Navigate to the `pharmagent-api` folder and use `uv` to build the virtual environment:
```bash
cd pharmagent-api
uv venv .venv
# Activate the environment:
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the package in editable mode:
uv pip install -e .
```

Verify python version:
```bash
uv run python --version
# Expected: Python 3.11.x
```

## 3. Environment Configuration

Copy the example environment file and configure your API keys:
```bash
cp .env.example .env
```
Open `.env` and fill in `GROQ_API_KEY` (and `COMET_API_KEY` / `OPENAI_API_KEY` if you plan to use Opik monitoring and evaluations).

---

# 📁 Project Structure

```bash
pharmagent-api/
    ├── data/                  # Ingestion dataset (jnj_content.txt) and evaluation samples
    ├── src/pharma_agent/      # Core package containing application logic
    │   ├── application/       # Ingestion, response generation, and evaluation layers
    │   ├── domain/            # Entities, agent profiles, and schemas
    │   ├── infrastructure/    # API endpoints, WebSocket handler, and DB connections
    │   └── config.py          # App settings and environment variables
    ├── tools/                 # CLI tools for ingestion and testing
    ├── .env.example           # Environment template
    ├── Dockerfile             # Docker definition for the API
    └── pyproject.toml         # Python packaging configuration
```

---

# 🏗️ Set Up Your Local Infrastructure

We run all services (Game UI, Backend API, MongoDB, Evidently) via Docker Compose.

Make sure ports `8080` (UI), `8000` (API), and `27017` (MongoDB) are unoccupied.

Run the following commands from the **root directory** of the project:

```bash
# Build & start all containers in detached mode
make infrastructure-up

# Stop all containers
make infrastructure-stop

# Build the containers without starting them
make infrastructure-build
```

---

# ⚡️ Running the Application

Once your infrastructure containers are up:

### 1. Ingest J&J Knowledge Base
Populate the database with the J&J site content:
```bash
make create-long-term-memory
```
This loads data from `pharmagent-api/data/jnj_content.txt` into the local MongoDB instance under the `pharma_agent` database.

### 2. Launch the UI
Access the 2D visual town game in your browser:
👉 **[http://localhost:8080](http://localhost:8080)**

Navigate around the town using the arrow keys and approach the Pharma Agent character. Press **Space** to interact and ask questions about Johnson & Johnson's operations or Credo.

### 3. API Documentation
Explore endpoint definitions and interact with raw requests:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

# 🔧 Developer Commands

Below is a reference of available scripts you can run from the project root:

### Query Agent via CLI
Directly invoke the J&J agent from the command line:
```bash
make call-agent
```

### Delete DB Collection
Wipe the long term memory data from MongoDB:
```bash
make delete-long-term-memory
```

### Run Evaluation
Generate a dataset or run the Opik evaluation suite:
```bash
# Generate evaluation dataset
make generate-evaluation-dataset

# Run LLM-as-a-judge tests
make evaluate-agent

# Run Evidently evaluation reports
make evaluate-agent-evidently
```
To view prompt logs and evaluations, log in to your dashboard at **[Opik](https://www.comet.com/site/products/opik/)**.
