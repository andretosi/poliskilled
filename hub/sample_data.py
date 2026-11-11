"""Short factual summaries; fictional activities are explicitly marked as samples."""

AEA = "https://www.aeapolimi.it/"
BEA = (
    "https://www.polimi.it/studenti/associazioni-degli-studenti/biomedical-engineering-association"
)
PIA = "https://www.polimi.it/formazione/passion-in-action"
PHYSIS = "https://physispeb.it/"
HACKATHON = PIA + "/dettaglio/ideare-inventare-innovare-dalle-idee-ai-prototipi-2"

ORGANIZATIONS = [
    (
        "AEA",
        "Automation Engineering Association",
        AEA,
        "Studenti, automazione e robotica. AEA propone progetti, workshop e visite in azienda.",
    ),
    (
        "BEA",
        "Biomedical Engineering Association",
        BEA,
        "La community di ingegneria biomedica del Poli: incontri, visite e progetti condivisi.",
    ),
    (
        "Polimi",
        "Politecnico di Milano",
        "https://www.polimi.it/",
        "L'ateneo e le sue iniziative per imparare anche oltre i corsi di studio.",
    ),
    (
        "Physis",
        "Physis PEB",
        PHYSIS,
        "Team studentesco che progetta imbarcazioni da competizione a propulsione sostenibile.",
    ),
]

# title, kind, level, organizers, sample, URL, description
ACTIVITIES = [
    (
        "Elettronica: il primo circuito",
        "course",
        1,
        ["AEA"],
        True,
        "",
        "Un laboratorio introduttivo immaginato per PoliSkilled: componenti e misure di base. "
        "Una tappa di esempio per capire come potrebbe iniziare un percorso di elettronica.",
    ),
    (
        "Python, dai dati alle idee",
        "course",
        1,
        ["BEA"],
        True,
        "",
        "Esempio di corso pratico: leggere un dataset, visualizzare segnali e costruire un piccolo "
        "esperimento. Questa scheda non rappresenta un'edizione aperta alle iscrizioni.",
    ),
    (
        "AEA Academy",
        "course",
        2,
        ["AEA"],
        False,
        AEA,
        "Workshop dell'associazione dedicati alle competenze per la robotica. "
        "Consulta AEA per conoscere gli appuntamenti e i contenuti delle edizioni disponibili.",
    ),
    (
        "Sensori, segnali e persone",
        "course",
        2,
        ["AEA", "BEA"],
        True,
        "",
        "Una proposta congiunta dimostrativa: collegare un sensore, leggere un segnale e "
        "sperimentare un'applicazione biomedica. "
        "Collaborazione ipotetica, non un evento annunciato.",
    ),
    (
        "Physis PEB: energia sull'acqua",
        "project",
        3,
        ["Physis"],
        False,
        PHYSIS,
        "Un team del Politecnico impegnato nella progettazione di imbarcazioni sostenibili e nel "
        "Monaco Energy Boat Challenge. Scopri le attività e i contatti direttamente dal team.",
    ),
    (
        "SAPIENS: robotica per la persona",
        "project",
        3,
        ["AEA"],
        False,
        AEA,
        "Tra i progetti AEA, SAPIENS esplora una mano protesica controllata tramite segnali "
        "biologici. La scheda introduce il progetto: disponibilità e modalità di accesso vanno "
        "verificate con l'associazione.",
    ),
    (
        "ARGO: costruisci il prossimo passo",
        "project",
        3,
        ["AEA"],
        True,
        "",
        "Segnaposto per il team ARGO citato nel brief. Organizzazione, attività e accesso "
        "sono da confermare con il team: questa non è una pagina ufficiale di recruiting.",
    ),
    (
        "Dalle idee ai prototipi",
        "course",
        2,
        ["Polimi"],
        False,
        HACKATHON,
        "Ideare, Inventare, Innovare è un'iniziativa Passion in Action dedicata a trasformare "
        "idee in prototipi attraverso un hackathon. Consulta la pagina ufficiale per l'edizione "
        "di riferimento, le date e gli eventuali termini di iscrizione.",
    ),
    (
        "Incontra le tue prossime passioni",
        "event",
        1,
        ["AEA", "BEA"],
        True,
        "",
        "Un incontro dimostrativo fra associazioni: conoscere le persone, scambiarsi idee e "
        "trovare compagni di progetto. Nessuna data reale è associata a questo esempio.",
    ),
]

TRACKS = [
    (
        "elettronica",
        "Elettronica & sistemi",
        "Dai primi circuiti ai progetti che si muovono.",
        [0, 1, 2, 3, 4, 5, 6],
    ),
    (
        "biomedicale",
        "Tecnologia per le persone",
        "Segnali, prototipi e idee con un impatto umano.",
        [1, 0, 3, 7, 5],
    ),
]

PREDECESSORS = {2: [0, 1], 3: [0, 1], 4: [2, 3], 5: [2, 3, 7], 6: [2, 3], 7: [0, 1]}

ACTIVITY_ICONS = {
    0: "circuit",
    1: "code",
    2: "robot",
    3: "signal",
    4: "flag",
    5: "robot",
    6: "flag",
    7: "design",
    8: "people",
}
