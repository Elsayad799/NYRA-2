#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/TgMusicBot-master"
exec go run ./cmd/nyra_voice_bridge
