"""
Test Voice Position - Demande ta position vocalement
- Dis "position" ou "ou sommes-nous" ou "ou on est"
- Recupere la position SimConnect
- Trouve la ville survolee
- Repond en vocal
"""

import sys
print("Demarrage...")

# Imports
try:
    import pyaudio
    import wave
    import asyncio
    import edge_tts
    import os
    import struct
    import math
    import tempfile
    import json
    from SimConnect import SimConnect, AircraftRequests
    print("[OK] Imports reussis")
except Exception as e:
    print(f"[ERREUR] Import: {e}")
    input("Appuie sur Entree...")
    sys.exit(1)

# Configuration audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 100
SILENCE_DURATION = 2.5  # Plus court pour les commandes
TTS_VOICE = "fr-FR-DeniseNeural"

# Charger cle Groq
GROQ_API_KEY = None
try:
    with open("config.json", "r") as f:
        config = json.load(f)
        GROQ_API_KEY = config.get("groq_api_key", "")
        if GROQ_API_KEY:
            print("[OK] Cle Groq chargee")
except:
    pass

if not GROQ_API_KEY:
    GROQ_API_KEY = input("Entre ta cle API Groq: ").strip()

# Connexion SimConnect
print("\nConnexion a MSFS...")
try:
    sm = SimConnect()
    aq = AircraftRequests(sm, _time=0)
    print("[OK] Connecte a MSFS")
except Exception as e:
    print(f"[ERREUR] SimConnect: {e}")
    print("Assure-toi que MSFS est lance!")
    input("Appuie sur Entree...")
    sys.exit(1)


def get_aircraft_position():
    """Recupere la position actuelle de l'avion"""
    try:
        lat = aq.get("PLANE_LATITUDE")
        lon = aq.get("PLANE_LONGITUDE")
        alt = aq.get("PLANE_ALTITUDE")
        heading = aq.get("PLANE_HEADING_DEGREES_TRUE")
        speed = aq.get("AIRSPEED_INDICATED")

        return {
            "lat": float(lat) if lat else 0,
            "lon": float(lon) if lon else 0,
            "alt": int(float(alt)) if alt else 0,
            "heading": int(float(heading) * 180 / 3.14159) if heading else 0,
            "speed": int(float(speed)) if speed else 0
        }
    except Exception as e:
        print(f"[ERREUR] Position: {e}")
        return None


def get_city_from_coords(lat, lon):
    """Trouve la ville la plus proche via reverse geocoding"""
    try:
        import requests
        # Utilise Nominatim (OpenStreetMap) - gratuit
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
        headers = {"User-Agent": "MSFS-Mission-Generator/1.0"}
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            address = data.get("address", {})

            # Cherche ville, village, ou commune
            city = (address.get("city") or
                   address.get("town") or
                   address.get("village") or
                   address.get("municipality") or
                   address.get("county") or
                   "zone inconnue")

            country = address.get("country", "")

            return city, country
    except Exception as e:
        print(f"[ERREUR] Geocoding: {e}")

    return "zone inconnue", ""


def heading_to_cardinal(heading):
    """Convertit un cap en direction cardinale (phonetique pour TTS)"""
    # "este" pour que le TTS prononce le t final
    directions = ["nord", "nord-este", "este", "sud-este", "sud", "sud-ouest", "ouest", "nord-ouest"]
    index = round(heading / 45) % 8
    return directions[index]


def format_coordinates(lat, lon):
    """Formate les coordonnees en degres (phonetique pour TTS)"""
    lat_dir = "nord" if lat >= 0 else "sud"
    lon_dir = "este" if lon >= 0 else "ouest"  # "este" pour prononcer le t

    lat_deg = abs(lat)
    lon_deg = abs(lon)

    return f"{lat_deg:.1f} degres {lat_dir}, {lon_deg:.1f} degres {lon_dir}"


def get_rms(data):
    count = len(data) // 2
    format_str = "%dh" % count
    shorts = struct.unpack(format_str, data)
    sum_squares = sum(s ** 2 for s in shorts)
    return math.sqrt(sum_squares / count) if count > 0 else 0


def record_command():
    """Enregistre une commande vocale courte"""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("\n[MIC] Dis ta commande... (ex: 'position', 'ou on est')")

    frames = []
    silent_chunks = 0
    chunks_per_second = RATE // CHUNK
    silence_chunks_needed = int(SILENCE_DURATION * chunks_per_second)
    is_speaking = False

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
        except:
            break

        frames.append(data)
        rms = get_rms(data)

        # Barre de niveau
        level = min(30, int(rms / 100))
        bar = "#" * level + "." * (30 - level)
        print(f"\r[{bar}] {rms:.0f}  ", end="", flush=True)

        if rms > SILENCE_THRESHOLD:
            if not is_speaking:
                print("\n[PAROLE]")
                is_speaking = True
            silent_chunks = 0
        else:
            if is_speaking:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_needed:
                    print("\n[FIN]")
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


def transcribe(audio_file):
    """Transcrit avec Whisper Groq"""
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    print("[STT] Transcription...")
    with open(audio_file, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="fr",
            response_format="text"
        )
    return transcription.strip().lower()


async def speak(text):
    """Synthese vocale"""
    print(f"[TTS] {text}")

    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_file.close()

    communicate = edge_tts.Communicate(text, TTS_VOICE, rate="-5%")
    await communicate.save(temp_file.name)

    import pygame
    pygame.mixer.init()
    pygame.mixer.music.load(temp_file.name)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

    pygame.mixer.quit()
    os.unlink(temp_file.name)


def is_position_command(text):
    """Detecte si c'est une demande de position"""
    keywords = ["position", "ou on est", "ou sommes", "ou suis", "coordonn",
                "localisation", "ou est", "survol", "ville", "endroit"]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


async def handle_position_request():
    """Traite une demande de position"""
    print("\n[INFO] Recuperation position...")

    pos = get_aircraft_position()
    if not pos:
        await speak("Desolee, je n'arrive pas a recuperer la position.")
        return

    print(f"  Lat: {pos['lat']:.4f}, Lon: {pos['lon']:.4f}")
    print(f"  Alt: {pos['alt']} ft, Cap: {pos['heading']} deg")

    # Trouver la ville
    print("[INFO] Recherche ville...")
    city, country = get_city_from_coords(pos['lat'], pos['lon'])
    print(f"  Ville: {city}, {country}")

    # Construire la reponse
    cardinal = heading_to_cardinal(pos['heading'])

    # Altitude en pieds
    alt_text = f"{pos['alt']} pieds"
    if pos['alt'] > 10000:
        alt_text = f"{pos['alt'] // 1000} mille pieds"

    # Construire phrase
    if city != "zone inconnue":
        response = f"Nous survolons actuellement {city}... "
        if country and country != "France":
            response += f"en {country}... "
    else:
        coords = format_coordinates(pos['lat'], pos['lon'])
        response = f"Position actuelle... {coords}... "

    response += f"Altitude {alt_text}... "
    response += f"Cap {cardinal}... "

    if pos['speed'] > 0:
        response += f"Vitesse {pos['speed']} noeuds."

    await speak(response)


async def main():
    print("\n" + "=" * 50)
    print("ASSISTANT DE VOL - Commandes vocales")
    print("=" * 50)
    print()
    print("Commandes disponibles:")
    print("  - 'position' ou 'ou on est' : donne ta position")
    print("  - 'quitter' ou 'stop' : arrete le programme")
    print()
    print("Ctrl+C pour quitter")
    print()

    while True:
        try:
            # Enregistrer commande
            audio_file = record_command()

            if not audio_file:
                print("[!] Aucune parole detectee")
                continue

            # Transcrire
            try:
                text = transcribe(audio_file)
                print(f"\n>>> Tu as dit: \"{text}\"")
            finally:
                os.unlink(audio_file)

            if not text:
                continue

            # Analyser la commande
            if "quitter" in text or "stop" in text or "arret" in text:
                await speak("Au revoir et bon vol!")
                break

            elif is_position_command(text):
                await handle_position_request()

            else:
                # Commande non reconnue - on reste muet
                print("[...] Commande non reconnue, j'ignore.")

            print("\n" + "-" * 50)
            print("En attente de commande...")

        except KeyboardInterrupt:
            print("\n\nAu revoir!")
            break
        except Exception as e:
            print(f"\n[ERREUR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n[ERREUR FATALE] {e}")
        import traceback
        traceback.print_exc()

    # Fermer SimConnect
    try:
        sm.exit()
    except:
        pass

    input("\nAppuie sur Entree pour fermer...")
