#!/usr/bin/env bash
# Installiert alle (kostenlosen) Programme für den Kinderlied-Generator.
# Getestet unter Ubuntu/Debian. Unter Windows: in WSL (Ubuntu) ausführen.
set -e
sudo apt-get update
sudo apt-get install -y ffmpeg fluidsynth fluid-soundfont-gm espeak-ng mbrola mbrola-de7 python3-pip
pip3 install --user mido numpy pillow
echo "Fertig! Jetzt z.B.:  python3 generator/erstellen.py --alle"
