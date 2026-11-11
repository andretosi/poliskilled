# Verifica della prima versione

11 novembre 2026. Checkout nativo Linux in WSL Ubuntu-26.04, Python 3.12.14,
Django 5.2.19. Nessun test Linux è stato eseguito sul filesystem NTFS.

## Risultati

- 48 test Django passati, Ruff e formattazione passati, nessun drift migrazioni.
- `pip-audit -r requirements.txt`: nessuna vulnerabilità nota rilevata.
- `check --deploy --fail-level WARNING`: nessun problema.
- `collectstatic` completato, inclusi asset con hash.
- Smoke Gunicorn con impostazioni produzione: HTTP301, richiesta dal proxy HTTPS200,
  HSTS e CSP presenti. Chiave effimera non salvata né stampata.
- SQLite reale su file temporaneo, due thread con stessa revisione: una scrittura
  accettata e una respinta come obsoleta; un solo nuovo elemento nello storico.

## Browser

Edge tramite agent-browser, sessione separata. Desktop 1440×1000, mobile 390×844.

- Home, filtri per tipo, ricerca e stato senza risultati.
- Percorsi e salvataggio progressi dopo ricaricamento.
- Proposta AEA + BEA: invio, rifiuto senza motivazione bloccato, rifiuto motivato,
  risposta dell'ente, modifica e reinvio, approvazione e visibilità pubblica.
- Thread interno assente per il visitatore anonimo.
- Upload immagine, visualizzazione, cancellazione e ritorno alla copertina predefinita.
- Dopo una modifica, l'attività pubblicata torna privata in attesa di approvazione.
- Tappa completata temporaneamente nascosta: 1/7 → 0/6; completata una seconda tappa;
  ripubblicata la prima → 2/7. Il progresso originario rimane.
- Nessun overflow orizzontale a 390px; nessun errore JavaScript osservato.
- Audit axe WCAG2 A/AA: zero violazioni automatiche sulle pagine controllate.
  I contrasti su fondi con pattern sono segnalati da axe come da esaminare manualmente:
  sono stati controllati visivamente. Non è una certificazione di accessibilità.

La proposta “Laboratorio sensori - prova UI” è conservata come bozza demo con il
thread di collaudo. Le nove schede iniziali restano nel catalogo.
Screenshot temporanei: cartella Windows `C:\Users\Andrea\AppData\Local\Temp`,
file `ramo-home-final.png`, `ramo-home-mobile.png`, `ramo-track-final.png`,
`ramo-track-mobile.png`.

## Revisione

Skill ce-code-review, run `20261111-125455-4f509c88`: **complete / Ready to merge**,
zero rilievi azionabili residui. Revisione con nove prospettive, una batch di validazione
indipendente e controllo dei fix finali. Nessun codice inviato a provider esterni.

Risolti limiti upload, permessi del pannello percorsi, nomi enti Unicode, quota login
dopo CSRF, seed rinominati, paginazione, gestione immagini in commit/rollback,
transazioni brevi e conservazione dei progressi.

L'ultima verifica indipendente includeva 17 test mirati; l'orchestratore della review
ne ha eseguiti 30 sul codice finale. I 48 test completi e il browser sono verifiche
del responsabile dell'implementazione. Concorrenza reale e progressi durante ritiro
sono verifiche di questa sessione, non regressioni browser automatiche committate.

## Confini

Demo locale attiva; produzione esterna non pubblicata. Configurazione Caddy/systemd
fornita come esempio, non installata su un host pubblico. CI predisposta, non
eseguita su GitHub in assenza di remote. SQLite è per singolo host.
Reset password manuale dell'amministratore, nessuna posta transazionale configurata.

## Revisione UX — 11 novembre 2026

Nuova home direttamente sul catalogo pubblico. Rimossi hero, illustrazioni, copertine,
upload visibile e testi promozionali; palette neutra con accento blu. CSS mobile first
con layout più ampio solo tramite media query min-width. Nessuna libreria aggiunta.
La gestione dei file già memorizzati e i relativi controlli di accesso restano nel backend.

Verifiche dopo la modifica:
- 48 test Django passati; Ruff, formato Python e controllo migrazioni passati.
- Ricerca per titolo, nome e sigla dell'ente; categoria e interesse conservati tra ricerche.
- Edge: home a 320×740, 390×844 e 1440×1000. Nessuna immagine, nessun overflow
  orizzontale; prima attività a 375px dall'inizio della pagina su mobile.
- Filtri combinati, ricerca con Invio, risultato vuoto e rimozione filtri verificati.
- Percorsi a colonne su desktop e verticali su mobile; completamento, persistenza
  dopo reload e azzeramento verificati.
- Dettaglio pubblico senza copertina; accessi demo nel footer e menu account funzionanti.
- Modifica della bozza di collaudo AEA + BEA e salvataggio riusciti dal browser.
- Navigazione da tastiera: skip link, ricerca con Invio, focus visibile.
- Axe WCAG2 A/AA: zero violazioni automatiche su catalogo, percorso, dettaglio e
  modulo proposta. I simboli di spunta/chevron hanno richiesto controllo visivo.
- Nessun errore JavaScript osservato.

Screenshot in Windows Temp: ramo-ux-mobile.png, ramo-ux-desktop.png,
ramo-ux-320.png, ramo-ux-track-mobile.png, ramo-ux-track-desktop.png,
ramo-ux-detail-mobile.png e ramo-ux-form.png.
La verifica precedente resta come storico; le copertine non fanno più parte della UI.

## Skill tree videogame e Tailscale — 11 novembre 2026

L'anteprima privata HTTPS è servita da Tailscale Serve verso Gunicorn su
127.0.0.1:8002. DEBUG e accessi demo disattivati. Proxy configurato solo nella tailnet,
nessun Funnel. Il server di sviluppo su 8000 rimane separato.
Avvio riproducibile in scripts/preview.py e docs/remote-preview.md.

Nuovo albero: nodi SVG funzionali originali, collegamenti geometrici, livelli
verticali, colori ambra/ciano, contatore e dialog nativo. Nessun gradiente,
nessuna immagine dei giochi, nessuna dipendenza frontend aggiunta.

Verifiche:
- 48 test Django passati; Ruff e controllo formato passati; nessuna nuova migrazione.
- Preview avviata con lo script documentato; collectstatic e richiesta HTTPS 200.
- Edge sul dominio Tailscale: home, percorsi e login caricati correttamente.
- Layout 1440×1100, 390×844 e 320×740; nessun overflow orizzontale.
- Apertura nodo e completamento dal dialog; 1/7 conservato dopo reload.
- Escape chiude il dialog e restituisce il focus allo stesso nodo.
- Azzeramento e passaggio al percorso biomedicale verificati.
- Axe WCAG2 A/AA: zero violazioni automatiche nelle schermate controllate.
  Alcuni simboli/collegamenti SVG e lo sfondo del dialog richiedono verifica manuale,
  effettuata visivamente. Non è una certificazione di accessibilità.
- Nessun errore JavaScript osservato. Browser di collaudo chiuso; server lasciati attivi.

Screenshot in Windows Temp: ramo-game-desktop.png, ramo-game-tail-mobile.png,
ramo-game-tail-dialog.png, ramo-game-biomedicale.png, ramo-game-home-desktop.png.
I progressi sono per browser e origine: localhost e il dominio Tailscale hanno
salvataggi distinti. La vista remota resta consultabile mentre il PC e WSL sono accesi.


## Account, grafi automatici e identità ARC — 11 novembre 2026

Questa iterazione sostituisce palette e limiti descritti nelle verifiche storiche.

- 76 test Django e 7 test Node passati; Ruff, formato e drift delle migrazioni puliti.
- Progressi anonimi condivisi fra percorsi e dettaglio; import dopo login, annullamento,
  isolamento dopo logout, coda offline e recupero della rete verificati nel browser.
- Regressioni automatiche: due tab concorrenti, batch oltre 200 elementi,
  attività temporaneamente private, sessione scaduta e POST tardivo dopo timeout.
- Da UI: proposta AEA + BEA con icona robot, percorso e predecessore SAPIENS;
  approvazione del moderatore e comparsa automatica al quarto livello.
- Nuovo percorso con due campi: colore assegnato automaticamente e stato vuoto corretto.
- La mappa pubblica non espone attività o titoli privati. I moduli obsoleti e i cambi
  di visibilità durante generazione/salvataggio non cancellano relazioni non viste.
- Migrazione storica 0006→0007: identità tappe, note, progressi e revisioni conservati;
  cicli preesistenti bloccano la migrazione senza modificarne i dati.
- Prova su copia del DB reale 0003: upgrade completo a 0007 riuscito, identità/revisioni/
  stati conservati; ripristino della copia restituisce esattamente lo stato 0003.
- Edge: dashboard a 1440×1000, 390×844 e 320×740, nessun overflow della pagina,
  nessuna immagine e nessun gradiente. Filtri corsi + ricerca Polimi verificati insieme.
- Politecnico di Milano compare fra i quattro enti; Passion in Action è un programma.
- Tab/Invio apre il dettaglio di un nodo; Escape chiude e ripristina il focus.
  Una mappa larga 793px scorre con le frecce dentro un pannello di 356px, senza
  allargare il documento da 390px. Fixture temporanea DOM, nessun dato reale aggiunto.
- Reset su 30 nodi: una sola ridisegnatura, 62 misure geometriche, 211 tratti conservati.
- Axe WCAG2 A/AA: zero violazioni automatiche in home, albero, dettaglio e registrazione.
  Etichette parzialmente nascoste nello scorrimento e simboli SVG controllati visivamente.
  Nessun errore JavaScript osservato. Non è una certificazione di accessibilità.

Screenshot in Windows Temp: `ramo-arc-home-desktop.png`, `ramo-arc-home-mobile.png`,
`ramo-arc-home-320.png`, `ramo-arc-tree-desktop.png`, `ramo-arc-tree-mobile.png`,
`ramo-arc-dialog-mobile.png`. Le prove aggiuntive vivono nel DB di collaudo separato:
non vengono copiate nell'anteprima Tailscale.

Review completate senza rilievi residui: `20261111-131329-program-identity`,
`20261111-133044-personal-progress`, `20261111-141528-automatic-skill-trees`.
I dettagli locali della revisione sono esclusi da Git; nessun invio a provider esterni.


### Rilascio dell'iterazione

Review visiva `20261111-144414-arc-dashboard`: complete / Ready to merge,
zero rilievi residui. Focus dei link scorrevoli verificato e corretto con bordo interno.
Tutte le feature sono passate da branch personali a main con merge diretto.

Anteprima aggiornata da main `be98753` l'11 novembre 2026, ore 15:50 CET.
Prima dell'upgrade: fermati i processi di scrittura, backup SQLite privato verificato
con integrity_check, associato a codice `1c2fd66` e schema 0003.
Backup locale: `.local/backups/pre-arc-be98753-20261111.sqlite3` (permessi 0600).
Dopo le migrazioni fino a 0007: dieci attività (nove pubbliche e la bozza precedente),
dodici identità di tappe e note conservate, tredici archi esatti, storico invariato.
I dati di collaudo aggiuntivi non sono stati trasferiti.

Verifica HTTPS dalla macchina Windows e da Edge: home, percorsi, enti e registrazione
rispondono 200; CSP e HSTS presenti. Asset aggiornati con hash. DEBUG e accessi demo
disattivati. Dialog dei nodi, navigazione e layout mobile verificati sul dominio
Tailscale; nessun errore JavaScript. Screenshot `ramo-live-home-mobile.png` e
`ramo-live-tree-mobile.png` in Windows Temp. Il link resta privato nella tailnet.

Monitoraggio del rilascio: durante la verifica il responsabile dell'implementazione
ha controllato risposte HTTP, avvio dei worker e console browser. Segnali attesi:
HTTP200 sulle pagine pubbliche, worker stabili, conteggi invariati. Errori 500,
traceback o perdita di dati richiedono stop del servizio e ripristino del backup
abbinato al vecchio codice; il ripristino elimina eventuali scritture successive.
Non sono stati osservati questi segnali. Non è stato configurato un monitoraggio continuo.
