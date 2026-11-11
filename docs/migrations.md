# Aggiornamento dati e ripristino

Prima di aggiornare l'anteprima, arrestare i worker e creare un backup SQLite
con l'API `Connection.backup()`, conservandolo fuori dal versionamento con permessi 600.

La migrazione 0004 consolida l'ente errato Passion in Action nel Politecnico di Milano.
Preserva gli altri organizzatori, proposte, revisioni e thread; non trasferisce
le membership dell'ente errato al Politecnico. Se il nome del Politecnico è occupato
da un ente non verificato, la migrazione si interrompe atomicamente: un amministratore
deve verificare l'identità reale e riconciliare il record prima di riprovare.

La migrazione è irreversibile: per tornare alla versione precedente, arrestare
i worker, ripristinare il backup completo del database e il commit precedente insieme,
poi riavviare. Non usare una migrazione inversa per ricostruire identità o membership.

Backup locale di questa iterazione: `.local/backups/before-progress.sqlite3`.
Il database di sviluppo della nuova versione è separato: `.local/dev-next.sqlite3`.
Nessuno dei due file deve essere aggiunto a Git.


La migrazione 0007 converte i livelli manuali in collegamenti fra attività,
preservando gli identificativi delle tappe per importare le vecchie spunte.
Se gli stessi corsi avevano ordinamenti contraddittori fra percorsi, rileva il ciclo
e si interrompe senza modificare i dati. Anche questa conversione è irreversibile:
per il rollback usare il backup e il commit corrispondente.
