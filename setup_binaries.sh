#!/bin/bash

# Exit on error
set -e

# Create directories for binaries
mkdir -p $HOME/bin
mkdir -p $HOME/lib

# Download and extract tesseract binary
echo "Downloading Tesseract..."
wget -q https://github.com/tesseract-ocr/tesseract/releases/download/5.3.3/tesseract-5.3.3.tar.gz
tar xf tesseract-5.3.3.tar.gz
mv tesseract-5.3.3/bin/* $HOME/bin/
mv tesseract-5.3.3/lib/* $HOME/lib/
rm -rf tesseract-5.3.3*

# Download English language data
echo "Downloading Tesseract English language data..."
mkdir -p $HOME/share/tessdata
wget -q https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata -O $HOME/share/tessdata/eng.traineddata

# Download and extract LibreOffice portable
echo "Downloading LibreOffice portable..."
wget -q https://downloadarchive.documentfoundation.org/libreoffice/old/7.5.4.2/portable/LibreOfficePortable_7.5.4.2_Linux_x86-64.tar.gz
tar xf LibreOfficePortable_7.5.4.2_Linux_x86-64.tar.gz -C $HOME/bin/
rm LibreOfficePortable_7.5.4.2_Linux_x86-64.tar.gz

# Add binaries to PATH
echo "export PATH=$HOME/bin:$PATH" >> $HOME/.profile
echo "export LD_LIBRARY_PATH=$HOME/lib:$LD_LIBRARY_PATH" >> $HOME/.profile
echo "export TESSDATA_PREFIX=$HOME/share/tessdata" >> $HOME/.profile

# Make binaries executable
chmod +x $HOME/bin/*

# Source the profile
source $HOME/.profile

# Verify installations
echo "Verifying installations..."
$HOME/bin/tesseract --version
$HOME/bin/soffice --version

echo "Setup complete!"
