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
if ! download_with_retry "https://github.com/tesseract-ocr/tesseract/releases/download/4.1.1/tesseract-4.1.1.tar.gz" "tesseract.tar.gz"; then
    echo "Failed to download Tesseract"
    exit 1
fi

# Extract and compile Tesseract
echo "Extracting and installing Tesseract..."
tar xf tesseract.tar.gz
cd tesseract-4.1.1
./autogen.sh
CXXFLAGS="-static" ./configure --prefix="$HOME"
make
make install
cd ..

# Download Tesseract language data
echo "Downloading Tesseract language data..."
if ! download_with_retry "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/eng.traineddata" "$HOME/share/tessdata/eng.traineddata"; then
    echo "Failed to download Tesseract language data"
    exit 1
fi

# Download and extract LibreOffice AppImage
echo "Downloading LibreOffice AppImage..."
if ! download_with_retry "https://download.documentfoundation.org/libreoffice/stable/7.6.4/deb/x86_64/LibreOffice_7.6.4_Linux_x86-64_deb.tar.gz" "libreoffice.tar.gz"; then
    echo "Failed to download LibreOffice"
    exit 1
fi

# Extract LibreOffice
echo "Extracting LibreOffice..."
tar xf libreoffice.tar.gz
cd LibreOffice_*_deb/DEBS
for deb in *.deb; do
    ar x "$deb"
    tar xf data.tar.* -C "$HOME"
done
cd ../..

# Clean up temporary files
cd "$HOME"
rm -rf "$HOME/tmp"

# Create wrapper scripts
cat > "$HOME/bin/tesseract" << 'EOF'
#!/bin/bash
export TESSDATA_PREFIX="$HOME/share/tessdata"
export LD_LIBRARY_PATH="$HOME/lib:$LD_LIBRARY_PATH"
"$HOME/bin/tesseract" "$@"
EOF
chmod +x "$HOME/bin/tesseract"

cat > "$HOME/bin/soffice" << 'EOF'
#!/bin/bash
export LD_LIBRARY_PATH="$HOME/lib:$LD_LIBRARY_PATH"
"$HOME/opt/libreoffice*/program/soffice" "$@"
EOF
chmod +x "$HOME/bin/soffice"

# Add to PATH and set environment variables
{
    echo "export PATH=$HOME/bin:$PATH"
    echo "export LD_LIBRARY_PATH=$HOME/lib:$LD_LIBRARY_PATH"
    echo "export TESSDATA_PREFIX=$HOME/share/tessdata"
} >> "$HOME/.profile"

# Source the profile
source "$HOME/.profile"

# Verify installations
echo "Verifying installations..."
echo "Testing Tesseract..."
"$HOME/bin/tesseract" --version || echo "Tesseract test failed"
echo "Testing LibreOffice..."
"$HOME/bin/soffice" --version || echo "LibreOffice test failed"

echo "Setup complete!"
