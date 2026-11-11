# PoliSkilled

- Django server-rendered, HTML/CSS e JavaScript essenziale. Nessuna SPA o API separata senza motivo.
- Codice in inglese; interfaccia e documentazione in italiano. File piccoli con una responsabilità.
- Decisioni del brief in agents.py; avanzamento in docs/tasks.md.
- WSL Ubuntu-26.04: checkout su /home/anthor/projects/poliskilled; mai test Linux su /mnt/c.
- main rappresenta la versione distribuibile. Mai sviluppare direttamente su main.
- Una branch personale per una feature piccola: nome/feature. Una sola persona per branch.
- Worktree facoltativi, uno per feature. Verificare, poi merge diretto su main; niente develop.
- Non pubblicare o usare veri account di enti senza autorizzazione.
- Dati reali con URL della fonte; non inventare iscrizioni aperte o prerequisiti ufficiali.
- Non esporre proposte/thread privati. Richiedere CSRF su ogni mutazione.
- Non permettere auto-approvazioni o registrazione dentro un ente già esistente.
- Test: .venv/bin/python manage.py test; .venv/bin/ruff check .; ruff format --check .
- Cambi UI: verificare desktop, mobile, tastiera e flusso interessato in un browser.
- Accessi demo solo con DJANGO_DEBUG=1 e POLISKILLED_DEMO=1 su loopback.
