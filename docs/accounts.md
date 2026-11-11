# Account personali ed email

L’account personale è gratuito e facoltativo: non crea un ente né assegna permessi di moderazione. La registrazione porta subito ai progressi, anche quando la verifica email è indisponibile. Il consenso «Tienimi nel giro: novità e attività del Poli» parte senza spunta. Si può attivare o revocare da **Account → Impostazioni account**. Il consenso non abilita campagne: nessun invio promozionale è implementato.

## Integrazione nel progetto

- Aggiungere `accounts` a `INSTALLED_APPS`.
- Includere `path("", include("accounts.urls"))` negli URL del progetto.
- Importare `accounts.mail_settings` nelle impostazioni. Contiene configurazione SMTP, flag `EMAIL_ENABLED`, origine pubblica e scadenze. Non stampare il modulo o i valori delle credenziali.
- Aggiungere al menu account il link `{% url 'accounts:profile' %}`.
- Eseguire `python manage.py migrate` nell’ambiente Linux del progetto.
- Integrazione indipendente dal nome del modulo settings: l’app usa `django.conf.settings`.

`accounts:profile` permette di cambiare nome utente e preferenze. Il cambio password usa le viste Django e conserva la sessione corrente; salva solo il campo password, preservando eventuali conferme email concorrenti. Il cambio email richiede la password attuale e una conferma al nuovo indirizzo; quello precedente resta attivo fino alla conferma. Una visita GET al link non modifica i dati: serve il pulsante protetto da CSRF. Un nuovo invio riuscito invalida il link precedente; un errore SMTP lo lascia valido. Un invio vecchio completato in ritardo non può sostituire la richiesta più recente. Cambiare password invalida anche le conferme email pendenti.

## Configurare Resend

Resend è stato scelto, ma non è configurato da questa modifica. Non è stata verificata alcuna consegna reale.

1. Nell’account Resend verificare il dominio del mittente, completando i record DNS richiesti dal provider.
2. Creare una chiave con il permesso necessario per inviare email e inserirla nel gestore segreti dell’ambiente come `RESEND_API_KEY`. Non copiarla nel repository, nei log o nella chat.
3. Impostare `DEFAULT_FROM_EMAIL` con un indirizzo del dominio verificato, per esempio `account@tuodominio.it` (solo indirizzo, senza nome visualizzato).
4. Impostare `POLISKILLED_PUBLIC_URL` all’origine HTTPS canonica, per esempio `https://poliskilled.tuodominio.it`, senza percorso, query o frammento. I link usano esclusivamente questo valore, mai l’header Host della richiesta.
5. Facoltativamente impostare `EMAIL_TIMEOUT` (secondi; predefinito 10), riavviare il servizio e provare una registrazione e un recupero su un indirizzo controllato.

Il backend configurato è `django.core.mail.backends.smtp.EmailBackend`, host `smtp.resend.com`, porta `465`, SSL attivo, utente `resend`, password da `RESEND_API_KEY`. Se manca chiave, mittente o origine pubblica, `EMAIL_ENABLED` resta falso: il recupero mostra che l’invio non è disponibile, senza dichiarare spedita una mail. La registrazione rimane funzionante. Non sono configurati backend console o invii simulati per la produzione.

I test usano esplicitamente il backend `locmem`; in quel contesto sovrascrivono anche `EMAIL_ENABLED=True`, mittente e origine pubblica. Il backend locmem non prova DNS, autenticazione SMTP, reputazione del mittente o consegna.

## Recupero e protezioni

Le viste Django gestiscono token password, scadenza di un’ora, cambio password e invalidazione dopo l’uso. Richieste per email note, sconosciute, inattive o senza password utilizzabile ricevono la stessa risposta pubblica. Un guasto SMTP viene intercettato senza esporre indirizzi o credenziali e produce la stessa risposta. Nessun `fail_silently=True`: gli errori del provider sono osservabili nei log tramite un messaggio generico. Gli invii sono sincroni, quindi il tempo di risposta può variare durante un invio; le risposte non espongono l’esistenza dell’account nel contenuto o nello stato HTTP.

La conferma email scade dopo 24 ore. CSRF è richiesto sulle mutazioni; le pagine account e recupero usano `no-store` e `Referrer-Policy: same-origin`. Il limite è condiviso nel database `hub.AuthThrottle`: namespace isolati, finestre di 900 secondi uguali a quelle del middleware esistente, 20 richieste per IP e 5 invii per destinazione/account a finestra. Il proxy segue la politica esistente di `hub.middleware.client_address`. Limiti e pulizia non dipendono dalla memoria del singolo worker.

## Account esistenti e integrità

`AccountProfile` è collegato uno a uno all’utente. L’email autorevole è normalizzata con NFKC, rimozione degli spazi esterni e casefold; il database applica unicità esatta e unicità case-insensitive. Gli indirizzi vuoti dei demo diventano `NULL`, quindi possono esistere più account demo senza email.

La migrazione iniziale crea i profili, normalizza anche `User.email` e lascia verifica e consenso non attivi. Prima di modificare dati controlla tutti gli indirizzi: duplicati normalizzati interrompono la migrazione con un errore. Non elimina, fonde o sceglie automaticamente un account. Risolvere esplicitamente l’ambiguità e ripetere la migrazione. Questa normalizzazione è irreversibile: prima del rilascio fare un backup consistente a scritture ferme. Il rollback richiede di ripristinare insieme database e versione del codice, non un migrate inverso.

Le registrazioni scrivono utente e profilo nella stessa transazione. Le conferme sono transazionali: un indirizzo occupato nel frattempo non può sostituire quello attuale. Il consenso ha `consent_at`; la revoca azzera consenso e timestamp. `email_verified_at` è separato. L’unico insieme eleggibile per eventuali future comunicazioni è `AccountProfile.objects.communication_recipients()`: account attivi, consenso attivo con timestamp e indirizzo confermato.

Gli utenti nuovi creati con `createsuperuser` o amministrazione ricevono un profilo normalizzato al primo accesso alle impostazioni o al recupero password. Non modificare direttamente `User.email` di un profilo esistente per cambiare indirizzo: usare il flusso account. Se uno script crea una divergenza, il recupero non invia token a quell’indirizzo e richiede una riconciliazione esplicita. L’app non introduce segnali che modifichino silenziosamente utenti gestiti altrove.

Il servizio Gunicorn distribuito registra solo metodo, stato e durata. I proxy devono adottare la stessa esclusione di path/query e Referer: i link di conferma e reset contengono token. Verificare la configurazione con un token sintetico prima di attivare gli invii.
