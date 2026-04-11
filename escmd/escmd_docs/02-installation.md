# Installation

## System requirements

| Item | Notes |
|------|--------|
| Python | 3.6 or newer |
| OS | Linux, macOS, or Windows |
| Terminal | Unicode-capable terminal recommended (rich output) |
| Network | Reachable Elasticsearch HTTP(S) endpoints |

## Install Python dependencies

From the directory that contains `escmd.py` and `requirements.txt`:

```bash
pip3 install -r requirements.txt
```

**Virtual environment (recommended):**

```bash
python3 -m venv escmd-env
source escmd-env/bin/activate
pip install -r requirements.txt
```

On Windows, activate with `escmd-env\Scripts\activate` then run `pip install -r requirements.txt`.

## Make the CLI executable (optional)

```bash
chmod +x escmd.py
./escmd.py --help
```

You can also invoke `python3 escmd.py` (or `python escmd.py` on Windows) without chmod.

## Optional: global command

```bash
sudo ln -s "$(pwd)/escmd.py" /usr/local/bin/escmd
escmd --help
```

Adjust the target path if you install escmd in a fixed location such as `/opt/escmd`.

## Verify installation

```bash
python3 escmd.py --help
python3 escmd.py ping
```

`ping` requires a working [03-configuration.md](03-configuration.md). Until `elastic_servers.yml` exists, `--help` still validates that the interpreter and imports work.

## Docker (outline)

A minimal pattern is: base image with Python, copy the project, `pip install -r requirements.txt`, set `ENTRYPOINT` to `python3 escmd.py`, and mount `elastic_servers.yml` (and optionally `escmd.yml`) as volumes. Adapt paths and users to your security policy.

## Troubleshooting install

- **pip errors**: upgrade pip (`pip install -U pip`) and retry; use a venv if system packages conflict.
- **SSL / corporate proxy**: configure pip trusted hosts or proxy variables as required by your network.
- **rich version**: escmd checks for a minimum `rich` version at startup; upgrade with `pip install -U rich` if prompted.

For cluster-side and runtime issues, see [06-workflows-reference.md](06-workflows-reference.md).

## Next step

Configure clusters in [03-configuration.md](03-configuration.md).
