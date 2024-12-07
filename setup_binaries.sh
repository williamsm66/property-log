#!/bin/bash

# Exit on error
set -e

echo "Starting binary setup..."

# Create directories
mkdir -p "$HOME/bin"
mkdir -p "$HOME/lib"
mkdir -p "$HOME/share/tessdata"

# Function to download with retry
download_with_retry() {
    local url=$1
    local output=$2
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "Downloading $output (attempt $attempt)..."
        if wget -q "$url" -O "$output"; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 5
    done
    return 1
}

# Download and install Tesseract
echo "Setting up Tesseract..."
if ! download_with_retry "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/eng.traineddata" "$HOME/share/tessdata/eng.traineddata"; then
    echo "Failed to download Tesseract language data"
    exit 1
fi

# Create simple tesseract wrapper script
cat > "$HOME/bin/tesseract" << 'EOF'
#!/bin/bash
export TESSDATA_PREFIX="$HOME/share/tessdata"
if [ -f "/usr/bin/tesseract" ]; then
    /usr/bin/tesseract "$@"
elif [ -f "/usr/local/bin/tesseract" ]; then
    /usr/local/bin/tesseract "$@"
else
    echo "Tesseract binary not found"
    exit 1
fi
EOF

chmod +x "$HOME/bin/tesseract"

# Create simple soffice wrapper script
cat > "$HOME/bin/soffice" << 'EOF'
#!/bin/bash
if [ -f "/usr/bin/soffice" ]; then
    /usr/bin/soffice "$@"
elif [ -f "/usr/local/bin/soffice" ]; then
    /usr/local/bin/soffice "$@"
else
    echo "LibreOffice binary not found"
    exit 1
fi
EOF

chmod +x "$HOME/bin/soffice"

# Add to PATH
echo "export PATH=$HOME/bin:$PATH" >> "$HOME/.profile"
echo "export LD_LIBRARY_PATH=$HOME/lib:$LD_LIBRARY_PATH" >> "$HOME/.profile"
echo "export TESSDATA_PREFIX=$HOME/share/tessdata" >> "$HOME/.profile"

# Source the profile
source "$HOME/.profile"

# Verify installations
echo "Verifying installations..."
echo "Testing Tesseract..."
"$HOME/bin/tesseract" --version || echo "Tesseract test failed"
echo "Testing LibreOffice..."
"$HOME/bin/soffice" --version || echo "LibreOffice test failed"

echo "Setup complete!"
