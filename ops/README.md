# Mantener http://localhost:5000 siempre encendido

Esta app se mantiene viva con dos capas:

1. `ops/run_forever.sh` arranca `server.py` y lo vuelve a levantar si el proceso termina.
2. `ops/sovd-dashboard.service` permite que `systemd` lo arranque automáticamente al encender la máquina.

## Arranque manual con autoreinicio

```bash
./ops/run_forever.sh
```

Logs:

```text
journalctl -u sovd-dashboard.service
```

## Instalar como servicio permanente

Desde `/home/sovd_user/sovd_practice`:

```bash
sudo cp ops/sovd-dashboard.service /etc/systemd/system/sovd-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now sovd-dashboard.service
sudo systemctl status sovd-dashboard.service
```

Después de esto, `http://localhost:5000` se levantará al arrancar la máquina y se reiniciará si el servidor se cae.

## Instalar el ECU DoIP permanente

El botón `Execute ReadDID` necesita que el simulador DoIP esté escuchando en `127.0.0.1:13400`.

```bash
sudo cp ops/sovd-doip-ecu.service /etc/systemd/system/sovd-doip-ecu.service
sudo systemctl daemon-reload
sudo systemctl enable --now sovd-doip-ecu.service
sudo systemctl status sovd-doip-ecu.service
```

Logs:

```text
journalctl -u sovd-doip-ecu.service
```
