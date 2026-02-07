"""
Test rapide pyttsx3 vs Edge-TTS
"""

import pyttsx3
import os

os.makedirs("voice_samples", exist_ok=True)

# Init engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')

# Trouver voix francaise
french_voice = None
for voice in voices:
    if 'french' in voice.name.lower() or 'hortense' in voice.name.lower():
        french_voice = voice
        break

if french_voice:
    print(f"Voix francaise trouvee: {french_voice.name}")
    engine.setProperty('voice', french_voice.id)
else:
    print("Pas de voix francaise, utilisation voix par defaut")

# Reglages
engine.setProperty('rate', 140)  # Vitesse (defaut 200)

# Phrases de test
phrases = [
    ("Bonjour capitaine, bienvenue a bord.", "pyttsx3_01_intro.wav"),
    ("Position actuelle, quarante-huit degres nord, deux degres est.", "pyttsx3_02_position.wav"),
    ("Altitude huit mille pieds. Vitesse deux cent vingt noeuds.", "pyttsx3_03_altitude.wav"),
    ("Attention, contrainte de vitesse depassee.", "pyttsx3_04_warning.wav"),
]

print("\nGeneration des fichiers...")

for text, filename in phrases:
    filepath = f"voice_samples/{filename}"
    engine.save_to_file(text, filepath)
    engine.runAndWait()
    print(f"[OK] {filepath}")

engine.stop()

print("\n" + "=" * 50)
print("Compare maintenant dans voice_samples/:")
print("  - pyttsx3_*.wav  (voix Windows offline)")
print("  - optimized_*.mp3 (Edge-TTS online)")
print("=" * 50)

# Lecture du premier fichier
try:
    import pygame
    pygame.mixer.init()
    pygame.mixer.music.load("voice_samples/pyttsx3_01_intro.wav")
    print("\n[AUDIO] Lecture pyttsx3...")
    pygame.mixer.music.play()
    import time
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    print("[OK] Termine")
except Exception as e:
    print(f"\n[!] Lecture auto impossible: {e}")
    print("    Ouvre les fichiers manuellement")
