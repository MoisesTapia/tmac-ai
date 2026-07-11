#!/usr/bin/env bash
# ci/github/entrypoint.sh
# GitHub Action entrypoint for TMAC CI.
#
# Responsibilities:
#   1. Validate action inputs (fail-on, report-format) – R5.13, R5.14, R5.15
#   2. Map inputs to `tmac ci` flags
#   3. Publish PR comment only on pull_request events – R5.8, R5.9
#   4. Invoke `tmac ci` and propagate its exit code unchanged – R5.11, R5.12
#
# Exit codes:
#   0        – no findings at/above threshold (R5.11)
#   1        – critical findings (R5.11)
#   2        – high findings (R5.11)
#   3        – execution error or invalid input (R5.12, R5.13, R5.14, R5.15)
#   non-zero – other findings-based exit from `tmac ci` (R5.12)

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Read inputs (passed via environment variables by action.yml)
# ---------------------------------------------------------------------------

INPUT_DIR="${TMAC_INPUT_DIR:-.}"
INPUT_FAIL_ON="${TMAC_INPUT_FAIL_ON:-high}"
INPUT_DELTA_ONLY="${TMAC_INPUT_DELTA_ONLY:-true}"
INPUT_COMMENT="${TMAC_INPUT_COMMENT:-true}"
INPUT_REPORT_FORMAT="${TMAC_INPUT_REPORT_FORMAT:-Markdown}"
INPUT_OUTPUT="${TMAC_INPUT_OUTPUT:-}"

# ---------------------------------------------------------------------------
# 2. Validate fail-on (R5.14)
# ---------------------------------------------------------------------------

VALID_FAIL_ON="critical high medium low"

fail_on_lower="$(echo "${INPUT_FAIL_ON}" | tr '[:upper:]' '[:lower:]')"

valid_fail_on=false
for v in ${VALID_FAIL_ON}; do
  if [ "${fail_on_lower}" = "${v}" ]; then
    valid_fail_on=true
    break
  fi
done

if [ "${valid_fail_on}" = false ]; then
  echo "Error: invalid value for input 'fail-on': '${INPUT_FAIL_ON}'." \
       "Accepted values: critical, high, medium, low." >&2
  exit 3
fi

# ---------------------------------------------------------------------------
# 3. Validate report-format and map to tmac CLI value (R5.15)
# ---------------------------------------------------------------------------
# Supported values (case-insensitive): Markdown / md → md, html → html, json → json

report_format_lower="$(echo "${INPUT_REPORT_FORMAT}" | tr '[:upper:]' '[:lower:]')"

case "${report_format_lower}" in
  markdown|md)
    REPORT_FMT="md"
    ;;
  html)
    REPORT_FMT="html"
    ;;
  json)
    REPORT_FMT="json"
    ;;
  *)
    echo "Error: invalid value for input 'report-format': '${INPUT_REPORT_FORMAT}'." \
         "Accepted values: Markdown, html, json." >&2
    exit 3
    ;;
esac

# ---------------------------------------------------------------------------
# 4. Determine output path (R5.7)
# ---------------------------------------------------------------------------

if [ -n "${INPUT_OUTPUT}" ]; then
  OUTPUT_PATH="${INPUT_OUTPUT}"
else
  # Default workspace output location: workspace root with standard extension
  case "${REPORT_FMT}" in
    md)   OUTPUT_PATH="${GITHUB_WORKSPACE:-$(pwd)}/tmac-report.md"   ;;
    html) OUTPUT_PATH="${GITHUB_WORKSPACE:-$(pwd)}/tmac-report.html" ;;
    json) OUTPUT_PATH="${GITHUB_WORKSPACE:-$(pwd)}/tmac-report.json" ;;
    *)    OUTPUT_PATH="${GITHUB_WORKSPACE:-$(pwd)}/tmac-report.md"   ;;
  esac
fi

# ---------------------------------------------------------------------------
# 5. Build delta-only / comment flags
# ---------------------------------------------------------------------------

delta_only_lower="$(echo "${INPUT_DELTA_ONLY}" | tr '[:upper:]' '[:lower:]')"
comment_lower="$(echo "${INPUT_COMMENT}" | tr '[:upper:]' '[:lower:]')"

if [ "${delta_only_lower}" = "true" ]; then
  DELTA_FLAG="--delta-only"
else
  DELTA_FLAG="--no-delta-only"
fi

# Determine whether to publish a PR comment (R5.8, R5.9):
# Publish only when on a pull_request event AND comment input is enabled.
EVENT_NAME="${GITHUB_EVENT_NAME:-}"

if [ "${comment_lower}" = "true" ] && [ "${EVENT_NAME}" = "pull_request" ]; then
  COMMENT_FLAG="--comment"
else
  # Not a PR event or comment disabled → skip publishing (R5.9)
  COMMENT_FLAG="--no-comment"
fi

# ---------------------------------------------------------------------------
# 6. Build base/head refs for delta mode
# ---------------------------------------------------------------------------

BASE_REF_FLAG=""
HEAD_REF_FLAG=""

if [ "${delta_only_lower}" = "true" ]; then
  if [ -n "${GITHUB_BASE_REF:-}" ]; then
    BASE_REF_FLAG="--base-ref ${GITHUB_BASE_REF}"
  fi
  if [ -n "${GITHUB_HEAD_REF:-}" ]; then
    HEAD_REF_FLAG="--head-ref ${GITHUB_HEAD_REF}"
  fi
fi

# ---------------------------------------------------------------------------
# 7. Invoke `tmac ci` and propagate exit code unchanged (R5.11, R5.12)
# ---------------------------------------------------------------------------

# Disable the errexit trap for the tmac invocation so we can capture its
# exit code explicitly and propagate it without interference.
set +e

# shellcheck disable=SC2086
tmac ci \
  --dir "${INPUT_DIR}" \
  --fail-on "${fail_on_lower}" \
  --report "${REPORT_FMT}" \
  --output "${OUTPUT_PATH}" \
  ${DELTA_FLAG} \
  ${COMMENT_FLAG} \
  ${BASE_REF_FLAG} \
  ${HEAD_REF_FLAG} \
  --platform github

TMAC_EXIT=$?

set -e

# Propagate the exit code unchanged (R5.11, R5.12)
exit ${TMAC_EXIT}
