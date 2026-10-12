#!/usr/bin/env bash
# Python-free Unix entry point. Never edits PATH, profiles or global packages.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
workspace= data_dir=${HWPDOC_PC_DATA:-${LOCALAPPDATA:-$HOME/AppData/Local}/hwpdoc} python= allow=0 data_explicit=0
forward=()
fail() { printf 'teacher_doc setup failed: %s\n' "$*" >&2; exit 2; }
while (($#)); do
    case "$1" in
        --workspace|--data-dir|--python|--mode|--app|--skill-name)
            (($# >= 2)) || fail "Missing value for $1"
            case "$1" in
                --workspace) workspace=$2 ;;
                --data-dir) data_dir=$2; data_explicit=1 ;;
                --python) python=$2 ;;
                *) forward+=("$1" "$2") ;;
            esac; shift 2 ;;
        --allow-python-install) allow=1; shift ;;
        --school-data|--visual) forward+=("$1"); shift ;;
        --help|-h)
            printf '%s\n' 'Usage: bash scripts/bootstrap.sh --workspace PATH [--data-dir PATH] [--python ABSOLUTE_PATH] [--allow-python-install] [--mode xml|full] [--app codex|claude] [--skill-name NAME] [--school-data] [--visual]' 'Only add --allow-python-install after the user approved application-local Astral uv/CPython installation.'; exit 0 ;;
        *) fail "Unknown option: $1" ;;
    esac
done
[[ -n $workspace ]] || fail '--workspace is required'
# A Python-free shell must not guess JSON paths or create a second runtime.
if [[ $data_explicit = 0 && -z ${HWPDOC_PC_DATA:-} && -f $workspace/.hwpdoc/onboarding.json ]]; then
    fail 'Existing installation receipt: read .hwpdoc/onboarding.json and use its python for document work, or pass its verified pc_data with --data-dir to resume setup. No files changed.'
fi
# Resolve existing parents (including symlinks) without creating a directory.
canonical() {
    local path=$1 suffix= name
    [[ $path = /* ]] || path=$PWD/$path
    while [[ ! -d $path ]]; do
        name=${path##*/}; [[ $name != '.' && $name != '..' ]] || fail 'Use a normalized path without trailing . or ..'
        suffix=/$name$suffix; path=${path%/*}; [[ -n $path ]] || path=/
    done
    printf '%s%s\n' "$(cd -- "$path" && pwd -P)" "$suffix"
}
workspace=$(canonical "$workspace"); data_dir=$(canonical "$data_dir")
for path in "$workspace" "$data_dir"; do
    [[ $path != "$root" && $path != "$root/"* && $root != "$path/"* ]] || fail 'Code, PC data and workspace must not overlap'
done
is_python312() { [[ -f $1 && -x $1 ]] && [[ $("$1" -I -S -c 'import sys; print("teacher-python-312" if sys.version_info[:2] == (3,12) else "wrong-version")' 2>/dev/null) = teacher-python-312 ]]; }
if [[ -n $python ]]; then
    [[ $python = /* ]] && is_python312 "$python" || fail '--python must be an existing absolute Python 3.12 executable path'
else
    # App-local candidates first; bootstrap.py still validates runtime.json and ownership.
    for candidate in "$data_dir"/runtimes/onboarding-*/bin/python "$data_dir"/managed-python/python/cpython-3.12.*/bin/python3.12; do
        if is_python312 "$candidate"; then python=$candidate; break; fi
    done
    if [[ -z $python ]]; then
        for name in python3.12 python3 python; do
            candidate=$(command -v "$name" || true)
            if [[ $candidate = /* ]] && is_python312 "$candidate"; then python=$candidate; break; fi
        done
    fi
fi
if [[ -z $python ]]; then
    [[ ! -e $data_dir/runtime.json ]] || fail 'Existing runtime.json preserved; specify its valid Python with --python or choose a separate --data-dir'
    [[ $allow = 1 ]] || fail 'PYTHON_INSTALL_CONSENT_REQUIRED: Ask once to download Astral uv and its CPython build into the teacher_doc PC data folder. After approval rerun with --allow-python-install. No download or settings change was made.'
    case "$(uname -s):$(uname -m)" in
        Linux:x86_64) platform=x86_64-unknown-linux-gnu; key=cpython-3.12.15-linux-x86_64-gnu ;;
        Linux:aarch64|Linux:arm64) platform=aarch64-unknown-linux-gnu; key=cpython-3.12.15-linux-aarch64-gnu ;;
        Darwin:x86_64) platform=x86_64-apple-darwin; key=cpython-3.12.15-darwin-x86_64-none ;;
        Darwin:arm64) platform=aarch64-apple-darwin; key=cpython-3.12.15-darwin-aarch64-none ;;
        *) fail 'Automatic Python setup supports macOS x64/ARM64 and glibc Linux x64/ARM64 only' ;;
    esac
    row=$(awk -F '\t' -v platform="$platform" '$1 == platform { print $0 }' "$root/distribution/runtime-downloads.tsv")
    [[ $row != *$'\n'* ]] || fail 'Ambiguous pinned uv metadata'
    IFS=$'\t' read -r actual_platform url expected <<< "$row"
    [[ $actual_platform = "$platform" && $url = "https://github.com/astral-sh/uv/releases/download/0.12.22/uv-$platform.tar.gz" && $expected =~ ^[a-f0-9]{64}$ ]] || fail 'Invalid pinned official uv metadata'
    managed=$data_dir/managed-python
    for destination in "$managed" "$managed/python" "$managed/cache" "$managed/python/$key"; do
        [[ ! -L $destination ]] || fail 'Symlink managed-runtime paths are not allowed; choose a plain --data-dir'
    done
    if [[ -e $managed ]]; then
        [[ -f $managed/.teacher-doc-owner && $(cat "$managed/.teacher-doc-owner") = teacher-doc-python-v1 ]] || fail 'Existing unmanaged managed-python folder preserved; choose another --data-dir'
    else
        mkdir -p -- "$data_dir"
        mkdir -- "$managed"
        printf 'teacher-doc-python-v1\n' > "$managed/.teacher-doc-owner"
    fi
    stage=$(mktemp -d "$managed/download-XXXXXXXX")
    trap 'rm -rf -- "$stage"' EXIT
    printf 'Downloading verified Astral uv 0.12.22: %s\n' "$url" >&2
    curl --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 30 --max-time 180 --output "$stage/uv.tar.gz" "$url" || fail 'UV_DOWNLOAD_FAILED: Download failed. Existing data was preserved; fix the network or permissions and retry.'
    if command -v sha256sum >/dev/null; then actual=$(sha256sum "$stage/uv.tar.gz"); else actual=$(shasum -a 256 "$stage/uv.tar.gz"); fi
    actual=${actual%% *}
    [[ $actual = "$expected" ]] || fail "UV_HASH_MISMATCH: expected $expected; got $actual. Download was not executed."
    printf 'uv SHA-256 verified: %s\n' "$actual" >&2
    tar xzf "$stage/uv.tar.gz" -C "$stage"
    uv=$stage/uv-$platform/uv
    [[ -x $uv ]] || fail 'Unexpected uv archive layout'
    # A clean uv environment prevents user mirrors/config/insecure-host overrides.
    # Preserve network proxy and platform CA settings, never disable TLS verification.
    uv_env=(env -i "HOME=$HOME" "PATH=$PATH" "TMPDIR=${TMPDIR:-/tmp}")
    for name in HTTPS_PROXY HTTP_PROXY ALL_PROXY NO_PROXY https_proxy http_proxy all_proxy no_proxy SSL_CERT_FILE SSL_CERT_DIR; do
        if [[ -n ${!name:-} ]]; then uv_env+=("$name=${!name}"); fi
    done
    printf 'Installing pinned CPython %s; uv enforces distribution/python-downloads.json SHA-256\n' "$key" >&2
    # file: URLs accept native spaces; uv normalizes them without Python or jq.
    "${uv_env[@]}" "$uv" python install "$key" --install-dir "$managed/python" --no-bin --no-registry --no-config --managed-python --cache-dir "$managed/cache" --python-downloads-json-url "file://$root/distribution/python-downloads.json" >&2 || fail 'PYTHON_DOWNLOAD_FAILED: Download/verification failed. Preserve data and retry after fixing network or permissions.'
    python=$managed/python/$key/bin/python3.12
    is_python312 "$python" || fail 'Managed Python failed its version/executable check'
    "$python" -I -S -c 'import json,sys,pathlib; root,data,key,uv_hash,python=sys.argv[1:]; entry=json.loads((pathlib.Path(root)/"distribution/python-downloads.json").read_text())[key]; (pathlib.Path(data)/"managed-python/install-receipt.json").write_text(json.dumps(dict(owner="teacher-doc-python-v1",uv_version="0.12.22",uv_sha256=uv_hash,python_key=key,python_sha256=entry["sha256"],python_url=entry["url"],python=python,registry_changed=False,path_changed=False),indent=2)+"\n")' "$root" "$data_dir" "$key" "$actual" "$python"
    rm -rf -- "$stage"; trap - EXIT
fi
printf 'Using Python 3.12: %s\n' "$python" >&2
exec "$python" -B -I -X utf8 "$root/scripts/bootstrap.py" --workspace "$workspace" --data-dir "$data_dir" "${forward[@]}"
