import os
import sys

def apply_patch():
    try:
        import treetaggerwrapper
        import configparser
        treetaggerwrapper_path = treetaggerwrapper.__file__

        # Lire le fichier treetaggerwrapper.py
        with open(treetaggerwrapper_path, 'r') as file:
            filedata = file.read()

        # Remplacer SafeConfigParser par ConfigParser
        filedata = filedata.replace('configparser.SafeConfigParser', 'configparser.ConfigParser')

        # Écrire les modifications dans le fichier
        with open(treetaggerwrapper_path, 'w') as file:
            file.write(filedata)
        
        print("Patch applied successfully.")

    except Exception as e:
        print(f"Failed to apply patch: {e}", file=sys.stderr)

if __name__ == "__main__":
    apply_patch()
