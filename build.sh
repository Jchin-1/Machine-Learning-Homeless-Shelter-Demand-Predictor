#!/bin/bash
# Build script for Render deployment

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Training ML model..."
python mlmodel.py

echo "Build complete!"
