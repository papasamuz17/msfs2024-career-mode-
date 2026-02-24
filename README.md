# MSFS 2024 — Mode Carriere & Copilote IA

Un mode carriere complet et un copilote IA vocal pour Microsoft Flight Simulator 2024.
Genere des missions, suit ta progression de pilote, et t'assiste en vol avec une vraie voix.

**Chaine YouTube** : [PAPA_SAMUZ](https://www.youtube.com/@papasamuz) — *L'IA code, je branche.*

---

## Telecharger

**[Telecharger la derniere version](https://github.com/papasamuz17/msfs2024-career-mode-/releases)**

> Aucune installation requise. Telecharge, extrait, lance.

---

## Installation (2 minutes)

1. **Telecharger** le ZIP depuis la page [Releases](https://github.com/papasamuz17/msfs2024-career-mode-/releases)
2. **Extraire** le ZIP dans un dossier de ton choix
3. **Copier** `config.template.json` et le renommer en `config.json`
4. **Lancer** `MSFS_Copilot_V2.exe`
5. **Lancer** MSFS 2024 — le programme se connecte automatiquement via SimConnect

C'est tout.

### Configuration

Le fichier `config.json` fonctionne tel quel avec les valeurs par defaut.
Pour activer les fonctions avancees, ajoute tes cles API :

| Cle | Service | Gratuit ? | Sert a... |
|-----|---------|-----------|-----------|
| `groq_api_key` | [Groq](https://console.groq.com/) | Oui | Copilote IA conversationnel + reconnaissance vocale |
| `openaip_api_key` | [OpenAIP](https://www.openaip.net/) | Oui | Donnees aeronautiques enrichies |

> Sans cles API, le generateur de missions, le mode carriere, les pannes, le carburant et la maintenance fonctionnent normalement. Seuls le copilote vocal et les donnees aero enrichies necessitent des cles.

### Options de configuration

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

## Configuration requise

- Windows 10/11
- Microsoft Flight Simulator 2024
- ~50 Mo d'espace disque

---

## Un probleme ? Une idee ?

Ouvre une [Issue](https://github.com/papasamuz17/msfs2024-career-mode-/issues) ou laisse un commentaire sur la chaine YouTube.

---

## Licence

**Ce programme est gratuit et doit le rester.**

Tu peux l'utiliser, le partager, en faire ce que tu veux — mais tu ne peux pas le revendre, ni sous sa forme actuelle, ni en le repackageant. Si quelqu'un te demande de payer pour ce programme, c'est une arnaque.

---

## Remerciements

Merci a la communaute MSFS et aux abonnes de la chaine qui ont rendu ce projet possible.
Ce projet est ne du vibecoding : coder pour le plaisir, sans deadline, sans client, juste l'envie de creer.

*PAPA_SAMUZ — L'IA code, je branche.*
