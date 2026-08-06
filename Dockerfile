FROM python:3.11.11-slim-bookworm
WORKDIR /workspace
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
ENTRYPOINT ["hera-run"]

