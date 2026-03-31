#!/bin/bash
cd "$(dirname "$0")"  # Скрипт сам поймет, в какой папке он лежит
python3 autobot.py
git add .
git commit -m "Auto-update: new articles"
git push origin main
