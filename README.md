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
#for example:
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

# Time definition and Data Structure: 
The request data to eumetsat server made in `fci_download.py` is done with a 10 minute interval that matches the time aquisitin frequency of FCI. 
Each chunk has a different time aquisition, however we collect all chuncks of one time request in one file that is set with the starting time of the request data range.


All output of the scripts are saved in `$outDir` with this tree directories (last download was for 2025107.0950).
```
$outDir
├── data # only keeping last 2 days raw data
│   ├── 20250416
│   └── 20250417
│       ├── W_XX-EUMETSAT-Darmstadt,IMG+SAT,MTI1+FCI-1C-RRAD-FDHSI-FD--CHK-BODY---NC4E_C_EUMT_20250417001030_IDPFI_OPE_20250417000744_20250417000834_N__O_0001_0033.nc
│       ├── W_XX-EUMETSAT-Darmstadt,IMG+SAT,MTI1+FCI-1C-RRAD-FDHSI-FD--CHK-BODY---NC4E_C_EUMT_20250417001049_IDPFI_OPE_20250417000752_20250417000850_N__O_0001_0034.nc
        ...
│       └── W_XX-EUMETSAT-Darmstadt,IMG+SAT,MTI1+FCI-1C-RRAD-HRFI-FD--CHK-TRAIL---NC4E_C_EUMT_20250417095314_IDPFI_OPE_20250417095007_20250417095935_N__O_0060_0041.nc
├── log
│   ├── cron.log
│   ├── download.log
│   ├── ortho.log
│   └── skipTime.txt
├── nc
│   ├── 20250404
    ...
│   └── 20250417
│       ├── fci-ir-SILEXdomain-2025107.0000.nc
        ...
│       └── fci-ir-SILEXdomain-2025107.0950.nc
├── tiff
│   ├── 20250404
    ...
│   └── 20250417
│       ├── fci-rgb-SILEXdomain-2025107.0240.tiff # first day light in the east of the domain
        ...
│       └── fci-rgb-SILEXdomain-2025107.0950.tiff
└── to_download.txt

```

