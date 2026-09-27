# systemd examples

Docker Compose owns container restart behavior via `restart: unless-stopped`; a separate systemd service is unnecessary for stack startup. The included backup service/timer is optional and must be reviewed for Ministry schedule, secret-bearing backup storage, retention and off-host transfer before enabling.

Install with `sudo cp config/systemd/nexaserve-backup.{service,timer} /etc/systemd/system/`, inspect/edit the timer, then `sudo systemctl daemon-reload`; enable only after backup path is approved: `sudo systemctl enable --now nexaserve-backup.timer`. Check with `systemctl list-timers nexaserve-backup.timer` and `journalctl -u nexaserve-backup.service`.
