#!/bin/bash

# Exit on error and print commands
set -ex

echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "System information:"
uname -a
cat /etc/os-release

# Update package lists
sudo apt-get update

# Install system dependencies with proper permissions
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    software-properties-common \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice \
    poppler-utils \
    ghostscript

# Print installation locations
echo "Tesseract location:"
which tesseract || echo "Tesseract not found in PATH"
tesseract --version || echo "Tesseract not working"

echo "LibreOffice location:"
which soffice || echo "LibreOffice not found in PATH"
soffice --version || echo "LibreOffice not working"

echo "System PATH:"
echo $PATH

# Ensure binaries are executable
if [ -f "$(which tesseract)" ]; then
    sudo chmod +x $(which tesseract)
fi

if [ -f "$(which soffice)" ]; then
    sudo chmod +x $(which soffice)
fi

# Create symlinks if needed
if [ ! -f "/usr/local/bin/tesseract" ] && [ -f "$(which tesseract)" ]; then
    sudo ln -sf $(which tesseract) /usr/local/bin/tesseract
fi

if [ ! -f "/usr/local/bin/soffice" ] && [ -f "$(which soffice)" ]; then
    sudo ln -sf $(which soffice) /usr/local/bin/soffice
fi

# Verify installations again after symlinks
echo "Final verification:"
echo "Tesseract version after symlink:"
/usr/local/bin/tesseract --version || echo "Tesseract still not working"
echo "LibreOffice version after symlink:"
/usr/local/bin/soffice --version || echo "LibreOffice still not working"
