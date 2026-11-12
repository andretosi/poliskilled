# Catalogo reale e collegamenti editoriali

Verifica del **12 novembre 2026**, fuso Europe/Rome. PoliSkilled è indipendente:
la presenza di un ente nel catalogo non significa che abbia un account, approvi
il progetto o abbia autorizzato l’uso del proprio logo.

Il [dataset](../data/catalog/current.json) contiene 107 attività e 49 enti.
Ogni attività conserva una fonte primaria, il periodo noto, lo stato delle
iscrizioni e i requisiti indicati dall’organizzatore. Nessun orario è inventato
quando la fonte indica solo il giorno. I testi sono brevi sintesi originali.

## Ricerca svolta

- **Passion in Action:** tutte le 20 schede nell’indice attivo e 110 schede
  dell’archivio con iscrizioni nel 2026. Inserite 35 attività uniche ancora
  pertinenti: 13 con iscrizioni aperte alla verifica e 22 con iscrizioni chiuse,
  anche quando il corso è ancora in svolgimento. [Metodo, esclusioni e fonti](catalog/passion-coverage.md).
- **Associazioni:** controllati tutti i 31 enti presenti nell’[albo Polimi](https://www.polimi.it/studenti/associazioni-degli-studenti),
  visitando siti e calendari pubblici disponibili. Dove non è stato possibile
  verificare iniziative attuali, resta il solo profilo dell’ente.
  [14 associazioni scientifiche](catalog/technical-coverage.md) e
  [17 culturali, sociali, internazionali e sportive](catalog/community-coverage.md).
- **Competizioni:** controllate le 20 schede nell’[indice ufficiale](https://www.polimi.it/campus-e-servizi/sport-e-tempo-libero/competizioni-internazionali).
  Sono inclusi anche X-Culture, IREC, CFA Research Challenge e Students Reinventing
  City, con i rispettivi vincoli di accesso, senza presentare bandi non pubblicati
  come aperti. Alcuni team si accedono tramite insegnamenti o tesi: le schede lo dicono.

Le tabelle `*-coverage.json` conservano gli esiti puntuali della ricerca.
La copertura dell’albo non garantisce la completezza di calendari privati, social
non leggibili o programmi pluriennali anteriori al 2026. Il catalogo è una fotografia
curata, **non un aggiornamento automatico dei siti esterni**.

## Come nasce l’albero

Il progetto, corso o evento scelto è l’obiettivo. Ogni scheda può indicare soltanto
altre attività preparatorie: il sistema risale i collegamenti, elimina i doppioni
e dispone livelli e rami automaticamente. I cicli sono rifiutati. Le proposte
private non compaiono nell’albero pubblico.

Per 47 obiettivi abbiamo proposto collegamenti utili fra attività reali. Le motivazioni
sono in `preparation_notes` e nella pagina dell’attività; tutti gli archi di questo
catalogo sono **preparazioni consigliate da PoliSkilled**, autorizzate nel brief.
I requisiti della fonte sono invece in `official_requirements`.

Esempio: materiali Python e Git → ARGO Training → ARGO; Arduino → PCB → ARGO è
un ramo per l’elettronica. ARGO e il training sono documentati nella call AEA
2026/27. La presenza dei materiali POuL nell’albero è una scelta editoriale,
non un requisito di AEA né una collaborazione dichiarata fra i due enti.

I rami possono rappresentare preparazioni diverse: per il musical la fonte indica
esperienza di canto **oppure** recitazione. Non è necessario spuntare tutti i nodi
per partecipare. I corsi a calendario hanno selezioni e scadenze proprie: l’albero
descrive competenze utili, non garantisce di poter frequentare l’edizione mostrata.

## Aggiornamento del catalogo

```bash
python manage.py import_catalog --dry-run
python manage.py import_catalog --archive-demo
```

L’importazione è transazionale e idempotente. Le chiavi esterne identificano le
attività; una firma nell’audit impedisce di sovrascrivere schede modificate nel sito.
L’utente tecnico `poliskilled-catalog` è inattivo e senza password. I nuovi enti
sono profili documentati, non account verificati o autorizzati a proporre.
La verifica e l’assegnazione di un referente spettano ai gestori: da
**Gestione → Enti e referenti** collegano un account personale già registrato,
dopo verifica attraverso i contatti ufficiali. L’operazione è auditata e separata
dall’approvazione dell’ente. Nessuna adesione automatica a un profilo esistente.

`--archive-demo` nasconde le vecchie schede dimostrative senza cancellare progressi,
commenti o preferenze. I vecchi percorsi sono conservati soltanto come storico.
Prima di aggiornare un’installazione esistente: backup consistente del database,
migrazioni, importazione, verifica dei conteggi e riavvio; vedi [deploy](deployment.md).
