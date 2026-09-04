import rich
rich.reconfigure(soft_wrap=True)
from rich import print
from pip_runner import Pip


def main():
    pip = Pip()

    print("Installed packages (freeze):")
    print("============================")
    for line in pip.freeze():
        print(line)
    print()

    print("Installed packages (no capture output):")
    print("=======================================")
    print(end="", flush=True)
    pip.list(capture_output=False)
    print()

    print("Installed packages:")
    print("===================")
    for pkg in pip.list(verbose=True).values():
        print(pkg)
    print()

    print("Editable packages:")
    print("==================")
    for pkg in pip.list(editable=True, verbose=True).values():
        print(pkg)
    print()

    print("Outdated packages:")
    print("==================")
    for pkg in pip.list(outdated=True).values():
        print(pkg)
    print()

    print("Uptodate packages:")
    print("==================")
    for pkg in pip.list(uptodate=True).values():
        print(pkg)
    print()


if __name__ == "__main__":
    main()
