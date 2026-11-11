# Percorsi automatici

Un moderatore crea un percorso con nome e descrizione. Il colore deriva stabilmente
dal suo identificativo, scegliendo fra sei colori accessibili della palette.

Chi propone un'attività può scegliere uno o più percorsi, un'icona da un set chiuso
e le attività precedenti. I successivi sono derivati: non vanno inseriti due volte.
La selezione è facoltativa e il modulo cerca fra le sole attività pubbliche.

Dopo l'approvazione il sito raccoglie le attività del percorso e i loro antenati
pubblici. Un ordinamento topologico determina i livelli in base al cammino più lungo:
non esiste più un limite di tre livelli o un posizionamento manuale. Il browser
disegna solo i collegamenti presenti nei dati e li ricalcola al ridimensionamento.
Le mappe larghe scorrono all'interno del pannello, anche da tastiera.

Il controllo dei cicli include anche le proposte non pubblicate e viene ripetuto
nella transazione di salvataggio. Le scelte validate restano esplicite: se nel
frattempo un ente è revocato, una tappa torna privata o un percorso viene eliminato,
il salvataggio chiede di ricaricare invece di perdere silenziosamente i collegamenti.

Un collegamento già esistente verso una tappa temporaneamente privata si conserva
quando si modifica la proposta, ma non ne espone il nuovo titolo. La mappa pubblica
esclude i nodi e i collegamenti privati. Il completamento resta legato all'attività,
quindi cambiare percorso, icona o livello nella mappa non azzera i progressi.

Le dipendenze sono suggerimenti editoriali, non requisiti ufficiali dei team.
Le icone sono SVG funzionali originali. Nessun dato di posizione o colore libero
deve essere inserito dai proponenti.


Il modulo firma lo stesso insieme di collegamenti pubblici che mostra all'apertura.
Scelte e selezioni sono congelate insieme: una modifica della visibilità mentre
la pagina viene generata non può eliminare una relazione non vista. I moduli
precedenti all'aggiornamento richiedono una ricarica prima del salvataggio.
