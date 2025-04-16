# Presentation:
Set of bash and pyhton scripts to upload in NRT data from FCI over the domain define in `fci_download.py`. 
see 
```
    user_roi = {
        "lat_min": 35,
        "lat_max": 51,
        "lon_min": -10,
        "lon_max": 20
    }
```
the script `run_get_fci_ir_rgb.sh` is run every minute. 
it controls if new chunck (strip of the full disc data of FCI) are available. 
Then download them in `$outDir` that is defined in `run_get_fci_ir_rgb.sh`
and run the `fci_ortho.py` to generate 2 files:
* geotiff with RGB
* netcdf with `ir_38`, `ir_105`, `nir_22`, `nir_16` 


# How to setup: 
1. in `run_get_fci_ir_rgb.sh` define the directories for output (`$outDir`) and log (`$logdir`)
2. set up a python environemnt named fci using the available `requirements.txt` file
```
python -m venv ~/Venv/fci
pip install -r requirements.txt
```
3. set your `consumer_key` and `consumer_secret` in file to source in `run_get_fci_ir_rgb.sh` (see `source /home/paugam/.myKey.sh` in `run_get_fci_ir_rgb.sh`). To get yor key you need to log to [https://api.eumetsat.int/api-key/#](https://api.eumetsat.int/api-key/#)

# How to run: 
There is also a script to delet old raw data, see `clean_fci_rawData.sh`
A cron example is:
```
* * * * * /home/paugam/Src/Download-FCI/run_get_fci_ir_rgb.sh > /mnt/data3/SILEX/MTG-FCI/log/cron.log
30 2 * * * /home/paugam/Src/Download-FCI/clean_fci_rawData.sh
```
If the scrip is 30 minutes behind realtime and cannot find the number of entries product on the eumetsat server it will skip this time step and go forwad.
A traks of the skipped time is saved in `$logDir/skipTime.txt`
