import os
import sys

print(" Démarrage du pipeline...")

python_exec = sys.executable

# -------------------
# Étape 1: Staging
# -------------------
print("\n Étape 1: Staging")
os.system(f'"{python_exec}" loads/load_staging.py')

# -------------------
# Étape 2: Clean
# -------------------
print("\n Étape 2: Clean")
os.system(f'"{python_exec}" scripts/clean.py')

# -------------------
# Étape 3: Warehouse
# -------------------
print("\n Étape 3: Warehouse")
os.system(f'"{python_exec}" loads/load_warehouse.py')

print("\n Pipeline terminé!")



