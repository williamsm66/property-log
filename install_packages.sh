#!/bin/bash

# Exit on error
set -e

# Update package lists
apt-get update

# Install system dependencies
apt-get install -y software-properties-common

# Add LibreOffice PPA
add-apt-repository -y ppa:libreoffice/ppa

# Update again after adding PPA
apt-get update

# Install required packages
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice \
    poppler-utils \
    ghostscript

# Verify installations
echo "Checking installations..."
which tesseract
which soffice
which pdftotext
