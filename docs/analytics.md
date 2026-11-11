# Risultati aggregati e preferenze personali

L’app `insights` separa due insiemi di dati: preferenze volontarie degli account e
contatori del pubblico. I digest dei browser non contengono né riferimenti agli
account né indirizzi IP, user agent, email o identificativi della sessione Django.
Non sono caricati servizi o script di analytics esterni.

## Integrazione

1. Aggiungere `insights` a `INSTALLED_APPS` e applicare la migrazione
   `insights.0001_initial` e le successive, che dipendono da `hub.0007_automatic_tracks` e dal modello
   utente configurato.
2. Aggiungere `insights.middleware.AudienceMiddleware` dopo autenticazione e
   `hub.middleware.SecurityHeadersMiddleware`. Il middleware conta solo risposte
   HTML pubbliche 200 delle route `home`, `activity`, `tracks`, `track`.
3. Includere `path("", include("insights.urls"))` nella configurazione URL.
4. In `base.html`, includere una volta
   `{% include "insights/partials/client.html" %}` nel body. Fornisce un token CSRF
   anche alle aperture anonime dei dialoghi e carica due script esterni. Non
   richiede modifiche ad `app.js`: intercetta i link esistenti `[data-node] > a`.
   Caricare il CSS `{% static 'insights/insights.css' %}` nel layout per stilare
   anche i pulsanti e le liste personali. La pagina risultati lo carica da sola.
5. Nelle pagine desiderate usare `{% load insights_tags %}` e
   `{% interest_button activity %}`, `{% follow_button track %}`,
   `{% saved_intents %}`. Quest’ultimo si integra in progressi/profilo e mostra
   soltanto le preferenze dell’utente corrente e attività ancora pubbliche.
   `interest_button` può essere incluso nel template del dialogo usando
   `step.activity`; lo script gestisce anche i pulsanti clonati dal template.
6. Collegare `insights:dashboard` solo per revisori e membri di enti verificati.
   L’autorizzazione viene comunque ricontrollata nel server. Per un ente specifico:
   `{% url 'insights:dashboard' %}?ente={{ organization.pk }}`.
7. Eseguire giornalmente `python manage.py cleanup_audience` con lo stesso ambiente
   del servizio. Il comando cancella in lotti da 1.000 righe fino a esaurimento;
   i file service/timer in `deploy/` sono esempi da installare sull’host scelto.

## Significato dei dati

- **Visitatori del sito:** browser stimati distinti nel mese, sulle pagine
  pubbliche ammesse. Il totale aggregato è visibile anche agli enti; solo i
  revisori possono vedere il grafico e le visualizzazioni complessive del sito.
- **Visualizzazioni:** aperture delle pagine delle attività e dei dialoghi nella
  mappa. Ripetizioni dello stesso browser sullo stesso oggetto entro 30 secondi
  sono ignorate. Un click che apre il dialogo seguito immediatamente dalla pagina
  dell’attività è quindi contato una sola volta.
- **Visitatori per attività:** browser distinti nel mese su quella attività.
  Non si sommano queste cifre per stimare le persone: lo stesso browser può
  visitare più attività. Le pagine e i dialoghi privati non vengono tracciati.
- **Attività pubblicate:** stato attuale delle attività della vista selezionata,
  non numero di pubblicazioni avvenute nel mese. La tabella include anche le
  attività attualmente non pubbliche e i loro dati storici, entro i permessi.
- **In calendario nel mese:** attività pubblicate con data di inizio nel mese
  selezionato. Non include attività senza data e non inventa date di pubblicazione.
- **Interessi e completamenti:** account distinti attualmente interessati o con
  almeno una attività completata; non sono iscrizioni ufficiali né misure di
  frequenza. La tabella conta gli account per singola attività. Le preferenze e i
  progressi cancellati non restano nel totale corrente.
- **Follower:** account che seguono un percorso pubblico. Per gli enti le persone
  coinvolte nelle tappe sono contate solo sulle proprie attività, includendo gli
  antenati pubblici secondo `build_track`; per la vista globale dei revisori il
  totale comprende anche i follower, senza duplicare account presenti in più
  categorie. Non vengono mostrati nomi, email o elenchi delle persone.

Il filtro `mese=YYYY-MM` accetta il mese corrente e i 23 precedenti. Visualizzazioni
e visitatori seguono questo filtro; preferenze, completamenti, follower e stato di
pubblicazione sono una fotografia attuale, esplicitata nell’interfaccia. Il filtro
`ente` è limitato alle appartenenze verificate dell’utente; i revisori possono
scegliere qualsiasi ente. Un’attività condivisa compare una volta sola. Le viste
sono di sola lettura e non aggiungono permessi di modifica delle attività.

## Cookie, conservazione e limiti

La prima visita pubblica valida crea un cookie casuale firmato
`poliskilled_audience`, HttpOnly, SameSite=Lax e Secure fuori dal debug. Il cookie
scade alla fine del mese del calendario Europe/Rome; il mese successivo viene
generato un nuovo valore indipendente. Il database conserva solo un HMAC con mese
e token; l’identità del browser non viene collegata all’utente autenticato. I
contatori incrementali giornalieri/mensili sopravvivono alla rimozione dei digest.

Il comando di pulizia elimina digest non più visti da oltre 40 giorni e mantiene
il mese corrente più i 23 precedenti di aggregati. L’activation marker resta per
mostrare la prima data realmente rilevata. Interessi e follow sono dati personali
volontari, separati dai digest: rimangono fino alla rimozione della preferenza o
dell’account. Non esiste un recupero retroattivo di visite precedenti all’attivazione.

HEAD, login, admin, proposte, copertine, asset, errori, prefetch, prerender e user
agent riconoscibili come bot sono esclusi. Non si salva lo user agent: viene
soltanto controllato in memoria. Il riconoscimento bot non è una garanzia contro
traffico artificiale. Cookie cancellati/bloccati e browser diversi possono
alterare le stime. Il cookie non è un conteggio di persone fisiche.

Le risposte tracciate sono `private, no-store` e variano su Cookie. Le scritture
usano vincoli univoci, transazioni e incrementi `F`; le ripetizioni ravvicinate
usano un aggiornamento condizionale atomico. Un `OperationalError` del contatore
non interrompe le pagine pubbliche; altri errori di codice non vengono mascherati.

## Preferenze anonime e sincronizzazione

“Mi interessa” e “Segui percorso” salvano localmente una chiave per preferenza
quando non si è autenticati. Dopo l’accesso vengono importate in modo idempotente
con POST e CSRF, massimo 200 per tipo a richiesta. Non aumentano i conteggi degli
enti prima dell’accesso. Interessi relativi ad attività private, mancanti o senza
ente verificato non sono importati e restano nel browser per un tentativo successivo.
Ogni scelta locale ha una versione; una risposta vecchia non cancella una scelta
ricreata nel frattempo. Il server conserva per la durata dell’account una ricevuta
hash della versione importata: un ritento tardivo non ripristina una preferenza
rimossa nell’account. Le ricevute non contengono dati del browser e si cancellano
con l’account. Se il browser nega localStorage, il messaggio
spiega che il salvataggio non è riuscito; non viene simulato un successo.

Le API dell’account verificano che la scheda appartenga all’account ancora attivo
tramite `X-Poliskilled-User`. Lo stesso header non viene inviato all’endpoint delle
visite. I progressi anonimi esistenti restano gestiti dall’app `hub`.

## Verifica

Test dell’app: accessi/IDOR per enti e revisori, attività multi-ente senza doppioni,
antenati pubblici nei percorsi, dati di altri enti esclusi, assenza di identità
nei risultati, interessi/follow idempotenti e protetti da CSRF, rotazione mensile,
dedup giornaliera e mensile, esclusioni bot/private/prefetch/HEAD, conservazione e
disponibilità delle pagine in caso di errore transitorio del contatore.

`node --test tests-js/insights.test.cjs` verifica il salvataggio locale per chiave,
la rimozione, gli import idempotenti, il rifiuto dello storage e i limiti del lotto.
La versione integrata è stata verificata in browser su desktop, mobile e tastiera.
