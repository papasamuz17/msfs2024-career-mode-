"""
Test STT + TTS
- Enregistre ta voix au micro
- Detecte le silence (3 sec)
- Transcrit avec Whisper Groq
- Repete avec Edge-TTS

Appuie sur Ctrl+C pour quitter
"""

import pyaudio
import wave
import asyncio
import edge_tts
import os
import struct
import math
import tempfile
from datetime import datetime

# Configuration Groq
GROQ_API_KEY = None  # Sera charge depuis config.json

# Configuration audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # 16kHz pour Whisper
SILENCE_THRESHOLD = 500  # Seuil de volume pour detecter le silence
SILENCE_DURATION = 3.0  # Secondes de silence avant de stopper

# Configuration TTS
TTS_VOICE = "fr-FR-DeniseNeural"
TTS_RATE = "-5%"


def load_groq_key():
    """Charge la cle Groq depuis config.json"""
    global GROQ_API_KEY
    try:
        import json
        with open("config.json", "r") as f:
            config = json.load(f)
            GROQ_API_KEY = config.get("groq_api_key", "")
            if GROQ_API_KEY:
                print(f"[OK] Cle Groq chargee depuis config.json")
                return True
    except:
        pass

    # Demander la cle si pas trouvee
    print("[!] Cle Groq non trouvee dans config.json")
    GROQ_API_KEY = input("Entre ta cle API Groq: ").strip()
    return bool(GROQ_API_KEY)


def get_rms(data):
    """Calcule le volume RMS d'un chunk audio"""
    count = len(data) // 2
    format_str = "%dh" % count
    shorts = struct.unpack(format_str, data)
    sum_squares = sum(s ** 2 for s in shorts)
    return math.sqrt(sum_squares / count) if count > 0 else 0


def record_until_silence():
    """Enregistre jusqu'a 3 secondes de silence"""
    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("\n[MIC] Parle maintenant... (3s de silence = fin)")

    frames = []
    silent_chunks = 0
    chunks_per_second = RATE // CHUNK
    silence_chunks_needed = int(SILENCE_DURATION * chunks_per_second)

    is_speaking = False

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        rms = get_rms(data)

        if rms > SILENCE_THRESHOLD:
            # Parole detectee
            if not is_speaking:
                print("[MIC] Parole detectee...")
                is_speaking = True
            silent_chunks = 0
        else:
            # Silence
            if is_speaking:
                silent_chunks += 1
                remaining = SILENCE_DURATION - (silent_chunks / chunks_per_second)
                if silent_chunks % chunks_per_second == 0:
                    print(f"[MIC] Silence... {remaining:.0f}s")

                if silent_chunks >= silence_chunks_needed:
                    print("[MIC] Fin de l'enregistrement")
                    break

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Si rien n'a ete dit, retourner None
    if not is_speaking:
        return None

    # Sauvegarder en fichier WAV temporaire
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wf = wave.open(temp_file.name, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    return temp_file.name


def transcribe_with_groq(audio_file):
    """Transcrit l'audio avec Whisper via Groq"""
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)

    print("[STT] Transcription en cours...")

    with open(audio_file, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="fr",
            response_format="text"
        )

    return transcription.strip()


async def speak_with_edge_tts(text):
    """Synthetise et joue le texte avec Edge-TTS"""
    print(f"[TTS] Synthese: {text}")

    # Generer l'audio
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_file.close()

    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
    await communicate.save(temp_file.name)

    # Jouer avec pygame
    import pygame
    pygame.mixer.init()
    pygame.mixer.music.load(temp_file.name)
    pygame.mixer.music.play()

    print("[TTS] Lecture...")
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

    pygame.mixer.quit()

    # Nettoyer
    try:
        os.unlink(temp_file.name)
    except:
        pass


async def main_loop():
    """Boucle principale"""
    print("=" * 50)
    print("TEST STT (Whisper Groq) + TTS (Edge-TTS)")
    print("=" * 50)
    print()
    print("Mode: Tu parles -> Je repete")
    print("Silence de 3 secondes = fin de phrase")
    print("Ctrl+C pour quitter")
    print()

    if not load_groq_key():
        print("[!] Cle Groq requise pour la transcription")
        return

    while True:
        try:
            # Enregistrer
            audio_file = record_until_silence()

            if audio_file is None:
                print("[!] Aucune parole detectee, reessaie...")
                continue

            # Transcrire
            try:
                text = transcribe_with_groq(audio_file)
                print(f"\n[STT] Tu as dit: \"{text}\"\n")
            except Exception as e:
                print(f"[!] Erreur transcription: {e}")
                continue
            finally:
                # Nettoyer le fichier audio
                try:
                    os.unlink(audio_file)
                except:
                    pass

            if not text:
                print("[!] Transcription vide")
                continue

            # Repeter avec TTS
            await speak_with_edge_tts(text)

            print("\n" + "-" * 50)
            print("Pret pour la prochaine phrase...")

        except KeyboardInterrupt:
            print("\n\n[OK] Au revoir!")
            break


if __name__ == "__main__":
    asyncio.run(main_loop())
