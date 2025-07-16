#!/usr/bin/env python3

# pip install pyyaml rds2py scipy
import yaml
import rds2py
import os

with open("config.yaml", "r") as f:
    data = yaml.safe_load(f)

colours = {"red": "\033[31m", "green": "\033[32m", "clear": "\033[0m"}


def print_colour(text, colour):
    print(colours[colour] + text + colours["clear"])


def print_okay(text):
    print_colour(text, "green")


def print_error(text):
    print_colour(text, "red")


def check_species_files(species, data):
    print("\n=== " + species + " ===")
    subdir = data[species]["data_subdir"]
    if not os.path.isdir(subdir):
        return print_error(f"Error: directory {subdir} does not exist!")

    for file_type in data[species]:
        if file_type == "data_subdir":
            continue

        file = os.path.join(subdir, data[species][file_type])

        print(file_type + "\t" + file, end="")
        try:
            if not os.path.exists(file):
                raise FileNotFoundError(f"File {file} does not exist!")

            if file.endswith(".RDS"):
                content = rds2py.read_rds(file)
            else:
                with open(file, "r") as f:
                    content = f.read()
            print_okay(" \u2713")
        except Warning as w:
            print(f"Warning caught: {w}")
        except Exception as e:
            print_error(f" \u2717\n  ! Error: {e}")


for species in data:
    if not "data_subdir" in data[species]:
        continue
    check_species_files(species, data)
