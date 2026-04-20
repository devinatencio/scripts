# systemd service for es-daemon

## Quick install

```bash
# 1. Create a service user (if it doesn't exist)
sudo useradd -r -s /sbin/nologin -d /opt/s3server elastic

# 2. Ensure the app directory is owned correctly
sudo chown -R elastic:elastic /opt/s3server

# 3. Copy the unit file
sudo cp es-daemon.service /etc/systemd/system/

# 4. (Optional) Copy the env file and edit as needed
sudo cp es-daemon.env /etc/default/es-daemon

# 5. Reload systemd, enable, and start
sudo systemctl daemon-reload
sudo systemctl enable es-daemon
sudo systemctl start es-daemon
```

## Common commands

```bash
sudo systemctl status es-daemon      # check status
sudo systemctl restart es-daemon     # restart
sudo systemctl stop es-daemon        # stop
journalctl -u es-daemon -f           # tail logs
journalctl -u es-daemon --since today  # today's logs
```

## Paths to adjust

The unit file assumes:

| Setting | Default | Notes |
|---|---|---|
| Install dir | `/opt/s3server` | `WorkingDirectory` in the unit |
| Python | `/opt/s3server/venv/bin/python` | virtualenv path in `ExecStart` |
| Config | `/opt/s3server/daemon_config.yml` | `--config` flag in `ExecStart` |
| Log dir | `/opt/s3server/logs` | allowed via `ReadWritePaths` |
| Metrics dir | `/opt/s3server/server/metrics` | allowed via `ReadWritePaths` |
| User/Group | `elastic` | change to match your environment |

Edit the unit file or override with `systemctl edit es-daemon` if your layout differs.
