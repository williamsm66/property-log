#!/bin/bash

# Exit on error and print commands
set -ex

echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "System information:"
uname -a
cat /etc/os-release

# Update package lists and install prerequisites
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    software-properties-common \
    wget \
    gnupg \
    lsb-release

# Add Tesseract repository
sudo wget -O - https://notesalexp.org/debian/alexp_key.asc | sudo apt-key add -
sudo echo "deb https://notesalexp.org/tesseract-ocr5/$(lsb_release -cs)/ $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/tesseract.list

# Update again with new repository
sudo apt-get update

# Install packages
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice \
    poppler-utils \
    ghostscript

# Print installation locations and versions
echo "Tesseract location and version:"
which tesseract || echo "Tesseract not found in PATH"
tesseract --version || echo "Tesseract not working"

echo "LibreOffice location and version:"
which soffice || echo "LibreOffice not found in PATH"
soffice --version || echo "LibreOffice not working"

echo "System PATH:"
echo $PATH

# Ensure proper permissions
if [ -f "$(which tesseract)" ]; then
    sudo chmod +x $(which tesseract)
fi

if [ -f "$(which soffice)" ]; then
    sudo chmod +x $(which soffice)
fi

# Create symlinks in standard locations
if [ ! -f "/usr/local/bin/tesseract" ] && [ -f "$(which tesseract)" ]; then
    sudo ln -sf $(which tesseract) /usr/local/bin/tesseract
fi

if [ ! -f "/usr/local/bin/soffice" ] && [ -f "$(which soffice)" ]; then
    sudo ln -sf $(which soffice) /usr/local/bin/soffice
fi

# Verify installations after setup
echo "Final verification:"
echo "Tesseract version after setup:"
/usr/local/bin/tesseract --version || echo "Tesseract still not working"
echo "LibreOffice version after setup:"
/usr/local/bin/soffice --version || echo "LibreOffice still not working"

# Create necessary directories for Tesseract
sudo mkdir -p /usr/local/share/tessdata
sudo chmod 777 /usr/local/share/tessdata

# Download and install English language data
sudo wget -O /usr/local/share/tessdata/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
