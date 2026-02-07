"""
Test Edge-TTS Avance - Avec SSML pour voix plus naturelles
"""

import asyncio
import edge_tts
import os

os.makedirs("voice_samples", exist_ok=True)


async def generate_with_ssml(text: str, voice: str, filename: str, rate: str = "+0%", pitch: str = "+0Hz"):
    """Genere un fichier audio avec controle SSML"""

    # SSML pour controler la voix
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="fr-FR">
        <voice name="{voice}">
            <prosody rate="{rate}" pitch="{pitch}">
                {text}
            </prosody>
        </voice>
    </speak>
    """

    communicate = edge_tts.Communicate(ssml, voice)
    await communicate.save(filename)
    print(f"  [OK] {filename}")


async def generate_natural(text: str, voice: str, filename: str):
    """Genere avec des pauses naturelles inserees automatiquement"""

    # Ajouter des pauses naturelles
    text_with_pauses = text.replace(". ", "... ")  # Pause apres les phrases
    text_with_pauses = text_with_pauses.replace(", ", ", ... ")  # Micro-pause apres virgules
    text_with_pauses = text_with_pauses.replace(":", ": ... ")  # Pause apres deux-points

    communicate = edge_tts.Communicate(text_with_pauses, voice)
    await communicate.save(filename)
    print(f"  [OK] {filename}")


async def test_different_rates():
    """Compare differents debits de parole"""
    print("=" * 50)
    print("TEST DEBITS DE PAROLE")
    print("=" * 50)

    voice = "fr-FR-DeniseNeural"
    text = "Bonjour capitaine. Position actuelle, quarante-huit degres nord, deux degres est. Altitude huit mille pieds."

    rates = [
        ("-15%", "lent"),
        ("-5%", "naturel"),
        ("+0%", "normal"),
        ("+10%", "rapide"),
    ]

    for rate, label in rates:
        filename = f"voice_samples/rate_{label}.mp3"
        await generate_with_ssml(text, voice, filename, rate=rate)


async def test_different_pitches():
    """Compare differentes tonalites"""
    print("=" * 50)
    print("TEST TONALITES")
    print("=" * 50)

    voice = "fr-FR-DeniseNeural"
    text = "Distance restante vers la destination, deux cent cinquante miles nautiques."

    pitches = [
        ("-10Hz", "grave"),
        ("+0Hz", "normal"),
        ("+5Hz", "aigu"),
    ]

    for pitch, label in pitches:
        filename = f"voice_samples/pitch_{label}.mp3"
        await generate_with_ssml(text, voice, filename, pitch=pitch)


async def test_optimized_assistant():
    """Phrases d'assistant avec reglages optimises"""
    print("=" * 50)
    print("ASSISTANT OPTIMISE")
    print("=" * 50)

    voice = "fr-FR-DeniseNeural"

    # Reglages optimises pour un assistant de vol pro
    # Rate -5% = legrement plus lent, plus pose
    # Pitch +0Hz = naturel

    phrases = [
        ("Bonjour capitaine... bienvenue a bord.", "intro"),
        ("Position actuelle... quarante-huit degres nord... deux degres est. Altitude... huit mille pieds.", "position"),
        ("Distance restante vers la destination... deux cent cinquante miles nautiques. Temps estime... une heure quinze.", "distance"),
        ("Meteo a l'arrivee... vent du deux cent soixante-dix... a quinze noeuds. Visibilite dix kilometres. Quelques nuages a trois mille pieds.", "meteo"),
        ("Attention... vous approchez de la contrainte de vitesse maximale.", "warning"),
        ("Felicitations capitaine ! Excellent atterrissage... quatre-vingt-cinq pieds par minute. Mission accomplie.", "success"),
    ]

    for text, label in phrases:
        filename = f"voice_samples/optimized_{label}.mp3"
        await generate_with_ssml(text, voice, filename, rate="-5%", pitch="+0Hz")


async def test_male_voice_optimized():
    """Test voix masculine optimisee"""
    print("=" * 50)
    print("VOIX MASCULINE OPTIMISEE (Henri)")
    print("=" * 50)

    voice = "fr-FR-HenriNeural"

    phrases = [
        ("Bonjour commandant... systemes operationnels... prets pour le depart.", "male_intro"),
        ("Position actuelle... quarante-huit degres nord... deux degres est. Altitude... trente-cinq mille pieds. Cap deux sept zero.", "male_position"),
        ("Alerte... deviation de route detectee. Correction recommandee... dix degres a droite.", "male_warning"),
    ]

    for text, label in phrases:
        filename = f"voice_samples/{label}.mp3"
        await generate_with_ssml(text, voice, filename, rate="-8%", pitch="-5Hz")


async def test_comparison_raw_vs_optimized():
    """Comparaison brut vs optimise"""
    print("=" * 50)
    print("COMPARAISON BRUT vs OPTIMISE")
    print("=" * 50)

    voice = "fr-FR-DeniseNeural"

    # Version brute (comme les Neural de base)
    raw_text = "Bonjour, je suis votre assistant de vol. Comment puis-je vous aider?"
    communicate = edge_tts.Communicate(raw_text, voice)
    await communicate.save("voice_samples/compare_RAW.mp3")
    print("  [OK] voice_samples/compare_RAW.mp3 (brut)")

    # Version optimisee avec pauses et debit
    optimized_text = "Bonjour... je suis votre assistant de vol. Comment puis-je vous aider?"
    await generate_with_ssml(optimized_text, voice, "voice_samples/compare_OPTIMIZED.mp3", rate="-5%")
    print("       ^ Compare ces deux fichiers!")


async def play_file(filename: str):
    """Joue un fichier audio"""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
    except:
        pass


async def demo_complete():
    """Demo complete avec lecture"""
    print("=" * 50)
    print("DEMO COMPLETE - Assistant de vol optimise")
    print("=" * 50)
    print()

    voice = "fr-FR-DeniseNeural"

    phrases = [
        "Bonjour capitaine... bienvenue a bord. Systemes initialises.",
        "Position actuelle... quarante-huit degres nord... deux degres est.",
        "Altitude... huit mille pieds. Vitesse... deux cent vingt noeuds.",
        "Distance restante... cent cinquante miles nautiques.",
        "Temps estime vers destination... quarante-cinq minutes.",
    ]

    print("Generation des fichiers...")
    for i, text in enumerate(phrases, 1):
        filename = f"voice_samples/demo_{i:02d}.mp3"
        await generate_with_ssml(text, voice, filename, rate="-5%")

    print("\nLecture de la demo...")
    try:
        import pygame
        pygame.mixer.init()

        for i in range(1, len(phrases) + 1):
            filename = f"voice_samples/demo_{i:02d}.mp3"
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.3)  # Pause entre phrases

        print("\n[OK] Demo terminee!")
    except ImportError:
        print("\n[!] pygame non disponible - ecoute les fichiers manuellement")


if __name__ == "__main__":
    print("\nTests avances Edge-TTS")
    print("=" * 50)
    print("1. Comparer differents debits")
    print("2. Comparer differentes tonalites")
    print("3. Assistant optimise (recommande)")
    print("4. Voix masculine optimisee")
    print("5. Comparaison BRUT vs OPTIMISE")
    print("6. Demo complete avec lecture")
    print()

    choice = input("Choix (1-6) : ").strip()

    if choice == "1":
        asyncio.run(test_different_rates())
    elif choice == "2":
        asyncio.run(test_different_pitches())
    elif choice == "3":
        asyncio.run(test_optimized_assistant())
    elif choice == "4":
        asyncio.run(test_male_voice_optimized())
    elif choice == "5":
        asyncio.run(test_comparison_raw_vs_optimized())
    elif choice == "6":
        asyncio.run(demo_complete())
    else:
        print("Choix invalide")
