#!/usr/bin/env bash
set -euo pipefail

# IMS Ubuntu Server Bootstrap (EC2-friendly)
# - Installs Docker Engine + Compose plugin
# - Starts full stack from compose.yaml
# - Runs Grafana in Docker with provisioning for Prometheus + dashboard import

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COMPOSE_FILE="${REPO_ROOT}/compose.yaml"
readonly GRAFANA_DIR="${REPO_ROOT}/monitoring/grafana"
readonly GRAFANA_PROVISIONING_DIR="${GRAFANA_DIR}/provisioning"
readonly GRAFANA_DS_DIR="${GRAFANA_PROVISIONING_DIR}/datasources"
readonly GRAFANA_DASH_DIR="${GRAFANA_PROVISIONING_DIR}/dashboards"
readonly DASHBOARDS_JSON_DIR="${GRAFANA_DIR}"
readonly DASHBOARD_JSON_FILE="${DASHBOARDS_JSON_DIR}/ims-observability-dashboard.json"
readonly OVERRIDE_FILE="${REPO_ROOT}/compose.grafana.override.yaml"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

require_file() {
  if [[ ! -f "$1" ]]; then
    log "ERROR: required file not found: $1"
    exit 1
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed."
    return
  fi

  log "Installing Docker Engine and Compose plugin..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl gnupg lsb-release
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable docker
  sudo systemctl start docker
}

ensure_user_can_run_docker() {
  if groups "${USER}" | grep -q "\bdocker\b"; then
    return
  fi
  log "Adding user '${USER}' to docker group..."
  sudo usermod -aG docker "${USER}"
  log "IMPORTANT: Re-login is required for docker group changes to apply."
  log "For this session, script will continue using sudo docker."
}

docker_compose_cmd() {
  if groups "${USER}" | grep -q "\bdocker\b"; then
    echo "docker compose"
  else
    echo "sudo docker compose"
  fi
}

prepare_grafana_provisioning() {
  log "Preparing Grafana provisioning files..."
  mkdir -p "${GRAFANA_DS_DIR}" "${GRAFANA_DASH_DIR}"

  cat > "${GRAFANA_DS_DIR}/prometheus.yaml" <<'YAML'
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
YAML

  cat > "${GRAFANA_DASH_DIR}/dashboards.yaml" <<'YAML'
apiVersion: 1
providers:
  - name: ims-dashboards
    orgId: 1
    folder: IMS
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
YAML

  require_file "${DASHBOARD_JSON_FILE}"
}

write_grafana_override_compose() {
  log "Writing Grafana compose override..."
  cat > "${OVERRIDE_FILE}" <<'YAML'
services:
  grafana:
    image: grafana/grafana:11.2.2
    container_name: incident-grafana
    depends_on:
      - prometheus
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    ports:
      - "3000:3000"
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana:/var/lib/grafana/dashboards:ro
YAML
}

start_stack() {
  local compose
  compose="$(docker_compose_cmd)"
  log "Starting IMS stack (including Prometheus + Grafana)..."
  cd "${REPO_ROOT}"
  ${compose} -f "${COMPOSE_FILE}" -f "${OVERRIDE_FILE}" up -d --build
}

print_access_info() {
  cat <<'EOF'

Stack is up. Access:
- Backend API:        http://<SERVER_IP>:8000
- Frontend:           http://<SERVER_IP>:5173
- Prometheus:         http://<SERVER_IP>:9090
- Grafana:            http://<SERVER_IP>:3000
  - Username: admin
  - Password: admin

Useful commands:
- Logs:        docker compose -f compose.yaml -f compose.grafana.override.yaml logs -f
- Restart:     docker compose -f compose.yaml -f compose.grafana.override.yaml up -d --build
- Stop:        docker compose -f compose.yaml -f compose.grafana.override.yaml down

If Docker permission is denied after script:
1) log out
2) log back in
3) run: docker ps
EOF
}

main() {
  require_file "${COMPOSE_FILE}"
  require_file "${DASHBOARD_JSON_FILE}"
  install_docker
  ensure_user_can_run_docker
  prepare_grafana_provisioning
  write_grafana_override_compose
  start_stack
  print_access_info
}

main "$@"
