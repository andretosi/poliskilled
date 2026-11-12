# Passion in Action — verifica del 12 novembre 2026

Catalogo curato per PoliSkilled. Sono state consultate le pagine pubbliche ufficiali, senza account o accesso a WeBeep.

- 20 schede nell’indice attivo, tutte lette.
- 868 schede nell’archivio completo, senza paginazione: esaminate le 110 con date di iscrizione nel 2026.
- 35 attività uniche attuali: 13 con iscrizioni aperte e 22 con iscrizioni chiuse. Il secondo gruppo contiene corsi in corso e attività programmate con candidatura già terminata.
- 10 enti esplicitamente indicati nelle fonti. Passion in Action è un programma del Politecnico di Milano, non un ente.
- Le descrizioni sono sintesi originali; ogni record conserva fonte, data di controllo, requisiti e incertezze.

## Criteri

La disponibilità è lo stato delle iscrizioni, determinato dalla scadenza effettiva. Non equivale al fatto che il corso si stia svolgendo. Il campo aggiuntivo `course_status` segnala attività in corso o conclusione non verificabile.

Un giorno privo di orario non viene convertito in una mezzanotte fittizia: `starts_at` resta null e, quando noto, `starts_on` conserva il giorno. Periodi mensili e calendari provvisori restano espliciti. Non sono stati inventati prerequisiti ufficiali o partner.

## Punti da preservare nell’importazione

- Smart Campus: due schede con stesso titolo, testo e calendario, ma ore/categorie differenti. Un unico record, seconda fonte allegata. Nessun collegamento “parte 1 → parte 2”.
- Startup 101: due edizioni reali, gennaio e giugno 2027. Il mese nel titolo è un’aggiunta editoriale per distinguerle.
- FPGA con AMD: scadenza oggi alle 12:00, già passata. Un appuntamento riportato come 07/11 è fuori sequenza: non è stato corretto arbitrariamente in 07/12.
- FPGA101: lezioni elencate fino al 9 novembre, periodo dichiarato fino a gennaio e Q&A su richiesta; non è stata inventata una data finale. La versione inglese esplicita basi di programmazione fra i requisiti.
- AI–Network Loop: il calendario è incompleto e provvisorio, perciò la conclusione resta non verificabile.
- Design Explorer: la prima finestra scade il 4 dicembre, ma la scheda descrive altre quattro finestre fino a settembre 2027.
- Design&Engineering Dialogues: raggruppata la scheda primaverile sovrapposta, preferendo il calendario autunnale dettagliato.
- Nessun programma aziendale è attribuito a un ente solo perché un relatore vi lavora. Le università giapponesi partner di Pagani non sono nominate e non sono state inventate.
- Il sito di CoLomba non è stato identificato con certezza: campo website vuoto; coordinamento documentato nella pagina Polimi.

## Esclusioni rilevanti

- Luoghi educativi accoglienti: aprile–maggio 2025.
- Gestione dello stress -17: febbraio 2026; inserita invece l’edizione di novembre -19.
- Laboratorio automazione industriale: ultima lezione 11 novembre.
- Elementi d’impresa: ultima lezione 4 novembre.
- Visti o invisibili: EICMA terminata l’8 novembre. L’annuncio del workshop futuro non costituisce un nuovo bando.
- Destinazione impresa: terminata il 12 novembre alle 14:00.
- Progettare futuri possibili: consegna del 3 novembre già passata; successive fasi selettive non presentate come corso disponibile.

Il JSON contiene l’esito puntuale per ciascuna delle 130 schede controllate.

## Copertura e limiti

Copertura completa dell’indice attivo osservato e delle schede archiviate con date di iscrizione nel 2026. Non si dichiara esaustività di tutti i programmi pluriennali avviati prima del 2026: le altre 758 schede storiche sono state enumerate, non tutte rilette. Fonti e disponibilità sono una fotografia del 12 novembre 2026, non una sincronizzazione automatica.

La pagina archivio ha inizialmente prodotto un errore di decodifica UTF-8 per un byte non conforme; la lettura è stata completata sul mirror ufficiale con sostituzione del singolo carattere. Tutte le 110 pagine di dettaglio selezionate sono state recuperate. Lo slug inglese del workshop Studenti in cantiere non funzionava sotto il percorso italiano: recuperato lo slug italiano corretto dall’archivio.

## Fonti iniziali

- [Catalogo attivo ufficiale](https://www.polimi.it/formazione/passion-in-action)
- [Mirror ufficiale](https://dynamicpoli.polimi.it/formazione/passion-in-action)
- [Archivio ufficiale completo](https://dynamicpoli.polimi.it/formazione/passion-in-action?tx_didatticainnovativa_innovativeteaching%5Baction%5D=list&tx_didatticainnovativa_innovativeteaching%5Barchived%5D=S&tx_didatticainnovativa_innovativeteaching%5Bcontroller%5D=InnovativeTeaching&tx_didatticainnovativa_innovativeteaching%5Bscroll%5D=true&cHash=a894005c150624e15c2d7d275833391c)

I possibili collegamenti editoriali fra attività devono essere creati separatamente e presentati come suggerimenti di PoliSkilled, non come condizioni ufficiali d’accesso.
