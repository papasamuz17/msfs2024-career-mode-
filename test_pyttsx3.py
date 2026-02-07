"""
Test pyttsx3 - Voix Windows SAPI5 (offline)
Comparaison avec Edge-TTS
"""

import pyttsx3
import os

os.makedirs("voice_samples", exist_ok=True)


def list_voices():
    """Liste toutes les voix disponibles sur le systeme"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    print("=" * 60)
    print("VOIX DISPONIBLES SUR CE SYSTEME (SAPI5)")
    print("=" * 60)

    for i, voice in enumerate(voices):
        print(f"\n[{i}] {voice.name}")
        print(f"    ID: {voice.id}")
        print(f"    Langues: {voice.languages}")

    engine.stop()
    return voices


def test_voice(voice_index: int, text: str, filename: str, rate: int = 150):
    """Teste une voix specifique"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    if voice_index < len(voices):
        engine.setProperty('voice', voices[voice_index].id)
        engine.setProperty('rate', rate)  # Vitesse (defaut ~200)

        # Sauvegarder en fichier
        engine.save_to_file(text, filename)
        engine.runAndWait()
        print(f"[OK] {filename}")
    else:
        print(f"[!] Voix {voice_index} non disponible")

    engine.stop()


def test_realtime(voice_index: int, text: str, rate: int = 150):
    """Lecture en temps reel"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    if voice_index < len(voices):
        engine.setProperty('voice', voices[voice_index].id)
        engine.setProperty('rate', rate)
        print(f"[AUDIO] Lecture avec: {voices[voice_index].name}")
        engine.say(text)
        engine.runAndWait()
    engine.stop()


def demo_all_voices():
    """Demo de toutes les voix avec la meme phrase"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    text = "Bonjour, je suis votre assistant de vol. Comment puis-je vous aider?"

    print("=" * 60)
    print("DEMO TOUTES LES VOIX")
    print("=" * 60)

    for i, voice in enumerate(voices):
        # Chercher voix francaises
        voice_name = voice.name.lower()
        if 'french' in voice_name or 'francais' in voice_name or 'fr-' in voice.id.lower():
            filename = f"voice_samples/pyttsx3_voice_{i}.wav"
            engine.setProperty('voice', voice.id)
            engine.setProperty('rate', 150)
            engine.save_to_file(text, filename)
            engine.runAndWait()
            print(f"[OK] {filename} - {voice.name}")

    engine.stop()


def demo_assistant():
    """Demo phrases assistant de vol"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    # Trouver une voix francaise
    french_voice = None
    for voice in voices:
        if 'french' in voice.name.lower() or 'hortense' in voice.name.lower():
            french_voice = voice
            break

    if not french_voice:
        print("[!] Pas de voix francaise trouvee, utilisation voix par defaut")
        french_voice = voices[0] if voices else None

    if not french_voice:
        print("[!] Aucune voix disponible")
        return

    print(f"Utilisation de: {french_voice.name}")

    phrases = [
        ("Bonjour capitaine, bienvenue a bord.", "pyttsx3_intro.wav"),
        ("Position actuelle, quarante-huit degres nord, deux degres est. Altitude huit mille pieds.", "pyttsx3_position.wav"),
        ("Distance restante vers la destination, deux cent cinquante miles nautiques.", "pyttsx3_distance.wav"),
        ("Attention, vous approchez de la contrainte de vitesse maximale.", "pyttsx3_warning.wav"),
    ]

    engine.setProperty('voice', french_voice.id)
    engine.setProperty('rate', 140)  # Un peu plus lent

    for text, filename in phrases:
        filepath = f"voice_samples/{filename}"
        engine.save_to_file(text, filepath)
        engine.runAndWait()
        print(f"[OK] {filepath}")

    engine.stop()


def compare_rates():
    """Compare differentes vitesses"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    # Trouver voix francaise
    french_voice = None
    for voice in voices:
        if 'french' in voice.name.lower() or 'hortense' in voice.name.lower():
            french_voice = voice
            break

    if not french_voice:
        french_voice = voices[0]

    text = "Position actuelle, quarante-huit degres nord. Altitude huit mille pieds."

    print("=" * 60)
    print("COMPARAISON VITESSES")
    print("=" * 60)

    engine.setProperty('voice', french_voice.id)

    for rate in [120, 140, 160, 180]:
        filename = f"voice_samples/pyttsx3_rate_{rate}.wav"
        engine.setProperty('rate', rate)
        engine.save_to_file(text, filename)
        engine.runAndWait()
        print(f"[OK] {filename} (rate={rate})")

    engine.stop()


if __name__ == "__main__":
    print("\nTest pyttsx3 (Voix Windows SAPI5)")
    print("=" * 60)
    print("1. Lister toutes les voix")
    print("2. Demo toutes les voix francaises")
    print("3. Demo assistant de vol")
    print("4. Comparer vitesses")
    print("5. Test lecture temps reel")
    print()

    choice = input("Choix (1-5) : ").strip()

    if choice == "1":
        list_voices()
    elif choice == "2":
        demo_all_voices()
    elif choice == "3":
        demo_assistant()
    elif choice == "4":
        compare_rates()
    elif choice == "5":
        voices = list_voices()
        print()
        idx = input("Numero de voix a tester : ").strip()
        if idx.isdigit():
            test_realtime(int(idx), "Bonjour, ceci est un test de la voix selectionnee.")
    else:
        print("Choix invalide")
