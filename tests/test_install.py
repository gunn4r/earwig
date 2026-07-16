import subprocess
from pathlib import Path

INSTALL_SH = Path(__file__).resolve().parent.parent / "install.sh"


def _shim(bindir, name, body="#!/bin/sh\nexit 0\n"):
    """Write an executable fake command into bindir."""
    p = bindir / name
    p.write_text(body)
    p.chmod(0o755)
    return p


def _bindir(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    return b


def _env(bindir, **extra):
    # PATH is ONLY the shim dir: /bin/sh is invoked by absolute path, its
    # builtins need no PATH, and every external command the script calls must
    # be a shim we control. This keeps the tests fully hermetic — no uv, pipx,
    # or python from the host machine can leak in.
    env = {"PATH": str(bindir), "HOME": str(bindir.parent)}
    env.update(extra)
    return env


def _source(fn, bindir, **extra):
    """Source install.sh (main suppressed) and run one function."""
    env = _env(bindir, EARWIG_INSTALL_LIB="1", **extra)
    return subprocess.run(
        ["/bin/sh", "-c", f". '{INSTALL_SH}'; {fn}"],
        capture_output=True, text=True, env=env,
    )


# --- detect_installer -------------------------------------------------------

def test_detect_installer_prefers_uv(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uv")
    _shim(b, "pipx")
    assert _source("detect_installer", b).stdout.strip() == "uv"


def test_detect_installer_pipx_when_no_uv(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "pipx")
    assert _source("detect_installer", b).stdout.strip() == "pipx"


def test_detect_installer_none_when_neither(tmp_path):
    b = _bindir(tmp_path)
    assert _source("detect_installer", b).stdout.strip() == "none"


# --- detect_os --------------------------------------------------------------

def test_detect_os_macos(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Darwin\n")
    assert _source("detect_os", b).stdout.strip() == "macos"


def test_detect_os_linux(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Linux\n")
    assert _source("detect_os", b).stdout.strip() == "linux"


def test_detect_os_windows(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho MINGW64_NT-10.0\n")
    assert _source("detect_os", b).stdout.strip() == "windows"


# --- python_ok --------------------------------------------------------------

def test_python_ok_true_for_recent(tmp_path):
    b = _bindir(tmp_path)
    # The shim ignores the -c arg and just reports "new enough".
    _shim(b, "python3", "#!/bin/sh\nexit 0\n")
    assert _source("python_ok", b).returncode == 0


def test_python_ok_false_for_old(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "python3", "#!/bin/sh\nexit 1\n")
    assert _source("python_ok", b).returncode == 1


def test_python_ok_false_when_missing(tmp_path):
    b = _bindir(tmp_path)
    assert _source("python_ok", b).returncode == 1


# --- ffmpeg -----------------------------------------------------------------

def test_have_ffmpeg_true(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "ffmpeg")
    assert _source("have_ffmpeg", b).returncode == 0


def test_have_ffmpeg_false(tmp_path):
    b = _bindir(tmp_path)
    assert _source("have_ffmpeg", b).returncode == 1


def test_ffmpeg_hint_macos_mentions_brew(tmp_path):
    b = _bindir(tmp_path)
    assert "brew" in _source("ffmpeg_hint macos", b).stdout


def test_ffmpeg_hint_linux_mentions_apt(tmp_path):
    b = _bindir(tmp_path)
    assert "apt" in _source("ffmpeg_hint linux", b).stdout


# --- build_install_cmd ------------------------------------------------------

def test_build_install_cmd_uv(tmp_path):
    b = _bindir(tmp_path)
    out = _source("build_install_cmd uv", b).stdout
    assert "uv tool install --force --python 3.12" in out
    assert "git+https://github.com/gunn4r/earwig@main" in out


def test_build_install_cmd_pipx(tmp_path):
    b = _bindir(tmp_path)
    out = _source("build_install_cmd pipx", b).stdout
    assert "pipx install --force" in out
    assert "git+https://github.com/gunn4r/earwig@main" in out


# --- resolve_earwig ---------------------------------------------------------

def test_resolve_earwig_on_path(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "earwig")
    assert _source("resolve_earwig", b).stdout.strip() == str(b / "earwig")


def test_resolve_earwig_in_local_bin(tmp_path):
    b = _bindir(tmp_path)
    local = tmp_path / ".local" / "bin"
    local.mkdir(parents=True)
    _shim(local, "earwig")
    # HOME is tmp_path (bindir.parent), so ~/.local/bin/earwig exists but is not on PATH.
    out = _source("resolve_earwig", b).stdout.strip()
    assert out == str(local / "earwig")


def test_resolve_earwig_empty_when_absent(tmp_path):
    b = _bindir(tmp_path)
    assert _source("resolve_earwig", b).stdout.strip() == ""


def test_resolve_earwig_no_crash_when_home_unset(tmp_path):
    # curl | sh can run in a shell with no HOME (minimal containers/CI). Under
    # set -u that must not crash — resolve just yields empty.
    b = _bindir(tmp_path)
    env = {"PATH": str(b), "EARWIG_INSTALL_LIB": "1"}  # deliberately no HOME
    r = subprocess.run(
        ["/bin/sh", "-c", f". '{INSTALL_SH}'; resolve_earwig"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""
    assert "parameter not set" not in r.stderr.lower()


# --- main (execute the script; main runs because EARWIG_INSTALL_LIB is unset) ---

def _run(bindir, **extra):
    """Execute install.sh so main() runs, with a restricted PATH."""
    return subprocess.run(
        ["/bin/sh", str(INSTALL_SH)],
        capture_output=True, text=True, env=_env(bindir, **extra),
    )


def test_main_installs_with_uv(tmp_path):
    b = _bindir(tmp_path)
    marker = tmp_path / "uv_args"
    _shim(b, "uname", "#!/bin/sh\necho Linux\n")
    _shim(b, "uv", f"#!/bin/sh\necho \"$@\" > '{marker}'\nexit 0\n")
    _shim(b, "ffmpeg")
    r = _run(b, EARWIG_NO_SETUP="1")
    assert r.returncode == 0, r.stderr
    args = marker.read_text()
    assert "tool install --force --python 3.12" in args
    assert "git+https://github.com/gunn4r/earwig@main" in args


def test_main_reports_install_failure(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Linux\n")
    _shim(b, "uv", "#!/bin/sh\nexit 3\n")  # the install itself fails
    r = _run(b, EARWIG_NO_SETUP="1")
    assert r.returncode == 1
    assert "installation failed" in r.stderr


def test_main_rejects_windows(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho MINGW64_NT-10.0\n")
    r = _run(b)
    assert r.returncode == 1
    assert "WSL" in r.stderr


def test_main_exits_when_no_installer(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Linux\n")  # no uv, no pipx
    r = _run(b)
    assert r.returncode == 1
    assert "uv" in r.stderr.lower()


def test_main_pipx_bails_on_old_python(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Linux\n")
    _shim(b, "pipx")  # only pipx present
    _shim(b, "python3", "#!/bin/sh\nexit 1\n")  # reports too-old
    r = _run(b)
    assert r.returncode == 1
    assert "older than 3.11" in r.stderr


def test_main_warns_when_ffmpeg_missing(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Darwin\n")
    _shim(b, "uv", "#!/bin/sh\nexit 0\n")  # no ffmpeg shim
    r = _run(b, EARWIG_NO_SETUP="1")
    assert r.returncode == 0, r.stderr
    assert "ffmpeg not found" in r.stdout
    assert "brew install ffmpeg" in r.stdout  # the macOS hint


def test_main_skips_setup_and_prints_next_step(tmp_path):
    b = _bindir(tmp_path)
    _shim(b, "uname", "#!/bin/sh\necho Linux\n")
    _shim(b, "uv", "#!/bin/sh\nexit 0\n")
    _shim(b, "ffmpeg")
    called = tmp_path / "earwig_called"
    _shim(b, "earwig", f"#!/bin/sh\ntouch '{called}'\n")  # records if launched
    r = _run(b, EARWIG_NO_SETUP="1")
    assert r.returncode == 0, r.stderr
    assert "earwig setup" in r.stdout
    assert not called.exists()  # EARWIG_NO_SETUP => setup is not launched
