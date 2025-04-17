import xarray as xr 
import satpy 
from satpy import Scene
import numpy as np
from satpy import find_files_and_readers
import sys
import os 
import zipfile
import math 
from datetime import datetime, timezone, timedelta
import pdb 
import pickle
import shutil
import rioxarray
import matplotlib.pyplot as plt 
import contextlib
import warnings 
import geopandas as gpd
import pandas as pd 
from shapely.geometry import Point
from pyproj import CRS, Transformer

##########################
def adjust_da_attr(da):
    #expand dict attr 
    # Expand the 'metadata' dictionary into multiple attributes
    for attrname in ['orbital_parameters','time_parameters']:
        if attrname in da.attrs.keys():
            metadata = da.attrs.get(attrname, {})  # Get the metadata dictionary

            # Add each key-value pair as a separate attribute
            for key, value in metadata.items():
                da.attrs['{:s}_{:s}'.format(attrname,key)] = value

            # Remove the original 'metadata' attribute
            del da.attrs[attrname]

    #replace datetime attr by string
    todel=[]
    for attr, value in da.attrs.items():
        if isinstance(value, datetime):
            da.attrs[attr] = value.strftime("%Y-%m-%d %H:%M:%S.%f") 
        if isinstance(value, bool):
            da.attrs[attr] = value.astype(np.uint8)
        if isinstance(value, bool):
            da.attrs[attr] = int(value)
        if isinstance(value, np.ndarray):
            da.attrs[attr] = ' '.join(['{:d}'.format(xx) for xx in value])
        if isinstance(value, np.uint16):
            da.attrs[attr] = int(value) 
        if isinstance(value, np.float64):
            da.attrs[attr] = float(value) 
        if isinstance(value, satpy.dataset.dataid.WavelengthRange):
            da.attrs[attr] = '{:.2f} {:.2f} {:.2f}'.format(value.min, value.central,value.max)
            
        if value is None:
            todel.append(attr)
    
    for attr in todel:
        del da.attrs[attr]
    return da


if __name__ == '__main__':
   
    time_str_input = sys.argv[1] 
    ##########################################################
    # Define time bounds 
    ##########################################################
    dtstart = datetime.strptime(time_str_input, "%Y-%m-%dT_%H%M") #- timedelta(minutes=30) #30 min latency from the datastore
    dtend   = dtstart + timedelta(minutes=10)
    
    dirdata  ='/mnt/data3/SILEX/MTG-FCI/data/'
    
    dirin = '{:s}/{:s}/'.format(dirdata,dtstart.strftime("%Y%m%d"))
    diroutnc = '{:s}/{:s}/'.format(dirdata.replace('data/','nc/'),dtstart.strftime("%Y%m%d"))
    os.makedirs(diroutnc,exist_ok=True)
    dirouttiff = '{:s}/{:s}/'.format(dirdata.replace('data/','tiff/'),dtstart.strftime("%Y%m%d"))
    os.makedirs(dirouttiff,exist_ok=True)
    
    files = find_files_and_readers(base_dir=dirin, reader='fci_l1c_nc', start_time=dtstart, end_time=dtend)
    
    # read the file
    scn = Scene(filenames=files)
    
    #load RGB and IR ands resample
    with open(os.devnull, 'w') as fnull:
        with contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
            #scn.load(['ir_38','ir_105','nir_22','vis_06'], upper_right_corner="NE")
            #scn.load(['natural_color','ir_38','ir_105','nir_22','nir_16','vis_06'], upper_right_corner="NE")
            scn.load(['natural_color','ir_38','ir_105','nir_22','nir_16'], upper_right_corner="NE")
    scn_resampled = scn.resample("eurol1", resampler='nearest', radius_of_influence=5000)
    
    #if transformer is None: 
    #    # Define the CRS (replace with your actual CRS from scn['ir_38'].crs)
    #    projected_crs = CRS.from_string(scn['ir_38'].crs.item().to_wkt())
    #    # Target CRS (WGS84 for lat/lon)
    #    target_crs = CRS.from_epsg(4326)  # WGS84
    #    # Create a transformer object
    #    transformer = Transformer.from_crs(projected_crs, target_crs, always_xy=True)
   
    fdir38 = scn['ir_38']
    x = fdir38.x
    y = fdir38.y[::-1]
    yy,xx = np.meshgrid(y,x)
    dxx = np.diff(xx,axis=0)
    dyy = -1*np.diff(yy,axis=1)
   
    #get time
    time = scn_resampled['ir_38'].attrs['start_time']
    time_img_ = scn_resampled['ir_38'].attrs['start_time'].strftime("%Y%j.%H%M") 
    if (time-dtstart).total_seconds() != 0 : 
        print('pb in time')
        sys.exit()

    #crop to zone
    scn_cropped = scn_resampled.crop(xy_bbox=(-1.2E6, -6.34E6, 3.0E6, -4.2E6))
   
    #scn_cropped['ir_38'].plot()
    #plt.show()
    #sys.exit()
    
    daR = adjust_da_attr(scn_cropped['natural_color'].sel(bands='R').drop_vars('bands').rename('R'))
    #daR.attrs.clear()
    daG = adjust_da_attr(scn_cropped['natural_color'].sel(bands='G').drop_vars('bands').rename('G'))
    #daG.attrs.clear()
    daB = adjust_da_attr(scn_cropped['natural_color'].sel(bands='B').drop_vars('bands').rename('B'))
    #daB.attrs.clear()
    daIR038 = adjust_da_attr(scn_cropped['ir_38'].rename('ir_38'))
    #daIR039.attrs.clear()
    daIR105 = adjust_da_attr(scn_cropped['ir_105'].rename('ir_105'))
    #daIR108.attrs.clear()
    daNIR22 = adjust_da_attr(scn_cropped['nir_22'].rename('nir_22'))
    daNIR16 = adjust_da_attr(scn_cropped['nir_16'].rename('nir_16'))
    #daVIS06 = adjust_da_attr(scn_cropped['vis_06'].rename('vis_06'))


    ds_ir = xr.merge([
                  daIR038,daIR105,daNIR22,daNIR16
                  #daR,daG,daB,daIR038,daIR105,daNIR22,daNIR16,daVIS06
                  #daIR038,daIR105,daNIR22,daVIS06
                  ], 
                  compat='override'
                  )
    ds_vis = xr.merge([
                  daR,daG,daB
                  ], 
                  compat='override'
                  )

    crs = ds_ir.attrs["area"].to_cartopy_crs()
    
    ds_ir = ds_ir.rio.write_crs(crs,inplace=True)
    ds_ir=ds_ir.drop_vars('crs')
    ds_ir = ds_ir.expand_dims({"time": [time]})  # Add time dimension
    ds_ir.attrs['crs']=ds_ir.rio.crs.to_string()
    
    ds_vis = ds_vis.rio.write_crs(crs,inplace=True)
    ds_vis=ds_vis.drop_vars('crs')
    ds_vis = ds_vis.expand_dims({"time": [time]})  # Add time dimension
    ds_vis.attrs['crs']=ds_vis.rio.crs.to_string()

   
    '''
    listofattrtosaveExt = ['area','_satpy_id','prerequisites']
    with open(dirout+'/seviri-extAttr-S-EU-{:s}.pkl'.format(time_img), 'wb') as f:
        pickle.dump([ds.attrs[xx] for xx in listofattrtosaveExt], f)
    for xx in listofattrtosaveExt:
        del ds.attrs[xx]
    for var in list(ds.data_vars): 
        for xx in listofattrtosaveExt:
            if xx in ds[var].attrs.keys():
                del ds[var].attrs[xx]
    '''

    #attr2del = ['area','_satpy_id', 'prerequisites', 'optional_prerequisites','ancillary_variables']
    attr2del = ['area','_satpy_id', 'ancillary_variables']
    for var in ds_ir.data_vars:
        for attrname in attr2del:
            if attrname in ds_ir[var].attrs:
                del ds_ir[var].attrs[attrname]
    for attrname in attr2del:
        del ds_ir.attrs[attrname]
    print('save NC')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        ds_ir.to_netcdf(diroutnc+'/fci-ir-SILEXdomain-{:s}.nc'.format(time_img_))
    
    
    attr2del = ['area','_satpy_id', 'prerequisites', 'optional_prerequisites']
    for var in ds_vis.data_vars:
        for attrname in attr2del:
            if attrname in ds_vis[var].attrs:
                del ds_vis[var].attrs[attrname]
    for attrname in attr2del:
        del ds_vis.attrs[attrname]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        rgb = ds_vis[["R", "G", "B"]].to_array(dim="band") 
        rgb_single_time = rgb.isel(time=0)
        
        #mask = (rgb_single_time != 0) & ~np.isnan(rgb_single_time)
        #print( 'test empty rgb', mask.any().compute().item())
        
        has_other_values = ((rgb_single_time != 0) & ~np.isnan(rgb_single_time)).any()

        # If using Dask, compute the result
        if hasattr(has_other_values, 'compute'):
            has_other_values = has_other_values.compute()

        print("Contains values other than 0 or NaN:", bool(has_other_values))

        if (bool(has_other_values)): 
            print('save RGB')
            rgb_single_time.rio.to_raster(dirouttiff+'/fci-rgb-SILEXdomain-{:s}.tiff'.format(time_img_))

    del scn 



