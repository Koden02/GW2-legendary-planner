# Packaging

GW2 Legendary Planner can be packaged as a Windows one-file executable with
PyInstaller. The packaged executable preserves the existing CLI contract, so the
desktop dashboard is launched with the same `gui serve` command.

## Windows Build

Requirements:

- Windows
- Python 3.13
- uv

Build from the repository root:

```powershell
.\scripts\build_windows_app.ps1
```

The script installs the optional `package` dependency group and writes:

```text
dist\gw2planner.exe
```

The executable includes packaged planner data such as recipes, activity goals,
collection definitions, recurring task definitions, starter-kit sets, and
Wizard's Vault season fixtures.

## Smoke Checks

After building, run:

```powershell
.\dist\gw2planner.exe --help
.\dist\gw2planner.exe recipes validate
.\dist\gw2planner.exe activities wizard-vault-validate --data tests\fixtures\wizards_vault\sample_season.json
.\dist\gw2planner.exe gui build --input tests\fixtures\exports --output build\packaging-smoke-dashboard.html
```

To launch the dashboard against a configured profile or API key:

```powershell
.\dist\gw2planner.exe gui serve --open --port 0
```

If no profile, environment API key, or local export directory is configured,
that command starts a local setup page. Entering a GW2 API key there loads the
dashboard for the current app session without writing the key to disk. The setup
field shows the key while typing. Checking the remember option stores the key as
plaintext in a local `local-dashboard` profile so future launches can load the
account automatically.

To launch against local exports:

```powershell
.\dist\gw2planner.exe gui serve --input .\exports --open --port 0
```

One-file executables can take a moment to start because they unpack bundled
runtime files before running.
