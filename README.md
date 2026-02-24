# MSFS 2024 — Mode Carriere & Copilote IA

Un mode carriere complet et un copilote IA vocal pour Microsoft Flight Simulator 2024.
Genere des missions, suit ta progression de pilote, et t'assiste en vol avec une vraie voix.

**Chaine YouTube** : [PAPA_SAMUZ](https://www.youtube.com/@papasamuz) — *L'IA code, je branche.*

---

## Installation rapide (executable)

> Aucune installation Python requise. Double-clic et c'est parti.

1. **Telecharger** la derniere [Release](https://github.com/TonyCorroenne/msfs2024-career-mode-/releases)
2. **Extraire** le ZIP dans un dossier de ton choix
3. **Copier** `config.template.json` et le renommer en `config.json`
4. **Lancer** `MSFS_Copilot_V2.exe`
5. **Lancer** MSFS 2024 — le programme se connecte automatiquement via SimConnect

C'est tout. Temps d'installation : ~2 minutes.

### Configuration minimale

Le fichier `config.json` fonctionne tel quel avec les valeurs par defaut.
Pour activer les fonctions avancees, ajoute tes cles API :

| Cle | Service | Gratuit ? | Sert a... |
|-----|---------|-----------|-----------|
| `groq_api_key` | [Groq](https://console.groq.com/) | Oui | Copilote IA conversationnel + reconnaissance vocale |
| `openaip_api_key` | [OpenAIP](https://www.openaip.net/) | Oui | Donnees aeronautiques enrichies |

> Sans cles API, le generateur de missions, le mode carriere, les pannes, le carburant et la maintenance fonctionnent normalement. Seuls le copilote vocal et les donnees aero enrichies necessitent des cles.

---

## Installation depuis les sources (developpeurs)

### Pre-requis
- Python 3.10+
- Microsoft Flight Simulator 2024 avec SimConnect

### Etapes

```bash
# Cloner le repo
git clone https://github.com/TonyCorroenne/msfs2024-career-mode-.git
cd msfs2024-mission-generator

# Installer les dependances
pip install -r requirements.txt

# Configurer
copy config.template.json config.json
# Editer config.json avec tes cles API (optionnel)

# Lancer (V2)
python v2/main_v2.py
```

### Compiler l'executable soi-meme

```bash
pip install pyinstaller
pyinstaller MSFS_Copilot_V2.spec
# L'exe sera dans dist/MSFS_Copilot_V2/
```

---

## Fonctionnalites

### Generateur de missions
- Missions aleatoires entre aeroports du monde entier
- Meteo reelle (METAR) integree
- Calcul automatique de la piste optimale (vent)
- Plans de vol `.pln` compatibles MSFS
- Waypoints generes par IA (Groq) ou base locale (navaids)

### Mode Carriere
- Progression : Student → PPL (40h) → CPL (200h) → ATPL (1500h)
- 8+ categories d'avions avec restrictions de licence
- Salaire realiste (55-280 EUR/h selon categorie)
- Check-rides (examens en vol) avec criteres mesurables
- Systeme de compagnies aeriennes avec reputation (x0.8 a x1.5)
- Logbook automatique exportable en CSV

### Copilote IA vocal
- 18 phases de vol detectees automatiquement
- Callouts : V1, Rotate, altitudes (500, 100, 50, 30, 20, 10 ft)
- Detection d'erreurs : survitesse, decrochage, approche instable, givrage
- Checklists interactives lues a voix haute
- Simulation ATC avec phraseologie realiste
- Assistant conversationnel (Groq LLM) — pose des questions en vol
- Debriefing vocal automatique apres chaque vol

### Systemes de simulation
- **Carburant** : consommation reelle lue via SimConnect, cout deduit du salaire
- **Pannes aleatoires** : 11 types (moteur, electrique, hydraulique, pitot, GPS...)
- **Maintenance** : usure progressive, cout de reparation
- **Confort passagers** : G-force, turbulence, taux de descente
- **Meteo** : lecture temps reel des conditions SimConnect

### Challenges d'atterrissage
- 8 types : Butter, Short Field, Crosswind, Night, Low Visibility, Gusty, Mountain, Carrier
- 4 niveaux de difficulte
- Scoring detaille (vitesse verticale, axe de piste, point de toucher)
- Notes : S / A / B / C / D / F

### Enregistrement de vol
- Export trajectoire en KML (Google Earth), GPX et JSON
- Statistiques : distance, altitude max, vitesse max
- Replay 3D dans Google Earth

---

## Structure du projet

```
├── main.py                  # V1 (legacy)
├── v2/
│   ├── main_v2.py           # Application principale V2
│   ├── career/              # Systeme de carriere (4 modules)
│   ├── copilot/             # Copilote IA (8 modules)
│   ├── systems/             # Pannes, fuel, maintenance (8 modules)
│   ├── optimization/        # Performance et cache (5 modules)
│   ├── utils/               # Outils (distance, flight recorder)
│   ├── airports.json        # Base de donnees aeroports
│   ├── navaids.json         # VOR et intersections
│   └── config.template.json # Template de configuration
├── config.template.json     # Template de configuration (racine)
├── requirements.txt         # Dependances Python
└── LICENSE                  # MIT
```

---

## Configuration complete

```json
{
  "pln_destination_folder": "",          // Dossier export plans de vol (auto-detecte si vide)
  "groq_api_key": "",                    // Cle API Groq (optionnel)
  "openaip_api_key": "",                 // Cle API OpenAIP (optionnel)
  "auto_copy_pln": true,                 // Copie auto des plans vers MSFS
  "copilot_enabled": true,               // Activer le copilote IA
  "voice_enabled": true,                 // Activer la synthese vocale
  "voice_language": "fr-FR",             // Langue (fr-FR ou en-US)
  "career_mode": true,                   // Activer le mode carriere
  "performance_mode": "balanced",        // powersaver / balanced / performance
  "fuel_management": true,               // Gestion carburant
  "maintenance_enabled": true,           // Usure et maintenance
  "passenger_comfort": true,             // Confort passagers
  "relaxed_mode": false,                 // Mode detendu (moins de penalites)
  "ptt_enabled": false,                  // Push-to-Talk
  "ptt_joystick_id": 0,                  // ID joystick pour PTT
  "ptt_button_id": 0,                    // ID bouton pour PTT
  "mission_distance_min": 50,            // Distance min mission (nm)
  "mission_distance_max": 500,           // Distance max mission (nm)
  "preferred_microphone": ""             // Micro prefere (auto si vide)
}
```

---

## Contribuer

Les contributions sont les bienvenues !

- **Bug** : ouvre une [Issue](https://github.com/TonyCorroenne/msfs2024-career-mode-/issues)
- **Feature request** : ouvre une Issue avec le tag `enhancement`
- **Code** : fork, branche, pull request

---

## Licence

MIT — fais ce que tu veux avec, c'est cadeau.

---

## Remerciements

Merci a la communaute MSFS et aux abonnes de la chaine qui ont rendu ce projet possible.
Ce projet est ne du vibecoding : coder pour le plaisir, sans deadline, sans client, juste l'envie de creer.

*PAPA_SAMUZ — L'IA code, je branche.*
