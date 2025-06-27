import os
import shutil
from datetime import datetime, timedelta
import sys

# Paths
#src_root = '/mnt/data3/SILEX/MTG-FCI/png'
#dst_root = '/home/paugam/WebSite/leaflet/data/fci_png'
src_root = sys.argv[1] + '/png/'
dst_root = sys.argv[2]

# Subdirectories mapping (source to destination)
subdirs = {
    'IR38': 'ir38',
    'NIR22': 'nir22',
    'RGB': 'rgb'
}

# Compute the valid date strings for the last 2 days (UTC)
today = datetime.utcnow()
valid_dates = { (today - timedelta(days=i)).strftime('%Y%j') for i in range(2) }

# Ensure destination directories exist
for dst_sub in subdirs.values():
    os.makedirs(os.path.join(dst_root, dst_sub), exist_ok=True)

def extract_datecode(filename):
    """Extracts the YYYYDDD part from the filename"""
    try:
        parts = filename.split('-')
        datecode = parts[-1].split('.')[0][:7]
        return datecode
    except Exception:
        return None

# Process each subdirectory
for src_sub, dst_sub in subdirs.items():
    src_path = os.path.join(src_root, src_sub)
    dst_path = os.path.join(dst_root, dst_sub)

    # --- Copy files from last 2 days ---
    if os.path.isdir(src_path):
        for filename in os.listdir(src_path):
            if filename.endswith('.png'):
                datecode = extract_datecode(filename)
                if datecode in valid_dates:
                    src_file = os.path.join(src_path, filename)
                    dst_file = os.path.join(dst_path, filename)
                    shutil.copy2(src_file, dst_file)

    # --- Delete outdated files in destination ---
    if os.path.isdir(dst_path):
        for filename in os.listdir(dst_path):
            if filename.endswith('.png'):
                datecode = extract_datecode(filename)
                if datecode and datecode not in valid_dates:
                    try:
                        os.remove(os.path.join(dst_path, filename))
                    except Exception as e:
                        print(f"Could not delete {filename}: {e}")

