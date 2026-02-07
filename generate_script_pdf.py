from fpdf import FPDF
import os

class ScriptPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "PAPA SAMUZ - Script Video YouTube", align="C")
        self.ln(4)
        self.set_draw_color(0, 120, 215)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title, color=(0, 120, 215)):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*color)
        self.set_fill_color(240, 245, 255)
        self.cell(0, 10, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def timing(self, text):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(200, 80, 0)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def direction(self, text):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(0, 130, 80)
        self.multi_cell(0, 5, f"[DIRECTION] {text}")
        self.ln(2)

    def dialogue(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.cell(6, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(1)


pdf = ScriptPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# ===================== PAGE DE TITRE =====================
pdf.ln(25)
pdf.set_font("Helvetica", "B", 28)
pdf.set_text_color(0, 90, 180)
pdf.cell(0, 15, "SCRIPT VIDEO YOUTUBE", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(5)
pdf.set_font("Helvetica", "B", 18)
pdf.set_text_color(50, 50, 50)
pdf.cell(0, 12, "J'ai code un generateur de missions", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 12, "pour MSFS 2024 !", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(5)
pdf.set_font("Helvetica", "", 14)
pdf.set_text_color(200, 80, 0)
pdf.cell(0, 10, "PARTIE 1 - Presentation V1", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(8)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 7, "Chaine : PAPA SAMUZ", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 7, "Duree cible : 15 minutes", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 7, "Format : Tutoriel / Demonstration", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(15)
pdf.set_draw_color(0, 120, 215)
pdf.set_line_width(0.3)
pdf.line(50, pdf.get_y(), 160, pdf.get_y())
pdf.ln(8)
pdf.set_font("Helvetica", "I", 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 7, "Ce script est un guide - adaptez le ton a votre style !", align="C", new_x="LMARGIN", new_y="NEXT")


# ===================== PLAN GENERAL =====================
pdf.add_page()
pdf.section_title("PLAN GENERAL DE LA VIDEO", (0, 80, 160))
pdf.ln(2)

plan_items = [
    ("00:00 - 00:45", "HOOK + Intro (45s)"),
    ("00:45 - 02:30", "Le probleme avec MSFS 2024 (1m45)"),
    ("02:30 - 04:30", "Presentation du concept (2m00)"),
    ("04:30 - 06:30", "L'interface et le lancement (2m00)"),
    ("06:30 - 08:30", "Generation d'une mission en LIVE (2m00)"),
    ("08:30 - 10:30", "Le systeme de paiement pilote (2m00)"),
    ("10:30 - 12:30", "Demo complete : du parking a l'atterrissage (2m00)"),
    ("12:30 - 14:00", "Resultats et debriefing mission (1m30)"),
    ("14:00 - 15:00", "Teaser V2 + Outro (1m00)"),
]

for timing, desc in plan_items:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(200, 80, 0)
    pdf.cell(45, 7, timing)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, desc, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


# ===================== SECTION 1 : HOOK =====================
pdf.add_page()
pdf.section_title("SECTION 1 : HOOK + INTRO")
pdf.timing("00:00 - 00:45  |  45 secondes")

pdf.direction("Plan serre sur l'ecran : un avion decolle dans MSFS 2024. Musique epique en fond. Montage rapide de differentes missions, atterrissages, l'interface du programme.")

pdf.dialogue('"Et si je vous disais que j\'ai transforme Flight Simulator 2024 en veritable simulateur de carriere pilote... avec un programme que j\'ai code moi-meme en Python ?"')
pdf.ln(1)
pdf.dialogue('"Salut a tous, c\'est PAPA SAMUZ !"')
pdf.ln(1)
pdf.dialogue('"Aujourd\'hui, je vous presente un projet sur lequel je bosse depuis un moment : un generateur de missions automatique pour MSFS 2024. Le programme se connecte directement au simulateur, genere des missions realistes avec de la vraie meteo, calcule votre salaire de pilote... et vous penalise si vous atterrissez comme un sac."')
pdf.ln(1)
pdf.dialogue('"C\'est la partie 1 : on decouvre ensemble la version 1 du programme. Dans la partie 2, je vous montrerai la V2 avec le copilote IA, le mode carriere complet et plein de nouvelles fonctionnalites."')
pdf.ln(1)
pdf.dialogue('"Allez, on y va !"')

pdf.direction("Transition animee vers la section suivante. Jingle court.")


# ===================== SECTION 2 : LE PROBLEME =====================
pdf.add_page()
pdf.section_title("SECTION 2 : LE PROBLEME AVEC MSFS 2024")
pdf.timing("00:45 - 02:30  |  1 minute 45")

pdf.direction("Montrer des screenshots de MSFS 2024, le menu principal, le mode monde libre.")

pdf.dialogue('"Alors si vous jouez a Flight Simulator 2024, vous connaissez le probleme : le jeu est magnifique, les avions sont incroyables... mais au bout d\'un moment, on tourne en rond."')
pdf.ln(1)
pdf.dialogue('"Le mode carriere integre est... comment dire... limité. Vous faites toujours les memes missions, y a pas de vrai challenge, pas de consequences si vous atterrissez n\'importe comment."')
pdf.ln(1)

pdf.direction("Montrer un atterrissage mediocre dans MSFS -- il ne se passe rien.")

pdf.dialogue('"Regardez : la, je viens de poser l\'avion a 500 pieds par minute -- en vrai un atterrissage comme ca, on vous retire votre licence. Dans le jeu ? Rien. Zero consequence."')
pdf.ln(1)
pdf.dialogue('"Moi ce que je voulais, c\'est :"')

pdf.bullet("Des missions aleatoires, partout dans le monde")
pdf.bullet("De la VRAIE meteo, avec le vent reel")
pdf.bullet("Un systeme qui me recompense si je pilote bien")
pdf.bullet("Et qui me penalise si je fais n'importe quoi")
pdf.bullet("Un suivi de ma progression, comme un vrai pilote")

pdf.ln(1)
pdf.dialogue('"Du coup... j\'ai code mon propre systeme. Et la, je vais tout vous montrer."')

pdf.direction("Transition vers l'ecran du PC avec le programme ouvert.")


# ===================== SECTION 3 : CONCEPT =====================
pdf.add_page()
pdf.section_title("SECTION 3 : PRESENTATION DU CONCEPT")
pdf.timing("02:30 - 04:30  |  2 minutes")

pdf.direction("Ecran splitte : le programme d'un cote, MSFS de l'autre. Ou schema explicatif anime.")

pdf.dialogue('"Alors comment ca marche concretement ? Le programme est code en Python, et il se connecte directement a MSFS 2024 grace a SimConnect -- c\'est l\'API officielle de Microsoft pour communiquer avec le simulateur."')
pdf.ln(1)
pdf.dialogue('"En gros, le programme lit en temps reel les donnees de votre avion : votre altitude, votre vitesse, votre position GPS, l\'angle d\'inclinaison, le taux de descente a l\'atterrissage... tout."')
pdf.ln(1)

pdf.sub_title("Les briques technologiques")

pdf.bullet("SimConnect : connexion directe a MSFS 2024, lecture de plus de 1200 variables")
pdf.bullet("API NOAA Aviation : recuperation de la VRAIE meteo en temps reel (METAR)")
pdf.bullet("Base de donnees de 4918 aeroports mondiaux")
pdf.bullet("Groq AI (LLaMA 3.3 70B) : generation de routes IFR intelligentes")
pdf.bullet("Interface graphique moderne en mode sombre avec CustomTkinter")

pdf.ln(1)
pdf.dialogue('"Et le truc cool, c\'est que quand vous generez une mission, le programme cree un vrai fichier de plan de vol .PLN que MSFS peut lire directement. Il le copie automatiquement dans le bon dossier. Vous avez juste a le charger dans le simulateur et decoller."')

pdf.direction("Montrer brievement le dossier de plans de vol et un fichier .PLN ouvert.")


# ===================== SECTION 4 : INTERFACE =====================
pdf.add_page()
pdf.section_title("SECTION 4 : L'INTERFACE ET LE LANCEMENT")
pdf.timing("04:30 - 06:30  |  2 minutes")

pdf.direction("Screencast du programme. Montrer chaque zone de l'interface une par une avec un rectangle de surbrillance ou un zoom.")

pdf.dialogue('"Ok, on lance le programme. Premiere chose que vous voyez : l\'interface."')
pdf.ln(1)
pdf.dialogue('"En haut, vous avez votre COMPTE PILOTE. Vous commencez avec 100 euros. En vert si vous etes en positif, en rouge si vous avez trop crash d\'avions."')
pdf.ln(1)

pdf.sub_title("Les zones de l'interface (800x900)")

pdf.bullet("HEADER : Solde du compte pilote + nombre de missions completees + record d'atterrissage")
pdf.bullet("STATUT : Indicateur de connexion SimConnect (connecte / deconnecte)")
pdf.bullet("ZONE MISSION : Aeroport de depart, aeroport d'arrivee, pistes, vent, distance")
pdf.bullet("BARRE DE PROGRESSION : Pourcentage d'avancement de la mission en temps reel")
pdf.bullet("CONTRAINTES ACTIVES : Les regles a respecter pendant le vol")
pdf.bullet("DONNEES AVION : Altitude, inclinaison, vitesse verticale, vitesse sol -- EN DIRECT")
pdf.bullet("PANNEAU CONFIG : Cle API Groq, dossier d'export des plans de vol")

pdf.ln(1)
pdf.dialogue('"Le programme detecte automatiquement votre avion toutes les 30 secondes. Il sait si vous etes dans un petit Cessna ou dans un Boeing 737. Et ca change tout : la distance des missions, l\'altitude de croisiere, et surtout votre salaire."')

pdf.direction("Montrer la detection automatique de l'avion dans les logs ou l'interface.")

pdf.dialogue('"Il y a 8 categories d\'avions detectees : du petit piston mono-moteur jusqu\'au gros porteur, en passant par les helicopteres. Chaque categorie a ses propres limites et son propre taux horaire."')


# ===================== SECTION 5 : GENERATION MISSION =====================
pdf.add_page()
pdf.section_title("SECTION 5 : GENERATION D'UNE MISSION EN LIVE")
pdf.timing("06:30 - 08:30  |  2 minutes")

pdf.direction("LIVE : Cliquer sur 'Generer Mission' dans le programme. Montrer tout le processus en temps reel.")

pdf.dialogue('"Allez, on genere une mission en direct ! Je clique sur le bouton..."')
pdf.ln(1)
pdf.dialogue('"Et voila ce qui se passe en coulisses :"')

pdf.sub_title("Etape 1 : Choix des aeroports")
pdf.body_text("Le programme detecte votre position actuelle dans MSFS, puis cherche dans sa base de 4918 aeroports un aeroport d'arrivee adapte a votre avion. Un Cessna 172 va faire 100-300 nautiques ; un Airbus va faire 500-1500 nautiques.")

pdf.sub_title("Etape 2 : Meteo en temps reel")
pdf.body_text("Il va chercher le METAR reel sur les serveurs NOAA Aviation. Il connait le vent, la visibilite, les conditions. Il selectionne automatiquement la piste la plus face au vent -- comme en vrai.")

pdf.sub_title("Etape 3 : Route IFR intelligente")
pdf.body_text("Grace a l'IA Groq (LLaMA 3.3), le programme genere une route IFR realiste avec des VOR et des intersections. Il a une base de 36 VOR et 35 intersections. Si l'API est indisponible, il cree une route de secours avec les navaids.")

pdf.sub_title("Etape 4 : Plan de vol .PLN")
pdf.body_text("Le programme genere un fichier XML au format MSFS, avec les pistes, les waypoints, l'altitude de croisiere... et le copie automatiquement dans le dossier missions de MSFS 2024.")

pdf.direction("Son 'mission.wav' qui se joue. Montrer le fichier PLN genere.")

pdf.dialogue('"Et voila ! En quelques secondes, j\'ai une mission complete avec depart, arrivee, pistes selectionnees selon le vent reel, et un plan de vol pret a charger. C\'est la que ca devient serieux."')


# ===================== SECTION 6 : SYSTEME PAIEMENT =====================
pdf.add_page()
pdf.section_title("SECTION 6 : LE SYSTEME DE PAIEMENT PILOTE")
pdf.timing("08:30 - 10:30  |  2 minutes")

pdf.direction("Afficher un tableau ou une infographie avec les tarifs. Ou un overlay anime sur l'ecran.")

pdf.dialogue('"Le coeur du programme, c\'est le systeme economique. Parce que piloter c\'est bien, mais se faire payer c\'est mieux."')
pdf.ln(1)

pdf.sub_title("Les taux horaires par categorie d'avion")

rates = [
    ("Piston leger (Cessna 172)", "55 EUR/h"),
    ("Bi-moteur piston", "75 EUR/h"),
    ("Turboprop mono", "95 EUR/h"),
    ("Turboprop", "120 EUR/h"),
    ("Jet leger", "150 EUR/h"),
    ("Jet", "200 EUR/h"),
    ("Gros porteur", "280 EUR/h"),
    ("Helicoptere", "85 EUR/h"),
]

for cat, rate in rates:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(80, 6, f"  {cat}")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 130, 0)
    pdf.cell(0, 6, rate, new_x="LMARGIN", new_y="NEXT")

pdf.ln(3)
pdf.sub_title("Les bonus")
pdf.bullet("Vol de nuit (21h-6h) : +25%")
pdf.bullet("Weekend : +15%")
pdf.bullet("Mauvaise meteo (visibilite < 3 SM) : +20%")
pdf.bullet("Atterrissage parfait (< 100 fpm) : +50 EUR")
pdf.bullet("Bon atterrissage (100-200 fpm) : +25 EUR")
pdf.bullet("Toutes les contraintes respectees : +30 EUR")
pdf.bullet("Per diem : 35 EUR (< 2h) / 65 EUR (2-5h) / 120 EUR (> 5h)")

pdf.ln(1)
pdf.sub_title("Les penalites")
pdf.bullet("Atterrissage dur (300-500 fpm) : -50 EUR")
pdf.bullet("Atterrissage tres dur (> 500 fpm) : -150 EUR !")
pdf.bullet("Violation de contrainte : -10 EUR chacune")
pdf.bullet("Survitesse : -25 EUR")

pdf.ln(1)
pdf.dialogue('"Donc la, vous comprenez l\'enjeu : si vous pilotez bien, vous gagnez bien votre vie. Si vous pilotez comme un manche... votre compte passe dans le rouge. Et croyez-moi, ca motive a faire des beaux atterrissages."')


# ===================== SECTION 7 : DEMO =====================
pdf.add_page()
pdf.section_title("SECTION 7 : DEMO COMPLETE EN VOL")
pdf.timing("10:30 - 12:30  |  2 minutes")

pdf.direction("MONTAGE ACCELERE d'un vol complet dans MSFS avec le programme visible en overlay ou en split screen. Montrer les moments cles.")

pdf.dialogue('"Allez, on fait un vol complet. Je charge le plan de vol dans MSFS, je me mets au parking..."')
pdf.ln(1)

pdf.sub_title("Phase 1 : Au parking")
pdf.body_text("Le programme detecte que vous etes au parking. La mission est en attente. Status : 'At Parking'.")
pdf.direction("Montrer le statut dans l'interface.")

pdf.sub_title("Phase 2 : Decollage et montee")
pdf.body_text("Des que vous decollez, le programme passe en mode 'In Flight'. La barre de progression commence a bouger. Les contraintes s'activent.")
pdf.direction("Montrer la barre de progression qui avance, les donnees live qui changent.")

pdf.sub_title("Phase 3 : En croisiere")
pdf.dialogue('"Regardez les donnees en direct : altitude, vitesse, inclinaison... tout est lu depuis SimConnect. Et la, le programme surveille mes contraintes. Par exemple, il m\'a mis une contrainte d\'angle d\'inclinaison maximum de 25 degres. Si je depasse... penalite."')
pdf.direction("Faire expres de depasser une contrainte pour montrer la penalite. Son 'penalty.wav'.")

pdf.sub_title("Phase 4 : Approche et atterrissage")
pdf.dialogue('"L\'approche... c\'est la que tout se joue. Le programme mesure mon taux de descente a l\'impact. Objectif : en dessous de 200 pieds par minute pour un bon atterrissage, en dessous de 100 pour un atterrissage parfait."')
pdf.direction("Montrer l'atterrissage. Suspense. Son 'success.wav' ou 'crash.wav' selon le resultat.")


# ===================== SECTION 8 : RESULTATS =====================
pdf.add_page()
pdf.section_title("SECTION 8 : RESULTATS ET DEBRIEFING")
pdf.timing("12:30 - 14:00  |  1 minute 30")

pdf.direction("Montrer l'ecran de resultats apres la mission. Zoomer sur chaque ligne du decompte.")

pdf.dialogue('"Et voila, mission terminee ! Regardons le decompte..."')
pdf.ln(1)

pdf.sub_title("Exemple de decompte (a adapter selon le vol reel)")
pdf.body_text("Imaginons un vol Paris - Londres en jet leger, 1h15 de vol, atterrissage a 150 fpm, de nuit, avec une contrainte violee :")

pdf.set_font("Courier", "", 10)
pdf.set_text_color(30, 30, 30)
decompte = [
    "Salaire horaire : 150 x 1.25h ............. 187.50 EUR",
    "Per diem (< 2h) ............................ +35.00 EUR",
    "Bonus nuit (+25%) .......................... +46.88 EUR",
    "Bon atterrissage (150 fpm) ................. +25.00 EUR",
    "Violation contrainte (x1) .................. -10.00 EUR",
    "                                            ----------",
    "TOTAL MISSION .............................. 284.38 EUR",
]
for line in decompte:
    pdf.cell(0, 5.5, f"  {line}", new_x="LMARGIN", new_y="NEXT")

pdf.ln(4)
pdf.set_font("Helvetica", "", 10)
pdf.dialogue('"284 euros pour un vol d\'une heure et quart, c\'est pas mal ! Et mon record d\'atterrissage est sauvegarde. Tout est persistant : votre solde, vos missions completees, votre meilleur atterrissage. Meme si vous fermez le programme, vous retrouvez tout au prochain lancement."')

pdf.direction("Montrer le fichier savegame.json brievement. Montrer le solde mis a jour dans le header.")

pdf.dialogue('"Et chaque session de jeu a ses propres logs detailles dans le dossier logs/. Vous pouvez revoir exactement ce qui s\'est passe."')


# ===================== SECTION 9 : TEASER V2 + OUTRO =====================
pdf.add_page()
pdf.section_title("SECTION 9 : TEASER V2 + OUTRO")
pdf.timing("14:00 - 15:00  |  1 minute")

pdf.direction("Musique qui monte en intensite. Montage rapide de screenshots ou apercu de la V2. Texte anime qui apparait a l'ecran.")

pdf.dialogue('"Bon, ca c\'etait la V1. Mais attendez de voir ce que j\'ai prepare pour la partie 2..."')
pdf.ln(1)

pdf.sub_title("Teaser des fonctionnalites V2")
pdf.bullet("Un COPILOTE IA qui vous parle en temps reel avec reconnaissance vocale")
pdf.bullet("Un mode CARRIERE complet avec licences pilote (PPL, CPL, ATPL)")
pdf.bullet("Des PANNES ALEATOIRES en plein vol (panne moteur, fuite carburant...)")
pdf.bullet("Un systeme de MAINTENANCE des avions")
pdf.bullet("Des CHALLENGES d'atterrissage (terrain court, vent de travers, nuit)")
pdf.bullet("Un LOGBOOK automatique comme les vrais pilotes")
pdf.bullet("La gestion du CARBURANT avec prix reels")
pdf.bullet("L'enregistrement du vol en KML pour Google Earth")

pdf.ln(1)
pdf.dialogue('"La V2, c\'est plus de 5600 lignes de code avec 25 modules. C\'est un autre niveau. Mais je vous garde tout ca pour la partie 2."')

pdf.ln(1)
pdf.dialogue('"Si cette video vous a plu, lacher un like, ca m\'aide enormement. Abonnez-vous si c\'est pas deja fait pour ne pas rater la partie 2. Et dites-moi en commentaire quelle fonctionnalite vous interesse le plus !"')

pdf.ln(1)
pdf.dialogue('"C\'etait PAPA SAMUZ, a la prochaine, et bon vol a tous !"')

pdf.direction("Ecran de fin avec animation d'abonnement, lien partie 2 (a venir), musique de fin.")


# ===================== NOTES DE PRODUCTION =====================
pdf.add_page()
pdf.section_title("NOTES DE PRODUCTION", (100, 0, 100))
pdf.ln(2)

pdf.sub_title("Materiel necessaire pour le tournage")
pdf.bullet("MSFS 2024 lance avec un avion au parking")
pdf.bullet("Le programme V1 (main.py) en cours d'execution")
pdf.bullet("OBS ou logiciel de capture pour le screencast")
pdf.bullet("Micro pour la voix off")

pdf.ln(2)
pdf.sub_title("Conseils de montage")
pdf.bullet("Utiliser des zooms et des highlights sur l'interface pour guider l'oeil")
pdf.bullet("Accelerer les phases de vol en croisiere (timelapse x8 ou x16)")
pdf.bullet("Ajouter des sous-titres sur les moments cles")
pdf.bullet("Utiliser des transitions fluides entre les sections")
pdf.bullet("Musique de fond discrete pendant les explications, plus intense pendant les demos")

pdf.ln(2)
pdf.sub_title("Tags YouTube suggeres")
pdf.body_text("MSFS 2024, Microsoft Flight Simulator 2024, generateur missions, mission generator, SimConnect, Python, programmation, pilote virtuel, flight sim, carriere pilote, tuto MSFS, mod MSFS 2024")

pdf.ln(1)
pdf.sub_title("Titre suggere pour la video")
pdf.body_text("J'ai code un GENERATEUR DE MISSIONS pour Flight Simulator 2024 ! (Partie 1)")

pdf.ln(1)
pdf.sub_title("Description YouTube suggeree")
pdf.body_text("Dans cette video, je vous presente un programme que j'ai entierement code en Python pour transformer MSFS 2024 en simulateur de carriere pilote ! Missions aleatoires, vraie meteo, systeme de paiement realiste... Partie 1 sur la V1 du programme.\n\nPartie 2 (V2 avec copilote IA, pannes, carriere) : [LIEN A VENIR]\n\nCode source : [LIEN SI APPLICABLE]\n\n#MSFS2024 #FlightSimulator #Python #SimConnect #Aviation")


# ===================== SAUVEGARDE =====================
output_path = os.path.join(os.path.dirname(__file__), "Script_YouTube_MSFS_Mission_Generator_V1.pdf")
pdf.output(output_path)
print(f"PDF genere avec succes : {output_path}")
