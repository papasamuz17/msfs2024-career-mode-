"""
LLM Integration for V2 Copilot
Natural language conversation with Groq LLaMA
"""

import logging
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("MissionGenerator.Copilot.LLM")

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not available")


@dataclass
class ConversationMessage:
    """Single conversation message"""
    role: str                    # user, assistant, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FlightContext:
    """Current flight context for LLM"""
    # Position
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_ft: float = 0.0
    heading: float = 0.0

    # Flight state
    flight_phase: str = "parked"
    airspeed_kts: float = 0.0
    vertical_speed_fpm: float = 0.0
    fuel_remaining_gal: float = 0.0

    # Mission
    departure_icao: str = ""
    departure_name: str = ""
    arrival_icao: str = ""
    arrival_name: str = ""
    distance_nm: float = 0.0
    distance_remaining_nm: float = 0.0

    # Aircraft
    aircraft_title: str = ""
    aircraft_category: str = ""

    # Weather
    wind_direction: float = 0.0
    wind_speed_kts: float = 0.0
    visibility_sm: float = 10.0

    # === NAVIGATION DATA ===
    # GPS/Flight Plan
    next_wp_distance_nm: float = 0.0
    next_wp_bearing: float = 0.0
    next_wp_eta_minutes: float = 0.0
    dest_eta_minutes: float = 0.0
    dest_ete_minutes: float = 0.0
    flight_plan_wp_count: int = 0
    flight_plan_wp_index: int = 0

    # Autopilot
    ap_active: bool = False
    ap_hdg_mode: bool = False
    ap_hdg_selected: float = 0.0
    ap_alt_mode: bool = False
    ap_alt_selected: float = 0.0
    ap_spd_mode: bool = False
    ap_spd_selected: float = 0.0
    ap_vs_mode: bool = False
    ap_vs_selected: float = 0.0
    ap_nav_mode: bool = False
    ap_appr_mode: bool = False

    # Radio
    nav1_freq: float = 0.0
    nav1_dme: float = 0.0
    com1_freq: float = 0.0

    def to_context_string(self) -> str:
        """Convert to context string for LLM"""
        # Determine flight status based on phase
        phase_upper = self.flight_phase.upper()
        if phase_upper in ['PARKED', 'ENGINE_START']:
            status = "AU SOL - Moteurs en cours de demarrage ou a l'arret"
        elif phase_upper in ['TAXI_OUT', 'TAXI_IN']:
            status = "AU SOL - En train de rouler"
        elif phase_upper in ['TAKEOFF', 'INITIAL_CLIMB']:
            status = "EN VOL - Decollage ou montee initiale"
        elif phase_upper in ['CLIMB']:
            status = "EN VOL - En montee"
        elif phase_upper in ['CRUISE']:
            status = "EN VOL - En croisiere"
        elif phase_upper in ['DESCENT', 'APPROACH']:
            status = "EN VOL - En descente ou approche"
        elif phase_upper in ['LANDING', 'LANDING_ROLL']:
            status = "Atterrissage en cours"
        else:
            status = "Statut inconnu"

        # Format ETA/ETE
        def format_time(minutes: float) -> str:
            if minutes <= 0:
                return "N/A"
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            if hours > 0:
                return f"{hours}h{mins:02d}min"
            return f"{mins}min"

        # Build autopilot status
        ap_modes = []
        if self.ap_active:
            if self.ap_hdg_mode:
                ap_modes.append(f"HDG {self.ap_hdg_selected:.0f}°")
            if self.ap_alt_mode:
                ap_modes.append(f"ALT {self.ap_alt_selected:.0f}ft")
            if self.ap_vs_mode:
                ap_modes.append(f"VS {self.ap_vs_selected:+.0f}fpm")
            if self.ap_spd_mode:
                ap_modes.append(f"IAS {self.ap_spd_selected:.0f}kts")
            if self.ap_nav_mode:
                ap_modes.append("NAV")
            if self.ap_appr_mode:
                ap_modes.append("APPR")
        ap_status = ", ".join(ap_modes) if ap_modes else "OFF"

        # Navigation info
        nav_info = ""
        if self.flight_plan_wp_count > 0:
            nav_info = f"""
Navigation GPS:
- Waypoint suivant: #{self.flight_plan_wp_index + 1}/{self.flight_plan_wp_count}
- Distance waypoint: {self.next_wp_distance_nm:.1f} nm, cap {self.next_wp_bearing:.0f}°
- ETA waypoint: {format_time(self.next_wp_eta_minutes)}
- ETA destination: {format_time(self.dest_eta_minutes)}
- Temps restant: {format_time(self.dest_ete_minutes)}"""

        # Radio info
        radio_info = ""
        if self.nav1_freq > 0 or self.com1_freq > 0:
            radio_parts = []
            if self.com1_freq > 0:
                radio_parts.append(f"COM1: {self.com1_freq:.3f}")
            if self.nav1_freq > 0:
                radio_parts.append(f"NAV1: {self.nav1_freq:.2f}")
                if self.nav1_dme > 0:
                    radio_parts.append(f"DME: {self.nav1_dme:.1f}nm")
            radio_info = f"\nRadio: {', '.join(radio_parts)}"

        return f"""=== DONNEES EN TEMPS REEL (A UTILISER OBLIGATOIREMENT) ===

PHASE DE VOL ACTUELLE: {self.flight_phase.upper()}
STATUT: {status}

Position:
- Latitude: {self.latitude:.4f}, Longitude: {self.longitude:.4f}
- Altitude: {self.altitude_ft:.0f} ft
- Cap: {self.heading:.0f} degres

Parametres de vol:
- Vitesse indiquee: {self.airspeed_kts:.0f} kts
- Vitesse verticale: {self.vertical_speed_fpm:.0f} fpm
- Carburant restant: {self.fuel_remaining_gal:.0f} gallons

Autopilot: {ap_status}
{nav_info}

Mission en cours:
- Depart: {self.departure_icao} ({self.departure_name})
- Arrivee: {self.arrival_icao} ({self.arrival_name})
- Distance totale: {self.distance_nm:.0f} nm
- Distance restante: {self.distance_remaining_nm:.0f} nm
{radio_info}

Avion: {self.aircraft_title}

=== FIN DES DONNEES EN TEMPS REEL ==="""


SYSTEM_PROMPT = """Tu es un copilote IA experimente et professionnel pour simulateurs de vol.
Tu assistes le pilote pendant le vol en fournissant:
- Des informations sur la position, l'altitude, la distance restante
- Des conseils sur la navigation et les procedures
- Des reponses aux questions sur l'avion et le vol
- Des alertes importantes si necessaire

Regles importantes:
- Sois concis et professionnel comme un vrai copilote
- Utilise la terminologie aeronautique appropriee
- Reponds en francais
- Tes reponses doivent etre courtes (1-3 phrases maximum) sauf si on te demande des details
- IMPORTANT: Utilise TOUJOURS les donnees du CONTEXTE DU VOL ACTUEL fourni ci-dessous. Ne te base JAMAIS sur tes reponses precedentes car la situation change constamment.
- Si on te demande la phase de vol, l'altitude, la vitesse, etc., utilise UNIQUEMENT les valeurs du contexte actuel.
- Tu es toujours "actif" quand le pilote te parle."""


class CopilotLLM:
    """LLM-powered copilot assistant"""

    def __init__(self, api_key: str = "", model: str = "llama-3.3-70b-versatile"):
        self._api_key = api_key
        self._model = model
        self._client: Optional[Groq] = None
        self._conversation: List[ConversationMessage] = []
        self._context = FlightContext()
        self._callbacks: List[Callable[[str], None]] = []

        # Stats
        self._total_queries = 0
        self._total_tokens = 0

        if api_key and GROQ_AVAILABLE:
            self._initialize_client()

    def _initialize_client(self) -> bool:
        """Initialize Groq client"""
        if not GROQ_AVAILABLE:
            logger.error("Groq library not available")
            return False

        if not self._api_key:
            logger.warning("No API key provided for Groq")
            return False

        try:
            self._client = Groq(api_key=self._api_key)
            logger.info("Groq client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            return False

    def set_api_key(self, api_key: str) -> bool:
        """Set or update API key"""
        self._api_key = api_key
        return self._initialize_client()

    @property
    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self._client is not None

    def update_context(self, context: FlightContext) -> None:
        """Update flight context"""
        self._context = context

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for responses"""
        self._callbacks.append(callback)

    def query(self, user_message: str, include_context: bool = True) -> Optional[str]:
        """
        Send a query to the LLM

        Args:
            user_message: User's question or command
            include_context: Whether to include flight context

        Returns:
            LLM response or None if unavailable
        """
        if not self.is_available:
            return self._fallback_response(user_message)

        try:
            # Build messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

            # Add conversation history (last 4 messages only to avoid stale context)
            for msg in self._conversation[-4:]:
                messages.append({"role": msg.role, "content": msg.content})

            # Add CURRENT context right before user message (most important!)
            if include_context:
                context_msg = f"CONTEXTE DU VOL ACTUEL (DONNEES TEMPS REEL):\n{self._context.to_context_string()}"
                messages.append({"role": "system", "content": context_msg})

            # Add current message
            messages.append({"role": "user", "content": user_message})

            # Query LLM
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )

            assistant_message = response.choices[0].message.content.strip()

            # Record conversation
            self._conversation.append(ConversationMessage(role="user", content=user_message))
            self._conversation.append(ConversationMessage(role="assistant", content=assistant_message))

            # Update stats
            self._total_queries += 1
            if hasattr(response, 'usage') and response.usage:
                self._total_tokens += response.usage.total_tokens

            logger.debug(f"LLM query: '{user_message[:50]}...' -> '{assistant_message[:50]}...'")

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(assistant_message)
                except Exception as e:
                    logger.error(f"LLM callback error: {e}")

            return assistant_message

        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return self._fallback_response(user_message)

    def _fallback_response(self, user_message: str) -> str:
        """Provide fallback response when LLM unavailable"""
        message_lower = user_message.lower()

        # Position queries
        if any(word in message_lower for word in ['position', 'ou', 'location']):
            return (f"Position actuelle: {self._context.latitude:.4f}N, "
                   f"{self._context.longitude:.4f}E, altitude {self._context.altitude_ft:.0f} pieds.")

        # Altitude queries
        if any(word in message_lower for word in ['altitude', 'haut', 'niveau']):
            return f"Altitude actuelle: {self._context.altitude_ft:.0f} pieds."

        # Distance queries
        if any(word in message_lower for word in ['distance', 'loin', 'reste']):
            return f"Distance restante jusqu'a destination: {self._context.distance_remaining_nm:.0f} nm."

        # Speed queries
        if any(word in message_lower for word in ['vitesse', 'speed', 'rapide']):
            return f"Vitesse actuelle: {self._context.airspeed_kts:.0f} noeuds."

        # Weather queries
        if any(word in message_lower for word in ['meteo', 'vent', 'weather']):
            return (f"Vent actuel: {self._context.wind_direction:.0f} degres "
                   f"a {self._context.wind_speed_kts:.0f} noeuds. "
                   f"Visibilite: {self._context.visibility_sm:.1f} SM.")

        # Fuel queries
        if any(word in message_lower for word in ['carburant', 'fuel', 'essence']):
            return f"Carburant restant: {self._context.fuel_remaining_gal:.0f} gallons."

        # Default response
        return "Je n'ai pas pu traiter votre demande. LLM non disponible."

    def quick_info(self, info_type: str) -> str:
        """Get quick info without full LLM query"""
        info_map = {
            'position': f"Position: {self._context.latitude:.4f}N, {self._context.longitude:.4f}E",
            'altitude': f"Altitude: {self._context.altitude_ft:.0f} ft",
            'speed': f"Vitesse: {self._context.airspeed_kts:.0f} kts",
            'heading': f"Cap: {self._context.heading:.0f} degres",
            'distance': f"Distance restante: {self._context.distance_remaining_nm:.0f} nm",
            'fuel': f"Carburant: {self._context.fuel_remaining_gal:.0f} gal",
            'phase': f"Phase de vol: {self._context.flight_phase}",
            'weather': f"Vent {self._context.wind_direction:.0f}/{self._context.wind_speed_kts:.0f}kt, vis {self._context.visibility_sm:.1f}SM"
        }

        return info_map.get(info_type, f"Information '{info_type}' non disponible")

    def process_voice_command(self, command: str) -> str:
        """Process a voice command and return response"""
        command_lower = command.lower().strip()

        # Quick commands (no LLM needed)
        quick_commands = {
            'position': 'position',
            'altitude': 'altitude',
            'vitesse': 'speed',
            'cap': 'heading',
            'distance': 'distance',
            'carburant': 'fuel',
            'phase': 'phase',
            'meteo': 'weather'
        }

        for cmd, info_type in quick_commands.items():
            if cmd in command_lower:
                return self.quick_info(info_type)

        # Full LLM query for complex questions
        return self.query(command)

    def clear_conversation(self) -> None:
        """Clear conversation history"""
        self._conversation.clear()
        logger.info("Conversation history cleared")

    def get_conversation(self) -> List[ConversationMessage]:
        """Get conversation history"""
        return self._conversation.copy()

    def get_stats(self) -> Dict:
        """Get LLM statistics"""
        return {
            'available': self.is_available,
            'model': self._model,
            'total_queries': self._total_queries,
            'total_tokens': self._total_tokens,
            'conversation_length': len(self._conversation)
        }


# Global copilot LLM instance
_copilot_llm: Optional[CopilotLLM] = None

def get_copilot_llm() -> CopilotLLM:
    """Get or create global copilot LLM"""
    global _copilot_llm
    if _copilot_llm is None:
        _copilot_llm = CopilotLLM()
    return _copilot_llm
