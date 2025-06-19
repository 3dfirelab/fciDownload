import os
import shutil
import subprocess
from datetime import datetime, timedelta
import sys
import tempfile
import pdb
from PIL import Image
import numpy as np

def resize_image_if_needed_and_copy(input_path, output_path):
    with Image.open(input_path) as img:
        if img.size == (2910, 2171):
            resized = img.resize((969, 723), Image.Resampling.LANCZOS)
            resized.save(output_path)
        else:
            img.save(output_path)  # Save as-is if no resize is needed

def parse_datetime_from_filename(fname):
    """Extract datetime object from filename assumed format: something-YYYYDDD.HHMM.png"""
    try:
        date_str = ''.join(fname.split('-')[-1].split('.')[:2])
        return datetime.strptime(date_str, '%Y%j%H%M')
    except Exception:
        return None

def convert_to_vp9(temp_dir, output_path_base, framerate=10, bitrate='2M'):
    """Use FFmpeg to convert PNGs in temp_dir to VP9 video, with start time and duration in filename."""
    pngs = sorted([f for f in os.listdir(temp_dir) if f.endswith('.png')])
    if not pngs:
        print(f"⚠️ No images to convert in {temp_dir}")
        return

    # Parse times
    timestamps = [parse_datetime_from_filename(f) for f in pngs]
    timestamps = [t for t in timestamps if t is not None]
    if not timestamps:
        print(f"⚠️ No valid timestamps found in {temp_dir}")
        return

    timestamps.sort()
    start_time = timestamps[0]
    deltaT = timedelta(minutes=10) # MTG freq 
    end_time = timestamps[-1] + deltaT
    duration = int((end_time - start_time).total_seconds())

    # Rename sequentially for FFmpeg
    for i, fname in enumerate(pngs):
        old_path = os.path.join(temp_dir, fname)
        new_name = f"frame_{i:04d}.png"
        new_path = os.path.join(temp_dir, new_name)
        os.rename(old_path, new_path)

    # Construct output path with start time and duration
    start_str = start_time.strftime('%Y%jT%H%MZ')
    print('now_utc: ', now_utc)
    print('start time: ', start_str)
    print('end time: ', end_time)

    output_path = f"{output_path_base}_new.webm"
    cmd = [
    'ffmpeg',
    '-y',
    '-framerate', str(framerate),
    '-i', os.path.join(temp_dir, 'frame_%04d.png'),
    '-c:v', 'libvpx-vp9',
    '-crf', '30',
    '-b:v', '0',
    '-r', str(framerate),
    '-g', '30',
    '-keyint_min', '30',
    '-sc_threshold', '0',
    '-cpu-used', '2',
    '-deadline', 'good',
    '-threads', '8',
    '-row-mt', '1',
    '-auto-alt-ref', '1',
    '-metadata', f'real_start_time={start_str}',
    '-metadata', f'real_duration={duration}',
    output_path
    ]
    '''
    cmd = [
		'ffmpeg',
		'-y',
		'-framerate', str(framerate),
		'-i', os.path.join(temp_dir, 'frame_%04d.png'),
		'-c:v', 'libvpx-vp9',
		'-b:v', bitrate,
		'-r', str(framerate),
		'-g', '10',
		'-keyint_min', '10',
		'-sc_threshold', '0',
		'-cpu-used', '8',
		'-deadline', 'realtime',
		'-threads', '8',
		'-row-mt', '1',
		'-auto-alt-ref', '1',
		'-metadata', f'real_start_time={start_str}',
		'-metadata', f'real_duration={duration}',
		output_path
	]
    '''
    

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Created video: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed: {e}")


# Create a blank RGB image with same size as resized outputs
def generate_placeholder_image(dst_path, size=(969, 723)):
    img = Image.new('RGB', size, color=(0, 0, 0))  # Black placeholder
    img.save(dst_path)


if __name__ == '__main__':

    # Input arguments
    src_root = os.path.join(sys.argv[1], 'png')  # e.g., /mnt/data3/SILEX/MTG-FCI/png
    dst_root = sys.argv[2]                       # e.g., /home/paugam/WebSite/leaflet/data/fci_png

    os.makedirs(dst_root, exist_ok=True)

    # Subdirectories mapping (source to output base name)
    subdirs = {
        'IR38': 'ir38',
        'NIR22': 'nir22',
        'RGB': 'rgb'
    }

    # UTC now and time window
    now_utc = datetime.utcnow()
    cutoff_time = now_utc - timedelta(hours=54)

    #Process each subdirectory (channel)
    for src_sub, output_name in subdirs.items():
        if 'nir' in output_name : continue
        src_path = os.path.join(src_root, src_sub)
        output_file_base = os.path.join(dst_root, output_name)

        if not os.path.isdir(src_path):
            print(f"⚠️ Source directory missing: {src_path}")
            continue

        with tempfile.TemporaryDirectory() as temp_dir:
            prev_dt = None
            for fname in sorted(os.listdir(src_path)):
                if not fname.endswith('.png'):
                    continue
                dt = parse_datetime_from_filename(fname)

                if dt is not None and dt >= cutoff_time:
                    if prev_dt is not None:
						# Fill gaps greater than 10 minutes
                        delta = dt - prev_dt
                        while delta > timedelta(minutes=10):
                            prev_dt += timedelta(minutes=10)
                            missing_fname = f"fci-rgb-SILEXdomain-{prev_dt.strftime('%Y%j.%H%M')}.png"
                            missing_dst = os.path.join(temp_dir, missing_fname)
                            generate_placeholder_image(missing_dst)
                            delta = dt - prev_dt

                    # Copy or resize the current image
                    src_file = os.path.join(src_path, fname)
                    dst_file = os.path.join(temp_dir, fname)
                    resize_image_if_needed_and_copy(src_file, dst_file)
                    prev_dt = dt
            
			#generate _new.webm file on the webserver        
            convert_to_vp9(temp_dir, output_file_base)
            #change _new.webm to webm file
            old_path = f"{output_file_base}_new.webm"
            new_path = f"{output_file_base}.webm"
            if os.path.exists(old_path):
                shutil.move(old_path, new_path)
                print(f"Moved {old_path} → {new_path}")
            else:
                print(f"Source file {old_path} does not exist.")


