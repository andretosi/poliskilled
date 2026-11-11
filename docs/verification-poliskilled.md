# Verifica PoliSkilled — 11 novembre 2026

## Codice

- 158 test Django e 20 test JavaScript superati, anche nella verifica indipendente.
- Ruff, formattazione e controllo migrazioni senza errori.
- Controllo impostazioni produzione superato; pip-audit senza vulnerabilità note.
- Review completate per identità/albero, enti/gestori e account/risultati. Le correzioni
  includono autorizzazioni, invii email sovrapposti, importazioni da più schede,
  disponibilità dei contatori e numero di query indipendente dal numero di percorsi.

## Browser

Edge: desktop 1440 px, mobile 390 px e 320 px; navigazione anche da tastiera.
Verificati dashboard pubblica, filtri, mappa e dialoghi, preferenze anonime persistenti,
registrazione senza consenso selezionato e importazione dei progressi nell’account.
Verificati impostazioni, cambio password, consenso revocabile, caricamento logo,
assegnazione/rimozione ruolo gestore e report limitati all’ente.

Nessun errore JavaScript rilevato. Axe non segnala violazioni nelle pagine verificate;
i casi non determinabili automaticamente (grafici, simboli e tabelle scorrevoli) sono
stati controllati visivamente. Gli screenshot del README provengono dall’app funzionante.
I dati e gli account di collaudo sono rimasti in un database separato da quello remoto.

## Limiti espliciti

L’anteprima HTTPS Tailscale è stata aggiornata conservando il database, dopo backup
a servizio fermo. Migrazioni applicate e primo gestore abilitato. Servizio preview
e timer di pulizia risultano attivi; il comando di pulizia ha restituito successo.
Home pubblica verificata dal browser remoto, senza accessi demo o errori JavaScript.

Le email sono provate con il backend di test in memoria, inclusi token, scadenza,
riutilizzo, errori SMTP e concorrenza. Resend non è ancora configurato: nessuna
consegna reale è stata verificata. Servono dominio verificato, mittente, chiave
del provider e origine HTTPS canonica.

I contatori iniziano all’attivazione e stimano browser, non persone. Il traffico
headless dei test è escluso. Non sono stati simulati utenti per gonfiare i risultati.
L’hosting pubblico e il deploy automatico da main restano da scegliere.
