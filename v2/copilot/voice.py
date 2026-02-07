"""
Voice System for V2 Copilot
Speech-to-Text (Whisper) and Text-to-Speech (Edge-TTS)
"""

import logging
import asyncio
import threading
import queue
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("MissionGenerator.Copilot.Voice")

# Try to import audio libraries
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("pygame not available for audio playback")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not available")

try:
    import pyaudio
    import wave
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not available for recording")


# Available TTS voices
TTS_VOICES = {
    'fr-FR-DeniseNeural': 'Denise (FR, female)',
    'fr-FR-HenriNeural': 'Henri (FR, male)',
    'fr-CA-SylvieNeural': 'Sylvie (CA, female)',
    'fr-CA-JeanNeural': 'Jean (CA, male)',
    'en-US-JennyNeural': 'Jenny (US, female)',
    'en-US-GuyNeural': 'Guy (US, male)',
    'en-GB-SoniaNeural': 'Sonia (GB, female)',
    'en-GB-RyanNeural': 'Ryan (GB, male)'
}


@dataclass
class VoiceConfig:
    """Voice system configuration"""
    tts_enabled: bool = True
    stt_enabled: bool = True
    voice: str = 'fr-FR-DeniseNeural'
    rate: str = '+10%'          # Speech rate adjustment
    volume: str = '+0%'         # Volume adjustment
    pitch: str = '+0Hz'         # Pitch adjustment
    cache_enabled: bool = True   # Cache TTS audio files
    cache_dir: Path = None
    mic_device_index: int = None  # Selected microphone device index (None = default)
    groq_api_key: str = ""       # Groq API key for Whisper transcription


class VoiceSystem:
    """
    Voice system with TTS and STT capabilities
    Uses Edge-TTS for synthesis and optional Whisper for recognition
    """

    def __init__(self, config: VoiceConfig = None):
        self._config = config or VoiceConfig()
        self._tts_queue: queue.Queue = queue.Queue()
        self._stt_queue: queue.Queue = queue.Queue()
        self._tts_thread: Optional[threading.Thread] = None
        self._stt_thread: Optional[threading.Thread] = None
        self._running = False

        # Callbacks
        self._tts_callbacks: List[Callable[[str], None]] = []
        self._stt_callbacks: List[Callable[[str], None]] = []

        # Cache
        if self._config.cache_dir is None:
            self._config.cache_dir = Path(tempfile.gettempdir()) / "msfs_voice_cache"
        self._config.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Path] = {}

        # Initialize pygame mixer for playback
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                logger.info("Audio playback initialized")
            except Exception as e:
                logger.error(f"Failed to init pygame mixer: {e}")

        # Event loop for async TTS
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Microphone level monitoring (persistent stream)
        self._mic_stream = None
        self._mic_pyaudio = None
        self._mic_level: float = 0.0
        self._mic_thread: Optional[threading.Thread] = None
        self._mic_monitor_running = False

    @property
    def tts_available(self) -> bool:
        return EDGE_TTS_AVAILABLE and PYGAME_AVAILABLE

    @property
    def stt_available(self) -> bool:
        return PYAUDIO_AVAILABLE

    def start(self) -> None:
        """Start voice system threads"""
        if self._running:
            return

        self._running = True

        # Start TTS thread
        if self._config.tts_enabled and self.tts_available:
            self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self._tts_thread.start()
            logger.info("TTS worker started")

        # Start STT thread
        if self._config.stt_enabled and self.stt_available:
            self._stt_thread = threading.Thread(target=self._stt_worker, daemon=True)
            self._stt_thread.start()
            logger.info("STT worker started")

    def stop(self) -> None:
        """Stop voice system"""
        self._running = False

        # Clear queues
        while not self._tts_queue.empty():
            try:
                self._tts_queue.get_nowait()
            except queue.Empty:
                break

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        # Stop mic monitor
        self._stop_mic_monitor()

        logger.info("Voice system stopped")

    def set_voice(self, voice: str) -> None:
        """Set TTS voice"""
        if voice in TTS_VOICES:
            self._config.voice = voice
            logger.info(f"TTS voice set to: {TTS_VOICES[voice]}")

    def set_rate(self, rate: str) -> None:
        """Set speech rate (e.g., '+10%', '-20%')"""
        self._config.rate = rate

    def register_tts_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for TTS events"""
        self._tts_callbacks.append(callback)

    def register_stt_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for STT events"""
        self._stt_callbacks.append(callback)

    def speak(self, text: str, priority: bool = False) -> None:
        """
        Queue text for speech synthesis

        Args:
            text: Text to speak
            priority: If True, speak immediately (clears queue)
        """
        if not self._config.tts_enabled:
            return

        if priority:
            # Clear queue for priority messages
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                except queue.Empty:
                    break

        self._tts_queue.put(text)
        logger.debug(f"TTS queued: {text[:50]}...")

    def speak_sync(self, text: str) -> bool:
        """
        Speak text synchronously (blocking)

        Args:
            text: Text to speak

        Returns:
            True if successful
        """
        if not self.tts_available:
            logger.warning("TTS not available")
            return False

        try:
            # Check cache
            cache_key = f"{self._config.voice}_{hash(text)}"
            audio_path = self._cache.get(cache_key)

            if not audio_path or not audio_path.exists():
                # Generate audio
                audio_path = self._config.cache_dir / f"{cache_key}.mp3"
                asyncio.run(self._generate_tts(text, audio_path))
                self._cache[cache_key] = audio_path

            # Play audio
            if audio_path.exists():
                pygame.mixer.music.load(str(audio_path))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                return True

        except Exception as e:
            logger.error(f"TTS sync error: {e}")

        return False

    async def _generate_tts(self, text: str, output_path: Path) -> bool:
        """Generate TTS audio file"""
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self._config.voice,
                rate=self._config.rate,
                volume=self._config.volume,
                pitch=self._config.pitch
            )
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return False

    def _tts_worker(self) -> None:
        """TTS worker thread"""
        # Create event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        while self._running:
            try:
                text = self._tts_queue.get(timeout=1.0)

                if text:
                    # Notify callbacks - starting
                    for callback in self._tts_callbacks:
                        try:
                            callback(f"speaking:{text}")
                        except:
                            pass

                    # Generate and play
                    self.speak_sync(text)

                    # Notify callbacks - done
                    for callback in self._tts_callbacks:
                        try:
                            callback("done")
                        except:
                            pass

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS worker error: {e}")

        self._loop.close()

    def _stt_worker(self) -> None:
        """STT worker thread (placeholder for Whisper integration)"""
        # Note: Full Whisper integration would require additional setup
        # This is a placeholder for the recording functionality

        while self._running:
            try:
                # Check for recording requests
                request = self._stt_queue.get(timeout=1.0)

                if request == "record":
                    text = self._record_and_transcribe()
                    if text:
                        for callback in self._stt_callbacks:
                            try:
                                callback(text)
                            except Exception as e:
                                logger.error(f"STT callback error: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"STT worker error: {e}")

    def set_groq_api_key(self, api_key: str) -> None:
        """Set Groq API key for Whisper transcription"""
        self._config.groq_api_key = api_key
        logger.info("Groq API key set for STT")

    def _get_rms(self, data) -> float:
        """Calculate RMS volume level from audio chunk"""
        import struct
        import math
        count = len(data) // 2
        if count == 0:
            return 0
        format_str = "<%dh" % count
        shorts = struct.unpack(format_str, data)
        sum_squares = sum(s ** 2 for s in shorts)
        return math.sqrt(sum_squares / count)

    def _record_and_transcribe(self, max_duration: float = 30.0) -> Optional[str]:
        """
        Record audio with automatic silence detection and transcribe using Groq Whisper
        Same logic as test_stt_tts.py that works well.

        Args:
            max_duration: Maximum recording duration in seconds (safety limit)

        Returns:
            Transcribed text or None
        """
        if not PYAUDIO_AVAILABLE:
            logger.warning("PyAudio not available for recording")
            return None

        # Audio config
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        SILENCE_THRESHOLD = 500   # RMS threshold - lowered for better speech detection
        SILENCE_DURATION = 4.0    # Seconds of silence before stopping (increased from 2.5)
        MIN_SPEECH_DURATION = 0.3 # Minimum speech duration to be valid (seconds)

        try:
            p = pyaudio.PyAudio()
            device_index = self._config.mic_device_index

            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )

            logger.info("Listening... (speak now, 2.5s silence = end)")

            frames = []
            silent_chunks = 0
            speech_chunks = 0
            chunks_per_second = RATE // CHUNK
            silence_chunks_needed = int(SILENCE_DURATION * chunks_per_second)
            min_speech_chunks = int(MIN_SPEECH_DURATION * chunks_per_second)
            max_chunks = int(max_duration * chunks_per_second)

            is_speaking = False
            chunk_count = 0

            while chunk_count < max_chunks:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                chunk_count += 1

                rms = self._get_rms(data)

                # Log level periodically for debugging
                if chunk_count % 10 == 0:
                    logger.debug(f"Mic level: {rms:.0f} (threshold: {SILENCE_THRESHOLD})")

                if rms > SILENCE_THRESHOLD:
                    # Speech detected
                    if not is_speaking:
                        logger.info(f"Speech detected (level: {rms:.0f})")
                        is_speaking = True
                    speech_chunks += 1
                    silent_chunks = 0
                else:
                    # Silence
                    if is_speaking:
                        silent_chunks += 1
                        if silent_chunks >= silence_chunks_needed:
                            logger.info(f"End of speech after {speech_chunks} chunks ({speech_chunks/chunks_per_second:.1f}s)")
                            break

            stream.stop_stream()
            stream.close()

            # Get sample size before terminating PyAudio
            sample_width = p.get_sample_size(FORMAT)
            p.terminate()

            # Check if we got enough speech
            if not is_speaking:
                logger.info("No speech detected")
                return None

            if speech_chunks < min_speech_chunks:
                logger.info(f"Speech too short ({speech_chunks} chunks < {min_speech_chunks} required)")
                return None

            # Save to temp WAV file
            temp_path = self._config.cache_dir / "recording.wav"
            wf = wave.open(str(temp_path), 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(sample_width)
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            logger.info(f"Audio recorded: {temp_path}")

            # Transcribe with Groq Whisper
            if self._config.groq_api_key:
                return self._transcribe_with_groq(temp_path)
            else:
                logger.warning("No Groq API key - cannot transcribe")
                return None

        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

    def _transcribe_with_groq(self, audio_path: Path) -> Optional[str]:
        """
        Transcribe audio file using Groq Whisper API
        Uses same format as working test_stt_tts.py

        Args:
            audio_path: Path to WAV file

        Returns:
            Transcribed text or None
        """
        try:
            from groq import Groq

            client = Groq(api_key=self._config.groq_api_key)

            logger.info("Transcribing with Groq Whisper...")

            # Use same format as working test file: file=f (open file object)
            with open(audio_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=f,
                    language="fr",
                    response_format="text"
                )

            # response_format="text" returns string directly
            text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
            logger.info(f"Transcription: {text}")
            return text

        except Exception as e:
            logger.error(f"Groq transcription error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def start_listening(self) -> None:
        """Start listening for voice input"""
        if self._config.stt_enabled and self.stt_available:
            self._stt_queue.put("record")

    def stop_current_speech(self) -> None:
        """Stop currently playing speech"""
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()

    def clear_cache(self) -> int:
        """Clear TTS cache"""
        count = 0
        if self._config.cache_dir.exists():
            for file in self._config.cache_dir.glob("*.mp3"):
                try:
                    file.unlink()
                    count += 1
                except:
                    pass
        self._cache.clear()
        logger.info(f"Cleared {count} cached audio files")
        return count

    def get_available_voices(self) -> Dict[str, str]:
        """Get available TTS voices"""
        return TTS_VOICES.copy()

    def get_available_microphones(self) -> List[tuple]:
        """
        Get list of available input devices

        Returns:
            List of tuples: (device_index, device_name)
        """
        devices = []
        if not PYAUDIO_AVAILABLE:
            return devices

        try:
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    # Only include input devices
                    if info.get('maxInputChannels', 0) > 0:
                        name = info.get('name', f'Device {i}')
                        devices.append((i, name))
                except Exception:
                    pass
            p.terminate()
        except Exception as e:
            logger.error(f"Error listing microphones: {e}")

        return devices

    def set_microphone(self, device_index: int) -> bool:
        """
        Set the microphone to use

        Args:
            device_index: PyAudio device index, or None for default

        Returns:
            True if device is valid
        """
        if device_index is None:
            self._config.mic_device_index = None
            logger.info("Microphone set to default")
            return True

        # Verify device exists and is an input device
        devices = self.get_available_microphones()
        for idx, name in devices:
            if idx == device_index:
                self._config.mic_device_index = device_index
                logger.info(f"Microphone set to: {name} (index {device_index})")
                return True

        logger.warning(f"Invalid microphone index: {device_index}")
        return False

    def _start_mic_monitor(self) -> None:
        """Start background thread for mic level monitoring"""
        if self._mic_thread is not None and self._mic_thread.is_alive():
            return

        self._mic_monitor_running = True
        self._mic_thread = threading.Thread(target=self._mic_monitor_worker, daemon=True)
        self._mic_thread.start()
        logger.info("Mic monitor thread started")

    def _stop_mic_monitor(self) -> None:
        """Stop mic monitoring and cleanup"""
        self._mic_monitor_running = False

        if self._mic_stream:
            try:
                self._mic_stream.stop_stream()
                self._mic_stream.close()
            except:
                pass
            self._mic_stream = None

        if self._mic_pyaudio:
            try:
                self._mic_pyaudio.terminate()
            except:
                pass
            self._mic_pyaudio = None

    def _mic_monitor_worker(self) -> None:
        """Background worker that continuously monitors mic level"""
        import struct

        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        current_device = self._config.mic_device_index

        while self._mic_monitor_running:
            try:
                # Check if device changed
                if current_device != self._config.mic_device_index:
                    self._stop_mic_monitor()
                    current_device = self._config.mic_device_index

                # Open stream if needed
                if self._mic_stream is None:
                    self._mic_pyaudio = pyaudio.PyAudio()
                    device_index = self._config.mic_device_index

                    if device_index is None:
                        try:
                            info = self._mic_pyaudio.get_default_input_device_info()
                            device_index = info.get('index')
                        except IOError:
                            self._mic_level = -1.0
                            import time
                            time.sleep(1)
                            continue

                    self._mic_stream = self._mic_pyaudio.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK
                    )

                # Read audio data
                data = self._mic_stream.read(CHUNK, exception_on_overflow=False)

                # Calculate RMS level
                count = len(data) // 2
                shorts = struct.unpack('<%dh' % count, data)
                sum_squares = sum(s * s for s in shorts)
                rms = (sum_squares / count) ** 0.5

                # Normalize and store
                self._mic_level = min(1.0, rms / 10000)

            except Exception as e:
                logger.debug(f"Mic monitor error: {e}")
                self._mic_level = -1.0
                self._stop_mic_monitor()
                import time
                time.sleep(0.5)

        # Cleanup on exit
        self._stop_mic_monitor()

    def get_mic_level(self) -> float:
        """
        Get current microphone input level from background monitor (0.0 to 1.0)
        Returns -1 if microphone not available
        """
        if not PYAUDIO_AVAILABLE:
            return -1.0

        # Start monitor thread if not running
        if self._mic_thread is None or not self._mic_thread.is_alive():
            self._start_mic_monitor()

        return self._mic_level

    def get_mic_level_once(self) -> float:
        """
        Get a single microphone level reading (blocking, no background thread)
        Use this for testing the mic, not for continuous monitoring

        Returns:
            Level 0.0 to 1.0, or -1 if error
        """
        if not PYAUDIO_AVAILABLE:
            return -1.0

        try:
            import struct

            CHUNK = 2048
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000

            p = pyaudio.PyAudio()
            device_index = self._config.mic_device_index

            # Get device index
            try:
                if device_index is None:
                    info = p.get_default_input_device_info()
                    device_index = info.get('index')
            except IOError:
                p.terminate()
                return -1.0

            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )

            # Read multiple chunks and get max level
            max_level = 0.0
            for _ in range(5):  # ~0.3 seconds of audio
                data = stream.read(CHUNK, exception_on_overflow=False)
                count = len(data) // 2
                shorts = struct.unpack('<%dh' % count, data)
                sum_squares = sum(s * s for s in shorts)
                rms = (sum_squares / count) ** 0.5
                level = min(1.0, rms / 10000)
                max_level = max(max_level, level)

            stream.stop_stream()
            stream.close()
            p.terminate()

            return max_level

        except Exception as e:
            logger.error(f"Mic level once error: {e}")
            return -1.0

    def check_mic_available(self) -> tuple:
        """
        Check if microphone is available and return info

        Returns:
            Tuple of (available: bool, device_name: str)
        """
        if not PYAUDIO_AVAILABLE:
            return (False, "PyAudio not installed")

        try:
            p = pyaudio.PyAudio()
            try:
                device_index = self._config.mic_device_index
                if device_index is not None:
                    info = p.get_device_info_by_index(device_index)
                else:
                    info = p.get_default_input_device_info()
                name = info.get('name', 'Unknown')[:30]
                p.terminate()
                return (True, name)
            except IOError:
                p.terminate()
                return (False, "No input device")
        except Exception as e:
            return (False, str(e))

    def get_stats(self) -> Dict:
        """Get voice system statistics"""
        return {
            'tts_available': self.tts_available,
            'stt_available': self.stt_available,
            'tts_enabled': self._config.tts_enabled,
            'stt_enabled': self._config.stt_enabled,
            'current_voice': self._config.voice,
            'queue_size': self._tts_queue.qsize(),
            'cached_files': len(self._cache)
        }


# Global voice system instance
_voice_system: Optional[VoiceSystem] = None

def get_voice_system() -> VoiceSystem:
    """Get or create global voice system"""
    global _voice_system
    if _voice_system is None:
        _voice_system = VoiceSystem()
    return _voice_system
