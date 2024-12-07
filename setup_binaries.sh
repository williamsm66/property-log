#!/bin/bash

# Exit on error
set -e

echo "Starting binary setup..."

# Create directories
mkdir -p "$HOME/bin"
mkdir -p "$HOME/lib"
mkdir -p "$HOME/share/tessdata"
mkdir -p "$HOME/tmp"

cd "$HOME/tmp"

# Function to download with retry
download_with_retry() {
    local url=$1
    local output=$2
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "Downloading $output (attempt $attempt)..."
        if curl -L -o "$output" "$url"; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 5
    done
    return 1
}

# Download and extract static Tesseract binary
echo "Downloading Tesseract static binary..."
TESSERACT_URL="https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
if ! download_with_retry "$TESSERACT_URL" "tesseract.exe"; then
    echo "Failed to download Tesseract binary"
    exit 1
fi

# Extract Tesseract binary
echo "Extracting Tesseract..."
7z x tesseract.exe -o"$HOME/bin/tesseract" > /dev/null

# Create Tesseract wrapper script
cat > "$HOME/bin/tesseract" << 'EOF'
#!/bin/bash
export TESSDATA_PREFIX="$HOME/share/tessdata"
"$HOME/bin/tesseract/tesseract.exe" "$@"
EOF
chmod +x "$HOME/bin/tesseract"

# Download Tesseract language data
echo "Downloading Tesseract language data..."
if ! download_with_retry "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/eng.traineddata" "$HOME/share/tessdata/eng.traineddata"; then
    echo "Failed to download Tesseract language data"
    exit 1
fi

# Download portable LibreOffice
echo "Downloading LibreOffice portable..."
LIBREOFFICE_URL="https://download.documentfoundation.org/libreoffice/stable/7.6.4/portable/LibreOfficePortable_7.6.4_Linux_x86-64.tar.gz"
if ! download_with_retry "$LIBREOFFICE_URL" "libreoffice.tar.gz"; then
    echo "Failed to download LibreOffice"
    exit 1
fi

# Extract LibreOffice
echo "Extracting LibreOffice..."
tar xf libreoffice.tar.gz -C "$HOME/bin/"

# Create LibreOffice wrapper script
cat > "$HOME/bin/soffice" << 'EOF'
#!/bin/bash
"$HOME/bin/LibreOfficePortable/program/soffice" "$@"
EOF
chmod +x "$HOME/bin/soffice"

# Clean up temporary files
cd "$HOME"
rm -rf "$HOME/tmp"

# Add to PATH and set environment variables
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
