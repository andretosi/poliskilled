# Alberi per obiettivo e catalogo reale

Decisione di Andrea, 12 novembre 2026: ogni attività è un obiettivo. L’albero resta
visuale, con l’obiettivo in cima e tutte le tappe precedenti. Nessun percorso nominato
da creare separatamente. Collegamenti editoriali consentiti fra attività reali;
devono essere distinti dai requisiti ufficiali delle fonti.

- [x] Albero per attività, proposte con soli predecessori, preferenze e report per obiettivo.
- [x] Ricerca su catalogo Passion in Action, tutte le associazioni nell’albo e team competitivi.
- [x] Importazione idempotente delle schede reali con fonti/date, archiviazione dei demo.
- [x] Collegamenti editoriali motivati, senza attività inventate.
- [ ] Test funzionali, browser mobile/desktop, review, pubblicazione e preview.

Workspace isolato: codex/objective-catalog, base b3013be. Nessun WIP preesistente.
Esecuzione nativa; tre ricerche indipendenti scrivono soltanto in .local/research.
I completamenti esistenti restano associati alle attività originali; nessuna spunta
di un esempio viene attribuita a un corso diverso. I vecchi percorsi restano nello
storico del database, senza nuove iscrizioni o pagine pubbliche dedicate.

## Verifica eseguita

- 107 attività reali, 49 enti; 47 obiettivi con preparazioni editoriali motivate.
- Browser Edge: 1440 px, 390 px e 320 px; nessun overflow della pagina.
- Salvataggio anonimo dell’obiettivo ARGO e completamento Python, ricarica e sync
  dopo login: verificati. Il nuovo corso sintetico di QA è stato creato soltanto
  nel database locale di prova, approvato da un altro account e mostra il suo albero.
- Referente collegato da gestore, richiesta dell’ente comparsa, approvazione separata,
  account del referente abilitato a proporre: verificato in browser.
- Report filtrato per ente: conteggi delle sole tappe proprie, scelta dell’obiettivo
  aggregata, nessuna identità dei partecipanti. Nessun errore JavaScript osservato.
- Rehearsal su copia consistente del database dell’anteprima: 107 create, 9 demo
  archiviati; secondo import 0 create/aggiornate/preservate. PK di progressi e
  preferenze invariati. Mai usato il database di QA per il rilascio.
- Simplify inline: eliminate viste/template/CSS dei percorsi autonomi e il pulsante
  follow inutilizzato; rimossa una query superflua. Compatibilità dei dati storici
  preservata. Stato disponibilità riunito nella stessa property per le tre viste.
- Review indipendente ce-code-review: correzioni per UTC, aggiornamenti del grafo,
  identità stabile/privilegi degli enti, metadati editabili, referenti e paginazione.
  Ricevuta privata in docs/reviews/objective-catalog-20261112; pubblicazione dopo
  il gate finale, secondo docs/deployment.md.
