# Distribuire main

Questa configurazione è preparata, non installata su un server pubblico.
Il servizio assume Linux, Python 3.12, Caddy e un utente dedicato `poliskilled`.

1. Copia/clona la repository in `/srv/poliskilled`, usa esclusivamente main verificato.
2. Crea `.venv` e installa `requirements.txt`.
3. Prepara `/srv/poliskilled/var` e `/srv/poliskilled/media`, scrivibili dall'utente poliskilled;
   lascia il codice non scrivibile dal servizio.
4. Crea `/etc/poliskilled.env`, permessi 0600, con una chiave casuale lunga (almeno 50 caratteri)
   e le variabili seguenti. Il file non va mai committato.
5. Carica quelle variabili nella shell amministrativa e avvia `manage.py migrate`,
   `manage.py collectstatic --noinput`, `manage.py check --deploy`,
   `manage.py createsuperuser`. Inserisci le credenziali direttamente nel terminale.
   Per il primo gestore usa `manage.py grant_site_admin nomeutente` su un account
   registrato. I successivi si abilitano dalla dashboard Gestione.
6. Installa `deploy/poliskilled.service` e le unità `poliskilled-cleanup.service/timer`.
   Abilita il timer con `systemctl enable --now poliskilled-cleanup.timer`.
   Adatta il dominio in `deploy/Caddyfile`;
   Caddy termina HTTPS e inoltra al solo listener loopback Gunicorn.
7. Avvia i servizi e verifica home, login, proposta e moderazione con account reali autorizzati.

```dotenv
DJANGO_DEBUG=0
POLISKILLED_DEMO=0
DJANGO_SECRET_KEY=<chiave privata casuale>
DJANGO_ALLOWED_HOSTS=poliskilled.example.org
DJANGO_CSRF_ORIGINS=https://poliskilled.example.org
DJANGO_DB_PATH=/srv/poliskilled/var/poliskilled.sqlite3
DJANGO_TRUST_LOCAL_PROXY=1
```

`DJANGO_TRUST_LOCAL_PROXY=1` è solo per questa topologia: listener loopback e proxy
che sovrascrive X-Real-IP. Non esporre Gunicorn a internet né fidarti di header di
proxy provenienti da client arbitrari. Caddy limita il body a 4 MB; Django limita
anche i file in streaming a 3 MiB, senza aspettare che siano scritti su disco.
Le copertine sono convertite in JPEG; i loghi in PNG, senza metadati, massimo 512 px.
Entrambi passano da viste con controllo permessi.
Non aggiungere un alias pubblico diretto a `media/`: esporrebbe copertine private.

I revisori ordinari ricevono solo il permesso `hub.review_activity`, senza `is_staff`
né superuser. I superuser sono amministratori dell'installazione, altamente fidati.
Verifica l'identità degli enti contattando i referenti tramite canali ufficiali
prima di approvare. I co-organizzatori indicati in una proposta
sono controllati dal revisore, non ricevono un invito automatico.

## Main e aggiornamenti

Il merge su main definisce la release. Su un hosting ancora da scegliere, collega
la pipeline di deploy al superamento della CI di main. Non è stato inserito un
deploy fittizio con segreti o destinazione non disponibili.

Per aggiornamento manuale: finestra di manutenzione, backup, arresto servizio,
`git pull --ff-only origin main`, installazione requirements, migrate, collectstatic,
check --deploy, riavvio. Per SQLite usa un solo host e backup consistente del database,
con servizio fermo o API backup SQLite, più la directory media. Non copiare un file
SQLite durante scritture attive.

La migrazione iniziale degli account normalizza gli indirizzi ed è irreversibile.
Per tornare alla release precedente ripristinare il backup insieme al codice;
non eseguire un migrate inverso. I duplicati normalizzati interrompono il rilascio
e richiedono una decisione esplicita del responsabile, senza fusioni automatiche.

## Verifica operativa

Responsabile: amministratore che esegue il deploy. Nei primi 30 minuti controlla
`journalctl -u poliskilled`, risposte 5xx, eccezioni `OperationalError` / `database is locked`,
413/429 inattesi e dimensione di database, media e disco temporaneo.
Segnali sani: home200, login valido, proposte private404 per anonimi, approvazione visibile.
Se un flusso fallisce, ferma il servizio, ripristina commit precedente e backup compatibile
con le migrazioni prima del riavvio. Non fare downgrade del solo codice su uno schema incompatibile.
Pulisci periodicamente le sessioni scadute con `manage.py clearsessions`.

## Email e conservazione

Configurare Resend seguendo [accounts.md](accounts.md). Servono dominio verificato,
`RESEND_API_KEY`, `DEFAULT_FROM_EMAIL` e `POLISKILLED_PUBLIC_URL`. Mantenere stabile
`DJANGO_SECRET_KEY`: cambiarla invalida sessioni e link di recupero/conferma pendenti.
L'anteprima genera una chiave temporanea solo se non ne viene fornita una.

Il formato access log Gunicorn distribuito registra solo metodo, stato e durata.
Non abilitare log di URL, query o Referer sul proxy: i percorsi di conferma e reset
contengono token. Il Caddyfile fornito non abilita access log HTTP. Prima degli
invii reali controllare il percorso completo con un token sintetico.

`poliskilled-cleanup.timer` applica ogni giorno la conservazione descritta in
[analytics.md](analytics.md): digest oltre 40 giorni, aggregati oltre 24 mesi.
Verificare `systemctl list-timers poliskilled-cleanup.timer` e l'esito del servizio.
Il timer richiede lo stesso database dell'applicazione; il servizio scrive solo in `var`.
I report non ricostruiscono visite precedenti all'attivazione.

Per traffico elevato o più host, pianifica PostgreSQL e una nuova verifica della concorrenza.
Non cambiare solo l'ENGINE: la strategia IMMEDIATE è specifica a SQLite.
