#!/usr/bin/env bash
#
# release.sh — cut a new earwig release.
#
# Builds CHANGELOG.md from the towncrier fragments in changelog.d/, bumps the
# version in pyproject.toml, reinstalls so __version__ refreshes, commits, and
# tags. Portable across macOS and Linux: it shells out to the project's venv
# Python for anything text-munging (no `sed -i`, which differs between BSD and
# GNU). It does NOT push — you review, then push yourself.
#
# This is a maintainer tool. On Windows, use WSL/Git Bash or the manual steps in
# CONTRIBUTING.md.
#
# Usage:
#   scripts/release.sh <version> [--dry-run]
#
# Examples:
#   scripts/release.sh 0.3.0             # cut 0.3.0
#   scripts/release.sh 0.3.0 --dry-run   # preview the changelog only; change nothing
#
set -euo pipefail

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

VERSION="${1:-}"
DRY_RUN="${2:-}"

[ -n "$VERSION" ] || die "usage: scripts/release.sh <version> [--dry-run]"
printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.]+)?$' \
  || die "version '$VERSION' is not semver (expected X.Y.Z)"

# Operate from the repo root, wherever the script was invoked from.
REPO_ROOT="$(git rev-parse --show-toplevel)" || die "not inside a git repository"
cd "$REPO_ROOT"

PY="$REPO_ROOT/.venv/bin/python"
TOWNCRIER="$REPO_ROOT/.venv/bin/towncrier"
[ -x "$PY" ] || die "no venv python at .venv/bin/python (create it: python -m venv .venv && pip install -e '.[dev]')"
[ -x "$TOWNCRIER" ] || die "towncrier not installed in the venv (pip install -e '.[dev]')"

# There must be at least one news fragment to release.
FRAGMENTS="$(find changelog.d -type f ! -name 'README.md' 2>/dev/null | wc -l | tr -d ' ')"
[ "$FRAGMENTS" -gt 0 ] || die "no changelog fragments in changelog.d/ — nothing to release"

echo "==> Preview of the $VERSION changelog:"
"$TOWNCRIER" build --draft --version "$VERSION"

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "==> --dry-run: nothing written."
  exit 0
fi

echo "==> Building CHANGELOG.md and consuming fragments..."
"$TOWNCRIER" build --yes --version "$VERSION"

echo "==> Bumping pyproject.toml to $VERSION..."
"$PY" - "$VERSION" <<'PY'
import pathlib, re, sys
ver = sys.argv[1]
path = pathlib.Path("pyproject.toml")
text = path.read_text()
new, n = re.subn(r'(?m)^version = "[^"]*"', f'version = "{ver}"', text)
if n != 1:
    sys.exit(f'expected exactly one top-level `version = "..."` line, found {n}')
path.write_text(new)
PY

echo "==> Reinstalling so __version__ refreshes..."
"$PY" -m pip install -e . --quiet

echo "==> Verifying __version__..."
GOT="$("$PY" -c 'import earwig; print(earwig.__version__)')"
[ "$GOT" = "$VERSION" ] || die "__version__ is '$GOT', expected '$VERSION'"

echo "==> Committing and tagging v$VERSION..."
git add CHANGELOG.md pyproject.toml changelog.d
git commit -m "Release $VERSION"
git tag "v$VERSION"

cat <<EOF

Done — $VERSION is committed and tagged locally.
Review it, then publish:

    git push && git push origin v$VERSION

EOF
