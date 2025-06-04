[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/-leASaOw)

# Image Extractor, AR-Flappy Bird und 3D AR Game

1. 🖼️ image_extractor.py der mit S saven und ESC canceln kann.
2. 🐦 Ein kleines Augmented-Reality-Spiel im Stil von Flappy Bird. Benötigt ArUco Marker Board (richtig herum!).
Dann folgt der Vogel dem Finger. Es wird mit der Zeit immer schneller.
3. 🎮 Ein 3D AR Spiel, bei dem 2 Entons einen Laserstrahl schießen und sich gegenseitig treffen können.

## Installation

Zunächst Git-Repo clonen/runterladen, dann:

1. **Virtuelle Umgebung erstellen und aktivieren**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    ```

2. **Abhängigkeiten installieren**
    ```bash
    pip install -r requirements.txt
    ```

## Starten

```bash
1. python image_extractor.py -> Dann per CMD in dem Ordner: python image_extractor.py -i sample_image.jpg -o extracted_rect.png --width 900 --height 600
2. python ar_game.py -> ArUco Marker-Sheet in die Kamera halten, dann Flappy Bird spielen. Falls der Vogel nur am Boden fliegt ist das Marker-Sheet falsch rum.
3. python ar_game_3d.py -> Dann ArUco Marker 4+5 in die Kamera halten und Entons steuern.

