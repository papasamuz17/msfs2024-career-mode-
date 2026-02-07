# MSFS 2024 Mission Generator & AI Copilot V2

Un generateur de missions et copilote IA pour Microsoft Flight Simulator 2024.

## Fonctionnalites

### Mission Generator
- Generation automatique de missions entre aeroports
- Integration meteo en temps reel (METAR)
- Export de plans de vol (.pln) compatibles MSFS
- Systeme de scoring et recompenses

### AI Copilot
- Callouts vocaux automatiques (altitudes, vitesses, phases de vol)
- Detection d'erreurs pilote (sink rate, overspeed, stall)
- Checklists interactives
- Commandes vocales (Push-to-Talk)
- Assistant IA conversationnel (Groq API)

### Systeme de Carriere
- Progression de licence (Student -> PPL -> CPL -> ATPL)
- Heures de vol par categorie d'avion
- Systeme de reputation avec compagnies
- Logbook automatique
- Statistiques detaillees

### Landing Challenge
- Entrainement au tour de piste
- Scoring des decollages et atterrissages
- Modes: Butter, Short Field, Crosswind, Night

## Installation

### Pre-requis
- Python 3.10+
- Microsoft Flight Simulator 2024
- SimConnect

### Installation des dependances
```bash
pip install -r requirements.txt
```

### Lancement
```bash
python main_v2.py
```

### Version compilee
Telecharger la derniere release dans `dist/MSFS_Copilot_V2/`

## Configuration

### API Keys (optionnel)
- **Groq API** : Pour l'assistant IA et la reconnaissance vocale
- **OpenAIP API** : Pour les donnees aeronautiques enrichies

### Microphone
Le microphone prefere est sauvegarde automatiquement.

### Push-to-Talk
Configurable via l'interface (joystick + bouton).

## Structure du projet

```
v2/
├── main_v2.py           # Application principale
├── career/              # Systeme de carriere
│   ├── pilot_profile.py
│   ├── companies.py
│   ├── logbook.py
│   └── progression.py
├── copilot/             # AI Copilot
│   ├── phases.py        # Detection phases de vol
│   ├── callouts.py      # Callouts vocaux
│   ├── voice.py         # TTS/STT
│   ├── llm.py           # Assistant IA
│   └── checklists.py
├── systems/             # Systemes de jeu
│   ├── fuel.py
│   ├── maintenance.py
│   ├── passengers.py
│   └── pattern_training.py
├── optimization/        # Performance
│   └── simconnect_opt.py
├── sounds/              # Fichiers audio
├── airports.json        # Base de donnees aeroports
└── config.json          # Configuration utilisateur
```

## Auteur

PAPA_SAMUZ

## Licence

MIT License
