# Corsi chiusi e possibili nuove edizioni

Verifica del 12 novembre 2026. Le schede restano consultabili e utilizzabili come
tappe anche quando le lezioni sono partite o finite. «Riapertura da verificare»
non promette un’edizione annuale o semestrale: date e nuove iscrizioni devono
essere confermate dall’organizzatore.

| Corso | Edizione documentata | Fonte |
| --- | --- | --- |
| Python PiA | Aprile–giugno e novembre–dicembre 2026; l’edizione autunnale è già partita, iscrizioni chiuse | [Primavera](https://www.polimi.it/formazione/passion-in-action/dettaglio/python-from-fundamentals-to-ml-neural-networks-and-secure-federated-learning), [autunno](https://www.polimi.it/formazione/passion-in-action/dettaglio/python-from-fundamentals-to-ml-neural-networks-and-secure-federated-learning-1) |
| Git POuL / PiA | 10, 17, 24 marzo 2026; iscrizioni terminate il 3 marzo | [POuL](https://poul.org/courses/git/), [Polimi](https://www.polimi.it/formazione/passion-in-action/dettaglio/version-control-con-git-2) |
| PCB Design POuL | 13–20 novembre 2025; archivio anche 2022 | [Corso](https://poul.org/courses/pcb/), [archivio](https://poul.org/courses/pcb/past/) |
| Linux Base POuL | 25 marzo – 1 aprile 2026 | [Corso e archivio](https://poul.org/courses/linux/) |
| Arduino POuL | 5–12 maggio 2025 | [Corso e archivio](https://poul.org/courses/arduino/) |
| Python POuL | 20–27 marzo 2024 | [Corso e archivio](https://poul.org/courses/python/) |
| Robotics Academy / AEA | Calendario 23 marzo – 4 maggio 2026; il periodo sintetico della fonte termina ad aprile | [PiA](https://www.polimi.it/formazione/passion-in-action/dettaglio/robotics-academy-un-corso-sui-robot-mobili-autonomi), [AEA Academy nel documento di Automazione](https://www.ingindinf.polimi.it/fileadmin/user_upload/upload/formazione/esperienza_studente/magistrale__inglese/Esperienza_Studente__Automazione_-_LM_English_-_clean.pdf) |
| ARGO Training | Presente nella call AEA 2026/27; calendario non pubblicato, candidatura ancora indicata come aperta | Fonte AEA collegata alla scheda esistente; nessuna futura data inventata |
| Laboratorio di sistemi di automazione industriale | 7 ottobre – 11 novembre 2026, appena concluso | [PiA](https://www.polimi.it/formazione/passion-in-action/dettaglio/laboratorio-di-sistemi-di-automazione-industriale-1) |
| Stampa 3D POuL | 13–22 ottobre 2025; archivio 2023 e 2022 | [Corso](https://poul.org/courses/3dprint/), [archivio](https://poul.org/courses/3dprint/past/) |
| Linux avanzato / HomeLab POuL | 26 marzo – 1 aprile 2025; archivio pluriennale | [Corso](https://poul.org/courses/linux-advanced/), [archivio](https://poul.org/courses/linux-advanced/past/) |
| LaTeX POuL | 27–28 aprile 2023; ancora nell’indice dei corsi POuL | [Corso](https://poul.org/courses/latex/), [archivio](https://poul.org/courses/latex/past/) |

Il catalogo conserva una scheda per corso e l’edizione rilevante, senza creare
duplicati per ogni anno. Le cinque schede POuL preesistenti mantengono gli ID e i
materiali, aggiungendo calendario storico e stato delle lezioni. Cinque nuove
schede portano il catalogo a 112 attività e 49 enti.

La riapertura da verificare si ricava automaticamente dallo stato chiuso o dalla
fine/scadenza passata di un **corso**. Non servono nuovi campi né migrazioni. Corsi
aperti, materiali continuativi e disponibilità sconosciuta restano distinti.
Una nuova edizione con iscrizioni aperte e date aggiornate perde l’avviso.
Nodi e rami interessati sono tratteggiati; le tappe già completate restano valide
e i loro rami non sono più segnalati come indisponibili per quella persona.

Le preparazioni sono editoriali: Python PiA e Linux → Academy; Academy → ARGO
è un’opzione formativa insieme al training, non un requisito obbligatorio. La
Academy richiede anche C++, esplicitamente indicato tra i requisiti ufficiali.
Il corso Arduino non sostituisce i requisiti universitari del laboratorio PLC.

## Collegamenti e verifica

I rami che saltano un livello passano nel margine dello stesso lato della tappa
di partenza. Le corsie orizzontali sono calcolate nello spazio fra i livelli;
i numeri hanno una colonna separata dalle corsie verticali su desktop.
Il caso BCI e il suo speculare sono coperti da test di regressione.

Verificati import ripetibile su copia del database, conservazione di progressi
e preferenze, ricerca dei corsi chiusi, dettagli Academy e completamento/annullamento
da browser. Controllati desktop e mobile a 390 e 320 px, dialog da tastiera
e assenza di errori JavaScript. Screenshot del README aggiornati.

Durante il rilascio: backup consistente prima dell’import, confronto dei progressi
e delle autorizzazioni, import ripetuto senza modifiche residue. Dopo il riavvio,
controllare HTTPS, BCI, ARGO, Academy, servizio e log per errori 500/Traceback.
Responsabile della verifica immediata: autore del rilascio. Una perdita di dati,
un errore di import o pagine non disponibili richiedono ripristino del backup
e della revisione precedente prima di riaprire l’anteprima.
