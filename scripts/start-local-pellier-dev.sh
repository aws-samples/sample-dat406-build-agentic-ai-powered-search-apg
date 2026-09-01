#!/usr/bin/env bash
# Start an isolated Pellier HMR stack: FastAPI on 8003 and Vite on 5173.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/pellier/backend"
FRONTEND_DIR="${REPO_ROOT}/pellier/frontend"
BACKEND_HOST="${PELLIER_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${PELLIER_BACKEND_PORT:-8003}"
BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
BACKEND_PYTHON="${BACKEND_DIR}/.venv/bin/python"
BACKEND_PID=""
TUNNEL_PID=""

dotenv_value() {
  awk -F= -v key="$1" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' \
    "${BACKEND_DIR}/.env"
}

DB_CLUSTER_ARN="$(dotenv_value DB_CLUSTER_ARN)"
DB_SECRET_ARN="$(dotenv_value DB_SECRET_ARN)"
CONFIGURED_AWS_REGION="$(dotenv_value AWS_REGION)"
CLUSTER_AWS_REGION="$(awk -F: '/^arn:/{ print $4; exit }' <<<"${DB_CLUSTER_ARN}")"
# A shell-wide AWS_REGION can belong to another local workshop. The configured
# cluster ARN is authoritative for this isolated Pellier stack.
AWS_REGION="${PELLIER_SSM_TUNNEL_REGION:-${CLUSTER_AWS_REGION:-${CONFIGURED_AWS_REGION:-${AWS_REGION:-us-east-1}}}}"
REMOTE_DB_HOST="${PELLIER_SSM_TUNNEL_REMOTE_HOST:-$(dotenv_value DB_HOST)}"
REMOTE_DB_PORT="${PELLIER_SSM_TUNNEL_REMOTE_PORT:-$(dotenv_value DB_PORT)}"
REMOTE_DB_PORT="${REMOTE_DB_PORT:-5432}"
TUNNEL_LOCAL_PORT="${PELLIER_SSM_TUNNEL_LOCAL_PORT:-15432}"

discover_tunnel_target() {
  [[ -n "${DB_CLUSTER_ARN}" ]] || return 0

  local cluster_id security_group descriptions
  cluster_id="${DB_CLUSTER_ARN##*:cluster:}"
  security_group="$(
    aws rds describe-db-clusters \
      --region "${AWS_REGION}" \
      --db-cluster-identifier "${cluster_id}" \
      --query 'DBClusters[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
      --output text 2>/dev/null || true
  )"
  [[ -n "${security_group}" && "${security_group}" != "None" ]] || return 0

  descriptions="$(
    aws ec2 describe-security-groups \
      --region "${AWS_REGION}" \
      --group-ids "${security_group}" \
      --query "SecurityGroups[0].IpPermissions[].UserIdGroupPairs[?starts_with(Description, 'Pellier via SSM tunnel')].Description[]" \
      --output text 2>/dev/null || true
  )"
  awk 'NF { print $NF; exit }' <<<"${descriptions}"
}

cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" 2>/dev/null; then
    kill "${TUNNEL_PID}" 2>/dev/null || true
    wait "${TUNNEL_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  echo "Pellier backend virtual environment is missing: ${BACKEND_PYTHON}" >&2
  echo "Create it with: cd pellier/backend && python3 -m venv .venv" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to verify the local Pellier API." >&2
  exit 1
fi

TUNNEL_TARGET="${PELLIER_SSM_TUNNEL_TARGET:-$(discover_tunnel_target)}"
if [[ -n "${TUNNEL_TARGET}" ]]; then
  if ! command -v aws >/dev/null 2>&1 \
    || ! command -v session-manager-plugin >/dev/null 2>&1 \
    || ! command -v jq >/dev/null 2>&1; then
    echo "AWS CLI, session-manager-plugin, and jq are required for the Pellier SSM tunnel." >&2
    exit 1
  fi
  if [[ -z "${REMOTE_DB_HOST}" || -z "${DB_SECRET_ARN}" ]]; then
    echo "DB_HOST and DB_SECRET_ARN are required for the Pellier SSM tunnel." >&2
    exit 1
  fi
  if command -v lsof >/dev/null 2>&1 \
    && lsof -nP -iTCP:"${TUNNEL_LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Pellier SSM tunnel port ${TUNNEL_LOCAL_PORT} is already in use." >&2
    echo "Set PELLIER_SSM_TUNNEL_LOCAL_PORT to an unused port and rerun npm run dev." >&2
    exit 1
  fi

  tunnel_parameters="$(
    printf '{"host":["%s"],"portNumber":["%s"],"localPortNumber":["%s"]}' \
      "${REMOTE_DB_HOST}" "${REMOTE_DB_PORT}" "${TUNNEL_LOCAL_PORT}"
  )"
  aws ssm start-session \
    --region "${AWS_REGION}" \
    --target "${TUNNEL_TARGET}" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "${tunnel_parameters}" &
  TUNNEL_PID="$!"

  for _ in {1..15}; do
    if command -v lsof >/dev/null 2>&1 \
      && lsof -nP -iTCP:"${TUNNEL_LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
      break
    fi
    if ! kill -0 "${TUNNEL_PID}" 2>/dev/null; then
      echo "Pellier SSM tunnel exited before opening local port ${TUNNEL_LOCAL_PORT}." >&2
      exit 1
    fi
    sleep 1
  done

  if ! lsof -nP -iTCP:"${TUNNEL_LOCAL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Pellier SSM tunnel did not open local port ${TUNNEL_LOCAL_PORT}." >&2
    exit 1
  fi

  secret_json="$(
    aws secretsmanager get-secret-value \
      --region "${AWS_REGION}" \
      --secret-id "${DB_SECRET_ARN}" \
      --query SecretString \
      --output text
  )"
  export DB_HOST="127.0.0.1"
  export DB_PORT="${TUNNEL_LOCAL_PORT}"
  export DB_USER="$(jq -r '.username' <<<"${secret_json}")"
  export DB_PASSWORD="$(jq -r '.password' <<<"${secret_json}")"
  export DATABASE_URL=""
fi

if command -v lsof >/dev/null 2>&1 \
  && lsof -nP -iTCP:"${BACKEND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Pellier local backend port ${BACKEND_PORT} is already in use." >&2
  echo "Set PELLIER_BACKEND_PORT to an unused port and rerun npm run dev." >&2
  exit 1
fi

(
  cd "${BACKEND_DIR}"
  exec "${BACKEND_PYTHON}" -m uvicorn app:app \
    --reload \
    --host "${BACKEND_HOST}" \
    --port "${BACKEND_PORT}"
) &
BACKEND_PID="$!"

for _ in {1..45}; do
  if curl -fsS --max-time 2 "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "Pellier API exited before it became healthy." >&2
    echo "Check pellier/backend/.env, especially whether DB_HOST resolves." >&2
    exit 1
  fi
  sleep 1
done

if ! curl -fsS --max-time 2 "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
  echo "Pellier API did not become healthy within 45 seconds." >&2
  echo "Check pellier/backend/.env, especially whether DB_HOST resolves." >&2
  exit 1
fi

cd "${FRONTEND_DIR}"
if [[ "$#" -eq 0 ]]; then
  set -- --host 127.0.0.1
fi

# HMR must stay same-origin so every client uses the Vite proxy below.
VITE_API_URL="" \
VITE_API_BASE_URL="" \
VITE_BASE_PATH="/" \
VITE_BACKEND_TARGET="${BACKEND_URL}" \
  npm run dev:vite -- "$@"
