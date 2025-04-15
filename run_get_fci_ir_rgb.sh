#!/bin/bash

source /home/paugam/miniconda3/bin/activate fci
export logDir=/mnt/data3/SILEX/MTG-FCI/log
export outDir=/mnt/data3/SILEX/MTG-FCI/

if [ ! -f "$outDir/to_download.txt" ]; then

    # Get current UTC timestamp in seconds
    now=$(date -u +%s)

    # Round down to the nearest 10 minutes (600 seconds)
    rounded=$(( now - (now % 600) ))

    # Convert back to readable UTC time
    utc_time4mtg=$(date -u -d "@$rounded" +"%Y-%m-%dT_%H%M")

    # Print the time
    echo "Current UTC time is to download: $utc_time4mtg"

else

    # Read the first line and set it as an environment variable
    first_line=$(head -n 1 "$outDir/to_download.txt")
    export utc_time4mtg="$first_line"
    echo "Current UTC time is to download: $utc_time4mtg"

fi

#download raw FCI data
if [ ! -f $outDir/lock_download.txt ]; then
    python /home/paugam/Src/Download-FCI/fci_download.py $utc_time4mtg $outDir >& $logDir/download.log
    export satus_download=$?
fi

echo 'status from fci_download.py'
echo $satus_download

#orthorectify raw FCI data to rgb tiff and nc ir
if [ $satus_download -eq 2 ]; then
    touch $outDir/lock_download.txt
    python /home/paugam/Src/Download-FCI/fci_ortho.py $utc_time4mtg  >& $logDir/ortho.log
   
    if [ $? -ne 0 ]; then 
        echo 'orth failed for '  $utc_time4mtg
        stop
    else
        echo 'ortho done, set now new time'
    fi
    # Replace T_ with space to make the datetime format more standard
    datetime="${utc_time4mtg//T_/ }"
    # Now pass the full expression as a single string to `-d`
    new_time=$(date -u -d "$datetime +10 minutes" +"%Y-%m-%dT_%H%M")

    echo $new_time &> $outDir/to_download.txt
    rm  $outDir/lock_download.txt
fi

if [ $satus_download -eq 0 ]; then
    echo $utc_time4mtg &> $outDir/to_download.txt
fi
