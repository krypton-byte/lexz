import argparse
import re


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument('--version', type=str)
    args = arg.parse_args()
    if args.version:
        vers = re.search(r'\/?([0-9][0-9A-Za-z\.]+)', args.version)
        if vers:
            version = vers[1]
        else:
            version = '0.0.1'
        new = open('pyproject.toml').read().replace('0.1.0', version)
        with open('pyproject.toml', 'w') as fil:
            print(new)
            fil.write(new)


main()
