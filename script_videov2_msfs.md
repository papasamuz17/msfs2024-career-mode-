# SCRIPT VIDEO - MSFS 2024 Mission Generator V2

> **Chaine** : PAPA SAMUZ
> **Duree cible** : 8-12 minutes
> **Format** : Screen capture + voix off
> **Ton** : Mix serieux / enthousiaste
> **Suite de** : Video V1 (virale)

---

## HOOK (0:00 - 0:45)

**[SCREEN : Plan large cockpit MSFS, vol en croisiere, ambiance calme]**

*"Il y a quelques semaines, je vous ai montre un programme que j'ai code pour corriger ce qui manque a Flight Simulator 2024. Un generateur de missions, avec du scoring, un salaire de pilote... un truc simple mais efficace."*

**[SCREEN : Montage rapide de commentaires/stats de la V1 - vues, likes, commentaires enthousiastes]**

*"Et vous avez completement pete les scores. Cette video a explose. Et dans les commentaires, vous etiez beaucoup a me demander le programme."*

**[SCREEN : Le programme V2 s'ouvre, interface sombre, on voit deja que c'est different]**

*"Alors j'ai fait mieux que de vous le partager. Je l'ai entierement reconstruit. De 1 700 lignes de code... on est passe a plus de 31 000. Voici la Version 2."*

**[OVERLAY : `01_anim_hook_intro.webm` - Compteur de lignes + titre V2]**

**[TITRE ANIME / TRANSITION]**

---

## PARTIE 1 - RAPPEL EXPRESS V1 (0:45 - 1:30)

*"Petit rappel pour ceux qui debarquent. Le concept de base c'est simple : le programme se connecte a Flight Simulator en temps reel via SimConnect. Il detecte ton avion, genere une mission aleatoire avec un aeroport de depart et d'arrivee, il calcule la piste optimale en fonction de la meteo reelle, il te genere un plan de vol avec des waypoints via l'IA, et a la fin du vol, il te donne un salaire en fonction de ta performance."*

**[SCREEN : Demo rapide V1 - generation mission, vol, scoring - en accelere]**

*"Ca marchait. C'etait fun. Mais c'etait un prototype. La V2... c'est un autre monde."*

---

## PARTIE 2 - LE MODE CARRIERE (1:30 - 3:30)

**[SCREEN : Onglet carriere du programme V2]**
**[OVERLAY : `02_anim_carriere.webm` - Timeline des licences + progression]**

*"Premier gros ajout : un vrai mode carriere. Tu commences avec une licence etudiant, 100 euros en poche, et tu dois gravir les echelons."*

**[SCREEN : Arbre de progression - licences PPL, CPL, ATPL]**

*"PPL a 40 heures de vol, CPL a 200 heures, et l'ATPL... 1 500 heures. Chaque licence debloque de nouveaux avions et de nouveaux taux horaires. En student tu gagnes des miettes. En ATPL sur un long-courrier, tu peux monter a 280 euros de l'heure."*

*"Et pour monter en grade, il faut passer des check-rides. De vrais examens en vol, avec des criteres precis a respecter. Si tu rates, tu paies quand meme les frais d'examen."*

**[SCREEN : Interface check-ride en cours - on voit les criteres en temps reel]**

*"T'as aussi un systeme de compagnies aeriennes. Chacune a sa reputation, ses hubs, ses avions preferes. Plus ta reputation est haute, meilleur est le multiplicateur de salaire. Tu peux monter jusqu'a x1.5... ou te faire blacklister si tu voles comme un manche."*

---

## PARTIE 3 - LE COPILOTE IA (3:30 - 5:30)

**[SCREEN : Vol en cours, on entend soudain une voix synthetique]**
**[Voix copilote : "V1... Rotate... Positive climb, gear up."]**
**[OVERLAY : `03_anim_copilote.webm` - Panneau copilote avec features]**

*"La. Vous entendez ca. Le programme a maintenant un copilote. Un copilote IA avec une vraie voix."*

**[SCREEN : Decollage complet avec les callouts automatiques]**

*"Il fait les annonces standard : V1, Rotate, les altitudes, les checks d'approche... 500 pieds, 100 pieds, 50, 30, 20, 10. Tout est automatique, base sur la telemetrie reelle du simulateur."*

*"Mais c'est pas juste un perroquet. Il detecte aussi tes erreurs."*

**[SCREEN : Alerte du copilote - overspeed ou approche instable]**

*"Survitesse, decrochage imminent, train non sorti en approche, givrage... il te previent. Et si tu veux lui poser une question en plein vol, tu peux. Il est connecte a un LLM via Groq, il connait ta position, ta vitesse, ta phase de vol. Tu lui parles au micro, il te repond vocalement."*

**[SCREEN : Demo interaction vocale avec le copilote]**

*"Il y a meme des checklists interactives qu'il te lit a voix haute et qu'il verifie automatiquement via SimConnect. Before takeoff, approach, landing... tout y est."*

---

## PARTIE 4 - REALISME : CARBURANT, MAINTENANCE, PANNES (5:30 - 7:30)

**[OVERLAY : `04_anim_systemes.webm` - Panneaux fuel/maintenance/pannes]**

*"Mais la ou ca devient vraiment serieux, c'est quand on parle des systemes."*

**[SCREEN : Panneau fuel du programme]**

*"Le carburant est maintenant simule. Le programme lit ta consommation reelle en gallons par heure. A la fin du vol, le cout est deduit de ton salaire. AvGas a 6,50 le litre, Jet-A1 a 4,50. Ca pique sur les gros porteurs."*

**[SCREEN : Panneau maintenance - usure de l'avion]**

*"Ton avion s'use. Chaque heure de vol accumule de l'usure, et ca depend de comment tu voles. Tu tires sur les moteurs, tu fais des atterrissages durs, ca s'use plus vite. Et quand l'usure est trop elevee... tu paies la maintenance. Inspection, reparation, revision complete."*

**[SCREEN : Alerte panne en vol - le moteur a un probleme]**

*"Et le meilleur pour la fin : les pannes aleatoires. 11 types de pannes possibles. Moteur, electrique, hydraulique, givrage, instruments... Elles peuvent arriver n'importe quand, avec une probabilite plus elevee au decollage et en approche. Exactement comme dans la vraie vie."*

*"Tu te retrouves en finale avec une panne electrique partielle... crois-moi, ton salaire a la fin du vol, tu l'as merite."*

---

## PARTIE 5 - LES EXTRAS (7:30 - 9:00)

**[OVERLAY : `05_anim_extras.webm` - Montage des features bonus]**

*"Et j'ai meme pas parle de tout. Il y a un systeme de passagers : si tu voles comme un bourrin, les passagers sont malades, et ca impacte ton salaire. G-forces, virages brutaux, taux de descente trop eleve... tout est pris en compte."*

*"Il y a un logbook automatique qui enregistre chaque vol : duree, distance, performance, note d'atterrissage. Exportable en CSV."*

*"Des challenges d'atterrissage dedies : butter landing, terrain court, vent de travers, atterrissage de nuit... chacun avec son propre scoring."*

*"Et tu peux exporter ta trajectoire de vol en KML pour Google Earth ou en GPX. Tu revois ton vol en 3D apres coup."*

**[SCREEN : Trajectoire de vol dans Google Earth]**

---

## PARTIE 6 - PERFORMANCE ET CONCLUSION (9:00 - 10:30)

**[OVERLAY : `06_anim_comparatif.webm` - Tableau V1 vs V2]**

*"Un dernier point important : j'ai aussi completement optimise le programme. La V1 consommait pas mal de ressources. La V2 a un systeme de polling adaptatif. Quand t'es en croisiere, il interroge le simulateur toutes les 2 secondes. En approche, toutes les 250 millisecondes. L'utilisation memoire a ete reduite de 90% grace a un index spatial pour les aeroports. Bref, ca tourne en tache de fond sans plomber tes FPS."*

**[SCREEN : Vol en cours, tout fonctionne, interface propre]**

*"En gros, la V1 c'etait un generateur de missions. La V2, c'est une carriere de pilote complete, avec un copilote qui te parle, des avions qui s'usent, des pannes qui te surprennent, et un vrai sentiment de progression."*

*"La question que vous me posez tous : est-ce que je vais partager le programme ? J'y reflechis serieusement. Si cette video performe aussi bien que la premiere, je pense qu'on pourra s'arranger."*

**[OVERLAY : `07_anim_conclusion.webm` - Signature PAPA SAMUZ]**

**[SCREEN : Interface V2 en plan large, musique qui monte]**

*"En attendant, dites-moi en commentaire quelle feature vous interesse le plus. Et si vous voulez pas rater la suite... vous savez quoi faire."*

**[SCREEN : Bouton like/abo anime]**

*"C'etait PAPA SAMUZ. On se retrouve dans le prochain vol."*

**[FIN - Ecran de fin avec liens videos]**

---

## NOTES DE MONTAGE

### Transitions
- Cuts rapides entre les demos, pas de temps mort
- Chaque overlay WebM est en fond transparent, superpose au gameplay MSFS

### Musique
- Fond ambient/lo-fi pendant les explications
- Montee epique sur le hook et la conclusion

### Texte a l'ecran
- Afficher les chiffres cles en gros quand tu les annonces :
  - **31 000 lignes**
  - **1 500h pour l'ATPL**
  - **-90% memoire**
  - **11 types de pannes**

### Rythme
- Chaque partie = une feature majeure, environ 2 min chacune
- Ca garde l'attention et cree un effet "ca ne s'arrete jamais"

### Thumbnail suggeree
- Screenshot cockpit MSFS + interface V2 en overlay
- Texte "V2" en gros avec visuel before/after
- Couleurs dominantes : cyan + orange (palette du programme)

---

## OVERLAYS WebM A GENERER (dossier `prez_video_v2/`)

| Fichier | Duree | Contenu |
|---------|-------|---------|
| `01_anim_hook_intro.webm` | 12s | Compteur lignes de code + titre V2 + tags features |
| `02_anim_carriere.webm` | 25s | Timeline licences STUDENT>ATPL + companies + logbook |
| `03_anim_copilote.webm` | 25s | 4 cartes copilote (Voix, Checklists, Callouts, LLM) |
| `04_anim_systemes.webm` | 25s | Panneaux Fuel + Maintenance + Passagers + Pannes |
| `05_anim_extras.webm` | 20s | Challenges atterrissage + Flight Recorder + exports |
| `06_anim_comparatif.webm` | 18s | Tableau comparatif V1 vs V2 + stats |
| `07_anim_conclusion.webm` | 12s | Message + signature PAPA SAMUZ |

### Specs techniques
- **Resolution** : 1920x1080
- **FPS** : 30
- **Codec** : VP9 WebM avec alpha (yuva420p)
- **Librairies** : PIL/Pillow + imageio + numpy
- **Style** : Identique V1 (dark UI, cyan/green/red/orange, monospace)
