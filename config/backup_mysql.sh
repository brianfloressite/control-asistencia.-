#!/usr/bin/env bash
# Respaldo diario de la base de datos (RNF10). Programar con cron:
#   0 2 * * * /opt/control-asistencia/config/backup_mysql.sh
set -euo pipefail
DESTINO="${BACKUP_DIR:-/var/backups/asistencia}"
mkdir -p "$DESTINO"
mysqldump --single-transaction --routines bd_asistencia | gzip > "$DESTINO/bd_asistencia_$(date +%Y%m%d_%H%M).sql.gz"
find "$DESTINO" -name "*.sql.gz" -mtime +30 -delete   # conserva 30 días
