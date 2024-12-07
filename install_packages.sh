#!/bin/bash

# Exit on error
set -e

# Update package lists
apt-get update

# Install system dependencies
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    software-properties-common \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice \
    poppler-utils \
    ghostscript

# Create symbolic links in /usr/local/bin if needed
if [ ! -f "/usr/local/bin/tesseract" ]; then
    ln -s $(which tesseract) /usr/local/bin/tesseract
fi

if [ ! -f "/usr/local/bin/soffice" ]; then
    ln -s $(which soffice) /usr/local/bin/soffice
fi

# Verify installations and print versions
echo "Checking installations..."
echo "Tesseract version:"
tesseract --version
echo "LibreOffice version:"
soffice --version
echo "PATH environment:"
echo $PATH
