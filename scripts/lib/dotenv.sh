#!/usr/bin/env bash
# Shared dotenv reader for Pellier's shell entrypoints.
#
# A dotenv file is configuration data, not a shell program. In particular,
# generated database passwords may contain `(`, `$`, or backslashes, so
# `source .env` can either fail or expand bytes that must remain literal.

pellier_load_dotenv() {
  local file="$1" line key value

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" != *=* ]] && continue

    key="${line%%=*}"
    value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    # The recovery file is emitted as `export KEY=value` so it can be read by
    # a human shell too. Accept that dotenv-compatible form without sourcing
    # the file or treating the value as code.
    if [[ "$key" == export\ * ]]; then
      key="${key#export }"
      key="${key#"${key%%[![:space:]]*}"}"
      key="${key%"${key##*[![:space:]]}"}"
    fi
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    # Match dotenv's common quoted-value convention without evaluating the
    # value as shell syntax.
    if [[ "$value" == \"*\" && ${#value} -ge 2 ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && ${#value} -ge 2 ]]; then
      value="${value:1:${#value}-2}"
    fi

    # `export KEY=value` assigns value verbatim. It does not expand command
    # substitutions, variables, or shell metacharacters embedded in the file.
    export "$key=$value"
  done < "$file"
}
