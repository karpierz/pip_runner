from pathlib import Path
import logging
# logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)
from pip_runner import Pip

here = Path(__file__).resolve().parent
docs_dir = here.parent/"docs"/".org"

pip_commands = (  # "support",
    "install", "lock", "download", "uninstall", "freeze", "inspect",
    "list", "show", "check", "config", "search", "cache", "index",
    "wheel", "hash", "completion", "debug", "help",
)

pip = Pip()

print("pip version:", pip.version)

fpath = docs_dir/"help.txt"
fpath.open("w", newline="").write(pip.help())
for command in pip_commands:
    fpath = docs_dir/f"help_{command}.txt"
    fpath.open("w", newline="").write(pip.help(command=command))
