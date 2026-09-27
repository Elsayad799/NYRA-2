#!/usr/bin/env bash
set -e
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
python3 run.py
