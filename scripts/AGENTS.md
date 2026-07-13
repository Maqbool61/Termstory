# scripts/ — Shell Scripts

## Files

- `install.sh` — One-line installer (`curl | bash`) that downloads the project source and installs it.
- `uninstall.sh` — One-line uninstaller that removes the installed command and related setup.
- `pocs/` — Proof-of-concept scripts used for experimentation. These are not part of the released package.

## Conventions

- The install script checks for a Python 3 interpreter and uses `pip` to install the project.
- The installer attempts a virtual environment installation first and falls back to a user installation if needed.
- Scripts in `pocs/` are experimental,  throwaway scripts and are not intended as stable tooling.