# Use an official Python runtime as a parent image
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app

COPY uv.lock /app/uv.lock
COPY pyproject.toml /app/pyproject.toml

RUN uv sync --frozen

COPY . /app

ENV PATH="/app/.venv/bin:$PATH"
# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV PORT=8080
ENV HOST=0.0.0.0

CMD ["python", "main.py"]
