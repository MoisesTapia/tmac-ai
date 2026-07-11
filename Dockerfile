# syntax=docker/dockerfile:1
# TMAC v1.6.0 – Official Docker image
#
# R9.1: ENTRYPOINT is "tmac"; container args are forwarded to the CLI
# R9.2: mount a directory and run `docker run tmac scan --dir /scan --output /out/report.html`
# R9.3: container exit status == CLI findings-based exit code (0, 1, 2, or 3)
# R9.4: missing/invalid mounted dir → ScanError → CLI exits 3 (handled by the CLI itself)
#
# Usage example:
#   docker build -t tmac .
#   docker run --rm \
#     -v /path/to/terraform:/scan:ro \
#     -v /path/to/output:/out \
#     tmac scan --dir /scan --output /out/report.html

FROM python:3.11-slim

# Create a non-root user for security best practice
RUN groupadd --gid 1001 tmac && \
    useradd --uid 1001 --gid 1001 --no-create-home --shell /sbin/nologin tmac

WORKDIR /app

# Copy the project source (pyproject.toml + src/ are required by pip install .)
COPY pyproject.toml README.md* ./
COPY src/ ./src/

# Install the package; this places the `tmac` console script on PATH via pyproject.toml
# [tool.poetry.scripts] tmac = "tmac.cli:cli"
RUN pip install --no-cache-dir .

# Smoke-test: confirm the entrypoint is resolvable before shipping the image
RUN tmac --version

# Drop to non-root at runtime
USER tmac

# R9.1: ENTRYPOINT forwards all container arguments to the tmac CLI
ENTRYPOINT ["tmac"]
