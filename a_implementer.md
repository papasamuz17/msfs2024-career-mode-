# MSFS 2024 Mission Generator - Améliorations à Implémenter

---

## VARIABLES EXISTANTES DANS LE CODE

### Constantes Globales

| Variable | Valeur | Description |
|----------|--------|-------------|
| `AIRPORTS_FILE` | "airports.json" | Fichier des aéroports locaux |
| `SAVE_FILE` | "savegame.json" | Fichier de sauvegarde du joueur |
| `CONFIG_FILE` | "config.json" | Configuration de l'application |
| `FLIGHTPLANS_DIR` | Path("flightplans") | Dossier des plans de vol générés |
| `UPDATE_INTERVAL` | 1000 | Intervalle de mise à jour UI (ms) |
| `NAVAIDS_FILE` | "navaids.json" | Base de données des VOR/intersections |

### Constantes Rémunération Pilote

| Variable | Valeur | Description |
|----------|--------|-------------|
| `PILOT_HOURLY_RATES` | dict | Tarifs horaires par catégorie d'avion (55-280 EUR/h) |
| `PER_DIEM_SHORT` | 35 | Indemnité vol < 2h |
| `PER_DIEM_MEDIUM` | 65 | Indemnité vol 2-5h |
| `PER_DIEM_LONG` | 120 | Indemnité vol > 5h |
| `BONUS_NIGHT_FLIGHT` | 0.25 | +25% vol de nuit |
| `BONUS_WEEKEND` | 0.15 | +15% week-end |
| `BONUS_BAD_WEATHER` | 0.20 | +20% mauvaise météo |
| `BONUS_SOFT_LANDING` | 50 | Bonus atterrissage < 100 fpm |
| `BONUS_GOOD_LANDING` | 25 | Bonus atterrissage 100-200 fpm |
| `BONUS_CONSTRAINTS_RESPECTED` | 30 | Bonus contraintes respectées |
| `PENALTY_HARD_LANDING_MEDIUM` | -50 | Pénalité atterrissage 300-500 fpm |
| `PENALTY_HARD_LANDING_SEVERE` | -150 | Pénalité atterrissage > 500 fpm |
| `PENALTY_CRASH` | -500 | Pénalité crash |
| `PENALTY_CONSTRAINT_VIOLATION` | -10 | Pénalité par violation |
| `PENALTY_OVERSPEED` | -25 | Pénalité survitesse |

### Variables d'Instance (classe MissionGeneratorApp)

#### Sauvegarde & Score
| Variable | Type | Description |
|----------|------|-------------|
| `self.config` | dict | Configuration chargée |
| `self.save_data` | dict | Données de sauvegarde |
| `self.score` | float | Compte en banque du pilote (EUR) |
| `self.missions_completed` | int | Nombre de missions terminées |

#### État Mission
| Variable | Type | Description |
|----------|------|-------------|
| `self.airports` | list | Liste des aéroports disponibles |
| `self.current_mission` | dict | Mission en cours (départ, arrivée, distance) |
| `self.current_constraint` | dict | Contrainte active (type, valeur, difficulté) |
| `self.current_flightplan` | str | Chemin du fichier PLN généré |
| `self.mission_active` | bool | Mission en cours ou non |
| `self.was_on_ground` | bool | État précédent (pour détecter atterrissage) |
| `self.penalty_cooldown` | int | Cooldown entre pénalités sonores |
| `self.update_count` | int | Compteur de cycles de mise à jour |

#### Progression Mission
| Variable | Type | Description |
|----------|------|-------------|
| `self.departure_lat` | float | Latitude aéroport de départ |
| `self.departure_lon` | float | Longitude aéroport de départ |
| `self.arrival_lat` | float | Latitude aéroport d'arrivée |
| `self.arrival_lon` | float | Longitude aéroport d'arrivée |
| `self.total_distance` | float | Distance totale de la mission (nm) |
| `self.mission_started` | bool | True après le décollage |
| `self.mission_progress` | float | Progression 0-100% |

#### Rémunération Pilote
| Variable | Type | Description |
|----------|------|-------------|
| `self.takeoff_time` | datetime | Heure de décollage |
| `self.landing_time` | datetime | Heure d'atterrissage |
| `self.flight_time_hours` | float | Temps de vol en heures |
| `self.constraint_violations` | int | Nombre de violations |
| `self.max_vs_landing` | float | VS à l'atterrissage (fpm) |
| `self.had_overspeed` | bool | Survitesse détectée |
| `self.is_night_flight` | bool | Vol de nuit (21h-6h) |
| `self.is_weekend` | bool | Vol le week-end |
| `self.is_bad_weather` | bool | Mauvaise météo |

#### SimConnect
| Variable | Type | Description |
|----------|------|-------------|
| `self.sim_connected` | bool | Connexion SimConnect active |
| `self.sim` | SimConnect | Instance SimConnect |
| `self.aircraft_requests` | AircraftRequests | Requêtes données avion |
| `self.aircraft_info` | dict | Infos avion (titre, type, moteur, catégorie...) |

### Variables SimConnect Lues

| Variable SimConnect | Utilisation actuelle |
|---------------------|---------------------|
| `PLANE_ALTITUDE` | Altitude MSL (ft) |
| `PLANE_ALT_ABOVE_GROUND` | Altitude AGL (ft) - détection vol/sol |
| `PLANE_BANK_DEGREES` | Inclinaison (rad → deg) |
| `VERTICAL_SPEED` | Vitesse verticale (fpm) |
| `SIM_ON_GROUND` | État au sol (non fiable) |
| `AIRSPEED_INDICATED` | Vitesse indiquée (kts) |
| `PLANE_LATITUDE` | Latitude actuelle |
| `PLANE_LONGITUDE` | Longitude actuelle |
| `GROUND_VELOCITY` | Vitesse sol (kts) |
| `ENG_COMBUSTION:1` | Moteur 1 en marche |
| `BRAKE_PARKING_POSITION` | Frein de parking |
| `TITLE` | Nom de l'avion |
| `ATC_TYPE` | Type ATC |
| `ATC_MODEL` | Modèle ATC |
| `ENGINE_TYPE` | Type moteur (0=Piston, 1=Jet, 5=Turboprop) |
| `NUMBER_OF_ENGINES` | Nombre de moteurs |
| `DESIGN_CRUISE_ALT` | Altitude de croisière design |
| `DESIGN_SPEED_VC` | Vitesse de croisière design |

---

## AMÉLIORATIONS À IMPLÉMENTER

---

### 1. PANNES ALÉATOIRES EN VOL

**Difficulté:** Moyenne | **Intérêt:** ⭐⭐⭐⭐⭐

**Description:**
Système de pannes aléatoires qui peuvent survenir pendant le vol pour augmenter le réalisme et le challenge.

**Variables SimConnect à utiliser (ÉCRITURE):**
```
GENERAL_ENG_COMBUSTION:index    - Couper un moteur
ELECTRICAL_MASTER_BATTERY       - Panne électrique
PARTIAL_PANEL_*                 - Masquer instruments
PITOT_HEAT                      - Givrage pitot
STRUCTURAL_ICE_PCT              - Givrage cellule
```

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.failures_enabled = True           # Activer/désactiver pannes
self.failure_probability = 0.05        # 5% de chance par tranche de 10min
self.active_failures = []              # Liste des pannes actives
self.failure_types = [
    {"name": "engine_1", "var": "GENERAL_ENG_COMBUSTION:1", "severity": "critical"},
    {"name": "engine_2", "var": "GENERAL_ENG_COMBUSTION:2", "severity": "critical"},
    {"name": "pitot", "var": "PITOT_HEAT", "severity": "moderate"},
    {"name": "electrical", "var": "ELECTRICAL_MASTER_BATTERY", "severity": "critical"},
    {"name": "vacuum", "var": "PARTIAL_PANEL_ATTITUDE", "severity": "moderate"},
]
```

**Nouvelles constantes:**
```python
FAILURE_CHECK_INTERVAL = 600000  # Vérifier toutes les 10 min
BONUS_FAILURE_HANDLED = 100      # Bonus si panne gérée correctement
PENALTY_FAILURE_CRASH = -500     # Pénalité si crash suite à panne
```

**Fonctions à créer:**
```python
def _check_random_failure(self):
    """Vérifie si une panne doit survenir (appelé toutes les 10 min)"""

def _trigger_failure(self, failure_type: str):
    """Déclenche une panne spécifique via SimConnect"""

def _clear_failure(self, failure_type: str):
    """Répare une panne (fin de mission ou option)"""

def _on_failure_handled(self):
    """Appelé quand le pilote gère correctement une panne"""
```

**Modification UI:**
- Ajouter checkbox "Pannes aléatoires" dans les options
- Afficher alerte rouge quand panne active
- Slider pour probabilité de panne

**Fichiers impactés:** `main.py`

---

### 2. GESTION CARBURANT RÉALISTE

**Difficulté:** Facile | **Intérêt:** ⭐⭐⭐⭐

**Description:**
Système économique de carburant avec prix variables, ravitaillement payant, et gestion de la consommation.

**Variables SimConnect à utiliser (LECTURE):**
```
FUEL_TOTAL_QUANTITY_WEIGHT      - Carburant total (lbs)
FUEL_TOTAL_CAPACITY             - Capacité totale
ENG_FUEL_FLOW_GPH:index         - Consommation par moteur
FUEL_TANK_*_QUANTITY            - Quantité par réservoir
```

**Variables SimConnect à utiliser (ÉCRITURE):**
```
FUEL_TANK_*_QUANTITY            - Modifier carburant (ravitaillement)
```

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.fuel_price_per_gallon = 6.50      # Prix JetA1/AvGas en EUR
self.fuel_at_departure = 0             # Carburant au départ (gallons)
self.fuel_at_arrival = 0               # Carburant à l'arrivée
self.fuel_consumed = 0                 # Consommation totale

# Constantes
FUEL_PRICES = {
    "avgas": 7.50,      # EUR/gallon - petits avions
    "jeta1": 5.80,      # EUR/gallon - jets/turboprops
}
```

**Fonctions à créer:**
```python
def _get_current_fuel(self) -> float:
    """Récupère le carburant actuel en gallons"""

def _calculate_fuel_cost(self) -> float:
    """Calcule le coût du carburant consommé"""

def _refuel_aircraft(self, gallons: float):
    """Ravitaille l'avion (payant)"""
```

**Logique économique:**
- Au départ: enregistrer niveau carburant
- À l'arrivée: calculer consommation
- Déduire coût carburant du salaire
- Option: ravitaillement à l'arrivée (payant)

**Modification UI:**
- Afficher consommation carburant en temps réel
- Afficher coût estimé du carburant
- Bouton "Ravitailler" avec prix

**Fichiers impactés:** `main.py`

---

### 3. CHALLENGES ATTERRISSAGE

**Difficulté:** Facile | **Intérêt:** ⭐⭐⭐⭐

**Description:**
Mode challenge avec conditions d'atterrissage spécifiques à respecter pour des bonus.

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.landing_challenge = None          # Challenge actif
self.landing_challenges = [
    {"name": "Butter", "max_vs": 50, "bonus": 100, "description": "VS < 50 fpm"},
    {"name": "Short Field", "max_distance": 500, "bonus": 75, "description": "Arrêt en < 500m"},
    {"name": "Crosswind", "min_crosswind": 15, "bonus": 80, "description": "Vent travers > 15kts"},
    {"name": "Night", "time_range": (20, 6), "bonus": 60, "description": "Atterrissage de nuit"},
    {"name": "Low Visibility", "max_visibility": 1000, "bonus": 90, "description": "Visibilité < 1km"},
    {"name": "No Flaps", "flaps": 0, "bonus": 70, "description": "Sans volets"},
]
```

**Variables SimConnect à utiliser:**
```
TRAILING_EDGE_FLAPS_LEFT_ANGLE  - Position volets
TOUCHDOWN_*                      - Données atterrissage
PLANE_TOUCHDOWN_*               - Vitesse/position au toucher
```

**Fonctions à créer:**
```python
def _assign_landing_challenge(self):
    """Assigne un challenge aléatoire compatible avec les conditions"""

def _check_landing_challenge(self) -> tuple[bool, float]:
    """Vérifie si le challenge est réussi, retourne (succès, bonus)"""

def _get_touchdown_data(self) -> dict:
    """Récupère les données précises de l'atterrissage"""
```

**Modification UI:**
- Afficher challenge actif dans section mission
- Badge de réussite/échec après atterrissage
- Statistiques des challenges réussis

**Fichiers impactés:** `main.py`

---

### 4. MODE CHECK-RIDE (EXAMEN PILOTE)

**Difficulté:** Moyenne | **Intérêt:** ⭐⭐⭐⭐

**Description:**
Simulation d'examen de pilotage avec checklist de manœuvres à effectuer.

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.checkride_active = False
self.checkride_type = None             # "PPL", "CPL", "IR", "TYPE_RATING"
self.checkride_tasks = []              # Liste des tâches à accomplir
self.checkride_score = 0               # Score de l'examen
self.checkride_tasks_completed = []    # Tâches validées

CHECKRIDE_DEFINITIONS = {
    "PPL": {
        "name": "Private Pilot License",
        "tasks": [
            {"name": "Steep turns 45°", "type": "bank", "value": 45, "tolerance": 5, "duration": 10},
            {"name": "Slow flight", "type": "speed", "value": 60, "tolerance": 5, "duration": 15},
            {"name": "Power-off stall recovery", "type": "stall_recovery", "time_limit": 5},
            {"name": "Emergency descent", "type": "vs", "value": -1500, "tolerance": 200},
            {"name": "Short field landing", "type": "landing_distance", "max": 400},
        ],
        "pass_score": 80,
        "reward": 500,
        "unlock": "CPL"
    },
    "IR": {
        "name": "Instrument Rating",
        "tasks": [
            {"name": "ILS approach", "type": "ils_precision", "tolerance": 0.5},
            {"name": "Holding pattern", "type": "holding", "duration": 120},
            {"name": "VOR tracking", "type": "vor_deviation", "max": 5},
        ],
        "pass_score": 85,
        "reward": 1000,
    }
}
```

**Fonctions à créer:**
```python
def _start_checkride(self, checkride_type: str):
    """Démarre un examen de pilotage"""

def _monitor_checkride_task(self, task: dict) -> bool:
    """Surveille l'exécution d'une tâche d'examen"""

def _complete_checkride(self):
    """Termine l'examen et calcule le score"""

def _award_license(self, license_type: str):
    """Attribue une licence au pilote"""
```

**Modification UI:**
- Onglet/bouton "Check-ride"
- Liste des tâches avec statut (en attente, en cours, réussi, échoué)
- Barre de progression de l'examen
- Certificat de réussite

**Fichiers impactés:** `main.py`, `savegame.json`

---

### 5. SYSTÈME DE RÉPUTATION COMPAGNIES

**Difficulté:** Facile | **Intérêt:** ⭐⭐⭐

**Description:**
Système de réputation auprès de différentes compagnies aériennes fictives.

**Nouvelles variables à ajouter:**
```python
# Dans __init__ ou save_data
self.company_reputation = {
    "Air Cargo Express": {"reputation": 50, "missions": 0, "unlocked": True},
    "EuroWings Charter": {"reputation": 0, "missions": 0, "unlocked": False},
    "TransOcean Airways": {"reputation": 0, "missions": 0, "unlocked": False},
    "Executive Jets": {"reputation": 0, "missions": 0, "unlocked": False},
    "Global Freight": {"reputation": 0, "missions": 0, "unlocked": False},
}

COMPANIES = {
    "Air Cargo Express": {
        "type": "cargo",
        "aircraft": ["single_turboprop", "turboprop"],
        "base_pay_multiplier": 1.0,
        "unlock_requirement": None,
    },
    "EuroWings Charter": {
        "type": "charter",
        "aircraft": ["light_jet", "jet"],
        "base_pay_multiplier": 1.2,
        "unlock_requirement": {"total_hours": 100},
    },
    "TransOcean Airways": {
        "type": "airline",
        "aircraft": ["jet", "heavy_jet"],
        "base_pay_multiplier": 1.5,
        "unlock_requirement": {"total_hours": 500, "reputation_min": 70},
    },
}
```

**Fonctions à créer:**
```python
def _update_reputation(self, company: str, delta: int):
    """Met à jour la réputation auprès d'une compagnie"""

def _check_company_unlock(self, company: str) -> bool:
    """Vérifie si une compagnie est débloquée"""

def _get_available_companies(self) -> list:
    """Retourne les compagnies disponibles pour le pilote"""

def _apply_company_bonus(self, base_pay: float, company: str) -> float:
    """Applique le multiplicateur de la compagnie"""
```

**Impact réputation:**
- Bonne performance = +5 réputation
- Mauvaise performance = -10 réputation
- Réputation < 20 = licenciement (compagnie bloquée temporairement)
- Réputation > 80 = bonus missions spéciales

**Modification UI:**
- Dropdown sélection compagnie
- Affichage réputation par compagnie
- Badge compagnie actuelle

**Fichiers impactés:** `main.py`, `savegame.json`

---

### 6. USURE AVION / MAINTENANCE

**Difficulté:** Moyenne | **Intérêt:** ⭐⭐⭐⭐

**Description:**
Système de suivi de l'usure des avions avec maintenance obligatoire.

**Nouvelles variables à ajouter:**
```python
# Dans save_data (persistant par avion)
self.aircraft_wear = {}  # {"aircraft_title": {"hours": 0, "wear": 0, "last_maintenance": date}}

MAINTENANCE_CONFIG = {
    "wear_per_hour": 0.5,              # % usure par heure de vol
    "wear_hard_landing": 5.0,          # % usure atterrissage dur
    "wear_overspeed": 2.0,             # % usure survitesse
    "maintenance_threshold": 80,        # % usure avant maintenance obligatoire
    "maintenance_cost_per_percent": 50, # EUR par % de réparation
    "grounded_threshold": 95,           # % usure = avion cloué au sol
}
```

**Variables SimConnect à utiliser:**
```
G_FORCE                         - G subis (usure si > 2G)
OVERSPEED_WARNING               - Survitesse
STALL_WARNING                   - Décrochage
```

**Fonctions à créer:**
```python
def _update_aircraft_wear(self, flight_hours: float, events: dict):
    """Met à jour l'usure de l'avion après un vol"""

def _get_aircraft_wear(self, aircraft_title: str) -> float:
    """Récupère le niveau d'usure d'un avion"""

def _perform_maintenance(self, aircraft_title: str, repair_percent: float):
    """Effectue une maintenance (payante)"""

def _is_aircraft_grounded(self, aircraft_title: str) -> bool:
    """Vérifie si l'avion est cloué au sol"""
```

**Modification UI:**
- Jauge d'usure de l'avion actuel
- Alerte si usure > 80%
- Bouton "Maintenance" avec coût estimé
- Historique maintenance

**Fichiers impactés:** `main.py`, `savegame.json`

---

### 7. PASSAGERS MÉCONTENTS (CONFORT)

**Difficulté:** Moyenne | **Intérêt:** ⭐⭐⭐

**Description:**
Simulation du confort passagers avec pénalités si vol inconfortable.

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.passenger_comfort = 100           # 0-100%
self.has_passengers = False            # Vol passagers ou cargo
self.comfort_events = []               # Historique événements

COMFORT_PENALTIES = {
    "high_bank": {"threshold": 30, "penalty_per_sec": 0.5},      # Inclinaison > 30°
    "high_vs": {"threshold": 1500, "penalty_per_sec": 0.3},      # VS > 1500 fpm
    "turbulence": {"threshold": 0.3, "penalty_per_sec": 0.2},    # G-force variation
    "hard_landing": {"threshold": 300, "penalty": 20},           # VS atterrissage
    "go_around": {"penalty": 15},                                 # Remise de gaz
}

COMFORT_BONUSES = {
    "smooth_flight": 50,    # Confort > 90%
    "on_time": 30,          # Arrivée à l'heure
}
```

**Variables SimConnect à utiliser:**
```
G_FORCE                         - Facteur de charge
ACCELERATION_BODY_*             - Accélérations
PLANE_BANK_DEGREES              - Inclinaison (déjà lu)
VERTICAL_SPEED                  - VS (déjà lu)
```

**Fonctions à créer:**
```python
def _update_passenger_comfort(self):
    """Met à jour le confort passagers en temps réel"""

def _calculate_comfort_penalty(self) -> float:
    """Calcule la pénalité finale basée sur le confort"""

def _log_comfort_event(self, event_type: str, severity: float):
    """Enregistre un événement affectant le confort"""
```

**Modification UI:**
- Jauge "Confort passagers" (seulement si vol passagers)
- Icône passager content/mécontent
- Détail des événements inconfortables en fin de vol

**Fichiers impactés:** `main.py`

---

### 8. LOG BOOK AUTOMATIQUE

**Difficulté:** Facile | **Intérêt:** ⭐⭐⭐⭐

**Description:**
Carnet de vol automatique enregistrant tous les vols effectués.

**Nouvelles variables à ajouter:**
```python
# Dans save_data (persistant)
self.logbook = []  # Liste de tous les vols

# Structure d'une entrée
LOGBOOK_ENTRY = {
    "date": "2026-01-25",
    "departure": {"icao": "LFPG", "name": "Paris CDG", "time": "14:30"},
    "arrival": {"icao": "EGLL", "name": "London Heathrow", "time": "15:45"},
    "aircraft": {"title": "A320neo", "category": "jet"},
    "flight_time": 1.25,               # Heures
    "distance": 215,                   # nm
    "conditions": {
        "day_night": "day",
        "weather": "IMC",
        "crosswind": 12
    },
    "performance": {
        "landing_vs": -150,
        "violations": 0,
        "comfort": 95
    },
    "earnings": {
        "base": 250.00,
        "bonuses": 75.00,
        "penalties": 0,
        "fuel_cost": -45.00,
        "total": 280.00
    },
    "remarks": "Vol sans incident"
}
```

**Fonctions à créer:**
```python
def _create_logbook_entry(self) -> dict:
    """Crée une entrée de carnet de vol après une mission"""

def _add_to_logbook(self, entry: dict):
    """Ajoute une entrée au carnet de vol"""

def _get_logbook_stats(self) -> dict:
    """Calcule les statistiques du carnet (heures totales, etc.)"""

def _export_logbook_csv(self, filepath: str):
    """Exporte le carnet au format CSV"""
```

**Statistiques calculées:**
- Heures totales de vol
- Heures par catégorie d'avion
- Heures de nuit / IMC
- Nombre d'atterrissages
- Moyenne VS atterrissage
- Revenus totaux

**Modification UI:**
- Nouvel onglet "Logbook"
- Tableau des vols récents
- Graphiques statistiques
- Bouton export CSV

**Fichiers impactés:** `main.py`, `savegame.json`

---

### 9. REJEU DU VOL (ENREGISTREMENT TRAJECTOIRE)

**Difficulté:** Difficile | **Intérêt:** ⭐⭐⭐

**Description:**
Enregistrement de la trajectoire pour analyse post-vol.

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.flight_recording = False
self.flight_track = []                 # Points de trajectoire
self.recording_interval = 5000         # Enregistrement toutes les 5s

# Structure d'un point
TRACK_POINT = {
    "timestamp": 1234567890,
    "lat": 48.8566,
    "lon": 2.3522,
    "alt": 35000,
    "heading": 270,
    "speed": 450,
    "vs": -500,
    "bank": 5,
    "flaps": 0,
    "gear": False,
    "throttle": 85
}
```

**Variables SimConnect à utiliser:**
```
PLANE_LATITUDE                  - (déjà lu)
PLANE_LONGITUDE                 - (déjà lu)
PLANE_ALTITUDE                  - (déjà lu)
PLANE_HEADING_DEGREES_TRUE      - Cap vrai
AIRSPEED_TRUE                   - TAS
TRAILING_EDGE_FLAPS_LEFT_ANGLE  - Volets
GEAR_HANDLE_POSITION            - Train
GENERAL_ENG_THROTTLE_LEVER_POSITION:1 - Manette gaz
```

**Fonctions à créer:**
```python
def _start_recording(self):
    """Démarre l'enregistrement de la trajectoire"""

def _record_track_point(self):
    """Enregistre un point de trajectoire"""

def _stop_recording(self) -> list:
    """Arrête l'enregistrement et retourne la trajectoire"""

def _export_track_kml(self, filepath: str):
    """Exporte la trajectoire au format KML (Google Earth)"""

def _export_track_gpx(self, filepath: str):
    """Exporte la trajectoire au format GPX"""
```

**Modification UI:**
- Bouton "Enregistrer vol"
- Indicateur enregistrement en cours
- Bouton export KML/GPX après vol
- Mini-carte de la trajectoire (optionnel, complexe)

**Fichiers impactés:** `main.py`

---

### 10. MODE CARRIÈRE COMPLET

**Difficulté:** Moyenne | **Intérêt:** ⭐⭐⭐⭐⭐

**Description:**
Système de progression complète du pilote avec licences, heures, et déblocages.

**Nouvelles variables à ajouter:**
```python
# Dans save_data (persistant)
self.pilot_profile = {
    "name": "Pilote",
    "total_hours": 0,
    "hours_by_category": {
        "light_piston": 0,
        "twin_piston": 0,
        "single_turboprop": 0,
        "turboprop": 0,
        "light_jet": 0,
        "jet": 0,
        "heavy_jet": 0,
        "helicopter": 0,
    },
    "licenses": [],                    # ["PPL", "IR", "CPL", "ATPL"]
    "type_ratings": [],                # ["C172", "A320", "B737"]
    "current_company": None,
    "career_start_date": "2026-01-25",
}

self.career_unlocks = {
    "aircraft_categories": ["light_piston"],  # Catégories débloquées
    "max_distance": 300,                       # Distance max autorisée (nm)
    "night_flights": False,                    # Vols de nuit autorisés
    "ifr_flights": False,                      # Vols IFR autorisés
    "international": False,                    # Vols internationaux
}

CAREER_PROGRESSION = {
    "PPL": {
        "required_hours": 40,
        "required_hours_category": {"light_piston": 40},
        "exam_cost": 500,
        "unlocks": {
            "aircraft_categories": ["light_piston", "twin_piston"],
            "max_distance": 500,
            "night_flights": True,
        }
    },
    "IR": {
        "required_hours": 50,
        "required_licenses": ["PPL"],
        "exam_cost": 1500,
        "unlocks": {
            "ifr_flights": True,
        }
    },
    "CPL": {
        "required_hours": 200,
        "required_licenses": ["PPL"],
        "exam_cost": 3000,
        "unlocks": {
            "aircraft_categories": ["single_turboprop", "turboprop"],
            "max_distance": 1500,
        }
    },
    "ATPL": {
        "required_hours": 1500,
        "required_licenses": ["CPL", "IR"],
        "exam_cost": 5000,
        "unlocks": {
            "aircraft_categories": ["light_jet", "jet", "heavy_jet"],
            "max_distance": 99999,
            "international": True,
        }
    },
}

TYPE_RATINGS = {
    "A320": {"required_hours": 500, "required_licenses": ["ATPL"], "cost": 15000},
    "B737": {"required_hours": 500, "required_licenses": ["ATPL"], "cost": 15000},
    "B747": {"required_hours": 2000, "required_licenses": ["ATPL"], "cost": 25000},
}
```

**Fonctions à créer:**
```python
def _update_pilot_hours(self, hours: float, category: str):
    """Met à jour les heures de vol du pilote"""

def _check_license_requirements(self, license: str) -> tuple[bool, str]:
    """Vérifie si le pilote peut passer une licence"""

def _purchase_license(self, license: str) -> bool:
    """Achète/passe une licence (si conditions remplies)"""

def _apply_career_restrictions(self, mission: dict) -> bool:
    """Vérifie si la mission est autorisée selon la progression"""

def _get_available_aircraft(self) -> list:
    """Retourne les catégories d'avion disponibles"""

def _get_career_progress(self) -> dict:
    """Retourne la progression vers la prochaine licence"""
```

**Modification UI:**
- Nouvel onglet "Carrière"
- Profil pilote avec heures et licences
- Arbre de progression visuel
- Boutique formations/licences
- Restrictions affichées sur génération mission

**Fichiers impactés:** `main.py`, `savegame.json`

---

### 11. MÉTÉO SIMCONNECT (LECTURE)

**Difficulté:** Facile | **Intérêt:** ⭐⭐⭐⭐

**Description:**
Lecture de la météo réelle du simulateur au lieu des METAR externes.

**Variables SimConnect à utiliser:**
```
AMBIENT_WIND_VELOCITY           - Vitesse vent (kts)
AMBIENT_WIND_DIRECTION          - Direction vent (°)
AMBIENT_TEMPERATURE             - Température (°C)
AMBIENT_PRESSURE                - Pression
AMBIENT_VISIBILITY              - Visibilité (m)
BAROMETER_PRESSURE              - QNH
AMBIENT_PRECIP_STATE            - Précipitations (0/1/2)
AMBIENT_IN_CLOUD                - Dans les nuages
SEA_LEVEL_PRESSURE              - QNH niveau mer
```

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.sim_weather = {
    "wind_speed": 0,
    "wind_direction": 0,
    "temperature": 15,
    "visibility": 9999,
    "pressure": 1013,
    "in_cloud": False,
    "precipitation": 0,
}
```

**Fonctions à créer:**
```python
def _update_sim_weather(self):
    """Met à jour les données météo depuis SimConnect"""

def _format_sim_weather(self) -> str:
    """Formate la météo pour affichage"""

def _check_imc_conditions(self) -> bool:
    """Vérifie si conditions IMC"""

def _auto_apply_weather_bonus(self):
    """Applique automatiquement le bonus mauvaise météo"""
```

**Modification UI:**
- Section "Météo actuelle" avec données en temps réel
- Icône conditions (soleil, nuages, pluie, neige)
- Indicateur IMC/VMC

**Fichiers impactés:** `main.py`

---

### 12. CALCUL DISTANCE RÉELLE (VIA WAYPOINTS)

**Difficulté:** Facile | **Intérêt:** ⭐⭐⭐

**Description:**
Calculer la distance réelle du vol en sommant les segments entre waypoints.

**Modification de code existant:**
```python
def calculate_route_distance(waypoints: list, departure: dict, arrival: dict) -> float:
    """Calcule la distance totale en suivant les waypoints"""
    total = 0

    # Départ -> premier waypoint
    if waypoints:
        total += calculate_distance_nm(
            departure['lat'], departure['lon'],
            waypoints[0]['lat'], waypoints[0]['lon']
        )

        # Entre waypoints
        for i in range(len(waypoints) - 1):
            total += calculate_distance_nm(
                waypoints[i]['lat'], waypoints[i]['lon'],
                waypoints[i+1]['lat'], waypoints[i+1]['lon']
            )

        # Dernier waypoint -> arrivée
        total += calculate_distance_nm(
            waypoints[-1]['lat'], waypoints[-1]['lon'],
            arrival['lat'], arrival['lon']
        )
    else:
        # Direct
        total = calculate_distance_nm(
            departure['lat'], departure['lon'],
            arrival['lat'], arrival['lon']
        )

    return total
```

**Nouvelles variables:**
```python
self.direct_distance = 0       # Distance directe
self.route_distance = 0        # Distance via waypoints
self.route_overhead = 0        # Surcoût en % (route vs direct)
```

**Modification UI:**
- Afficher "Distance directe: X nm / Route: Y nm (+Z%)"

**Fichiers impactés:** `main.py`

---

### 13. COPILOTE IA INTELLIGENT

**Difficulté:** Difficile | **Intérêt:** ⭐⭐⭐⭐⭐

**Description:**
Assistant vocal intelligent capable de faire des annonces radio, détecter les erreurs, lire les checklists, et assister le pilote comme un vrai copilote.

**Architecture globale:**
```
[Microphone] -> [Whisper STT (Groq)] -> [LLM Copilote (Groq)] -> [Edge-TTS] -> [Audio]
                                               ^
                                               |
                                        [SimConnect Data]
                                        (position, vitesse, config, phase, météo...)
```

**Dépendances:**
- `pyaudio` - Capture microphone
- `groq` - Whisper STT + LLM (LLaMA)
- `edge-tts` - Synthèse vocale
- `SimConnect` - Données vol

---

#### 13.1 DÉTECTION DE PHASE DE VOL

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.flight_phase = "parked"           # Phase actuelle
self.previous_phase = None             # Phase précédente
self.phase_start_time = None           # Heure début phase

FLIGHT_PHASES = {
    "parked": {"ground": True, "speed": 0, "engine": False},
    "engine_start": {"ground": True, "speed": 0, "engine": True},
    "taxi": {"ground": True, "speed": (1, 30), "engine": True},
    "takeoff_roll": {"ground": True, "speed": (30, 999), "engine": True},
    "initial_climb": {"ground": False, "agl": (0, 1000), "vs": (100, 9999)},
    "climb": {"ground": False, "agl": (1000, 99999), "vs": (300, 9999)},
    "cruise": {"ground": False, "vs": (-300, 300)},
    "descent": {"ground": False, "vs": (-9999, -300)},
    "approach": {"ground": False, "agl": (0, 3000), "vs": (-9999, -100)},
    "final": {"ground": False, "agl": (0, 500)},
    "landing_roll": {"ground": True, "speed": (30, 999)},
    "taxi_in": {"ground": True, "speed": (1, 30)},
}
```

**Fonctions à créer:**
```python
def _detect_flight_phase(self) -> str:
    """Détecte la phase de vol actuelle basée sur SimConnect"""

def _on_phase_change(self, old_phase: str, new_phase: str):
    """Appelé lors d'un changement de phase"""

def _get_phase_duration(self) -> float:
    """Retourne la durée de la phase actuelle en secondes"""
```

---

#### 13.2 CALLOUTS AUTOMATIQUES

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.callouts_enabled = True
self.callouts_made = set()             # Callouts déjà faits ce vol
self.v_speeds = {                       # Vitesses V (configurables par avion)
    "v1": 120,
    "vr": 130,
    "v2": 140,
}

CALLOUTS = {
    "takeoff": [
        {"trigger": "speed >= v1", "text": "V1", "once": True},
        {"trigger": "speed >= vr", "text": "Rotate", "once": True},
        {"trigger": "airborne", "text": "Positive climb", "once": True},
        {"trigger": "gear_up", "text": "Gear up", "once": True},
    ],
    "climb": [
        {"trigger": "alt % 1000 == 0", "text": "Passing {alt} feet"},
        {"trigger": "alt_target - alt <= 1000", "text": "1000 to level off", "once": True},
        {"trigger": "level_off", "text": "Level off, flight level {fl}", "once": True},
    ],
    "descent": [
        {"trigger": "tod", "text": "Top of descent", "once": True},
        {"trigger": "alt % 1000 == 0", "text": "Passing {alt} feet"},
    ],
    "approach": [
        {"trigger": "agl <= 2500", "text": "2500 feet, approach checklist", "once": True},
        {"trigger": "agl <= 1000", "text": "1000 feet", "once": True},
        {"trigger": "agl <= 500", "text": "500 feet, stabilized", "once": True},
        {"trigger": "agl <= 100", "text": "100 feet", "once": True},
        {"trigger": "agl <= 50", "text": "50", "once": True},
        {"trigger": "agl <= 30", "text": "30", "once": True},
        {"trigger": "agl <= 20", "text": "20", "once": True},
        {"trigger": "agl <= 10", "text": "10", "once": True},
        {"trigger": "touchdown", "text": "Touchdown", "once": True},
    ],
    "landing": [
        {"trigger": "speed < 60", "text": "60 knots", "once": True},
        {"trigger": "stopped", "text": "Runway vacated", "once": True},
    ],
}
```

**Fonctions à créer:**
```python
def _check_callouts(self):
    """Vérifie et déclenche les callouts appropriés"""

def _make_callout(self, text: str, priority: int = 1):
    """Fait une annonce vocale"""

def _format_callout(self, template: str) -> str:
    """Remplace les variables dans un callout ({alt}, {speed}, etc.)"""

async def _speak_callout(self, text: str):
    """Synthétise et joue un callout"""
```

---

#### 13.3 DÉTECTION D'ERREURS PILOTE

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.error_detection_enabled = True
self.errors_detected = []              # Historique erreurs
self.error_cooldown = {}               # Cooldown par type d'erreur

PILOT_ERRORS = {
    "overspeed": {
        "condition": "speed > vne or (flaps > 0 and speed > vfe)",
        "message": "Attention, survitesse!",
        "severity": "warning",
        "cooldown": 30
    },
    "underspeed": {
        "condition": "speed < vs0 * 1.1 and not landing",
        "message": "Attention, vitesse basse!",
        "severity": "warning",
        "cooldown": 15
    },
    "bank_excessive": {
        "condition": "abs(bank) > 35 and phase not in ['takeoff', 'landing']",
        "message": "Inclinaison excessive",
        "severity": "caution",
        "cooldown": 20
    },
    "descent_rate_high": {
        "condition": "vs < -2000 and agl < 5000",
        "message": "Taux de descente élevé",
        "severity": "warning",
        "cooldown": 15
    },
    "gear_not_down": {
        "condition": "agl < 1000 and speed < 200 and not gear_down",
        "message": "Train d'atterrissage!",
        "severity": "critical",
        "cooldown": 10
    },
    "flaps_not_set": {
        "condition": "phase == 'final' and flaps < min_landing_flaps",
        "message": "Volets non configurés",
        "severity": "warning",
        "cooldown": 15
    },
    "unstable_approach": {
        "condition": "agl < 500 and (abs(vs) > 1000 or speed_deviation > 10)",
        "message": "Approche non stabilisée, envisagez une remise de gaz",
        "severity": "warning",
        "cooldown": 30
    },
    "altitude_deviation": {
        "condition": "abs(alt - alt_assigned) > 300",
        "message": "Déviation d'altitude",
        "severity": "caution",
        "cooldown": 60
    },
    "no_lights": {
        "condition": "phase in ['takeoff', 'landing'] and not landing_lights",
        "message": "Phares d'atterrissage",
        "severity": "info",
        "cooldown": 60
    },
    "taxi_fast": {
        "condition": "phase == 'taxi' and ground_speed > 25",
        "message": "Vitesse de roulage excessive",
        "severity": "caution",
        "cooldown": 30
    },
}
```

**Variables SimConnect supplémentaires:**
```
FLAPS_HANDLE_PERCENT           - Position volets
GEAR_HANDLE_POSITION           - Position train
LIGHT_LANDING                  - Phares atterrissage
LIGHT_BEACON                   - Beacon
LIGHT_NAV                      - Feux nav
LIGHT_STROBE                   - Strobes
STALL_WARNING                  - Alarme décrochage
OVERSPEED_WARNING              - Alarme survitesse
DESIGN_SPEED_VS0               - Vitesse décrochage
DESIGN_SPEED_VC                - Vitesse croisière
```

**Fonctions à créer:**
```python
def _check_pilot_errors(self):
    """Vérifie les erreurs de pilotage"""

def _alert_error(self, error_type: str, message: str, severity: str):
    """Alerte le pilote d'une erreur"""

def _is_error_on_cooldown(self, error_type: str) -> bool:
    """Vérifie si une erreur est en cooldown"""

def _log_error(self, error_type: str, details: dict):
    """Enregistre une erreur pour le debriefing"""
```

---

#### 13.4 ANNONCES RADIO (SIMULATION ATC)

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.radio_enabled = True
self.current_frequency = "121.500"     # Fréquence actuelle
self.callsign = "F-GXXX"               # Indicatif avion
self.atc_instructions = []             # Instructions ATC en attente

ATC_MESSAGES = {
    "clearance": [
        "{callsign}, autorisé {destination} via {route}, niveau initial {alt}, transpondeur {squawk}",
    ],
    "taxi": [
        "{callsign}, roulez piste {runway} via {taxiway}",
        "{callsign}, maintenez position, trafic en courte finale",
    ],
    "takeoff": [
        "{callsign}, piste {runway}, autorisé décollage, vent {wind}",
        "{callsign}, alignez-vous piste {runway}, prêt immédiat",
    ],
    "departure": [
        "{callsign}, contactez départ {freq}",
        "{callsign}, montez niveau {alt}, cap {heading}",
    ],
    "cruise": [
        "{callsign}, radar contact, poursuivez route",
        "{callsign}, attendez-vous niveau {alt} dans {time} minutes",
    ],
    "approach": [
        "{callsign}, descendez {alt}, rappelez établi ILS piste {runway}",
        "{callsign}, virage main gauche cap {heading}, vecteur ILS",
        "{callsign}, autorisé approche ILS piste {runway}",
    ],
    "landing": [
        "{callsign}, piste {runway}, autorisé atterrissage, vent {wind}",
        "{callsign}, après atterrissage, dégagez par {taxiway}",
    ],
}

READBACK_TEMPLATES = {
    "altitude": "On monte {alt}, {callsign}",
    "heading": "Cap {heading}, {callsign}",
    "cleared": "Autorisé, {callsign}",
    "contact": "On contacte {freq}, {callsign}",
}
```

**Fonctions à créer:**
```python
def _generate_atc_message(self, phase: str) -> str:
    """Génère un message ATC réaliste pour la phase"""

def _generate_readback(self, instruction: str) -> str:
    """Génère un collationnement automatique"""

async def _play_atc_exchange(self, atc_msg: str, readback: str):
    """Joue un échange ATC (message + readback)"""

def _get_airport_frequencies(self, icao: str) -> dict:
    """Récupère les fréquences d'un aéroport"""
```

---

#### 13.5 CHECKLISTS INTERACTIVES

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.checklist_active = None           # Checklist en cours
self.checklist_index = 0               # Item actuel

CHECKLISTS = {
    "before_start": {
        "name": "Avant mise en route",
        "items": [
            {"check": "Parking brake", "response": "Set", "verify": "BRAKE_PARKING_POSITION == 1"},
            {"check": "Beacon", "response": "On", "verify": "LIGHT_BEACON == 1"},
            {"check": "Fuel", "response": "Checked", "verify": "FUEL_TOTAL_QUANTITY > 0"},
            {"check": "Doors", "response": "Closed"},
        ]
    },
    "before_takeoff": {
        "name": "Avant décollage",
        "items": [
            {"check": "Flight controls", "response": "Checked"},
            {"check": "Flaps", "response": "Set for takeoff", "verify": "FLAPS > 0"},
            {"check": "Trim", "response": "Set"},
            {"check": "Transponder", "response": "On"},
            {"check": "Landing lights", "response": "On", "verify": "LIGHT_LANDING == 1"},
            {"check": "Strobes", "response": "On", "verify": "LIGHT_STROBE == 1"},
        ]
    },
    "approach": {
        "name": "Approche",
        "items": [
            {"check": "Altimeter", "response": "Set"},
            {"check": "Landing gear", "response": "Down", "verify": "GEAR_HANDLE_POSITION == 1"},
            {"check": "Flaps", "response": "Set"},
            {"check": "Speed", "response": "Checked"},
        ]
    },
    "after_landing": {
        "name": "Après atterrissage",
        "items": [
            {"check": "Flaps", "response": "Retracted"},
            {"check": "Landing lights", "response": "Off"},
            {"check": "Strobes", "response": "Off"},
            {"check": "Transponder", "response": "Standby"},
        ]
    },
}
```

**Fonctions à créer:**
```python
def _start_checklist(self, checklist_name: str):
    """Démarre une checklist interactive"""

def _next_checklist_item(self):
    """Passe à l'item suivant de la checklist"""

async def _read_checklist_item(self, item: dict):
    """Lit un item de checklist et vérifie"""

def _verify_checklist_item(self, item: dict) -> bool:
    """Vérifie si l'item est correctement configuré"""

def _complete_checklist(self):
    """Termine la checklist en cours"""
```

---

#### 13.6 CONVERSATION NATURELLE (LLM)

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.copilot_llm_enabled = True
self.conversation_history = []         # Historique conversation
self.copilot_personality = "professional"  # Style du copilote

COPILOT_SYSTEM_PROMPT = '''
Tu es un copilote professionnel expérimenté. Tu assistes le commandant de bord pendant le vol.
Tu as accès aux données suivantes en temps réel:
- Position: {lat}, {lon}
- Altitude: {alt} ft
- Vitesse: {speed} kts
- Cap: {heading}°
- Phase de vol: {phase}
- Météo: vent {wind_speed}kts de {wind_dir}°

Réponds de manière concise et professionnelle. Utilise la phraséologie aéronautique standard.
Si on te demande la position, donne la ville survolée et les coordonnées.
Si on te demande des calculs (carburant, temps, etc.), fais-les précisément.
'''

VOICE_COMMANDS = {
    "position": ["position", "ou on est", "ou sommes nous", "localisation", "coordonnees"],
    "altitude": ["altitude", "a combien on est", "niveau"],
    "speed": ["vitesse", "combien on fait"],
    "weather": ["meteo", "vent", "conditions"],
    "fuel": ["carburant", "essence", "fuel", "autonomie"],
    "time": ["heure", "temps", "eta", "arrivee"],
    "checklist": ["checklist", "check list", "liste"],
    "briefing": ["briefing", "approche", "arrivee"],
}
```

**Fonctions à créer:**
```python
async def _process_voice_command(self, text: str) -> str:
    """Traite une commande vocale et génère une réponse"""

def _build_llm_context(self) -> str:
    """Construit le contexte pour le LLM avec les données de vol"""

async def _query_llm(self, user_input: str, context: str) -> str:
    """Interroge le LLM pour une réponse intelligente"""

def _detect_intent(self, text: str) -> str:
    """Détecte l'intention de la commande vocale"""

async def _handle_specific_command(self, intent: str) -> str:
    """Traite une commande spécifique (position, météo, etc.)"""
```

---

#### 13.7 INTERFACE VOCALE CONTINUE

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.voice_active = False              # Écoute active
self.voice_thread = None               # Thread d'écoute
self.tts_queue = []                    # File d'attente TTS
self.wake_word = "copilote"            # Mot de réveil optionnel

VOICE_CONFIG = {
    "silence_threshold": 100,          # Seuil de silence
    "silence_duration": 2.0,           # Durée silence = fin phrase
    "sample_rate": 16000,              # Taux échantillonnage
    "tts_voice": "fr-FR-DeniseNeural", # Voix TTS
    "tts_rate": "-5%",                 # Vitesse TTS
}
```

**Fonctions à créer:**
```python
def _start_voice_listener(self):
    """Démarre l'écoute vocale en arrière-plan"""

def _stop_voice_listener(self):
    """Arrête l'écoute vocale"""

async def _voice_loop(self):
    """Boucle principale d'écoute vocale"""

def _record_audio(self) -> str:
    """Enregistre l'audio jusqu'au silence"""

async def _transcribe_audio(self, audio_file: str) -> str:
    """Transcrit l'audio avec Whisper"""

async def _speak(self, text: str, priority: int = 1):
    """Ajoute un message à la file TTS"""

async def _tts_worker(self):
    """Worker qui traite la file TTS"""
```

---

#### 13.8 DEBRIEFING FIN DE VOL

**Nouvelles variables à ajouter:**
```python
# Dans __init__
self.flight_events = []                # Tous les événements du vol
self.debriefing_enabled = True

DEBRIEF_CATEGORIES = {
    "performance": ["landing_vs", "fuel_efficiency", "time_accuracy"],
    "errors": ["overspeeds", "altitude_deviations", "unstable_approaches"],
    "procedures": ["checklists_completed", "callouts_acknowledged"],
    "atc": ["readbacks_correct", "instructions_followed"],
}
```

**Fonctions à créer:**
```python
def _log_flight_event(self, event_type: str, data: dict):
    """Enregistre un événement de vol"""

async def _generate_debriefing(self) -> str:
    """Génère un debriefing vocal de fin de vol"""

def _calculate_flight_score(self) -> dict:
    """Calcule le score détaillé du vol"""

async def _speak_debriefing(self):
    """Lit le debriefing à voix haute"""
```

---

**Fichiers à créer:**
| Fichier | Description |
|---------|-------------|
| `copilot/__init__.py` | Module copilote |
| `copilot/voice.py` | Gestion STT/TTS |
| `copilot/phases.py` | Détection phases de vol |
| `copilot/callouts.py` | Système de callouts |
| `copilot/errors.py` | Détection erreurs |
| `copilot/atc.py` | Simulation radio ATC |
| `copilot/checklists.py` | Checklists interactives |
| `copilot/llm.py` | Interface LLM conversationnel |
| `copilot/debrief.py` | Debriefing fin de vol |

**Fichiers impactés:** `main.py`, `config.json`

---

### 14. OPTIMISATIONS PERFORMANCE

**Difficulté:** Moyenne | **Intérêt:** ⭐⭐⭐⭐⭐

**Description:**
Ensemble d'optimisations pour réduire la consommation CPU, RAM et réseau du programme, permettant un fonctionnement fluide même sur des configurations modestes.

---

#### 14.1 OPTIMISATION SIMCONNECT

**Problème actuel:**
- Polling constant à 1000ms quelle que soit la phase
- Lecture de toutes les variables à chaque cycle
- Pas de mise en cache

**Solution - Polling adaptatif:**
```python
# Nouvelles constantes
POLLING_RATES = {
    "parked": 5000,           # Au parking: 1x/5sec
    "engine_start": 2000,     # Démarrage: 1x/2sec
    "taxi": 2000,             # Roulage: 1x/2sec
    "takeoff": 500,           # Décollage: 2x/sec
    "climb": 1000,            # Montée: 1x/sec
    "cruise": 2000,           # Croisière: 1x/2sec
    "descent": 1000,          # Descente: 1x/sec
    "approach": 500,          # Approche: 2x/sec
    "final": 250,             # Finale: 4x/sec
    "landing": 250,           # Atterrissage: 4x/sec
}

# Variables par phase (ne lire que le nécessaire)
SIMCONNECT_VARS_BY_PHASE = {
    "parked": ["BRAKE_PARKING_POSITION", "ENG_COMBUSTION:1"],
    "taxi": ["GROUND_VELOCITY", "PLANE_HEADING_DEGREES_TRUE", "BRAKE_PARKING_POSITION"],
    "flight": ["PLANE_ALTITUDE", "AIRSPEED_INDICATED", "VERTICAL_SPEED",
               "PLANE_LATITUDE", "PLANE_LONGITUDE", "PLANE_BANK_DEGREES"],
    "approach": ["PLANE_ALTITUDE", "PLANE_ALT_ABOVE_GROUND", "AIRSPEED_INDICATED",
                 "VERTICAL_SPEED", "GEAR_HANDLE_POSITION", "FLAPS_HANDLE_PERCENT"],
}
```

**Fonctions à créer:**
```python
def _get_polling_rate(self) -> int:
    """Retourne le taux de polling adapté à la phase actuelle"""

def _get_required_vars(self) -> list:
    """Retourne les variables SimConnect nécessaires pour la phase"""

def _batch_read_simconnect(self, vars: list) -> dict:
    """Lit plusieurs variables en un seul appel optimisé"""

def _adjust_update_interval(self):
    """Ajuste dynamiquement l'intervalle de mise à jour"""
```

**Gains estimés:**
| Phase | Avant | Après | Réduction |
|-------|-------|-------|-----------|
| Parked | 1000ms | 5000ms | -80% CPU |
| Cruise | 1000ms | 2000ms | -50% CPU |
| Approach | 1000ms | 500ms | +Performance |

---

#### 14.2 OPTIMISATION INTERFACE TKINTER

**Problème actuel:**
- Mise à jour de tous les labels à chaque cycle
- Pas de détection de changement
- Redraw complet de l'UI

**Solution - Updates conditionnels:**
```python
# Cache des valeurs affichées
self.ui_cache = {
    "altitude": None,
    "speed": None,
    "heading": None,
    "vs": None,
    # ...
}

def _update_label_if_changed(self, label_name: str, new_value: str):
    """Met à jour un label seulement si la valeur a changé"""
    if self.ui_cache.get(label_name) != new_value:
        self.ui_cache[label_name] = new_value
        self.labels[label_name].config(text=new_value)

def _batch_update_ui(self, updates: dict):
    """Regroupe les mises à jour UI en un seul refresh"""
    changed = False
    for label, value in updates.items():
        if self.ui_cache.get(label) != value:
            self.ui_cache[label] = value
            self.labels[label].config(text=value)
            changed = True
    if changed:
        self.root.update_idletasks()  # Un seul refresh
```

**Optimisation throttling UI:**
```python
UI_UPDATE_RATES = {
    "critical": 250,     # Altitude, vitesse, VS (critique)
    "important": 500,    # Position, cap
    "normal": 1000,      # Distance, progression
    "low": 2000,         # Score, infos mission
}

def _should_update_ui_element(self, element_type: str) -> bool:
    """Vérifie si un élément doit être mis à jour selon son taux"""
```

**Gains estimés:** -50% charge UI, interface plus réactive

---

#### 14.3 OPTIMISATION MÉMOIRE - AÉROPORTS

**Problème actuel:**
- 40000+ aéroports chargés en RAM
- Toutes les données de chaque aéroport
- Recherche linéaire O(n)

**Solution - Chargement par zone:**
```python
# Configuration
AIRPORT_LOAD_RADIUS = 500  # nm - rayon de chargement
AIRPORT_CACHE_SIZE = 1000  # Max aéroports en cache

# Structure optimisée
class AirportIndex:
    def __init__(self):
        self.spatial_index = {}     # Grille spatiale pour recherche rapide
        self.loaded_airports = {}   # Cache LRU des aéroports détaillés
        self.grid_size = 1.0        # 1 degré = ~60nm

    def _get_grid_key(self, lat: float, lon: float) -> tuple:
        """Retourne la clé de grille pour des coordonnées"""
        return (int(lat), int(lon))

    def get_nearby_airports(self, lat: float, lon: float, radius_nm: float) -> list:
        """Retourne les aéroports dans un rayon donné"""
        # Calcule les cellules de grille à vérifier
        # Retourne seulement les aéroports dans ces cellules

    def load_region(self, center_lat: float, center_lon: float):
        """Charge les aéroports d'une région en mémoire"""

    def unload_distant(self, current_lat: float, current_lon: float):
        """Décharge les aéroports trop éloignés"""
```

**Format fichier optimisé:**
```python
# Fichier airports_index.bin (compact)
# Structure: [ICAO(4)] [LAT(4)] [LON(4)] [FLAGS(1)] = 13 bytes/airport
# vs JSON actuel: ~500 bytes/airport

def load_airport_index(filepath: str) -> dict:
    """Charge l'index compact des aéroports"""

def load_airport_details(icao: str) -> dict:
    """Charge les détails d'un aéroport à la demande"""
```

**Gains estimés:**
| Métrique | Avant | Après | Réduction |
|----------|-------|-------|-----------|
| RAM aéroports | ~150MB | ~15MB | -90% |
| Temps recherche | ~50ms | ~2ms | -96% |
| Temps démarrage | ~3s | ~0.5s | -83% |

---

#### 14.4 OPTIMISATION RÉSEAU

**Solution - Cache intelligent:**
```python
# Configuration cache
CACHE_CONFIG = {
    "metar": {
        "duration": 600,        # 10 minutes
        "max_entries": 100,
    },
    "geocoding": {
        "duration": 86400,      # 24 heures
        "max_entries": 500,
        "persist": True,        # Sauvegarder sur disque
    },
    "airport_frequencies": {
        "duration": 604800,     # 1 semaine
        "max_entries": 200,
        "persist": True,
    },
}

class NetworkCache:
    def __init__(self, config: dict):
        self.memory_cache = {}
        self.disk_cache_path = "cache/"
        self.config = config

    def get(self, cache_type: str, key: str) -> Optional[dict]:
        """Récupère une valeur du cache (mémoire puis disque)"""

    def set(self, cache_type: str, key: str, value: dict):
        """Stocke une valeur dans le cache"""

    def is_valid(self, cache_type: str, key: str) -> bool:
        """Vérifie si une entrée est encore valide"""

    def cleanup(self):
        """Nettoie les entrées expirées"""
```

**Requêtes groupées:**
```python
async def batch_fetch_metar(icao_list: list) -> dict:
    """Récupère plusieurs METAR en une seule requête"""

def prefetch_route_data(departure: str, arrival: str, waypoints: list):
    """Précharge les données de la route en arrière-plan"""
```

**Gains estimés:** -70% requêtes réseau, latence réduite

---

#### 14.5 OPTIMISATION THREADS ET ASYNC

**Architecture multi-thread optimisée:**
```python
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio

class OptimizedApp:
    def __init__(self):
        # Thread principal: UI (tkinter)
        self.ui_thread = threading.current_thread()

        # Thread dédié SimConnect
        self.simconnect_thread = threading.Thread(
            target=self._simconnect_loop,
            daemon=True
        )

        # Pool pour tâches réseau
        self.network_pool = ThreadPoolExecutor(max_workers=3)

        # Event loop pour async (voice, TTS)
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(
            target=self._run_async_loop,
            daemon=True
        )

        # Queues de communication inter-thread
        self.simconnect_queue = queue.Queue()  # SimConnect -> UI
        self.voice_queue = queue.Queue()        # Voice -> Main
        self.tts_queue = queue.Queue()          # Main -> TTS

    def _simconnect_loop(self):
        """Boucle SimConnect dans son propre thread"""
        while self.running:
            data = self._read_simconnect()
            self.simconnect_queue.put(data)
            time.sleep(self._get_polling_rate() / 1000)

    def _process_simconnect_data(self):
        """Traite les données SimConnect depuis le thread UI"""
        try:
            while True:
                data = self.simconnect_queue.get_nowait()
                self._update_flight_data(data)
        except queue.Empty:
            pass
        self.root.after(100, self._process_simconnect_data)
```

**Éviter les blocages:**
```python
# Mauvais - bloque l'UI
def bad_fetch_metar(self):
    response = requests.get(url)  # Bloque!
    self.update_weather(response)

# Bon - non bloquant
def good_fetch_metar(self):
    def fetch():
        response = requests.get(url)
        self.root.after(0, lambda: self.update_weather(response))
    self.network_pool.submit(fetch)
```

---

#### 14.6 MODE PERFORMANCE GLOBAL

**Configuration utilisateur:**
```python
PERFORMANCE_MODES = {
    "high": {
        "name": "Haute Performance",
        "description": "Pour PC puissants - Toutes fonctionnalités actives",
        "simconnect_base_rate": 500,
        "ui_rate": 100,
        "airport_cache_size": 2000,
        "voice_enabled": True,
        "voice_mode": "continuous",
        "callouts_enabled": True,
        "network_prefetch": True,
    },
    "balanced": {
        "name": "Équilibré",
        "description": "Bon compromis performance/fonctionnalités",
        "simconnect_base_rate": 1000,
        "ui_rate": 250,
        "airport_cache_size": 1000,
        "voice_enabled": True,
        "voice_mode": "push_to_talk",
        "callouts_enabled": True,
        "network_prefetch": False,
    },
    "low": {
        "name": "Économie",
        "description": "Pour PC modestes - Fonctionnalités réduites",
        "simconnect_base_rate": 2000,
        "ui_rate": 500,
        "airport_cache_size": 500,
        "voice_enabled": False,
        "voice_mode": "disabled",
        "callouts_enabled": True,
        "network_prefetch": False,
    },
    "minimal": {
        "name": "Minimal",
        "description": "Ressources minimales - Essentiel uniquement",
        "simconnect_base_rate": 5000,
        "ui_rate": 1000,
        "airport_cache_size": 200,
        "voice_enabled": False,
        "voice_mode": "disabled",
        "callouts_enabled": False,
        "network_prefetch": False,
    },
}
```

**Auto-détection performance:**
```python
def detect_optimal_mode() -> str:
    """Détecte automatiquement le mode optimal"""
    import psutil

    cpu_count = psutil.cpu_count()
    ram_gb = psutil.virtual_memory().total / (1024**3)

    if cpu_count >= 8 and ram_gb >= 16:
        return "high"
    elif cpu_count >= 4 and ram_gb >= 8:
        return "balanced"
    elif cpu_count >= 2 and ram_gb >= 4:
        return "low"
    else:
        return "minimal"
```

**Monitoring ressources:**
```python
class ResourceMonitor:
    def __init__(self):
        self.cpu_history = []
        self.ram_history = []
        self.warning_threshold_cpu = 80
        self.warning_threshold_ram = 85

    def update(self):
        """Met à jour les métriques"""
        import psutil
        self.cpu_history.append(psutil.cpu_percent())
        self.ram_history.append(psutil.virtual_memory().percent)

        # Garde les 60 dernières secondes
        self.cpu_history = self.cpu_history[-60:]
        self.ram_history = self.ram_history[-60:]

    def get_average_cpu(self) -> float:
        return sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0

    def should_reduce_performance(self) -> bool:
        """Suggère de réduire les performances si surcharge"""
        return self.get_average_cpu() > self.warning_threshold_cpu

    def auto_adjust_mode(self):
        """Ajuste automatiquement le mode si nécessaire"""
```

---

#### 14.7 OPTIMISATION COPILOTE/VOICE

**Écoute intelligente:**
```python
VOICE_OPTIMIZATION = {
    # Mode push-to-talk (recommandé)
    "push_to_talk": {
        "cpu_idle": 0,          # 0% quand inactif
        "cpu_active": 5,        # 5% pendant écoute
        "latency": "immediate",
    },

    # Mode wake word
    "wake_word": {
        "cpu_idle": 2,          # 2% écoute passive
        "cpu_active": 5,        # 5% après activation
        "latency": "100ms",
        "wake_words": ["copilote", "assistant"],
    },

    # Mode continu (déconseillé)
    "continuous": {
        "cpu_idle": 5,          # 5% constant
        "cpu_active": 8,
        "latency": "immediate",
    },
}

# Réponses pré-calculées (sans LLM)
QUICK_RESPONSES = {
    "position": "_get_position_response",      # Direct SimConnect
    "altitude": "_get_altitude_response",      # Direct SimConnect
    "vitesse": "_get_speed_response",          # Direct SimConnect
    "cap": "_get_heading_response",            # Direct SimConnect
    "heure": "_get_time_response",             # Direct système
}

# LLM seulement pour questions complexes
LLM_REQUIRED = [
    "pourquoi", "comment", "explique", "calcule",
    "combien de temps", "est-ce que", "dois-je",
]

def needs_llm(text: str) -> bool:
    """Détermine si la question nécessite le LLM"""
    return any(kw in text.lower() for kw in LLM_REQUIRED)
```

**Cache TTS:**
```python
# Pré-génération des callouts communs
TTS_PRECACHE = [
    "V1", "Rotate", "Positive climb",
    "1000 feet", "500 feet", "100 feet",
    "50", "30", "20", "10",
    "Touchdown", "60 knots",
    "Gear down", "Flaps set",
    # ...
]

class TTSCache:
    def __init__(self):
        self.cache_dir = "tts_cache/"
        self.cache = {}

    async def precache_common_phrases(self):
        """Pré-génère les phrases courantes au démarrage"""
        for phrase in TTS_PRECACHE:
            if not self._is_cached(phrase):
                await self._generate_and_cache(phrase)

    async def speak(self, text: str):
        """Joue depuis le cache ou génère"""
        if self._is_cached(text):
            self._play_cached(text)
        else:
            await self._generate_and_play(text)
```

---

#### 14.8 LAZY LOADING ET DÉMARRAGE RAPIDE

**Chargement différé des modules:**
```python
# Au lieu de tout importer au démarrage
class LazyLoader:
    _modules = {}

    @classmethod
    def get_simconnect(cls):
        if 'simconnect' not in cls._modules:
            from SimConnect import SimConnect, AircraftRequests
            cls._modules['simconnect'] = (SimConnect, AircraftRequests)
        return cls._modules['simconnect']

    @classmethod
    def get_voice(cls):
        if 'voice' not in cls._modules:
            import pyaudio
            import edge_tts
            from groq import Groq
            cls._modules['voice'] = (pyaudio, edge_tts, Groq)
        return cls._modules['voice']

    @classmethod
    def get_pygame(cls):
        if 'pygame' not in cls._modules:
            import pygame
            pygame.mixer.init()
            cls._modules['pygame'] = pygame
        return cls._modules['pygame']
```

**Séquence de démarrage optimisée:**
```python
STARTUP_SEQUENCE = [
    # Phase 1 - Critique (bloquant)
    {"name": "config", "blocking": True, "timeout": 1},
    {"name": "ui_base", "blocking": True, "timeout": 1},

    # Phase 2 - Important (parallèle)
    {"name": "simconnect", "blocking": False, "timeout": 5},
    {"name": "airport_index", "blocking": False, "timeout": 3},

    # Phase 3 - Optionnel (arrière-plan)
    {"name": "voice_init", "blocking": False, "timeout": 10},
    {"name": "tts_precache", "blocking": False, "timeout": 30},
    {"name": "network_cache", "blocking": False, "timeout": 5},
]

async def optimized_startup():
    """Démarrage optimisé avec feedback"""
    for phase in STARTUP_SEQUENCE:
        update_splash(f"Chargement: {phase['name']}...")
        if phase['blocking']:
            await load_module(phase['name'])
        else:
            asyncio.create_task(load_module(phase['name']))
```

---

#### 14.9 TABLEAU RÉCAPITULATIF OPTIMISATIONS

| Composant | Avant | Après | Gain CPU | Gain RAM |
|-----------|-------|-------|----------|----------|
| SimConnect polling | 1Hz constant | Adaptatif 0.2-4Hz | -60% | - |
| UI updates | Tous labels/cycle | Conditionnel | -50% | - |
| Aéroports | 40K en RAM | Index + cache LRU | - | -90% |
| METAR/Réseau | Requête directe | Cache 10min | -70% | +5MB |
| Voice (PTT) | - | Push-to-talk | -90% vs continu | - |
| TTS | Génération live | Cache phrases | -30% | +20MB |
| Démarrage | Séquentiel 5s | Parallèle 1.5s | - | - |

**Estimation globale:**
| Mode | CPU moyen | RAM | Démarrage |
|------|-----------|-----|-----------|
| Sans optim | 15-20% | 250MB | 5s |
| Optimisé High | 8-12% | 150MB | 2s |
| Optimisé Balanced | 5-8% | 100MB | 1.5s |
| Optimisé Low | 2-4% | 60MB | 1s |
| Optimisé Minimal | 1-2% | 40MB | 0.5s |

---

**Fichiers à créer/modifier:**
| Fichier | Description |
|---------|-------------|
| `optimization/cache.py` | Système de cache unifié |
| `optimization/performance.py` | Modes performance et monitoring |
| `optimization/lazy_loader.py` | Chargement différé des modules |
| `optimization/simconnect_opt.py` | Polling adaptatif SimConnect |
| `optimization/airport_index.py` | Index spatial aéroports |
| `main.py` | Intégration des optimisations |
| `config.json` | Ajout paramètres performance |

---

## ORDRE D'IMPLÉMENTATION RECOMMANDÉ

### Phase 0 - Optimisations (Prioritaire) ⚡
1. **Polling adaptatif SimConnect** (base performance)
2. **Cache réseau unifié** (METAR, geocoding)
3. **Index spatial aéroports** (réduction RAM)
4. **Updates UI conditionnels** (fluidité)
5. **Modes performance** (config utilisateur)

### Phase 1 - Fondations (Facile)
6. **Météo SimConnect** (utile immédiatement)
7. **Calcul distance réelle** (améliore précision)
8. **Log Book automatique** (très demandé)
9. **Gestion carburant** (ajoute économie)

### Phase 2 - Gameplay (Facile/Moyen)
10. **Challenges atterrissage** (ajoute gameplay)
11. **Réputation compagnies** (ajoute profondeur)
12. **Mode carrière** (gros ajout de valeur)
13. **Usure avion** (réalisme)

### Phase 3 - Copilote IA (Moyen/Difficile) ⭐
14. **Copilote - Détection phases** (base du système)
15. **Copilote - Callouts automatiques** (V1, rotate, altitudes)
16. **Copilote - Détection erreurs** (survitesse, train, approche)
17. **Copilote - Checklists vocales** (interactif)
18. **Copilote - Conversation LLM** (réponses intelligentes)
19. **Copilote - Annonces radio ATC** (immersion)
20. **Copilote - Debriefing** (analyse fin de vol)

### Phase 4 - Bonus (Moyen/Difficile)
21. **Check-ride** (contenu additionnel)
22. **Pannes aléatoires** (challenge)
23. **Confort passagers** (détail)
24. **Rejeu vol** (export KML/GPX)

---

## FICHIERS À CRÉER

### Module Optimisation (dossier `optimization/`) ⚡ PRIORITAIRE
| Fichier | Description |
|---------|-------------|
| `optimization/__init__.py` | Point d'entrée module optimisation |
| `optimization/cache.py` | Cache unifié (METAR, geocoding, fréquences) |
| `optimization/performance.py` | Modes performance + monitoring ressources |
| `optimization/lazy_loader.py` | Chargement différé des modules lourds |
| `optimization/simconnect_opt.py` | Polling adaptatif par phase de vol |
| `optimization/airport_index.py` | Index spatial + cache LRU aéroports |
| `optimization/ui_throttle.py` | Throttling et updates conditionnels UI |

### Modules fonctionnels à créer
| Fichier | Description |
|---------|-------------|
| `career.py` | Module gestion carrière pilote |
| `maintenance.py` | Module usure et maintenance |
| `logbook.py` | Module carnet de vol |
| `weather.py` | Module météo SimConnect |
| `challenges.py` | Module challenges et check-rides |
| `companies.py` | Module compagnies aériennes |

### Module Copilote IA (dossier `copilot/`)
| Fichier | Description |
|---------|-------------|
| `copilot/__init__.py` | Point d'entrée du module copilote |
| `copilot/voice.py` | Gestion STT (Whisper) et TTS (Edge-TTS) |
| `copilot/phases.py` | Détection automatique des phases de vol |
| `copilot/callouts.py` | Système de callouts (V1, rotate, altitudes...) |
| `copilot/errors.py` | Détection et alertes erreurs pilote |
| `copilot/atc.py` | Simulation communications radio ATC |
| `copilot/checklists.py` | Checklists vocales interactives |
| `copilot/llm.py` | Interface LLM pour conversation naturelle |
| `copilot/debrief.py` | Génération debriefing fin de vol |
| `copilot/config.py` | Configuration voix, seuils, personnalité |

### Dépendances Copilote
```
pyaudio          # Capture microphone
groq             # Whisper STT + LLM (LLaMA/Mixtral)
edge-tts         # Synthèse vocale Microsoft
pygame           # Lecture audio
requests         # Reverse geocoding (ville survolée)
```

### Dépendances Optimisation
```
psutil           # Monitoring CPU/RAM
msgpack          # Sérialisation binaire rapide (optionnel)
```

---

## RÉSUMÉ IMPACT OPTIMISATIONS

### Avant optimisations
```
CPU:       15-20% constant
RAM:       ~250 MB
Démarrage: ~5 secondes
Réseau:    Requêtes systématiques
```

### Après optimisations (mode Balanced)
```
CPU:       5-8% (adaptatif selon phase)
RAM:       ~100 MB
Démarrage: ~1.5 secondes
Réseau:    -70% (cache intelligent)
```

### Configuration recommandée par hardware

| RAM | CPU | Mode recommandé |
|-----|-----|-----------------|
| 4 GB | 2 cores | Minimal |
| 8 GB | 4 cores | Low |
| 16 GB | 6 cores | Balanced |
| 32 GB | 8+ cores | High |

---

*Document mis à jour le 25/01/2026*
