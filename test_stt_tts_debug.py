"""
Test STT + TTS - Version Debug
"""

import sys
print("Demarrage du script...")
print(f"Python: {sys.version}")

try:
    print("Import pyaudio...")
    import pyaudio
    print("  OK")
except Exception as e:
    print(f"  ERREUR: {e}")
    input("Appuie sur Entree pour quitter...")
    sys.exit(1)

try:
    print("Import autres modules...")
    import wave
    import asyncio
    import edge_tts
    import os
    import struct
    import math
    import tempfile
    print("  OK")
except Exception as e:
    print(f"  ERREUR: {e}")
    input("Appuie sur Entree pour quitter...")
    sys.exit(1)

# Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 100  # Baisse pour detecter la voix plus facilement
SILENCE_DURATION = 3.0
TTS_VOICE = "fr-FR-DeniseNeural"

# Charger cle Groq
print("\nChargement cle Groq...")
GROQ_API_KEY = None
try:
    import json
    with open("config.json", "r") as f:
        config = json.load(f)
        GROQ_API_KEY = config.get("groq_api_key", "")
        if GROQ_API_KEY:
            print(f"  OK - Cle trouvee")
        else:
            print("  ERREUR - Cle vide dans config.json")
except Exception as e:
    print(f"  ERREUR: {e}")

if not GROQ_API_KEY:
    GROQ_API_KEY = input("Entre ta cle API Groq: ").strip()

# Test micro
print("\nTest du microphone...")
try:
    p = pyaudio.PyAudio()

    # Lister les peripheriques audio
    print(f"  Peripheriques audio disponibles:")
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            print(f"    [{i}] {dev['name']} (input)")

    # Ouvrir le stream
    print("\n  Ouverture du micro...")
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    print("  OK - Micro ouvert")

    stream.close()
    p.terminate()
except Exception as e:
    print(f"  ERREUR micro: {e}")
    input("Appuie sur Entree pour quitter...")
    sys.exit(1)

def get_rms(data):
    count = len(data) // 2
    format_str = "%dh" % count
    shorts = struct.unpack(format_str, data)
    sum_squares = sum(s ** 2 for s in shorts)
    return math.sqrt(sum_squares / count) if count > 0 else 0

def record_until_silence():
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("\n" + "=" * 50)
    print("PARLE MAINTENANT!")
    print("(3 secondes de silence = fin)")
    print("=" * 50)

    frames = []
    silent_chunks = 0
    chunks_per_second = RATE // CHUNK
    silence_chunks_needed = int(SILENCE_DURATION * chunks_per_second)
    is_speaking = False

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
        except Exception as e:
            print(f"Erreur lecture micro: {e}")
            break

        frames.append(data)
        rms = get_rms(data)

        # Afficher le niveau audio
        level = min(50, int(rms / 100))
        bar = "#" * level + "." * (50 - level)
        print(f"\rNiveau: [{bar}] {rms:.0f}  ", end="", flush=True)

        if rms > SILENCE_THRESHOLD:
            if not is_speaking:
                print("\n[PAROLE DETECTEE]")
                is_speaking = True
            silent_chunks = 0
        else:
            if is_speaking:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_needed:
                    print("\n[FIN - 3s de silence]")
                    break

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not is_speaking:
        return None

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wf = wave.open(temp_file.name, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    return temp_file.name

def transcribe_with_groq(audio_file):
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    print("\nTranscription Whisper en cours...")
    with open(audio_file, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="fr",
            response_format="text"
        )
    return transcription.strip()

async def speak(text):
    print(f"Synthese vocale: {text}")
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_file.close()

    communicate = edge_tts.Communicate(text, TTS_VOICE, rate="-5%")
    await communicate.save(temp_file.name)

    import pygame
    pygame.mixer.init()
    pygame.mixer.music.load(temp_file.name)
    pygame.mixer.music.play()

    print("Lecture audio...")
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

    pygame.mixer.quit()
    os.unlink(temp_file.name)

async def main():
    print("\n" + "=" * 50)
    print("TEST STT/TTS PRET")
    print("=" * 50)

    while True:
        try:
            # Enregistrer
            audio_file = record_until_silence()

            if not audio_file:
                print("\nAucune parole detectee. Reessaie...")
                continue

            # Transcrire
            try:
                text = transcribe_with_groq(audio_file)
                print(f"\n>>> TU AS DIT: \"{text}\"")
            finally:
                os.unlink(audio_file)

            if text:
                # Repeter
                await speak(text)

            print("\n" + "-" * 50)
            print("Pret pour la prochaine phrase...")

        except KeyboardInterrupt:
            print("\n\nAu revoir!")
            break
        except Exception as e:
            print(f"\nErreur: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nErreur fatale: {e}")
        import traceback
        traceback.print_exc()

    input("\nAppuie sur Entree pour fermer...")
