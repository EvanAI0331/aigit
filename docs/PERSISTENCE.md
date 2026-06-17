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

The ops loop runs immediately on service start, then every 12 hours.

## Logs

Keep runtime logs out of git:

```text
logs/
```
