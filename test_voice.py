"""
Test Edge-TTS - Démonstration des voix Microsoft
"""

import asyncio
import edge_tts
import os

# Phrases de test pour un assistant de vol
TEST_PHRASES = [
    "Bonjour capitaine, bienvenue à bord.",
    "Position actuelle : 48 degrés nord, 2 degrés est. Altitude 35000 pieds.",
    "Distance restante vers la destination : 250 miles nautiques.",
    "Météo à l'arrivée : vent du 270 à 15 noeuds, visibilité 10 kilomètres, quelques nuages à 3000 pieds.",
    "Attention, vous dépassez la contrainte de vitesse maximale.",
    "Mission accomplie ! Excellent atterrissage à 85 pieds par minute.",
]

# Voix françaises disponibles
FRENCH_VOICES = [
    "fr-FR-DeniseNeural",      # Femme - Naturelle, pro
    "fr-FR-HenriNeural",       # Homme - Naturel
    "fr-FR-EloiseNeural",      # Femme - Jeune
    "fr-CA-SylvieNeural",      # Femme - Québécois
    "fr-CA-JeanNeural",        # Homme - Québécois
    "fr-BE-CharlineNeural",    # Femme - Belge
]


async def test_single_voice(voice: str, text: str, filename: str):
    """Génère un fichier audio avec une voix spécifique"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)
    print(f"  [OK] {filename}")


async def demo_all_voices():
    """Démo de toutes les voix françaises avec la même phrase"""
    print("=" * 50)
    print("DEMO EDGE-TTS - Toutes les voix françaises")
    print("=" * 50)

    test_phrase = "Bonjour, je suis votre assistant de vol. Comment puis-je vous aider ?"

    os.makedirs("voice_samples", exist_ok=True)

    for voice in FRENCH_VOICES:
        filename = f"voice_samples/{voice}.mp3"
        await test_single_voice(voice, test_phrase, filename)

    print("\n[OK] Fichiers générés dans le dossier 'voice_samples/'")
    print("  Écoute-les pour choisir ta voix préférée !")


async def demo_assistant_phrases():
    """Démo des phrases d'assistant avec la meilleure voix"""
    print("=" * 50)
    print("DEMO ASSISTANT DE VOL")
    print("=" * 50)

    # Voix recommandée pour un assistant pro
    voice = "fr-FR-DeniseNeural"

    os.makedirs("voice_samples", exist_ok=True)

    for i, phrase in enumerate(TEST_PHRASES, 1):
        filename = f"voice_samples/assistant_{i:02d}.mp3"
        await test_single_voice(voice, phrase, filename)

    print(f"\n[OK] {len(TEST_PHRASES)} phrases générées avec la voix {voice}")


async def quick_test():
    """Test rapide avec lecture immédiate (nécessite pygame)"""
    print("=" * 50)
    print("TEST RAPIDE AVEC LECTURE")
    print("=" * 50)

    voice = "fr-FR-DeniseNeural"
    text = "Position actuelle : 48 degrés nord, 2 degrés est. Altitude 8000 pieds. Distance restante : 150 miles nautiques."

    # Générer le fichier
    filename = "voice_samples/quick_test.mp3"
    os.makedirs("voice_samples", exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)
    print(f"[OK] Fichier généré : {filename}")

    # Essayer de lire avec pygame
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        print("[AUDIO] Lecture en cours...")

        # Attendre la fin de la lecture
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        print("[OK] Lecture terminée")
    except ImportError:
        print("\n[!] pygame non disponible - ouvre le fichier manuellement")
        print(f"  → {os.path.abspath(filename)}")


async def list_all_voices():
    """Liste toutes les voix disponibles"""
    print("=" * 50)
    print("TOUTES LES VOIX DISPONIBLES")
    print("=" * 50)

    voices = await edge_tts.list_voices()

    # Filtrer les voix françaises
    french_voices = [v for v in voices if v["Locale"].startswith("fr-")]

    print(f"\nVoix françaises ({len(french_voices)}) :\n")
    for v in french_voices:
        gender = "[F]" if v["Gender"] == "Female" else "[M]"
        print(f"  {gender} {v['ShortName']:30} - {v['Locale']}")

    print(f"\nTotal voix disponibles : {len(voices)}")


if __name__ == "__main__":
    print("\nQue veux-tu tester ?")
    print("1. Écouter toutes les voix françaises")
    print("2. Générer les phrases d'assistant de vol")
    print("3. Test rapide avec lecture")
    print("4. Lister toutes les voix disponibles")
    print()

    choice = input("Choix (1-4) : ").strip()

    if choice == "1":
        asyncio.run(demo_all_voices())
    elif choice == "2":
        asyncio.run(demo_assistant_phrases())
    elif choice == "3":
        asyncio.run(quick_test())
    elif choice == "4":
        asyncio.run(list_all_voices())
    else:
        print("Choix invalide")
