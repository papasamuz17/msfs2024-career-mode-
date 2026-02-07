"""
Phase Calibration Tool
======================
Capture les variables SimConnect pour chaque phase de vol.
Permet de definir precisement les conditions de detection.

Usage:
1. Lancer ce programme
2. Se mettre dans la phase de vol demandee dans MSFS
3. Appuyer sur Entree pour capturer
4. Passer a la phase suivante
5. A la fin, un fichier JSON avec toutes les donnees est genere
"""

import json
import time
from datetime import datetime
from pathlib import Path

try:
    from SimConnect import SimConnect, AircraftRequests
    SIMCONNECT_OK = True
except ImportError:
    SIMCONNECT_OK = False
    print("[ERREUR] SimConnect non disponible")

# Liste des phases a calibrer (dans l'ordre du vol)
PHASES = [
    ("menu_principal", "MENU PRINCIPAL - Dans le menu du jeu, pas encore en vol"),
    ("menu_vol_libre", "MENU VOL LIBRE - Selection de l'aeroport/avion"),
    ("chargement", "CHARGEMENT - Ecran de chargement du vol"),
    ("pause", "JEU EN PAUSE - Vol actif mais en pause (touche P ou menu pause)"),
    ("cold_and_dark", "Avion froid - Moteurs eteints, parking, tout eteint"),
    ("preflight", "Preflight - Batteries ON, moteurs eteints"),
    ("engine_start", "Demarrage moteur - Moteur(s) en train de demarrer ou au ralenti"),
    ("taxi_out_start", "Debut taxi - Frein parking relache, pret a rouler"),
    ("taxi_out_moving", "Taxi en mouvement - En train de rouler vers la piste"),
    ("holding_runway", "En bout de piste - Aligne, pret au decollage, immobile"),
    ("takeoff_roll_start", "Debut roulement decollage - Plein gaz, debut acceleration"),
    ("takeoff_roll_v1", "Roulement a V1 - Vitesse V1 atteinte"),
    ("rotation", "Rotation - Nez qui se leve, juste avant de quitter le sol"),
    ("liftoff", "Decollage - Roues quittent le sol"),
    ("initial_climb", "Montee initiale - Train rentre, <1000ft AGL"),
    ("climb", "Montee - Au dessus de 1000ft, en montee"),
    ("cruise", "Croisiere - Vol stabilise en palier"),
    ("descent", "Descente - Descente vers destination"),
    ("approach", "Approche - En approche, train sorti"),
    ("short_final", "Finale courte - < 500ft AGL, piste en vue"),
    ("flare", "Arrondi - Juste avant le toucher"),
    ("touchdown", "Toucher des roues - Au moment du contact"),
    ("landing_roll", "Roulement atterrissage - Freinage sur piste"),
    ("taxi_in", "Taxi retour - Roulage vers parking"),
    ("shutdown", "Arret moteur - Parking, moteur au ralenti puis arret"),
    ("parked", "Parke - Moteur eteint, frein parking mis"),
]

# Variables SimConnect a capturer
SIMCONNECT_VARS = [
    # Position et mouvement
    "PLANE_LATITUDE",
    "PLANE_LONGITUDE",
    "PLANE_ALTITUDE",
    "PLANE_ALT_ABOVE_GROUND",
    "GROUND_ALTITUDE",
    "PLANE_HEADING_DEGREES_TRUE",
    "PLANE_HEADING_DEGREES_MAGNETIC",
    "PLANE_PITCH_DEGREES",
    "PLANE_BANK_DEGREES",

    # Vitesses
    "AIRSPEED_INDICATED",
    "AIRSPEED_TRUE",
    "GROUND_VELOCITY",
    "VERTICAL_SPEED",
    "ACCELERATION_BODY_Z",

    # Moteur
    "GENERAL_ENG_COMBUSTION:1",
    "GENERAL_ENG_RPM:1",
    "GENERAL_ENG_THROTTLE_LEVER_POSITION:1",
    "TURB_ENG_N1:1",
    "TURB_ENG_N2:1",
    "ENG_FUEL_FLOW_GPH:1",

    # Controles
    "BRAKE_PARKING_POSITION",
    "GEAR_HANDLE_POSITION",
    "GEAR_POSITION:0",
    "GEAR_POSITION:1",
    "GEAR_POSITION:2",
    "FLAPS_HANDLE_PERCENT",
    "FLAPS_HANDLE_INDEX",
    "SPOILERS_HANDLE_POSITION",
    "AILERON_POSITION",
    "ELEVATOR_POSITION",
    "RUDDER_POSITION",
    "ELEVATOR_TRIM_POSITION",

    # Etat avion
    "SIM_ON_GROUND",
    "ON_ANY_RUNWAY",
    "PLANE_IN_PARKING_STATE",
    "SURFACE_TYPE",
    "STALL_WARNING",
    "OVERSPEED_WARNING",

    # Systemes
    "ELECTRICAL_MASTER_BATTERY",
    "AVIONICS_MASTER_SWITCH",
    "LIGHT_LANDING",
    "LIGHT_TAXI",
    "LIGHT_BEACON",
    "LIGHT_NAV",
    "LIGHT_STROBE",
    "TRANSPONDER_STATE",

    # Carburant
    "FUEL_TOTAL_QUANTITY",
    "FUEL_TOTAL_QUANTITY_WEIGHT",

    # Autopilot
    "AUTOPILOT_MASTER",
    "AUTOPILOT_ALTITUDE_LOCK_VAR",
    "AUTOPILOT_HEADING_LOCK_DIR",

    # Simulation state
    "SIM_DISABLED",
    "CAMERA_STATE",

    # Poids
    "TOTAL_WEIGHT",
]


def safe_get(aq, var_name):
    """Recupere une variable SimConnect de facon securisee"""
    try:
        value = aq.get(var_name)
        if value is not None:
            return float(value) if not isinstance(value, str) else value
        return None
    except Exception as e:
        return f"ERROR: {e}"


def capture_state(aq):
    """Capture l'etat complet de toutes les variables"""
    state = {}
    for var in SIMCONNECT_VARS:
        state[var] = safe_get(aq, var)
    state['timestamp'] = datetime.now().isoformat()
    return state


def print_state_summary(state):
    """Affiche un resume de l'etat capture"""
    print("\n--- Resume de l'etat capture ---")
    print(f"  Position: {state.get('PLANE_LATITUDE', 'N/A'):.4f}, {state.get('PLANE_LONGITUDE', 'N/A'):.4f}")
    print(f"  Altitude: {state.get('PLANE_ALTITUDE', 'N/A'):.0f} ft (AGL: {state.get('PLANE_ALT_ABOVE_GROUND', 'N/A'):.0f} ft)")
    print(f"  Cap: {state.get('PLANE_HEADING_DEGREES_TRUE', 'N/A'):.0f} deg")
    print(f"  Pitch: {state.get('PLANE_PITCH_DEGREES', 'N/A'):.1f} deg")
    print(f"  IAS: {state.get('AIRSPEED_INDICATED', 'N/A'):.0f} kts")
    print(f"  GS: {state.get('GROUND_VELOCITY', 'N/A'):.0f} kts")
    print(f"  VS: {state.get('VERTICAL_SPEED', 'N/A'):.0f} fpm")
    print(f"  On Ground: {state.get('SIM_ON_GROUND', 'N/A')}")
    print(f"  On Runway: {state.get('ON_ANY_RUNWAY', 'N/A')}")
    print(f"  Engine Running: {state.get('GENERAL_ENG_COMBUSTION:1', 'N/A')}")
    print(f"  Engine RPM: {state.get('GENERAL_ENG_RPM:1', 'N/A'):.0f}" if state.get('GENERAL_ENG_RPM:1') else "  Engine RPM: N/A")
    print(f"  Parking Brake: {state.get('BRAKE_PARKING_POSITION', 'N/A')}")
    print(f"  Gear: {state.get('GEAR_HANDLE_POSITION', 'N/A')}")
    print(f"  Flaps: {state.get('FLAPS_HANDLE_PERCENT', 'N/A'):.0f}%" if state.get('FLAPS_HANDLE_PERCENT') else "  Flaps: N/A")
    print(f"  Throttle: {state.get('GENERAL_ENG_THROTTLE_LEVER_POSITION:1', 'N/A'):.0f}%" if state.get('GENERAL_ENG_THROTTLE_LEVER_POSITION:1') else "  Throttle: N/A")
    print("--------------------------------\n")


def main():
    print("=" * 60)
    print("   CALIBRATION DES PHASES DE VOL")
    print("=" * 60)
    print()
    print("Ce programme va capturer l'etat de SimConnect pour chaque")
    print("phase de vol afin d'ameliorer la detection automatique.")
    print()

    if not SIMCONNECT_OK:
        print("[ERREUR] SimConnect non disponible!")
        return

    # Connexion SimConnect
    print("Connexion a MSFS...")
    try:
        sm = SimConnect()
        aq = AircraftRequests(sm, _time=0)
        print("[OK] Connecte a MSFS\n")
    except Exception as e:
        print(f"[ERREUR] Impossible de se connecter: {e}")
        print("Assurez-vous que MSFS est lance!")
        return

    # Capture de l'avion
    aircraft = safe_get(aq, "TITLE")
    print(f"Avion detecte: {aircraft}\n")

    # Resultat
    calibration_data = {
        'aircraft': aircraft,
        'date': datetime.now().isoformat(),
        'phases': {}
    }

    print("Instructions:")
    print("- Placez-vous dans la phase de vol indiquee")
    print("- Appuyez sur ENTREE pour capturer")
    print("- Tapez 'skip' pour sauter une phase")
    print("- Tapez 'quit' pour terminer\n")
    print("-" * 60)

    for phase_id, phase_description in PHASES:
        print(f"\n>>> PHASE: {phase_id.upper()}")
        print(f"    {phase_description}")
        print()

        # Afficher l'etat actuel en temps reel
        current = capture_state(aq)
        print(f"    Etat actuel: IAS={current.get('AIRSPEED_INDICATED', 0):.0f}kts, "
              f"GS={current.get('GROUND_VELOCITY', 0):.0f}kts, "
              f"ALT={current.get('PLANE_ALTITUDE', 0):.0f}ft, "
              f"OnGround={current.get('SIM_ON_GROUND', 'N/A')}")

        user_input = input("    Appuyez sur ENTREE quand pret (ou 'skip'/'quit'): ").strip().lower()

        if user_input == 'quit':
            print("\nArret demande.")
            break
        elif user_input == 'skip':
            print(f"    [SKIP] Phase {phase_id} ignoree")
            continue

        # Capture
        print("    Capture en cours...")
        state = capture_state(aq)
        calibration_data['phases'][phase_id] = state

        print_state_summary(state)
        print(f"    [OK] Phase '{phase_id}' capturee!")

    # Sauvegarde
    output_file = Path(__file__).parent / f"phase_calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(calibration_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Calibration terminee!")
    print(f"Fichier sauvegarde: {output_file}")
    print(f"Phases capturees: {len(calibration_data['phases'])}")
    print("=" * 60)

    # Afficher un resume des differences cles entre phases
    if len(calibration_data['phases']) > 1:
        print("\n--- Analyse des differences entre phases ---")
        phases_list = list(calibration_data['phases'].keys())
        key_vars = ['SIM_ON_GROUND', 'AIRSPEED_INDICATED', 'GROUND_VELOCITY',
                    'VERTICAL_SPEED', 'GENERAL_ENG_COMBUSTION:1', 'BRAKE_PARKING_POSITION',
                    'GEAR_HANDLE_POSITION', 'PLANE_ALT_ABOVE_GROUND', 'ON_ANY_RUNWAY',
                    'FLAPS_HANDLE_PERCENT', 'GENERAL_ENG_THROTTLE_LEVER_POSITION:1']

        print(f"\n{'Phase':<20} | " + " | ".join(f"{v[:12]:<12}" for v in key_vars[:6]))
        print("-" * 100)
        for phase_id in phases_list:
            data = calibration_data['phases'][phase_id]
            values = []
            for v in key_vars[:6]:
                val = data.get(v, 'N/A')
                if isinstance(val, float):
                    values.append(f"{val:>12.1f}")
                else:
                    values.append(f"{str(val):>12}")
            print(f"{phase_id:<20} | " + " | ".join(values))

    # Fermeture
    try:
        sm.exit()
    except:
        pass

    input("\nAppuyez sur ENTREE pour fermer...")


if __name__ == "__main__":
    main()
