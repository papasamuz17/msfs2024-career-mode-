# MSFS 2024 Mission Generator - Features V1

*Version 1.0 - Janvier 2026*

---

## RÉSUMÉ

Application de génération de missions pour Microsoft Flight Simulator 2024 avec :
- Connexion SimConnect temps réel
- Génération de missions aléatoires mondiales
- Système de rémunération pilote réaliste
- Interface moderne Dark Mode

---

## FONCTIONNALITÉS IMPLÉMENTÉES

---

### 1. CONNEXION SIMCONNECT

**Description:** Connexion au simulateur MSFS 2024 via la bibliothèque Python-SimConnect.

**Caractéristiques:**
- Connexion asynchrone (non-bloquante)
- Reconnexion automatique si le sim n'est pas lancé
- Lecture des données avion en temps réel (1 Hz)

**Données lues:**
| Variable | Description |
|----------|-------------|
| PLANE_ALTITUDE | Altitude MSL (ft) |
| PLANE_ALT_ABOVE_GROUND | Altitude AGL (ft) |
| PLANE_BANK_DEGREES | Inclinaison (°) |
| VERTICAL_SPEED | Vitesse verticale (fpm) |
| AIRSPEED_INDICATED | Vitesse indiquée (kts) |
| PLANE_LATITUDE | Latitude |
| PLANE_LONGITUDE | Longitude |
| GROUND_VELOCITY | Vitesse sol (kts) |
| ENG_COMBUSTION:1 | État moteur 1 |
| TITLE | Nom de l'avion |
| ENGINE_TYPE | Type moteur (Piston/Jet/Turboprop) |
| NUMBER_OF_ENGINES | Nombre de moteurs |

---

### 2. DÉTECTION AUTOMATIQUE DE L'AVION

**Description:** Identification automatique du type d'avion et de sa catégorie.

**Catégories supportées:**
| Catégorie | Exemples | Détection |
|-----------|----------|-----------|
| light_piston | Cessna 172, PA-28 | ENGINE_TYPE=0, 1 moteur |
| twin_piston | Baron, DA62 | ENGINE_TYPE=0, 2+ moteurs |
| single_turboprop | TBM, PC-12 | ENGINE_TYPE=5, 1 moteur |
| turboprop | King Air, ATR | ENGINE_TYPE=5, 2+ moteurs |
| light_jet | Citation, Phenom | ENGINE_TYPE=1, 1-2 moteurs |
| jet | A320, 737 | ENGINE_TYPE=1, 2 moteurs |
| heavy_jet | 747, A380 | ENGINE_TYPE=1, 4 moteurs ou mots-clés |
| helicopter | Tous hélicos | ENGINE_TYPE=3 |

**Mise à jour:** Toutes les 30 secondes pour détecter changement d'avion.

---

### 3. BASE DE DONNÉES AÉROPORTS MONDIALE

**Description:** Téléchargement dynamique de la base OurAirports.

**Source:** `https://davidmegginson.github.io/ourairports-data/airports.csv`

**Caractéristiques:**
- ~4918 aéroports avec pistes asphaltées > 2000ft
- Filtrage : grands et moyens aéroports uniquement
- Données : ICAO, nom, latitude, longitude, élévation

**Critères de filtrage:**
```
- type IN ('large_airport', 'medium_airport')
- surface_type contient 'ASP' ou 'CON' (asphalte/béton)
- longueur piste >= 2000 ft
```

---

### 4. MÉTÉO TEMPS RÉEL (METAR)

**Description:** Récupération des METAR réels via l'API NOAA.

**Source:** `https://aviationweather.gov/api/data/metar`

**Données extraites:**
- Direction du vent (°)
- Vitesse du vent (kts)
- Rafales (si présentes)
- Visibilité (SM)

**Utilisation:**
- Calcul de la piste optimale
- Détection mauvaise météo (bonus pilote)
- Affichage dans l'interface

---

### 5. SÉLECTION AUTOMATIQUE DES PISTES

**Description:** Calcul de la piste optimale selon le vent.

**Source pistes:** `https://davidmegginson.github.io/ourairports-data/runways.csv`

**Algorithme:**
1. Récupérer le METAR de l'aéroport
2. Extraire direction et vitesse du vent
3. Pour chaque piste, calculer :
   - Composante de face (headwind)
   - Composante de travers (crosswind)
4. Sélectionner la piste avec le meilleur headwind

**Formules:**
```
angle_diff = wind_direction - runway_heading
headwind = wind_speed * cos(angle_diff)
crosswind = wind_speed * sin(angle_diff)
```

**Affichage:** "RWY 27L | Vent: 280/15kt (face 14kt, travers 4kt)"

---

### 6. GÉNÉRATION DE ROUTES IA (GROQ)

**Description:** Génération de waypoints réalistes via l'API Groq (LLaMA 3.3 70B).

**Fonctionnement:**
1. Charger les navaids proches de la route (VOR, intersections)
2. Envoyer prompt à Groq avec :
   - Type d'avion et caractéristiques
   - Aéroports départ/arrivée
   - Distance et altitude de croisière
3. Recevoir liste de waypoints JSON
4. Valider et intégrer au plan de vol

**Fallback:** Si Groq indisponible, génération locale avec navaids.json

**Base navaids:** 36 VORs + 35 intersections européennes

---

### 7. GÉNÉRATION FICHIERS PLN

**Description:** Création de plans de vol au format MSFS (.pln).

**Contenu du fichier:**
- En-tête XML MSFS compatible
- Aéroport de départ avec piste
- Waypoints intermédiaires (User/VOR/Intersection)
- Aéroport d'arrivée avec piste
- Type de vol (VFR/IFR)
- Altitude de croisière

**Copie automatique:** Option pour copier vers le dossier MSFS :
```
%APPDATA%\Microsoft Flight Simulator 2024\MISSIONS\Custom\
```

---

### 8. CALCUL ALTITUDE DE CROISIÈRE

**Description:** Altitude optimale selon distance et type d'avion.

**Table:**
| Distance | Altitude base |
|----------|---------------|
| < 50 nm | 5 000 ft |
| 50-100 nm | 8 000 ft |
| 100-200 nm | 12 000 ft |
| 200-350 nm | 18 000 ft |
| 350-500 nm | 24 000 ft |
| > 500 nm | 32 000 ft |

**Plafonds par catégorie:**
| Catégorie | Plafond |
|-----------|---------|
| light_piston | 12 000 ft |
| twin_piston | 20 000 ft |
| single_turboprop | 28 000 ft |
| turboprop | 31 000 ft |
| light_jet | 45 000 ft |
| jet | 41 000 ft |
| heavy_jet | 43 000 ft |
| helicopter | 10 000 ft |

---

### 9. SYSTÈME DE CONTRAINTES

**Description:** Contraintes de vol aléatoires à respecter.

**Types de contraintes:**
| Type | Exemples | Difficultés |
|------|----------|-------------|
| bank | Inclinaison max 25/30/35° | Facile à Difficile |
| altitude_min | Altitude min 1000/1500 ft | Facile à Normal |
| altitude_max | Altitude max 10000 ft | Facile |
| speed_max | Vitesse max 250/280 kts | Facile à Normal |
| vs_max | VS max 700/1000 fpm | Facile à Normal |

**Système de difficulté:**
- Facile : pondération x3
- Normal : pondération x2
- Difficile : pondération x1

---

### 10. PROGRESSION DE MISSION

**Description:** Suivi en temps réel de l'avancement du vol.

**Calcul:**
```
progress = (distance_parcourue / distance_totale) * 100
```

**Détection état:**
- Au parking : AGL < 10ft ET vitesse < 15kts
- En vol : AGL > 20ft ET vitesse > 10kts (OU AGL > 100ft)
- Décollage : première transition sol → vol

**Affichage:**
- Barre de progression 0-100%
- Distance restante en nm
- Statut textuel (Au parking / En vol / Au sol)

**Couleurs:**
- Bleu : au parking, prêt
- Vert : en vol
- Orange : au sol en route

---

### 11. DÉTECTION FIN DE MISSION

**Description:** Détection automatique de l'arrivée au parking.

**Conditions (toutes requises):**
1. Mission démarrée (décollage effectué)
2. Distance à l'arrivée < 5 nm
3. Altitude AGL < 10 ft
4. Vitesse < 15 kts
5. Vitesse sol < 2 kts (arrêté)
6. Moteur coupé (ENG_COMBUSTION = false)

---

### 12. SYSTÈME DE RÉMUNÉRATION PILOTE

**Description:** Calcul réaliste du salaire pilote.

#### Tarifs horaires
| Catégorie | Tarif |
|-----------|-------|
| light_piston | 55 €/h |
| twin_piston | 75 €/h |
| single_turboprop | 95 €/h |
| turboprop | 120 €/h |
| light_jet | 150 €/h |
| jet | 200 €/h |
| heavy_jet | 280 €/h |
| helicopter | 85 €/h |

#### Indemnités (Per Diem)
| Durée vol | Indemnité |
|-----------|-----------|
| < 2h | 35 € |
| 2-5h | 65 € |
| > 5h | 120 € |

#### Bonus
| Condition | Bonus |
|-----------|-------|
| Vol de nuit (21h-6h) | +25% du salaire |
| Week-end | +15% du salaire |
| Mauvaise météo (visi < 3 SM) | +20% du salaire |
| Atterrissage parfait (< 100 fpm) | +50 € |
| Bon atterrissage (100-200 fpm) | +25 € |
| Contraintes respectées | +30 € |

#### Pénalités
| Infraction | Pénalité |
|------------|----------|
| Atterrissage dur (300-500 fpm) | -50 € |
| Atterrissage très dur (> 500 fpm) | -150 € |
| Violation de contrainte | -10 € par violation |
| Survitesse | -25 € |

#### Fiche de paie
Affichage détaillé en fin de mission :
- Temps de vol
- Salaire de base
- Per diem
- Détail des bonus
- Détail des pénalités
- Total

---

### 13. COMPTE EN BANQUE PILOTE

**Description:** Solde persistant du pilote.

**Caractéristiques:**
- Solde initial : 100 €
- Sauvegarde automatique dans `savegame.json`
- Affichage vert si positif, rouge si négatif
- Compteur de missions accomplies

---

### 14. INTERFACE UTILISATEUR

**Description:** Interface graphique moderne avec CustomTkinter.

**Thème:** Dark Mode

**Sections:**
1. **Header** - Compte en banque + statistiques
2. **Status** - État connexion SimConnect
3. **Bouton** - Génération de mission
4. **Mission** - Détails du vol (départ, arrivée, pistes, vent)
5. **Progression** - Barre + pourcentage + distance restante
6. **Contrainte** - Contrainte active avec difficulté
7. **Données avion** - Alt, Bank, VS, Speed en temps réel
8. **Configuration PLN** - Dossier destination + copie auto
9. **Groq API** - Clé API pour routes IA
10. **Boutons** - Reset score, Sauvegarder config

**Dimensions:** 800x900 pixels, redimensionnable (min 750x800)

---

### 15. SYSTÈME AUDIO

**Description:** Sons de feedback via Pygame.

**Sons:**
| Fichier | Événement |
|---------|-----------|
| mission.wav | Nouvelle mission générée |
| success.wav | Mission réussie / bon atterrissage |
| penalty.wav | Violation de contrainte |
| crash.wav | Atterrissage très dur |

**Dossier:** `sounds/`

---

### 16. CONFIGURATION PERSISTANTE

**Description:** Sauvegarde des préférences utilisateur.

**Fichier:** `config.json`

**Paramètres:**
- `pln_destination_folder` : Dossier export PLN
- `groq_api_key` : Clé API Groq
- `auto_copy_pln` : Copie automatique activée

---

### 17. SYSTÈME DE LOGGING

**Description:** Journalisation complète des événements.

**Fichier:** `logs/mission_generator_YYYYMMDD_HHMMSS.log`

**Niveaux:**
- DEBUG : Détails techniques (connexions HTTP, calculs)
- INFO : Événements importants (mission, détection avion)
- WARNING : Problèmes non-bloquants
- ERROR : Erreurs

**Format:** `HH:MM:SS | LEVEL | Message`

---

### 18. SAUVEGARDE PERSISTANTE

**Description:** Sauvegarde de la progression du joueur.

**Fichier:** `savegame.json`

**Contenu:**
```json
{
  "score": 1234.56,
  "missions_completed": 42,
  "best_landing": 0
}
```

**Sauvegarde automatique:**
- À chaque fin de mission
- À la fermeture de l'application

---

## FICHIERS DE L'APPLICATION

| Fichier | Description |
|---------|-------------|
| `main.py` | Application principale (~1750 lignes) |
| `aviation_api.py` | Module API aviation (METAR, aéroports, pistes) |
| `navaids.json` | Base de données VOR/intersections |
| `airports.json` | Aéroports locaux de fallback |
| `config.json` | Configuration utilisateur |
| `savegame.json` | Sauvegarde progression |
| `logs/` | Dossier des logs |
| `sounds/` | Dossier des sons |
| `flightplans/` | Dossier des PLN générés |

---

## DÉPENDANCES

| Package | Version | Usage |
|---------|---------|-------|
| customtkinter | >= 5.0 | Interface graphique |
| Python-SimConnect | >= 0.5 | Connexion MSFS |
| pygame | >= 2.0 | Sons |
| requests | >= 2.0 | API HTTP |
| groq | >= 0.4 | API Groq (optionnel) |

---

## COMPATIBILITÉ

- **OS:** Windows 10/11
- **Simulateur:** Microsoft Flight Simulator 2024
- **Python:** 3.10+

---

*Document généré le 25/01/2026*
