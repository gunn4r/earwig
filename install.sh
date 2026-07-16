#!/bin/sh
#
# install.sh — one-line installer for earwig.
#
#   curl -fsSL https://raw.githubusercontent.com/gunn4r/earwig/main/install.sh | sh
#
# Installs earwig into an isolated environment with uv (preferred) or pipx,
# checks for ffmpeg, and hands off to `earwig setup`. POSIX sh, idempotent
# (safe to re-run), and never uses sudo.
#
set -eu

REPO_URL="https://github.com/gunn4r/earwig"
PKG="git+${REPO_URL}@main" # flip to "earwig" if ever published to PyPI
PY_MIN_MAJOR=3
PY_MIN_MINOR=11
UV_PYTHON="3.12" # the Python uv fetches for the uv install path
UV_INSTALL_HINT="curl -LsSf https://astral.sh/uv/install.sh | sh"

# --- pure decision functions (no side effects) ------------------------------

detect_os() {
	case "$(uname -s)" in
	Darwin) echo macos ;;
	Linux) echo linux ;;
	MINGW* | MSYS* | CYGWIN*) echo windows ;;
	*) echo unknown ;;
	esac
}

detect_installer() {
	if command -v uv >/dev/null 2>&1; then
		echo uv
	elif command -v pipx >/dev/null 2>&1; then
		echo pipx
	else
		echo none
	fi
}

have_ffmpeg() {
	command -v ffmpeg >/dev/null 2>&1
}

python_ok() {
	command -v python3 >/dev/null 2>&1 || return 1
	python3 -c "import sys; sys.exit(0 if sys.version_info[:2] >= (${PY_MIN_MAJOR}, ${PY_MIN_MINOR}) else 1)"
}

ffmpeg_hint() {
	case "$1" in
	macos) echo "brew install ffmpeg" ;;
	linux) echo "sudo apt install ffmpeg  # or your distro's package manager" ;;
	*) echo "install ffmpeg and put it on your PATH" ;;
	esac
}

build_install_cmd() {
	case "$1" in
	uv) echo "uv tool install --force --python ${UV_PYTHON} ${PKG}" ;;
	pipx) echo "pipx install --force ${PKG}" ;;
	esac
}

resolve_earwig() {
	if command -v earwig >/dev/null 2>&1; then
		command -v earwig
	elif [ -x "${HOME}/.local/bin/earwig" ]; then
		echo "${HOME}/.local/bin/earwig"
	fi
	return 0 # always succeed: empty output means "not found", not an error
}

# --- side effects / orchestration -------------------------------------------

run_setup() {
	earwig_bin="$(resolve_earwig)"
	if [ -z "$earwig_bin" ]; then
		echo ""
		echo "Installed, but 'earwig' isn't on your PATH yet."
		echo "Add ~/.local/bin to your PATH, then run:  earwig setup"
		return 0
	fi

	# Show the bare command when it's really on PATH; otherwise the full path,
	# so the printed instruction works as written.
	if command -v earwig >/dev/null 2>&1; then
		setup_hint="earwig setup"
	else
		setup_hint="$earwig_bin setup"
	fi

	# curl | sh makes the script the shell's stdin, so a bare prompt would hit
	# EOF. Reconnect setup to the terminal via /dev/tty when there is one;
	# otherwise (CI, or EARWIG_NO_SETUP) just print the next step.
	if [ -z "${EARWIG_NO_SETUP:-}" ] && [ -r /dev/tty ]; then
		echo "Running earwig setup..."
		"$earwig_bin" setup </dev/tty
	else
		echo ""
		echo "earwig is installed. Next step:"
		echo "    $setup_hint"
	fi
}

main() {
	os="$(detect_os)"
	if [ "$os" = windows ]; then
		echo "earwig doesn't run natively on Windows yet — use WSL2 and re-run this." >&2
		exit 1
	fi
	if [ "$os" = unknown ]; then
		echo "warning: unrecognized OS ($(uname -s)); continuing best-effort." >&2
	fi

	installer="$(detect_installer)"
	if [ "$installer" = none ]; then
		echo "earwig installs with uv or pipx, and neither was found." >&2
		echo "Install uv (recommended):  ${UV_INSTALL_HINT}" >&2
		echo "then re-run this installer. (Or install pipx: https://pipx.pypa.io)" >&2
		exit 1
	fi

	if [ "$installer" = pipx ] && ! python_ok; then
		echo "pipx would use python3, which is older than ${PY_MIN_MAJOR}.${PY_MIN_MINOR}." >&2
		echo "Install uv instead (${UV_INSTALL_HINT}) — it brings its own Python — then re-run." >&2
		exit 1
	fi

	echo "Installing earwig with ${installer}..."
	if ! eval "$(build_install_cmd "$installer")"; then
		echo "installation failed — see the output above." >&2
		exit 1
	fi

	if ! have_ffmpeg; then
		echo "note: ffmpeg not found (earwig needs it to extract audio). Install it: $(ffmpeg_hint "$os")"
	fi

	run_setup
}

# Run main only when executed, not when sourced for testing.
if [ -z "${EARWIG_INSTALL_LIB:-}" ]; then
	main "$@"
fi
