#!/usr/bin/env bash

# Install system-level dependencies
apt-get update && apt-get install -y gcc libpq-dev

# Install Python packages
pip install -r requirements.txt
