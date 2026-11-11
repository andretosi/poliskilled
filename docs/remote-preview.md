# Anteprima dal telefono con Tailscale

Tailscale Serve espone l'anteprima solo nella tailnet, in HTTPS.
Il telefono deve avere Tailscale attivo nella stessa rete; Windows e WSL devono
rimanere accesi. Non è stata attivata la pubblicazione Internet tramite Funnel.

L'anteprima usa Gunicorn su loopback, DEBUG disattivato, cookie sicuri e nessun
accesso demo automatico. Lo sviluppo locale resta su http://127.0.0.1:8000.

## Avvio

Da PowerShell, ricava il nome DNS del PC senza il punto finale:

```powershell
$poliskilledHost = ((& 'C:\Program Files\Tailscale\tailscale.exe' status --json | ConvertFrom-Json).Self.DNSName).TrimEnd('.')
wsl.exe -d Ubuntu-26.04 --cd /home/anthor/projects/poliskilled -- .venv/bin/python scripts/preview.py $poliskilledHost
```

Il comando resta attivo e raccoglie gli asset aggiornati prima di avviare Gunicorn.
In un'altra finestra PowerShell:

```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' serve --bg --https=443 http://127.0.0.1:8002
& 'C:\Program Files\Tailscale\tailscale.exe' serve status
```

Apri l'URL HTTPS mostrato; aggiungi /percorsi/ per lo skill tree.
Il proxy Tailscale rimane configurato; il processo Python va riavviato dopo
lo spegnimento del PC o per caricare modifiche a codice/template/asset.

Per fermare l'anteprima usa Ctrl+C sul processo Python.
Per rimuovere esclusivamente questo inoltro: `tailscale serve --https=443 off`.
Non eseguire reset se esistono altri servizi.

La chiave Django viene generata in memoria a ogni avvio, salvo una variabile
DJANGO_SECRET_KEY fornita dal chiamante. Il riavvio può quindi chiudere le sessioni
dell'anteprima; nessuna chiave viene stampata o scritta su file.
Il database è quello locale del progetto: le modifiche fatte dall'anteprima restano.

## Servizi installati sulla macchina di sviluppo

L’11 novembre 2026 l’anteprima è stata spostata su un servizio utente systemd in WSL:
`poliskilled-preview.service`. È abilitato all’avvio della sessione utente WSL;
Windows e la distribuzione devono comunque essere in esecuzione.

```bash
systemctl --user status poliskilled-preview.service
systemctl --user restart poliskilled-preview.service
systemctl --user stop poliskilled-preview.service
```

Il servizio usa il database del progetto e raccoglie gli asset prima dell’avvio.
Non avviare contemporaneamente il comando manuale sulla stessa porta.
È installato anche `poliskilled-cleanup.timer`, quotidiano e persistente; il primo
avvio manuale della pulizia è terminato con successo. Controllare con:

```bash
systemctl --user list-timers poliskilled-cleanup.timer
systemctl --user show poliskilled-cleanup.service -p Result -p ExecMainStatus
```

Il rilascio ha conservato account e progressi, applicato le migrazioni e creato un
backup privato consistente prima dell’aggiornamento. Il backup rimane fuori dal
repository pubblico insieme ai dati e ai loghi caricati.

Riferimenti: [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve),
[comando Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).
