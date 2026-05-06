# Use a base image with both Python 3.12 and Node.js 20
FROM nikolaik/python-nodejs:python3.12-nodejs20-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy your forked repository into the container
COPY . /app/

# Initialize git submodules (vendor/awesome-agent-skills index for reference)
RUN git submodule update --init --recursive || true

# Install UV (Python package manager required by OMC)
RUN pip install uv

# Make the start script executable
RUN chmod +x start.sh

# Expose the default OMC port
EXPOSE 8000

# ──────────────────────────────────────────────────────────────────────────────
# Persistent state lives at /app/.onemancompany/ because OMC uses Path.cwd()
# (see core/config.py: DATA_ROOT = Path.cwd() / ".onemancompany").
#
# Mount a host volume to /app/.onemancompany to persist data across rebuilds:
#   - /app/.onemancompany/.env             ← API keys and provider config
#   - /app/.onemancompany/config.yaml      ← Runtime settings (sandbox, talent market)
#   - /app/.onemancompany/company/         ← All business data
#     ├── human_resource/employees/        ← Employee profiles, skills, manifests
#     ├── assets/tools/                    ← Custom tool definitions
#     ├── business/projects/               ← Project workspaces and deliverables
#     ├── business/products/               ← Product definitions
#     └── company_culture.yaml              ← Company culture rules
#   - /app/.onemancompany/logs/            ← Log files (7-day rotation)
#
# If NOT mounted, onemancompany-init will populate the directory inside the
# container — but ALL data will be lost on container removal.
# ──────────────────────────────────────────────────────────────────────────────

# Start the application using their native script
CMD ["bash", "start.sh"]
