# Variables SimConnect - MSFS 2024 Reference Complete

> **Derniere mise a jour**: Janvier 2026
> **Source officielle**: [MSFS 2024 SDK Documentation](https://docs.flightsimulator.com/msfs2024/html/6_Programming_APIs/SimVars/Simulation_Variables.htm)

Ce document est le referentiel complet des variables SimConnect pour MSFS 2024.

---

## Table des matieres

1. [Position et Mouvement](#1-position-et-mouvement)
2. [Vitesses](#2-vitesses)
3. [Etat Avion](#3-etat-avion)
4. [Moteurs - General](#4-moteurs---general)
5. [Moteurs - Turboprop/Jet](#5-moteurs---turbopropjet)
6. [Moteurs - Piston](#6-moteurs---piston)
7. [Carburant](#7-carburant)
8. [Surfaces de Controle](#8-surfaces-de-controle)
9. [Train d'atterrissage et Freins](#9-train-datterrissage-et-freins)
10. [Autopilot](#10-autopilot)
11. [Systemes Electriques](#11-systemes-electriques)
12. [Lumieres](#12-lumieres)
13. [Radio et Navigation](#13-radio-et-navigation)
14. [GPS](#14-gps)
15. [Transponder et ATC](#15-transponder-et-atc)
16. [Instruments](#16-instruments)
17. [Meteo et Environnement](#17-meteo-et-environnement)
18. [Hydraulique et Pneumatique](#18-hydraulique-et-pneumatique)
19. [Avertissements](#19-avertissements)
20. [Usure et Maintenance](#20-usure-et-maintenance)
21. [Etat Simulation](#21-etat-simulation)
22. [Evenements (Key Events)](#22-evenements-key-events)
23. [Notes Importantes](#23-notes-importantes)

---

## 1. Position et Mouvement

### Position Geographique

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `PLANE_LATITUDE` | Float | Radians | R | Latitude (Nord positif) |
| `PLANE_LONGITUDE` | Float | Radians | R | Longitude (Est positif) |
| `PLANE_ALTITUDE` | Float | Feet | R | Altitude MSL |
| `PLANE_ALT_ABOVE_GROUND` | Float | Feet | R | Altitude AGL incluant obstacles |
| `AIRCRAFT_AGL` | Float | Feet | R | Hauteur au-dessus du terrain |
| `GROUND_ALTITUDE` | Float | Meters | R | Altitude du sol sous l'avion |
| `STRUCT_LATLONALT` | Struct | - | R | Lat, Lon, Alt en une structure |

### Orientation

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `PLANE_PITCH_DEGREES` | Float | **Radians** | R | Assiette (malgre le nom "degrees") |
| `PLANE_BANK_DEGREES` | Float | **Radians** | R | Inclinaison (malgre le nom) |
| `PLANE_HEADING_DEGREES_TRUE` | Float | **Radians** | R | Cap vrai |
| `PLANE_HEADING_DEGREES_MAGNETIC` | Float | **Radians** | R | Cap magnetique |
| `PLANE_HEADING_DEGREES_GYRO` | Float | Radians | R | Indication gyrocompas |
| `MAGVAR` | Float | Degrees | R | Variation magnetique locale |

### Accelerations

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ACCELERATION_BODY_X` | Float | ft/s² | R | Acceleration laterale (avion) |
| `ACCELERATION_BODY_Y` | Float | ft/s² | R | Acceleration verticale (avion) |
| `ACCELERATION_BODY_Z` | Float | ft/s² | R | Acceleration longitudinale (avion) |
| `ACCELERATION_WORLD_X` | Float | ft/s² | R | Acceleration Est/Ouest |
| `ACCELERATION_WORLD_Y` | Float | ft/s² | R | Acceleration verticale (monde) |
| `ACCELERATION_WORLD_Z` | Float | ft/s² | R | Acceleration Nord/Sud |
| `G_FORCE` | Float | G | R | Force G actuelle |

### Rotations

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ROTATION_VELOCITY_BODY_X` | Float | rad/s | R | Taux de roulis |
| `ROTATION_VELOCITY_BODY_Y` | Float | rad/s | R | Taux de tangage |
| `ROTATION_VELOCITY_BODY_Z` | Float | rad/s | R | Taux de lacet |
| `ROTATION_ACCELERATION_BODY_X` | Float | rad/s² | R | Acceleration roulis |
| `ROTATION_ACCELERATION_BODY_Y` | Float | rad/s² | R | Acceleration tangage |
| `ROTATION_ACCELERATION_BODY_Z` | Float | rad/s² | R | Acceleration lacet |

### Donnees d'atterrissage (dernier touchdown)

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `PLANE_TOUCHDOWN_LATITUDE` | Float | Radians | R | Latitude du dernier atterrissage |
| `PLANE_TOUCHDOWN_LONGITUDE` | Float | Radians | R | Longitude du dernier atterrissage |
| `PLANE_TOUCHDOWN_NORMAL_VELOCITY` | Float | ft/s | R | Vitesse verticale au toucher |
| `PLANE_TOUCHDOWN_PITCH_DEGREES` | Float | Degrees | R | Assiette au toucher |
| `PLANE_TOUCHDOWN_BANK_DEGREES` | Float | Degrees | R | Inclinaison au toucher |
| `PLANE_TOUCHDOWN_HEADING_DEGREES_TRUE` | Float | Degrees | R | Cap au toucher |

---

## 2. Vitesses

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AIRSPEED_INDICATED` | Float | Knots | R | Vitesse indiquee (IAS) |
| `AIRSPEED_TRUE` | Float | Knots | R | Vitesse vraie (TAS) |
| `AIRSPEED_TRUE_RAW` | Float | Knots | R | TAS sans correction vent |
| `AIRSPEED_INDICATED_THEORETICAL` | Float | Knots | R | IAS theorique (ignore cache pitot) |
| `AIRSPEED_MACH` | Float | Mach | R | Nombre de Mach |
| `AIRSPEED_BARBER_POLE` | Float | Knots | R | Vitesse max (VMO/MMO) |
| `GROUND_VELOCITY` | Float | Knots | R | Vitesse sol (GS) |
| `SURFACE_RELATIVE_GROUND_SPEED` | Float | ft/s | R | Vitesse relative surface (porte-avions) |
| `VERTICAL_SPEED` | Float | **ft/s** | R | Vitesse verticale (convertir en fpm x60) |
| `TOTAL_VELOCITY` | Float | ft/s | R | Vitesse totale 3D |
| `VELOCITY_BODY_X` | Float | ft/s | R | Vitesse laterale (avion) |
| `VELOCITY_BODY_Y` | Float | ft/s | R | Vitesse verticale (avion) |
| `VELOCITY_BODY_Z` | Float | ft/s | R | Vitesse longitudinale = TAS |

### Vent relatif

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `RELATIVE_WIND_VELOCITY_BODY_X` | Float | ft/s | R | Vent lateral relatif |
| `RELATIVE_WIND_VELOCITY_BODY_Y` | Float | ft/s | R | Vent vertical relatif |
| `RELATIVE_WIND_VELOCITY_BODY_Z` | Float | ft/s | R | Vent longitudinal relatif |
| `AIRCRAFT_WIND_X` | Float | Knots | R | Composante vent lateral |
| `AIRCRAFT_WIND_Y` | Float | Knots | R | Composante vent vertical |
| `AIRCRAFT_WIND_Z` | Float | Knots | R | Composante vent longitudinal |

---

## 3. Etat Avion

### Etats principaux

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `SIM_ON_GROUND` | Bool | - | R | Avion au sol |
| `PLANE_IN_PARKING_STATE` | Bool | - | R | **Avion en etat parking** |
| `ON_ANY_RUNWAY` | Bool | - | R | Sur une piste (peut ne pas fonctionner!) |
| `IS_SLEW_ACTIVE` | Bool | - | R | Mode slew actif |
| `IS_SLEW_ALLOWED` | Bool | - | R | Mode slew autorise |
| `IS_USER_SIM` | Bool | - | R | Avion controle par joueur |
| `SIM_DISABLED` | Bool | - | R | Simulation desactivee |

### Surface

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `SURFACE_TYPE` | Enum | - | R | Type: Concrete, Grass, Water, Asphalt, etc. (25 types) |
| `SURFACE_CONDITION` | Enum | - | R | Etat: Normal, Wet, Icy, Snow |
| `SURFACE_INFO_VALID` | Bool | - | R | Donnees surface valides |

### Identification avion

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `TITLE` | String | - | R | Titre avion (config) |
| `ATC_MODEL` | String | - | R/W | Modele ATC (ex: "A320") |
| `ATC_TYPE` | String | - | R/W | Type avion |
| `ATC_ID` | String | - | R/W | Identifiant ATC (max 10 car) |
| `AIRCRAFT_CATEGORY` | String | - | R | Categorie (ui_typerole) |
| `LIVERY_NAME` | String | - | R | Nom de la livree |
| `ENGINE_TYPE` | Enum | - | R | 0=Piston, 1=Jet, 3=Heli, 5=Turboprop |
| `NUMBER_OF_ENGINES` | Int | - | R | Nombre moteurs (0-4) |

### Poids

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `TOTAL_WEIGHT` | Float | Pounds | R | Poids total actuel |
| `EMPTY_WEIGHT` | Float | Pounds | R | Poids a vide |
| `MAX_GROSS_WEIGHT` | Float | Pounds | R | Masse max |

### Givrage

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `STRUCTURAL_ICE_PCT` | Float | Percent | R | Givrage structure (0-100) |
| `PITOT_ICE_PCT` | Float | Percent | R | Givrage tube pitot (0-100) |

---

## 4. Moteurs - General

### Etat moteur (utiliser avec index :1, :2, etc.)

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GENERAL_ENG_COMBUSTION:n` | Bool | - | R/W | Moteur n en marche |
| `GENERAL_ENG_RPM:n` | Float | RPM | R | RPM moteur n |
| `GENERAL_ENG_PCT_MAX_RPM:n` | Float | Percent | R | % RPM max |
| `GENERAL_ENG_THROTTLE_LEVER_POSITION:n` | Float | Percent | R/W | Position manette gaz (0-100%) |
| `GENERAL_ENG_MIXTURE_LEVER_POSITION:n` | Float | Percent | R/W | Position richesse (0-100%) |
| `GENERAL_ENG_PROPELLER_LEVER_POSITION:n` | Float | Percent | R/W | Position pas helice |
| `GENERAL_ENG_STARTER:n` | Bool | - | R/W | Demarreur actif |
| `GENERAL_ENG_STARTER_ACTIVE:n` | Bool | - | R | Demarreur en cours |
| `GENERAL_ENG_FAILED:n` | Bool | - | R | Moteur en panne |
| `GENERAL_ENG_FUEL_VALVE:n` | Bool | - | R/W | Vanne carburant ouverte |
| `GENERAL_ENG_FUEL_PUMP_SWITCH:n` | Bool | - | R/W | Pompe carburant |
| `GENERAL_ENG_ANTI_ICE_POSITION:n` | Bool | - | R/W | Antigivrage moteur |
| `GENERAL_ENG_REVERSE_THRUST_ENGAGED:n` | Bool | - | R | Reverse engage |
| `ENG_ON_FIRE:n` | Bool | - | R/W | Moteur en feu |
| `MASTER_IGNITION_SWITCH` | Bool | - | R/W | Contact general |

### Temperatures et pressions

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GENERAL_ENG_OIL_PRESSURE:n` | Float | PSF | R | Pression huile |
| `GENERAL_ENG_OIL_TEMPERATURE:n` | Float | Rankine | R | Temperature huile |
| `GENERAL_ENG_EXHAUST_GAS_TEMPERATURE:n` | Float | Rankine | R/W | Temperature EGT |
| `ENG_CYLINDER_HEAD_TEMPERATURE:n` | Float | Rankine | R | Temperature culasse |
| `ENG_MANIFOLD_PRESSURE:n` | Float | inHg | R | Pression admission |
| `ENG_FUEL_FLOW_GPH:n` | Float | Gal/h | R | Debit carburant |
| `ENG_FUEL_FLOW_PPH:n` | Float | Lbs/h | R | Debit carburant (poids) |

---

## 5. Moteurs - Turboprop/Jet

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `TURB_ENG_N1:n` | Float | Percent | R | N1 (0-100%) |
| `TURB_ENG_N2:n` | Float | Percent | R | N2 (0-100%) |
| `TURB_ENG_ITT:n` | Float | Rankine | R/W | Temperature ITT |
| `TURB_ENG_JET_THRUST:n` | Float | Pounds | R | Poussee |
| `TURB_ENG_FUEL_FLOW_PPH:n` | Float | Lbs/h | R | Debit carburant |
| `TURB_ENG_CORRECTED_N1:n` | Float | Percent | R | N1 corrige |
| `TURB_ENG_CORRECTED_N2:n` | Float | Percent | R | N2 corrige |
| `TURB_ENG_COMMANDED_N1:n` | Float | Percent | R/W | N1 commande |
| `TURB_ENG_BLEED_AIR:n` | Float | PSI | R | Pression bleed air |
| `TURB_ENG_IGNITION_SWITCH:n` | Bool | - | R/W | Contact allumage |
| `TURB_ENG_IGNITION_SWITCH_EX1:n` | Enum | - | R/W | 0=OFF, 1=AUTO, 2=ON |
| `TURB_ENG_IS_IGNITING:n` | Bool | - | R | Allumage en cours |
| `TURB_ENG_CONDITION_LEVER_POSITION:n` | Enum | - | R/W | 0=cutoff, 1=low idle, 2=high idle |
| `TURB_ENG_AFTERBURNER:n` | Bool | - | R | Postcombustion active |
| `TURB_ENG_REVERSE_NOZZLE_PERCENT:n` | Float | Percent | R | Reverse deploye |
| `TURB_ENG_FUEL_AVAILABLE:n` | Bool | - | R | Carburant disponible |
| `TURB_ENG_VIBRATION:n` | Float | Number | R | Vibration moteur |
| `TURB_ENG_MAX_TORQUE_PERCENT:n` | Float | Percent | R | % couple max |

---

## 6. Moteurs - Piston

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `RECIP_ENG_MANIFOLD_PRESSURE:n` | Float | PSI | R | Pression admission |
| `RECIP_ENG_CYLINDER_HEAD_TEMPERATURE:n` | Float | Celsius | R | Temperature culasse |
| `RECIP_CARBURETOR_TEMPERATURE:n` | Float | Celsius | R/W | Temperature carburateur |
| `RECIP_ENG_FUEL_FLOW:n` | Float | Lbs/h | R | Debit carburant |
| `RECIP_ENG_LEFT_MAGNETO:n` | Bool | - | R/W | Magneto gauche |
| `RECIP_ENG_RIGHT_MAGNETO:n` | Bool | - | R/W | Magneto droite |
| `RECIP_ENG_PRIMER:n` | Bool | - | R/W | Amorce |
| `RECIP_ENG_BRAKE_POWER:n` | Float | Ftlbs/s | R | Puissance freinage |
| `RECIP_ENG_COWL_FLAP_POSITION:n` | Float | Percent | R/W | Volet capot |
| `RECIP_ENG_DETONATING:n` | Bool | - | R/W | Detonation |
| `RECIP_ENG_EMERGENCY_BOOST_ACTIVE:n` | Bool | - | R/W | Boost urgence |
| `RECIP_ENG_STARTER_TORQUE:n` | Float | Ft-lb | R | Couple demarreur |
| `RECIP_ENG_TURBOCHARGER_FAILED:n` | Bool | - | R | Turbo en panne |
| `RECIP_ENG_WASTEGATE_POSITION:n` | Float | Percent | R | Wastegate |
| `RECIP_MIXTURE_RATIO:n` | Float | Ratio | R | Ratio air/fuel |
| `RECIP_ENG_NUM_CYLINDERS:n` | Int | - | R | Nombre cylindres |
| `RECIP_ENG_NUM_CYLINDERS_FAILED:n` | Int | - | R | Cylindres en panne |

### Helice

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `PROP_RPM:n` | Float | RPM | R | RPM helice |
| `PROP_THRUST:n` | Float | Pounds | R | Poussee helice |
| `PROP_BETA:n` | Float | Radians | R | Pas helice |
| `PROP_FEATHERED:n` | Bool | - | R | Helice en drapeau |
| `PROP_FEATHER_SWITCH:n` | Bool | - | R/W | Switch drapeau |
| `PROP_SYNC_ACTIVE:n` | Bool | - | R | Synchro helices active |
| `PROP_DEICE_SWITCH:n` | Bool | - | R | Antigivrage helice |
| `PROP_AUTO_FEATHER_ARMED:n` | Bool | - | R | Auto-feather arme |
| `PROP_MAX_RPM_PERCENT:n` | Float | Percent | R | % RPM max |

---

## 7. Carburant

### General

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `FUEL_TOTAL_QUANTITY` | Float | Gallons | R | Total carburant (utilisable) |
| `FUEL_TOTAL_QUANTITY_WEIGHT` | Float | Pounds | R | Poids total carburant |
| `FUEL_TOTAL_CAPACITY` | Float | Gallons | R | Capacite totale |
| `FUEL_WEIGHT_PER_GALLON` | Float | Pounds | R | Densite carburant |
| `UNLIMITED_FUEL` | Bool | - | R | Mode carburant infini |
| `FUEL_LEFT_QUANTITY` | Float | Gallons | R | Carburant gauche |
| `FUEL_RIGHT_QUANTITY` | Float | Gallons | R | Carburant droite |
| `FUEL_DUMP_ACTIVE` | Bool | - | R | Vidange en cours |
| `FUEL_DUMP_SWITCH` | Bool | - | R/W | Commande vidange |

### Reservoirs (systeme moderne)

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `FUELSYSTEM_TANK_QUANTITY:name` | Float | Gallons | R/W | Quantite reservoir |
| `FUELSYSTEM_TANK_LEVEL:name` | Float | Percent | R/W | Niveau reservoir (0-1) |
| `FUELSYSTEM_TANK_CAPACITY:name` | Float | Gallons | R | Capacite reservoir |
| `FUELSYSTEM_TANK_WEIGHT:name` | Float | Pounds | R/W | Poids carburant |
| `FUELSYSTEM_PUMP_SWITCH:name` | Bool | - | R/W | Pompe carburant |
| `FUELSYSTEM_PUMP_ACTIVE:name` | Bool | - | R | Pompe active |
| `FUELSYSTEM_VALVE_SWITCH:name` | Bool | - | R/W | Vanne ouverte |
| `FUELSYSTEM_VALVE_OPEN:name` | Float | Percent | R | Ouverture vanne |
| `FUELSYSTEM_LINE_FUEL_FLOW:name` | Float | Gal/h | R | Debit ligne |
| `FUELSYSTEM_LINE_FUEL_PRESSURE:name` | Float | kPa | R | Pression ligne |
| `FUELSYSTEM_ENGINE_PRESSURE:n` | Float | kPa | R | Pression au moteur |

### Reservoirs (systeme legacy)

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `FUEL_TANK_LEFT_MAIN_QUANTITY` | Float | Gallons | R/W | Reservoir principal gauche |
| `FUEL_TANK_RIGHT_MAIN_QUANTITY` | Float | Gallons | R/W | Reservoir principal droit |
| `FUEL_TANK_CENTER_QUANTITY` | Float | Gallons | R/W | Reservoir central |
| `FUEL_TANK_LEFT_AUX_QUANTITY` | Float | Gallons | R/W | Auxiliaire gauche |
| `FUEL_TANK_RIGHT_AUX_QUANTITY` | Float | Gallons | R/W | Auxiliaire droit |
| `FUEL_TANK_LEFT_TIP_QUANTITY` | Float | Gallons | R/W | Bout d'aile gauche |
| `FUEL_TANK_RIGHT_TIP_QUANTITY` | Float | Gallons | R/W | Bout d'aile droit |
| `FUEL_CROSS_FEED:n` | Enum | - | R/W | Cross-feed (0=auto,1=off,2=apu,3=eng) |

---

## 8. Surfaces de Controle

### Ailerons

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AILERON_POSITION` | Float | Position | R/W | Position ailerons (-16K a 0) |
| `AILERON_LEFT_DEFLECTION_PCT` | Float | Percent | R/W | Deflexion gauche |
| `AILERON_RIGHT_DEFLECTION_PCT` | Float | Percent | R/W | Deflexion droite |
| `AILERON_TRIM_PCT` | Float | Float | R/W | Trim ailerons (-1 a 1) |
| `AILERON_TRIM_DISABLED` | Bool | - | R/W | Trim desactive |

### Profondeur

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ELEVATOR_POSITION` | Float | Position | R/W | Position profondeur (-16K a 0) |
| `ELEVATOR_DEFLECTION_PCT` | Float | Percent | R/W | Deflexion % |
| `ELEVATOR_TRIM_POSITION` | Float | Radians | R/W | Position trim |
| `ELEVATOR_TRIM_PCT` | Float | Percent | R/W | Trim % |
| `ELEVATOR_TRIM_INDICATOR` | Float | Position | R | Indicateur trim |
| `ELEVATOR_TRIM_DISABLED` | Bool | - | R/W | Trim desactive |

### Gouverne

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `RUDDER_POSITION` | Float | Position | R/W | Position gouverne (-16K a 0) |
| `RUDDER_DEFLECTION_PCT` | Float | Percent | R/W | Deflexion % |
| `RUDDER_TRIM` | Float | Radians | R/W | Trim gouverne |
| `RUDDER_TRIM_PCT` | Float | Float | R/W | Trim % (-1 a 1) |
| `RUDDER_TRIM_DISABLED` | Bool | - | R/W | Trim desactive |
| `RUDDER_PEDAL_POSITION` | Float | Position | R/W | Position palonniers |

### Volets

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `FLAPS_HANDLE_PERCENT` | Float | Percent | R/W | Position volets (0-100%) |
| `FLAPS_HANDLE_INDEX` | Int | - | R | Cran actuel |
| `FLAPS_NUM_HANDLE_POSITIONS` | Int | - | R | Nombre de crans |
| `FLAPS_AVAILABLE` | Bool | - | R | Volets disponibles |
| `TRAILING_EDGE_FLAPS_LEFT_PERCENT` | Float | Percent | R/W | Volet arriere gauche |
| `TRAILING_EDGE_FLAPS_RIGHT_PERCENT` | Float | Percent | R/W | Volet arriere droit |
| `LEADING_EDGE_FLAPS_LEFT_PERCENT` | Float | Percent | R/W | Bec gauche |
| `LEADING_EDGE_FLAPS_RIGHT_PERCENT` | Float | Percent | R/W | Bec droit |
| `FLAP_SPEED_EXCEEDED` | Bool | - | R | Vitesse volets depassee |
| `FLAP_DAMAGE_BY_SPEED` | Bool | - | R | Volets endommages |
| `FLAPS_CURRENT_SPEED_LIMITATION` | Float | Knots | R | Vitesse max volets |

### Spoilers/Aerofreins

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `SPOILERS_HANDLE_POSITION` | Float | Percent | R/W | Position spoilers (0-100%) |
| `SPOILERS_LEFT_POSITION` | Float | Percent | R/W | Spoiler gauche |
| `SPOILERS_RIGHT_POSITION` | Float | Percent | R/W | Spoiler droit |
| `SPOILERS_ARMED` | Bool | - | R/W | Spoilers armes |
| `SPOILER_AVAILABLE` | Bool | - | R | Spoilers disponibles |

---

## 9. Train d'atterrissage et Freins

### Train d'atterrissage

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GEAR_HANDLE_POSITION` | Float | Percent | R/W | Commande train (0=rentre, 1=sorti) |
| `GEAR_POSITION:n` | Enum | - | R | 0=unknown, 1=up, 2=down |
| `GEAR_LEFT_POSITION` | Float | Percent | R | Extension train gauche |
| `GEAR_CENTER_POSITION` | Float | Percent | R | Extension train central |
| `GEAR_RIGHT_POSITION` | Float | Percent | R | Extension train droit |
| `GEAR_TOTAL_PCT_EXTENDED` | Float | Percent | R | % total extension |
| `GEAR_IS_ON_GROUND:n` | Bool | - | R | Train n au sol |
| `GEAR_IS_SKIDDING:n` | Bool | - | R | Train n derape |
| `GEAR_SPEED_EXCEEDED` | Bool | - | R | Vitesse train depassee |
| `GEAR_DAMAGE_BY_SPEED` | Bool | - | R | Train endommage |
| `GEAR_WARNING:n` | Enum | - | R | Alarme train |
| `GEAR_EMERGENCY_HANDLE_POSITION` | Bool | - | R/W | Commande urgence |
| `IS_GEAR_RETRACTABLE` | Bool | - | R | Train retractable |
| `IS_GEAR_WHEELS` | Bool | - | R | Train a roues |
| `IS_GEAR_FLOATS` | Bool | - | R | Flotteurs |
| `IS_GEAR_SKIS` | Bool | - | R | Skis |

### Index train
- 0 = Centre
- 1 = Gauche
- 2 = Droit
- 3 = Auxiliaire

### Direction

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GEAR_CENTER_STEER_ANGLE` | Float | Radians | R | Direction roue avant |
| `GEAR_CENTER_STEER_ANGLE_PCT` | Float | Percent | R | Direction % |
| `NOSEWHEEL_LOCK_ON` | Bool | - | R/W | Blocage roue avant |
| `NOSEWHEEL_MAX_STEERING_ANGLE` | Float | Radians | R/W | Angle max direction |
| `TAILWHEEL_LOCK_ON` | Bool | - | R/W | Blocage roulette |
| `STEER_INPUT_CONTROL` | Float | Percent | R | Position tiller |

### Freins

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `BRAKE_PARKING_POSITION` | Bool | - | R/W | Frein de parking |
| `BRAKE_PARKING_INDICATOR` | Bool | - | R | Indicateur parking |
| `BRAKE_LEFT_POSITION` | Float | Position | R/W | Frein gauche (0-32K) |
| `BRAKE_RIGHT_POSITION` | Float | Position | R/W | Frein droit (0-32K) |
| `BRAKE_INDICATOR` | Float | Position | R | Indicateur freins |
| `ANTISKID_BRAKES_ACTIVE` | Bool | - | R/W | Antiderapage actif |
| `AUTOBRAKES_ACTIVE` | Bool | - | R | Autobrake actif |
| `AUTO_BRAKE_SWITCH_CB` | Int | - | R | Position autobrake |
| `TOE_BRAKES_AVAILABLE` | Bool | - | R | Freins pedale dispo |
| `REJECTED_TAKEOFF_BRAKES_ACTIVE` | Bool | - | R | Freins RTO actifs |

### Roues

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `LEFT_WHEEL_RPM` | Float | RPM | R | RPM roue gauche |
| `RIGHT_WHEEL_RPM` | Float | RPM | R | RPM roue droite |
| `CENTER_WHEEL_RPM` | Float | RPM | R | RPM roue centrale |
| `WHEEL_RPM:n` | Float | RPM | R | RPM roue n |
| `WHEEL_ROTATION_ANGLE:n` | Float | Radians | R | Rotation roue n |

### Points de contact

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `CONTACT_POINT_COMPRESSION:n` | Float | Position | R | Compression amortisseur |
| `CONTACT_POINT_IS_ON_GROUND:n` | Bool | - | R | Point au sol |
| `CONTACT_POINT_IS_SKIDDING:n` | Bool | - | R | Point derape |
| `CONTACT_POINT_WATER_DEPTH:n` | Float | Feet | R | Profondeur eau |

---

## 10. Autopilot

### Etat general

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_MASTER` | Bool | - | R/W | AP active |
| `AUTOPILOT_AVAILABLE` | Bool | - | R | AP disponible |
| `AUTOPILOT_DISENGAGED` | Bool | - | R | AP deconnecte |
| `AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE` | Bool | - | R | FD actif |

### Modes lateraux

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_HEADING_LOCK` | Bool | - | R | Mode HDG actif |
| `AUTOPILOT_HEADING_LOCK_DIR` | Float | Degrees | R/W | Cap selectionne |
| `AUTOPILOT_WING_LEVELER` | Bool | - | R/W | Wings level |
| `AUTOPILOT_BANK_HOLD` | Bool | - | R | Bank hold actif |
| `AUTOPILOT_BANK_HOLD_REF` | Float | Degrees | R/W | Bank reference |
| `AUTOPILOT_MAX_BANK` | Float | Radians | R | Bank max |
| `AUTOPILOT_NAV1_LOCK` | Bool | - | R | NAV1 lock |
| `AUTOPILOT_NAV_SELECTED` | Int | - | R | NAV selectionnee |

### Modes verticaux

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_ALTITUDE_LOCK` | Bool | - | R/W | Mode ALT actif |
| `AUTOPILOT_ALTITUDE_LOCK_VAR` | Float | Feet | R/W | Altitude selectionnee |
| `AUTOPILOT_ALTITUDE_ARM` | Bool | - | R | Altitude arm |
| `AUTOPILOT_VERTICAL_HOLD` | Bool | - | R/W | Mode VS actif |
| `AUTOPILOT_VERTICAL_HOLD_VAR` | Float | Ft/min | R/W | VS selectionnee |
| `AUTOPILOT_PITCH_HOLD` | Bool | - | R/W | Pitch hold |
| `AUTOPILOT_PITCH_HOLD_REF` | Float | Radians | R/W | Pitch reference |
| `AUTOPILOT_FLIGHT_LEVEL_CHANGE` | Bool | - | R/W | Mode FLCH |

### Modes vitesse

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_AIRSPEED_HOLD` | Bool | - | R | IAS hold actif |
| `AUTOPILOT_AIRSPEED_HOLD_VAR` | Float | Knots | R/W | IAS selectionnee |
| `AUTOPILOT_MACH_HOLD` | Bool | - | R | Mach hold actif |
| `AUTOPILOT_MACH_HOLD_VAR` | Float | Mach | R/W | Mach selectionne |
| `AUTOPILOT_MANAGED_THROTTLE_ACTIVE` | Bool | - | R | Autothrottle actif |
| `AUTOPILOT_THROTTLE_ARM` | Bool | - | R | Autothrottle arme |
| `AUTOPILOT_TAKEOFF_POWER_ACTIVE` | Bool | - | R | TO/GA actif |

### Modes approche

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_APPROACH_HOLD` | Bool | - | R | Mode APPR actif |
| `AUTOPILOT_APPROACH_ARM` | Bool | - | R | APPR arme |
| `AUTOPILOT_APPROACH_ACTIVE` | Bool | - | R | APPR capture |
| `AUTOPILOT_APPROACH_CAPTURED` | Bool | - | R | LOC capture |
| `AUTOPILOT_APPROACH_IS_LOCALIZER` | Bool | - | R | C'est un ILS |
| `AUTOPILOT_GLIDESLOPE_HOLD` | Bool | - | R | Mode G/S actif |
| `AUTOPILOT_GLIDESLOPE_ARM` | Bool | - | R | G/S arme |
| `AUTOPILOT_GLIDESLOPE_ACTIVE` | Bool | - | R | G/S capture |
| `AUTOPILOT_BACKCOURSE_HOLD` | Bool | - | R | Backcourse actif |

### Flight Director

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_FLIGHT_DIRECTOR_BANK` | Float | Radians | R | Commande FD bank |
| `AUTOPILOT_FLIGHT_DIRECTOR_PITCH` | Float | Radians | R | Commande FD pitch |

### Yaw damper

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AUTOPILOT_YAW_DAMPER` | Bool | - | R/W | Yaw damper actif |

---

## 11. Systemes Electriques

### Batteries

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ELECTRICAL_MASTER_BATTERY` | Bool | - | R/W | Contact batterie |
| `ELECTRICAL_BATTERY_VOLTAGE:name` | Float | Volts | R/W | Tension batterie |
| `ELECTRICAL_BATTERY_LOAD:name` | Float | Amperes | R/W | Charge batterie |
| `ELECTRICAL_BATTERY_ESTIMATED_CAPACITY_PCT:name` | Float | Percent | R | Capacite restante |

### Generateurs/Alternateurs

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GENERAL_ENG_MASTER_ALTERNATOR:n` | Bool | - | R/W | Contact alternateur |
| `GENERAL_ENG_GENERATOR_SWITCH:n` | Bool | - | R | Switch generateur |
| `GENERAL_ENG_GENERATOR_ACTIVE:n` | Bool | - | R/W | Generateur actif |
| `ELECTRICAL_GENERATOR_VOLTAGE:name` | Float | Volts | R | Tension sortie |
| `ELECTRICAL_GENERATOR_AMPS:name` | Float | Amperes | R | Courant sortie |

### Bus et circuits

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ELECTRICAL_BUS_VOLTAGE:name` | Float | Volts | R | Tension bus |
| `ELECTRICAL_BUS_AMPS:name` | Float | Amperes | R | Courant bus |
| `ELECTRICAL_TOTAL_LOAD_AMPS` | Float | Amperes | R | Charge totale |
| `CIRCUIT_SWITCH_ON:name` | Bool | - | R/W | Circuit actif |
| `CIRCUIT_ON:name` | Bool | - | R | Circuit alimente |

### Avionique

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AVIONICS_MASTER_SWITCH` | Bool | - | R/W | Contact avionique |

---

## 12. Lumieres

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `LIGHT_LANDING` | Bool | - | R/W | Phares atterrissage (switch) |
| `LIGHT_LANDING_ON` | Bool | - | R | Phares allumes |
| `LIGHT_TAXI` | Bool | - | R/W | Phares roulage (switch) |
| `LIGHT_TAXI_ON` | Bool | - | R | Taxi allume |
| `LIGHT_STROBE` | Bool | - | R/W | Strobes (switch) |
| `LIGHT_STROBE_ON` | Bool | - | R | Strobes allumes |
| `LIGHT_NAV` | Bool | - | R/W | Feux navigation (switch) |
| `LIGHT_NAV_ON` | Bool | - | R | Nav allumes |
| `LIGHT_BEACON` | Bool | - | R/W | Beacon (switch) |
| `LIGHT_BEACON_ON` | Bool | - | R | Beacon allume |
| `LIGHT_WING` | Bool | - | R/W | Feux ailes (switch) |
| `LIGHT_WING_ON` | Bool | - | R | Ailes allumes |
| `LIGHT_LOGO` | Bool | - | R/W | Logo (switch) |
| `LIGHT_LOGO_ON` | Bool | - | R | Logo allume |
| `LIGHT_RECOGNITION` | Bool | - | R/W | Feux reconnaissance |
| `LIGHT_PANEL` | Bool | - | R/W | Eclairage panel |
| `LIGHT_PANEL_ON` | Bool | - | R | Panel allume |
| `LIGHT_PANEL_POWER_SETTING` | Float | Percent | R | Intensite panel |
| `LIGHT_CABIN` | Bool | - | R/W | Eclairage cabine |
| `LIGHT_CABIN_ON` | Bool | - | R | Cabine allumee |
| `LIGHT_CABIN_POWER_SETTING` | Float | Percent | R | Intensite cabine |
| `LIGHT_GLARESHIELD` | Bool | - | R/W | Eclairage glareshield |
| `LIGHT_PEDESTRAL` | Bool | - | R/W | Eclairage pedestal |
| `LIGHT_POTENTIOMETER:n` | Float | Percent | R/W | Potentiometre n |
| `LIGHT_ON_STATES` | Mask | - | R | Bitmask tous feux |

---

## 13. Radio et Navigation

### COM

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `COM_ACTIVE_FREQUENCY:n` | Float | MHz | R/W | Frequence COM active |
| `COM_STANDBY_FREQUENCY:n` | Float | MHz | R/W | Frequence COM standby |
| `COM_AVAILABLE:n` | Bool | - | R | COM disponible |
| `COM_TRANSMIT:n` | Bool | - | R/W | Transmission active |
| `COM_RECEIVE:n` | Bool | - | R/W | Reception active |
| `COM_VOLUME` | Float | Percent | R/W | Volume |
| `COM_SPACING_MODE:n` | Enum | - | R/W | 25kHz ou 8.33kHz |
| `COM_STATUS:n` | Enum | - | R | Invalid, OK, no power, failed |

### NAV

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `NAV_ACTIVE_FREQUENCY:n` | Float | MHz | R/W | Frequence NAV active |
| `NAV_STANDBY_FREQUENCY:n` | Float | MHz | R/W | Frequence NAV standby |
| `NAV_OBS:n` | Float | Degrees | R/W | OBS selectionne |
| `NAV_AVAILABLE:n` | Bool | - | R | NAV disponible |
| `NAV_CDI:n` | Float | Number | R | Deviation CDI (-127 a +127) |
| `NAV_GSI:n` | Float | Number | R | Deviation G/S (-119 a +119) |
| `NAV_GS_FLAG:n` | Bool | - | R | Flag glideslope |
| `NAV_DME:n` | Float | NM | R | Distance DME |
| `NAV_RADIAL:n` | Float | Degrees | R | QDR actuel |
| `NAV_RADIAL_ERROR:n` | Float | Degrees | R | Erreur radiale |
| `NAV_TOFROM` | Enum | - | R | OFF, TO, FROM |
| `NAV_HAS_DME` | Bool | - | R | DME disponible |
| `NAV_HAS_LOCALIZER` | Bool | - | R | Localizer dispo |
| `NAV_HAS_GLIDE_SLOPE` | Bool | - | R | Glideslope dispo |
| `NAV_LOCALIZER` | Float | Degrees | R | Axe localizer |
| `NAV_GLIDE_SLOPE` | Float | Number | R | Pente G/S |
| `NAV_GLIDE_SLOPE_ERROR` | Float | Degrees | R | Erreur G/S |
| `NAV_IDENT` | String | - | R | Identifiant station |
| `NAV_NAME` | String | - | R | Nom station |
| `NAV_VOLUME` | Float | Percent | R/W | Volume |

### ADF

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ADF_ACTIVE_FREQUENCY:n` | Float | KHz | R/W | Frequence ADF |
| `ADF_STANDBY_FREQUENCY:n` | Float | KHz | R/W | Standby ADF |
| `ADF_AVAILABLE:n` | Bool | - | R | ADF disponible |
| `ADF_RADIAL:n` | Float | Degrees | R | QDM vers NDB |
| `ADF_SIGNAL:n` | Float | Number | R | Force signal |
| `ADF_IDENT` | String | - | R | Identifiant |
| `ADF_NAME:n` | String | - | R | Nom station |
| `ADF_VOLUME` | Float | Percent | R/W | Volume |

### Marker Beacons

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `OUTER_MARKER` | Bool | - | R | Balise exterieure |
| `MIDDLE_MARKER` | Bool | - | R | Balise mediane |
| `INNER_MARKER` | Bool | - | R | Balise interieure |
| `MARKER_BEACON_STATE` | Enum | - | R/W | None, Outer, Middle, Inner |
| `MARKER_AVAILABLE` | Bool | - | R | Recepteur dispo |

---

## 14. GPS

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GPS_POSITION_LAT` | Float | Degrees | R/W | Latitude GPS |
| `GPS_POSITION_LON` | Float | Degrees | R/W | Longitude GPS |
| `GPS_POSITION_ALT` | Float | Meters | R/W | Altitude GPS |
| `GPS_GROUND_SPEED` | Float | m/s | R | Vitesse sol |
| `GPS_GROUND_TRUE_TRACK` | Float | Radians | R | Route vraie |
| `GPS_GROUND_MAGNETIC_TRACK` | Float | Radians | R | Route magnetique |
| `GPS_GROUND_TRUE_HEADING` | Float | Radians | R | Cap vrai |
| `GPS_WP_DISTANCE` | Float | Meters | R | Distance waypoint |
| `GPS_WP_BEARING` | Float | Radians | R | Relevement waypoint |
| `GPS_WP_ETA` | Float | Seconds | R | ETA waypoint |
| `GPS_ETA` | Float | Seconds | R | ETA destination |
| `GPS_ETE` | Float | Seconds | R | Temps restant |
| `GPS_CDI_NEEDLE` | Float | Number | R | Deviation laterale (-127 a +127) |
| `GPS_CDI_SCALING` | Float | Meters | R/W | Echelle CDI |
| `GPS_GSI_NEEDLE` | Float | Number | R | Deviation verticale |
| `GPS_HAS_GLIDEPATH` | Bool | - | R | Glidepath dispo |
| `GPS_COURSE_TO_STEER` | Float | Radians | R | Cap suggere |
| `GPS_DRIVES_NAV1` | Bool | - | R/W | GPS pilote NAV1 |
| `GPS_IS_ACTIVE_FLIGHT_PLAN` | Bool | - | R | Plan de vol actif |
| `GPS_IS_ARRIVED` | Bool | - | R | Arrive a destination |
| `GPS_FLIGHT_PLAN_WP_COUNT` | Int | - | R | Nombre waypoints |
| `GPS_FLIGHT_PLAN_WP_INDEX` | Int | - | R/W | Waypoint courant |
| `GPS_FLIGHTPLAN_TOTAL_DISTANCE` | Float | Meters | R | Distance totale |
| `GPS_OBS_ACTIVE` | Bool | - | R/W | Mode OBS actif |
| `GPS_OBS_VALUE` | Float | Degrees | R/W | Valeur OBS |
| `GPS_OVERRIDDEN` | Bool | - | R/W | Controle externe GPS |

### Approche GPS

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `GPS_APPROACH_AIRPORT_ID` | String | - | R/W | ICAO aeroport |
| `GPS_APPROACH_APPROACH_ID` | String | - | R/W | ID approche |
| `GPS_APPROACH_APPROACH_TYPE` | Enum | - | R/W | Type (GPS,ILS,VOR,etc.) |
| `GPS_APPROACH_MODE` | Enum | - | R/W | None,Transition,Final,Missed |

---

## 15. Transponder et ATC

### Transponder

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `TRANSPONDER_CODE:n` | Int | BCD16 | R/W | Code transpondeur (0000-7777) |
| `TRANSPONDER_STATE:n` | Enum | - | R/W | Off,Standby,Test,On,Alt,Ground |
| `TRANSPONDER_IDENT:n` | Bool | - | R/W | Ident (18s auto-reset) |
| `TRANSPONDER_AVAILABLE` | Bool | - | R | Transpondeur dispo |

### ATC

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ATC_ID` | String | - | R/W | Immatriculation (max 10) |
| `ATC_AIRLINE` | String | - | R/W | Compagnie (max 50) |
| `ATC_FLIGHT_NUMBER` | String | - | R/W | Numero vol (max 6) |
| `ATC_HEAVY` | Bool | - | R | Categorie Heavy |
| `ATC_CLEARED_IFR` | Bool | - | R | Clearance IFR |
| `ATC_CLEARED_LANDING` | Bool | - | R | Clearance atterrissage |
| `ATC_CLEARED_TAKEOFF` | Bool | - | R | Clearance decollage |
| `ATC_CLEARED_TAXI` | Bool | - | R | Clearance taxi |
| `ATC_ASSIGNED_ALTITUDE` | Float | Feet | R | Altitude assignee |
| `ATC_DESIGNATED_RUNWAY_LANDING` | String | - | R | Piste assignee |
| `ATC_DESIGNATED_RUNWAY_TAKEOFF` | String | - | R | Piste decollage |
| `ATC_RUNWAY_DISTANCE` | Float | Meters | R | Distance piste |
| `ATC_RUNWAY_END_DISTANCE` | Float | Meters | R | Distance fin piste |
| `ATC_RUNWAY_HEADING_DEGREES_TRUE` | Float | Degrees | R | QFU piste |
| `ATC_RUNWAY_LENGTH` | Float | Meters | R | Longueur piste |
| `ATC_RUNWAY_WIDTH` | Float | Meters | R | Largeur piste |
| `ATC_TAXIPATH_DISTANCE` | Float | Meters | R | Distance taxiway |

### TCAS

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `TCAS_MODE` | Int | - | R | 0=STBY, 1=XPNDR, 2=TA ONLY, 3=AUTO |
| `TCAS_INTRUDER_BEARING` | Float | Degrees | R | Relevement intrus |
| `TCAS_INTRUDER_DISTANCE` | Float | NM | R | Distance intrus |
| `TCAS_INTRUDER_RELATIVE_ALTITUDE` | Float | Feet | R | Altitude relative |
| `TCAS_INTRUDER_VERTICAL_SPEED` | Float | ft/s | R | VS intrus |

---

## 16. Instruments

### Altimetre

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `INDICATED_ALTITUDE` | Float | Feet | R/W | Altitude indiquee |
| `INDICATED_ALTITUDE_CALIBRATED` | Float | Feet | R | Alt calibree QNH |
| `KOHLSMAN_SETTING_HG` | Float | inHg | R/W | Calage inHg |
| `KOHLSMAN_SETTING_MB` | Float | mbar | R/W | Calage mbar |
| `KOHLSMAN_SETTING_STD` | Bool | - | R/W | Mode STD |
| `PRESSURE_ALTITUDE` | Float | Meters | R | Altitude pression (1013) |

### Gyroscopes

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `HEADING_INDICATOR` | Float | Radians | R | Conservateur de cap |
| `ATTITUDE_INDICATOR_PITCH_DEGREES` | Float | Radians | R | Horizon artificiel pitch |
| `ATTITUDE_INDICATOR_BANK_DEGREES` | Float | Radians | R | Horizon artificiel bank |
| `TURN_COORDINATOR_BALL` | Float | Position | R | Bille (-127 a +127) |
| `TURN_INDICATOR_RATE` | Float | rad/s | R | Taux de virage |
| `GYRO_DRIFT_ERROR` | Float | Radians | R | Erreur precession |

### Variometre

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `VARIOMETER_RATE` | Float | ft/s | R | Vitesse verticale |
| `VARIOMETER_SWITCH` | Bool | - | R | Switch vario |
| `VARIOMETER_NETTO` | Float | ft/s | R | Vario Netto (planeurs) |
| `VARIOMETER_TOTAL_ENERGY` | Float | ft/s | R | Vario energie totale |
| `VARIOMETER_MAC_CREADY_SETTING` | Float | m/s | R/W | Reglage MacCready |
| `VARIOMETER_SPEED_TO_FLY` | Float | km/h | R | Vitesse optimale |

### Angle d'attaque

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `ANGLE_OF_ATTACK_INDICATOR` | Float | Radians | R | Indicateur AoA |
| `INCIDENCE_ALPHA` | Float | Radians | R | Incidence alpha |
| `INCIDENCE_BETA` | Float | Radians | R | Derapage beta |

---

## 17. Meteo et Environnement

### Temperature et pression

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AMBIENT_TEMPERATURE` | Float | Celsius | R | Temperature exterieure |
| `TOTAL_AIR_TEMPERATURE` | Float | Celsius | R | TAT (avec RAM) |
| `STANDARD_ATM_TEMPERATURE` | Float | Rankine | R | Temperature ISA |
| `SEA_LEVEL_AMBIENT_TEMPERATURE` | Float | Celsius | R | Temperature mer |
| `AMBIENT_PRESSURE` | Float | inHg | R | Pression statique |
| `BAROMETER_PRESSURE` | Float | mbar | R | QNH local |
| `SEA_LEVEL_PRESSURE` | Float | mbar | R | QFF |
| `AMBIENT_DENSITY` | Float | slug/ft³ | R | Densite air |
| `DENSITY_ALTITUDE` | Float | Feet | R | Altitude densite |

### Vent

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AMBIENT_WIND_VELOCITY` | Float | Knots | R | Vitesse vent |
| `AMBIENT_WIND_DIRECTION` | Float | Degrees | R | Direction vent (d'ou) |
| `AMBIENT_WIND_X` | Float | m/s | R | Composante E/O |
| `AMBIENT_WIND_Y` | Float | m/s | R | Composante verticale |
| `AMBIENT_WIND_Z` | Float | m/s | R | Composante N/S |

### Visibilite et precipitations

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `AMBIENT_VISIBILITY` | Float | Meters | R | Visibilite |
| `AMBIENT_PRECIP_STATE` | Mask | - | R | None, Rain, Snow |
| `AMBIENT_PRECIP_RATE` | Float | mm | R | Taux precipitations |
| `AMBIENT_IN_CLOUD` | Bool | - | R | Dans les nuages |
| `AMBIENT_IN_SMOKE` | Bool | - | R | Dans la fumee |
| `ENV_CLOUD_DENSITY` | Float | Percent | R | Densite nuages (0-1) |
| `ENV_SMOKE_DENSITY` | Float | Percent | R | Densite fumee (0-1) |

---

## 18. Hydraulique et Pneumatique

### Hydraulique

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `HYDRAULIC_PRESSURE` | Float | PSF | R/W | Pression hydraulique (legacy) |
| `HYDRAULIC_SYSTEM_INTEGRITY` | Float | Percent | R | Integrite systeme |
| `HYDRAULIC_SWITCH:name` | Bool | - | R/W | Switch pompe |
| `HYDRAULIC_PUMP_ACTIVE:name` | Bool | - | R/W | Pompe active |
| `HYDRAULIC_PUMP_PRESSURE:name` | Float | PSI | R | Pression pompe |
| `HYDRAULIC_RESERVOIR_PERCENT:name` | Float | Percent | R/W | Niveau reservoir |
| `HYDRAULIC_RESERVOIR_QUANTITY:name` | Float | Litres | R/W | Quantite fluide |

### Pneumatique/Pressurisation

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `PRESSURIZATION_CABIN_ALTITUDE` | Float | Feet | R | Altitude cabine |
| `PRESSURIZATION_CABIN_ALTITUDE_GOAL` | Float | Feet | R | Cible altitude cabine |
| `PRESSURIZATION_CABIN_ALTITUDE_RATE` | Float | ft/s | R | Taux changement |
| `PRESSURIZATION_PRESSURE_DIFFERENTIAL` | Float | PSF | R | Differentiel pression |
| `PRESSURIZATION_DUMP_SWITCH` | Bool | - | R | Switch dump |
| `PNEUMATICS_CABIN_ALTITUDE` | Float | Feet | R | Altitude cabine |
| `PNEUMATICS_DIFFERENTIAL_PRESSURE` | Float | PSI | R | Delta P |
| `PNEUMATICS_ENGINE_BLEED_AIR:n` | Bool | - | R | Bleed air moteur |
| `PNEUMATICS_APU_BLEED_AIR` | Bool | - | R | Bleed air APU |
| `PNEUMATICS_PACK_SWITCH:name` | Bool | - | R/W | Pack clim |
| `PNEUMATICS_PACK_STATUS:name` | Bool | - | R | Pack actif |

---

## 19. Avertissements

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `STALL_WARNING` | Bool | - | R | Alarme decrochage |
| `OVERSPEED_WARNING` | Bool | - | R | Alarme survitesse |
| `WARNING_FUEL` | Bool | - | R | Alarme carburant |
| `WARNING_FUEL_LEFT` | Bool | - | R | Alarme fuel gauche |
| `WARNING_FUEL_RIGHT` | Bool | - | R | Alarme fuel droit |
| `WARNING_LOW_HEIGHT` | Bool | - | R | Alarme hauteur |
| `WARNING_OIL_PRESSURE` | Bool | - | R | Alarme pression huile |
| `WARNING_VACUUM` | Bool | - | R | Alarme vacuum |
| `WARNING_VOLTAGE` | Bool | - | R | Alarme tension |
| `GPWS_WARNING` | Bool | - | R | Alarme GPWS active |
| `GPWS_SYSTEM_ACTIVE` | Bool | - | R/W | GPWS actif |

---

## 20. Usure et Maintenance

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `WEAR_AND_TEAR_LEVEL:comp,idx` | Float | Percent | R | Niveau usure composant |
| `WEAR_AND_TEAR_IS_FAILED:comp,idx` | Bool | - | R | Composant en panne |
| `WEAR_AND_TEAR_IS_WEAK:comp,idx` | Bool | - | R | Composant affaibli |
| `WEAR_AND_TEAR_EXPOSED_PARTS_LEVEL` | Float | Percent | R | Usure moyenne |

### IDs composants
- 0-4: Fuel (tank, pump, valve, junction, line)
- 5-20: Controles (flaps, ailerons, elevator, rudder + cables)
- 21-27: Hydraulique
- 28-34: Electrique
- 35-38: Train (gear, brake, tire)
- 39-42: Moteur et huile
- 43-46: Autopilot et general

---

## 21. Etat Simulation

| Variable | Type | Unite | R/W | Description |
|----------|------|-------|-----|-------------|
| `SIM_DISABLED` | Bool | - | R | Simulation desactivee |
| `SIM_ON_GROUND` | Bool | - | R | Au sol |
| `SIMULATION_RATE` | Float | - | R | Vitesse simulation |
| `ABSOLUTE_TIME` | Float | Seconds | R | Temps absolu sim |
| `ZULU_TIME` | Float | Seconds | R | Heure Zulu |
| `LOCAL_TIME` | Float | Seconds | R | Heure locale |
| `IS_SLEW_ACTIVE` | Bool | - | R | Mode slew |
| `IS_SLEW_ALLOWED` | Bool | - | R | Slew autorise |
| `USER_INPUT_ENABLED` | Bool | - | R | Input joueur actif |
| `REALISM` | Float | Percent | R | Niveau realisme |
| `REALISM_CRASH_DETECTION` | Bool | - | R | Crash detection |
| `CRASH_FLAG` | Enum | - | R | Cause crash |
| `CRASH_SEQUENCE` | Enum | - | R | Etat crash |
| `PARACHUTE_OPEN` | Bool | - | R | Parachute ouvert |

---

## 22. Evenements (Key Events)

Les evenements permettent d'ENVOYER des commandes au simulateur.

### Autopilot

| Evenement | Description |
|-----------|-------------|
| `AP_MASTER` | Toggle AP on/off |
| `AP_HDG_HOLD` | Toggle mode HDG |
| `AP_ALT_HOLD` | Toggle mode ALT |
| `AP_VS_HOLD` | Toggle mode VS |
| `AP_NAV1_HOLD` | Toggle mode NAV |
| `AP_APR_HOLD` | Toggle mode APPR |
| `HEADING_BUG_SET` | Definir cap (0-360) |
| `AP_ALT_VAR_SET_ENGLISH` | Definir altitude (feet) |
| `AP_VS_VAR_SET_ENGLISH` | Definir VS (fpm) |
| `AP_SPD_VAR_SET` | Definir vitesse |
| `AUTOPILOT_OFF` | Deconnecter AP |
| `YAW_DAMPER_TOGGLE` | Toggle yaw damper |
| `FLIGHT_LEVEL_CHANGE` | Toggle FLCH |

### Moteurs

| Evenement | Description |
|-----------|-------------|
| `ENGINE_AUTO_START` | Demarrage auto |
| `ENGINE_AUTO_SHUTDOWN` | Arret auto |
| `THROTTLE_SET` | Position gaz (0-16383) |
| `THROTTLE1_SET` | Gaz moteur 1 |
| `MIXTURE_SET` | Richesse (0-16383) |
| `PROPELLER_SET` | Pas helice |
| `TOGGLE_STARTER1` | Demarreur moteur 1 |
| `MAGNETO_OFF` | Magnetos off |
| `MAGNETO_LEFT` | Magneto gauche |
| `MAGNETO_RIGHT` | Magneto droite |
| `MAGNETO_BOTH` | Les deux magnetos |
| `FUEL_PUMP` | Toggle pompe |

### Controles vol

| Evenement | Description |
|-----------|-------------|
| `AILERON_SET` | Ailerons (-16383 a +16383) |
| `ELEVATOR_SET` | Profondeur |
| `RUDDER_SET` | Gouverne |
| `FLAPS_UP` | Volets cran - |
| `FLAPS_DOWN` | Volets cran + |
| `FLAPS_SET` | Volets (0-16383) |
| `SPOILERS_ARM_TOGGLE` | Armer spoilers |
| `SPOILERS_TOGGLE` | Toggle spoilers |
| `GEAR_TOGGLE` | Toggle train |
| `GEAR_UP` | Rentrer train |
| `GEAR_DOWN` | Sortir train |

### Freins

| Evenement | Description |
|-----------|-------------|
| `BRAKES` | Appliquer freins |
| `BRAKES_LEFT` | Frein gauche |
| `BRAKES_RIGHT` | Frein droit |
| `PARKING_BRAKES` | Toggle frein parking |

### Lumieres

| Evenement | Description |
|-----------|-------------|
| `TOGGLE_BEACON_LIGHTS` | Toggle beacon |
| `TOGGLE_NAV_LIGHTS` | Toggle nav |
| `TOGGLE_LANDING_LIGHTS` | Toggle landing |
| `TOGGLE_TAXI_LIGHTS` | Toggle taxi |
| `STROBES_TOGGLE` | Toggle strobes |
| `TOGGLE_WING_LIGHTS` | Toggle wing |
| `TOGGLE_LOGO_LIGHTS` | Toggle logo |
| `PANEL_LIGHTS_TOGGLE` | Toggle panel |
| `CABIN_LIGHTS_SET` | Definir cabine |

### Radio

| Evenement | Description |
|-----------|-------------|
| `COM1_RADIO_SET_HZ` | Frequence COM1 (Hz) |
| `COM1_STBY_RADIO_SET_HZ` | Standby COM1 |
| `COM_RADIO_SWAP` | Swap COM |
| `NAV1_RADIO_SET_HZ` | Frequence NAV1 |
| `NAV1_STBY_SET_HZ` | Standby NAV1 |
| `VOR1_SET` | OBS NAV1 (degrees) |
| `ADF_SET` | Frequence ADF |
| `XPNDR_SET` | Code transpondeur |

### Simulation

| Evenement | Description |
|-----------|-------------|
| `PAUSE_TOGGLE` | Pause |
| `PAUSE_ON` | Activer pause |
| `PAUSE_OFF` | Desactiver pause |
| `SLEW_TOGGLE` | Mode slew |
| `SIM_RATE_INCR` | Accelerer temps |
| `SIM_RATE_DECR` | Ralentir temps |
| `FREEZE_LATITUDE_LONGITUDE_TOGGLE` | Geler position |
| `FREEZE_ALTITUDE_TOGGLE` | Geler altitude |
| `FREEZE_ATTITUDE_TOGGLE` | Geler attitude |

---

## 23. Notes Importantes

### Unites attention!

Malgre leurs noms, ces variables retournent des **RADIANS** :
- `PLANE_PITCH_DEGREES`
- `PLANE_BANK_DEGREES`
- `PLANE_HEADING_DEGREES_TRUE`
- `PLANE_HEADING_DEGREES_MAGNETIC`

### Variables qui NE FONCTIONNENT PAS bien

D'apres nos tests (calibration Janvier 2026) :
- `ON_ANY_RUNWAY` - Retourne souvent NULL
- `CAMERA_STATE` - Retourne souvent NULL
- `SIM_DISABLED` - Pas fiable pour detection menu

### Variables RECOMMANDEES pour detection phases

| Phase | Variables a utiliser |
|-------|---------------------|
| Au sol | `SIM_ON_GROUND`, `GROUND_VELOCITY` |
| Parking | `PLANE_IN_PARKING_STATE`, `BRAKE_PARKING_POSITION` |
| Moteur | `GENERAL_ENG_COMBUSTION:1`, `GENERAL_ENG_RPM:1` |
| Taxi | `GROUND_VELOCITY` > 2kts, `LIGHT_TAXI` |
| Pret decollage | `GENERAL_ENG_THROTTLE_LEVER_POSITION:1` > 80% |
| En vol | `SIM_ON_GROUND` = false |
| Approche | `LIGHT_LANDING`, `GEAR_HANDLE_POSITION`, `ALTITUDE_AGL` |
| Atterri | `SPOILERS_HANDLE_POSITION` > 50% |

### Exemple Python

```python
from SimConnect import SimConnect, AircraftRequests, AircraftEvents

# Connexion
sim = SimConnect()
aq = AircraftRequests(sim, _time=0)
ae = AircraftEvents(sim)

# Lecture variables
altitude = aq.get("PLANE_ALTITUDE")
speed = aq.get("AIRSPEED_INDICATED")
on_ground = aq.get("SIM_ON_GROUND")
throttle = aq.get("GENERAL_ENG_THROTTLE_LEVER_POSITION:1")
beacon = aq.get("LIGHT_BEACON")
parking = aq.get("PLANE_IN_PARKING_STATE")

# Conversion radians -> degres si necessaire
import math
heading_rad = aq.get("PLANE_HEADING_DEGREES_TRUE")
heading_deg = math.degrees(heading_rad) if heading_rad else 0

# Envoi evenements
ae.find("AP_MASTER")()  # Toggle AP
ae.find("HEADING_BUG_SET")(180)  # Cap 180
ae.find("AP_ALT_VAR_SET_ENGLISH")(5000)  # Alt 5000ft
ae.find("TOGGLE_BEACON_LIGHTS")()  # Toggle beacon
```

---

## Sources

- [MSFS 2024 SDK - SimVars](https://docs.flightsimulator.com/msfs2024/html/6_Programming_APIs/SimVars/Simulation_Variables.htm)
- [MSFS 2024 SDK - Key Events](https://docs.flightsimulator.com/msfs2024/html/6_Programming_APIs/Key_Events/Key_Events.htm)
- [Python-SimConnect](https://pypi.org/project/SimConnect/)
- [MSFS Universal Announcer - State Machine](https://fearlessfrog.github.io/MSFS_Universal_Announcer/statemachine.html)
- [FlyByWire A32NX SimVars](https://github.com/flybywiresim/aircraft/blob/master/fbw-a32nx/docs/a320-simvars.md)

---

*Document genere automatiquement - Referentiel V2 Mission Generator MSFS 2024*
