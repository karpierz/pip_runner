import rich
rich.reconfigure(soft_wrap=True)
from rich import print
from pip_runner import Pip


def main():
    pip = Pip()

    print("Installed packages:")
    print("===================")
    for pkg_name in pip.list(verbose=True):
        pkg_info = pip.show(pkg_name)[pkg_name]
        print(pkg_info)
    print()


if __name__ == "__main__":
    main()
