# Progressi personali

La consultazione e il completamento non richiedono un account. Le spunte anonime
restano in localStorage; ogni attività ha una chiave separata, per evitare che due
schede sovrascrivano modifiche diverse. Il passaggio dai vecchi identificativi
delle tappe agli identificativi delle attività è automatico.

Al login le spunte anonime vengono unite ai progressi dell'account e rimosse dalla
parte anonima dopo la conferma del server. Cache e modifiche in attesa sono separate
per account. Uscire non copia i progressi personali nella sessione anonima.

Le modifiche offline vengono ritentate alla riapertura, al ritorno sulla finestra
o al ripristino della connessione. Una spunta su un'attività tornata in revisione
rimane in attesa; nessun titolo privato viene esposto. Una successiva pubblicazione
permette di sincronizzarla. Le spunte già salvate sopravvivono alla moderazione.

Un Web Lock per account serializza le richieste fra schede. Una revisione
verificata atomicamente dal server impedisce a richieste scadute e arrivate tardi
di sovrascrivere modifiche già confermate. La pagina confronta
anche l'identità dell'account con la sessione attuale: una scheda vecchia si ricarica
senza scrivere nel nuovo account. Fra dispositivi diversi prevale l'ultima modifica
ricevuta dal server. Per aggiornare un altro dispositivo basta tornare sulla pagina.

La sincronizzazione richiede HTTPS (o localhost) e un browser con
[Web Locks](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API).
Se non disponibili, le modifiche rimangono nel browser e l'interfaccia lo indica.

Verifica: `node --test tests-js/*.test.cjs`, incluso in `scripts/check.sh`.
I test simulano richieste ritardate fra schede, importazioni a lotti, temporanea
moderazione e ripristino di modifiche offline. Node serve solo per questi test,
non per eseguire Django o distribuire il sito.

