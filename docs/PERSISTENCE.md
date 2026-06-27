# Local Persistence

Use a process supervisor for long-running operation. On macOS, LaunchAgent is the simplest local option.

The project provides two generic scripts:

```bash
scripts/run_web.sh
scripts/run_ops_loop.sh
```

Both scripts load `.env`, initialize the database, compile specs, and then run the service.

## Services

- Web/API: `python -m aigithub_radar.service_entry web`
- Ops loop: `python -m aigithub_radar.service_entry ops`
- Market monitor loop: `python -m aigithub_radar.service_entry monitor`

The ops loop runs immediately on service start, then every 12 hours.
The market monitor loop runs immediately on service start, then every 1 hour. It only collects platform evidence, runs `market_monitor_agent`, and writes dynamic candidate themes into the database. It does not run full repository analysis.

## Logs

Keep runtime logs out of git:

```text
logs/
```
