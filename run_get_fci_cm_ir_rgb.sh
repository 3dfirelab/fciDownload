#!/bin/bash

# Create a temporary file
TMP_LOG=$(mktemp)

# Function to clean up temp file on exit
cleanup() {
    rm -f "$TMP_LOG"
}
trap cleanup EXIT


source /home/paugam/.myKey.sh
source /home/paugam/miniconda3/bin/activate fci
export srcDir=/home/paugam/Src/fciDownload/
export logDir=/mnt/data3/SILEX/FCI/RASTER/log
export outDir=/mnt/data3/SILEX/FCI/RASTER/

#below variable are not necessary outside UPC
export webDir=/home/paugam/WebSite/leaflet/data/fci_png/
export webDirVp9=/home/paugam/WebSite/leaflet/data/fci_vp9/

if [ ! -f "$logDir/skipTime.txt" ]; then
    mkdir -p $logDir
    touch "$logDir/skipTime.txt"
fi

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
    echo 'call fci_download.py'
    python $srcDir/fci_download.py $utc_time4mtg $outDir >& $logDir/download.log
    export satus_download=$?
else
    echo 'fci_download is locked'
    exit 0
fi

echo 'status from fci_download.py'
echo $satus_download

if [ $satus_download -eq 3 ]; then
    #data not found on eumetsat server we go forward
    #echo "$utc_time4mtg" | cat - "$logDir/skipTime.txt" > temp && mv temp "$logDir/skipTime.txt"
    { echo "$utc_time4mtg"; cat "$logDir/skipTime.txt"; } > temp && mv temp "$logDir/skipTime.txt"

    # Replace T_ with space to make the datetime format more standard
    datetime="${utc_time4mtg//T_/ }"
    # Now pass the full expression as a single string to `-d`
    new_time=$(date -u -d "$datetime +10 minutes" +"%Y-%m-%dT_%H%M")

    echo $new_time &> $outDir/to_download.txt
    rm  $outDir/lock_download.txt
fi


#orthorectify raw FCI data to rgb tiff and nc ir
if [ $satus_download -eq 2 ]; then
    if pgrep -f "python /home/paugam/Src/fciDownload//fci_ortho.py" > /dev/null; then
        exit 0
    else
        touch $outDir/lock_download.txt
        python $srcDir/fci_ortho.py $utc_time4mtg $outDir >& $logDir/ortho.log
       
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

        #only for estrella to udpate server at UPC
        if [ "$(hostname)" = "estrella" ]; then
            #udpate file on the data dir of the webserver
            #python $srcDir/updateWebsite_with_last2days.py $outDir $webDir
            #update webm only every hour
            if [[ "${utc_time4mtg: -2}" == "00" ]]; then
                python "$srcDir/updateWebsite_vp9_with_last2days.py" "$outDir" "$webDirVp9"
                python "$srcDir/make_sidecar.py" "$webDirVp9/rgb.webm"
                python "$srcDir/make_sidecar.py" "$webDirVp9/ir38.webm"
            fi
        fi 
        
        echo $new_time &> $outDir/to_download.txt
        rm  $outDir/lock_download.txt
    fi
fi 

if [ $satus_download -eq 0 ]; then
    echo $utc_time4mtg &> $outDir/to_download.txt
fi


# Your script logic, redirect all output to temp log
{
    echo "Running the script at $(date)"
    # your commands here
} >> "$TMP_LOG" 2>&1

# If we reached here, we want to write the output to cron.log
cat "$TMP_LOG"

