# --- BUILD STAGE ---
FROM python:3.11-slim as builder

# Set working directory for the build
WORKDIR /build

# Install build dependencies including Rust
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install maturin for Python-Rust bindings
RUN pip install --no-cache-dir maturin

# Copy Rust source and configuration
COPY rust_core/ ./rust_core/

# Build the Rust extension as a Python wheel
WORKDIR /build/rust_core
RUN maturin build --release --out /build/wheels

# --- FINAL STAGE ---
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies (e.g. libgcc for Rust binaries)
RUN apt-get update && apt-get install -y \
    libgcc1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from the current directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install the built Rust wheel from builder stage
COPY --from=builder /build/wheels /app/wheels
RUN pip install /app/wheels/*.whl && rm -rf /app/wheels

# Copy the rest of the backend files into /app/backend
COPY . ./backend/

# Move to the backend directory
WORKDIR /app/backend

# Add /app to PYTHONPATH so 'backend' package is found
ENV PYTHONPATH=/app

# Expose the port FastAPI will run on
EXPOSE 8010

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "4"]
