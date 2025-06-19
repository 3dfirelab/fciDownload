import eumdac
from datetime import datetime, timezone, timedelta
import shutil
import fnmatch
import requests
import time
import os
import zipfile
import json
import os
from shapely.wkt import loads
from shapely.geometry import Polygon
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import LineString
import sys
import pdb 
import subprocess

#########################################
def prepend_time_downloaded(dirout, new_line, max_lines=144):
    """
    Reads all lines from 'filepath', prepends 'new_line' at the top,
    and keeps only the first 'max_lines' lines. Then overwrites the file.
    """
    filepath = '{:s}/../../last_downloadCompleted.txt'.format(dirout)

    # Read existing lines
    if os.path.isfile(filepath): 
        with open(filepath, 'r') as f:
            lines = f.readlines()
    else: 
        lines = []

    # Prepend the new line at the top
    lines.insert(0, new_line + "\n")

    # Keep only the first max_lines lines
    lines = lines[:max_lines]

    # Overwrite the file with the updated lines
    with open(filepath, 'w') as f:
        f.writelines(lines)


#########################################
def run_eumdac_search(collection):
    """
    Runs 'eumdac search -c EO:EUM:DAT:0665 --limit 1' via subprocess,
    returning both return code and output.
    """
    # subprocess.run is recommended over subprocess.call and Popen directly
    # for simpler usage; 'capture_output=True' captures stdout/stderr
    process = subprocess.run(
            ["eumdac", "search", "-c", "EO:EUM:DAT:{:s}".format(collection), "--limit", "1"],
        capture_output=True,
        text=True,            # text=True ensures output is string rather than bytes
        check=False           # if True, would raise CalledProcessError on non-zero return
    )

    # You can inspect process.stdout, process.stderr, process.returncode
    return process.stdout



#########################################
# This function checks if a product entry is part of the requested coverage
def get_coverage(coverage, filenames):
    chunks = []
    for pattern in coverage:
        for file in filenames:
            if fnmatch.fnmatch(file, pattern):
                chunks.append(file)
    return chunks


#########################################
def download_chunks_in_time_window(dirout, fci_collection, selected_collection, dtstart, dtend, chunk_ids):
    """
    Search for products in the given time window, download relevant .nc entries and trailer chunk (0041).
    """

    if fci_collection == '0662':
        expected_product_entry_size = 61
    elif fci_collection == '0665':
        expected_product_entry_size = 49

    utc_now = datetime.now(timezone.utc)

    chunk_patterns = [f"_{cid}.nc" for cid in chunk_ids]

    # Products in time window
    products = selected_collection.search(dtstart=dtstart, dtend=dtend)
    print(f"Found {len(products)} matching timestep(s).")

    len_product_entry = 0  # assume nothing, so if behind schedule we pass, see below utc_now > dtstart.replace(tzinfo=timezone.utc)+timedelta(minutes=30)
    files_on_local_machine = 0
    # Filter relevant entries
    for product in products:
        len_product_entry =  len(product.entries)
        for entry in product.entries:
            if os.path.isfile(dirout+entry) : 
                files_on_local_machine += 1
                continue
            if any(pattern in entry for pattern in chunk_patterns):
                try:
                    with product.open(entry=entry) as fsrc:
                        local_filename = os.path.basename(fsrc.name)
                        print(f"Downloading file {local_filename}...")
                        dst_filename = '{:s}/{:s}'.format(dirout,local_filename)
                        with open(dst_filename, 'wb') as fdst:
                            shutil.copyfileobj(fsrc, fdst)
                            files_on_local_machine += 1
                        #print(f"Saved file {local_filename}")
                        
                        #prepend_line_and_limit(dirout, fci_collection, local_filename.split('.')[0])
                except Exception as e:
                    print(f"Error downloading {entry}: {e}")

    #for not being stuck on data not available. if we are 30 minute behind current time and len
    if utc_now > dtstart.replace(tzinfo=timezone.utc)+timedelta(minutes=30): 
        if len_product_entry < expected_product_entry_size:
            return 'could not find chunck on eumetsat server' 

    print('files on machine    : ',files_on_local_machine- len(chunk_ids) + 1)
    print('products to download: ',len(products))
    if files_on_local_machine - len(chunk_ids) +1  == len(products):
        return 'all file here for collec'
    else:
        return None


#########################################
def plot_chunk():
    # Convert chunk polygons to a GeoDataFrame
    gdf_chunks = gpd.GeoDataFrame({"chunk_id": list(chunk_polygons.keys()), "geometry": list(chunk_polygons.values())}, crs="EPSG:4326")

    # Plot setup
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={"projection": ccrs.PlateCarree()})
    ax.set_extent([-90, 90, -90, 90])
    ax.coastlines("50m", linewidth=0.25)
    ax.add_feature(cfeature.LAND, facecolor="lightgray", edgecolor="black", linewidth=0.25)

    # Plot chunks with labels
    for i, row in gdf_chunks.iterrows():
        chunk_id, chunk_poly = row["chunk_id"], row["geometry"]
        if not chunk_poly.is_valid: continue
        ax.fill(*chunk_poly.exterior.xy, color=plt.cm.tab20.colors[i % 20], alpha=0.25, transform=ccrs.PlateCarree())

        # Label position inside polygon
        center_x = (chunk_poly.bounds[0] + chunk_poly.bounds[2]) / 2 
        vertical_line = LineString([(center_x, chunk_poly.bounds[1]), (center_x, chunk_poly.bounds[3])])
        label_y = vertical_line.intersection(chunk_poly).centroid.y
        ax.text(center_x, label_y, chunk_id, fontsize=6, transform=ccrs.PlateCarree(), ha="center", va="center")

    # Highlight ROI
    ax.plot(*roi_polygon.exterior.xy, color="red", linewidth=1, linestyle="dashed", transform=ccrs.PlateCarree())
    plt.title("MTG Chunk coverage extent and user ROI")
    plt.show()


#########################################
if __name__ == '__main__':
#########################################
    
    time_str_input = sys.argv[1]
    dirout =  sys.argv[2]
    script_dir = os.path.dirname(os.path.abspath(__file__))

    ##########################################################
    # Define time bounds 
    ##########################################################
    dtstart = datetime.strptime(time_str_input, "%Y-%m-%dT_%H%M") #- timedelta(minutes=30) #30 min latency from the datastore
    #dtstart = datetime(2025, 4, 4, 9, 00)
    dtend   = dtstart + timedelta(seconds=9*60+59)
    
    ############################################################
    # Insert your personal key and secret into the single quotes
    ############################################################
    consumer_key = os.environ['EUMETSAT_consumer_key']       
    consumer_secret = os.environ['EUMETSAT_consumer_secret'] 

    credentials = (consumer_key, consumer_secret)

    token = eumdac.AccessToken(credentials)

    print(f"This token '{token}' expires {token.expiration}")

    dirout= dirout + '/data/'
    dirout = '{:s}/{:s}/'.format(dirout,dtstart.strftime("%Y%m%d"))
    os.makedirs(dirout,exist_ok=True)

    ##########################################################
    # Define ROI bounds (latitude and longitude bounding bbox)
    ##########################################################
    user_roi = {
        "lat_min": 35,
        "lat_max": 51,
        "lon_min": -10,
        "lon_max": 20
    }
    print(f"Defined ROI: {user_roi}")

    ###########################################
    # load chunk info
    ###########################################
    # Define file path to precomputed FCI data chunk map in WKT format 
    wkt_file_path = script_dir+"/FCI_chunks.wkt"  

    if not os.path.exists(wkt_file_path):
        raise FileNotFoundError(f"File {wkt_file_path} not found. Make sure it is in the repository.")

    # Load WKT chunk footprints
    with open(wkt_file_path, "r") as file:
        wkt_data = file.readlines()

    # Parse chunk polygons from WKT
    chunk_polygons = {}
    for line in wkt_data:
        chunk_id, wkt_poly = line.strip().split(',', 1)  # Extract chunk ID
        chunk_polygons[chunk_id] = loads(wkt_poly)  

    print(f"Loaded {len(chunk_polygons)} chunk footprints from WKT file.")


    ###########################################
    # get chunck from ROI
    ###########################################

    # Convert user ROI to a Shapely Polygon
    roi_polygon = Polygon([
        (user_roi["lon_min"], user_roi["lat_min"]),
        (user_roi["lon_min"], user_roi["lat_max"]),
        (user_roi["lon_max"], user_roi["lat_max"]),
        (user_roi["lon_max"], user_roi["lat_min"])
    ])

    # Find chunks that intersect with ROI
    relevant_chunks = []
    for chunk_id, chunk_poly in chunk_polygons.items():
        if roi_polygon.intersects(chunk_poly):
            relevant_chunks.append(chunk_id)

    print(f"Found {len(relevant_chunks)} chunks intersecting the ROI: {relevant_chunks}")
    # Always ensure trailer chunk "0041" is included
    relevant_chunks.append("0041")
    
    ###########################################
    # plot chunck and ROI
    ###########################################
    if False: 
        plot_chunk()

    all_good = 0 
    for fci_collection in ['0662','0665','0678']:
       
        #check if collection is available
        #lastAvailable = run_eumdac_search(fci_collection)
        
        '''
        if not(os.path.isfile('{:s}/../../last_downloaded_{:s}.txt'.format(dirout,fci_collection))):
            with open('{:s}/../../last_downloaded_{:s}.txt'.format(dirout,fci_collection), 'w') as f:
                pass

        filepath_lastDownloaded = '{:s}/../../last_downloaded_{:s}.txt'.format(dirout,fci_collection)
        with open(filepath_lastDownloaded, 'r') as f:
            lastDownloaded = [line.strip() for line in f]
        pdb.set_trace()
        if lastAvailable in lastDownloaded: 
            continue
        '''

        print(f"Time window: from {dtstart} to {dtend}.")
        datastore = eumdac.DataStore(token)
        selected_collection = datastore.get_collection('EO:EUM:DAT:{:s}'.format(fci_collection))
        
        #print collection info
        if False:
            #all collection available at https://api.eumetsat.int/data/browse/collections
            datastore = eumdac.DataStore(token)
            selected_collection = datastore.get_collection('EO:EUM:DAT:{:s}'.format(fci_collection))
            print(f"{selected_collection} - {selected_collection.title}")
            print(f"Description: {selected_collection.abstract}")
            print(f"Metadata: {selected_collection.metadata}")
            print(f"Search options: {selected_collection.search_options}")

     
        # Run the function
        flag = download_chunks_in_time_window(dirout,fci_collection,
                                              selected_collection=selected_collection, dtstart=dtstart, dtend=dtend, chunk_ids=relevant_chunks)

        #print(flag)
        if flag == 'all file here for collec': 
            all_good += 1 
   
        if flag == 'could not find chunck on eumetsat server':
            sys.exit(3)

    #print(all_good)
    if all_good == 2:
    #    prepend_time_downloaded(dirout, time_str_input)
        sys.exit(2)
