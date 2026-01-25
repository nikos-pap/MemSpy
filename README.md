# MemSpy

MemSpy is a Windows-first memory scanner built with Python and PyQt6. It provides a desktop UI for attaching to running processes, searching for values in their address spaces, and keeping those discoveries organized for later reuse. The scanner supports common integer and floating-point types, live value refreshing, and pointer-chain discovery to make values stable across sessions.

## Features
- **Process attachment:** Browse running processes and attach to one to enable scanning.
- **Value scanning:** Search for Int8/16/32/64, UInt8/16/32/64, Float, Double, or String values with configurable scan conditions.
- **Workspace management:** Save interesting addresses to a workspace, track their current values, and move items between tables.
- **Pagination for large scans:** Results tables are paged and filterable so you can navigate large result sets efficiently.
- **Pointer scanning:** Discover pointer chains, page through pointer results, and import/export pointer scans for reuse.
- **Configurable experience:** Application settings (such as scan defaults and workspace behavior) can be adjusted through the Settings dialog.

## Requirements
- Windows 10/11 with permissions to open other processes (administrator rights are recommended for full access).
- Python 3.10 or newer.
- System dependencies listed in [`pyproject.toml`](pyproject.toml); install them with `pip` as shown below. (Windows-only packages such as `pywin32` and `wmi` are included conditionally.)

## Installation
```bash
# From the repository root
python -m venv .venv
source .venv/Scripts/activate  # or `.venv\\Scripts\\activate` in PowerShell
pip install --upgrade pip
pip install -e .
```

If you prefer not to use an editable install, replace the last command with `pip install .`.

If using powershell, replace the `source ..` above with ` .\\.venv\Scripts\activate`

## Running MemSpy
Activate your virtual environment (if used) and launch the UI:

```bash
memspy
```

You can also start the app directly with Python:

```bash
python -m memspy
```

## Usage overview
1. **Select a process:** Use the process selector to pick the target process. Attach before starting a scan.
2. **Configure a scan:** Choose the value type and condition, then run the scan. Results appear in the Search Address Table.
3. **Filter and page:** Use pagination controls to move through results and apply filters to narrow them down.
4. **Save addresses:** Double-click or use the workspace controls to add addresses you care about to the Workspace panel, where their values keep updating.
5. **Pointer scan:** Kick off a pointer scan from the workspace or pointer table. Page through pointer chains, export them to a file, or import prior scans.
6. **Tweak settings:** Open the Settings dialog from the menu to adjust scanning options and workspace behavior.

## Testing
Run the automated tests with:

```bash
pytest
```

## Notes
- MemSpy relies on Windows APIs to inspect and manipulate other processes. Run it on Windows and close the application before shutting down target processes to avoid stale handles.
- Scanning large processes can take time; progress updates are shown in the status bar.
