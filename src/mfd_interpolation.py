# -*- coding: utf-8 -*-
"""
Created on Wed Aug 29 15:13:21 2018

mfd_interpolation.py 
"Helsinki edition" (2018)

Copyright (C) 2018.  Digital Geography Lab / Accessibility Research Group, University of Helsinki.
Programmed by: Henrikki Tenkanen, University of Helsinki, Finland. Edits for the Helsinki edition made by Claudia Bergroth.

This script is used for creating the data in Bergroth et al. (submitted). 
This script is based on the script behind the following article:
Järv Olle, Tenkanen Henrikki & Toivonen Tuuli (2017). Enhancing spatial accuracy of mobile
phone data using multi-temporal dasymetric interpolation. Published in International Journal of 
Geographical Information Science.

PURPOSE:
--------
This script implements the multi-temporal dasymetric interpolation method (see Järv et al. 2017) for mobile phone data. The script reallocates the mobile phone data into statistical grid cells using ancillary data sources.

REQUIREMENTS:
-------------
Python 3 with following packages and their dependencies: pandas, geopandas.
  
DATA:
-----
In short, this script requires four datasets:
  
1) a disaggregated physical surface layer, 
2) time-dependent human activity data,
3) mobile phone data 
4) desired target zones (statistical grid 250 m x 250 m)
    
CONTACT:
--------
 - claudia.bergroth (a) helsinki.fi
 - olle.jarv (a) helsinki.fi
 - henrikki.tenkanen (a) helsinki.fi
 - http://www.helsinki.fi/science/accessibility
  
LICENCE:
--------
mfd_interpolation.py by Digital Geography Lab / Accessibility Research Group (University of Helsinki) is licensed under
a Creative Commons Attribution 4.0 International License.
More information about license: http://creativecommons.org/licenses/by-sa/4.0/
  
"""

import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
import os

def main():    
    
    """ Main method that controls the Multi-temporal function-based dasymetric interpolation method (MFD interpolation). """
   

    # File paths
    # ...........
    
    # Human activity type data
    hat_fp = r"...\data\TimeUseData\TimeUse.xlsx"
    
    # Disaggregated physical surface layer ( landuse + buildings + coverage areas + predefined statistical units )
    dps_fp = r"...\data\PhysicalSurfaceData\Disaggregated_physical_surface_250m.shp"
    
    # Mobile phone data (network data)
    cdr_fp = r"...\data\MobilePhoneData\hourlymedian_HSPA_tz.xlsx"
    
    # Target zones (Predefined spatial units)
    tz_fp = r"...\data\TargetZones\Target_zones_grid250m.shp"
    
    # Output folder for the results
    out_dir = r"...\results"
    
    # Prefix for the output name (time info for the filename will be added automatically)
    out_prefix = "ZROP_results_HSPA"
    
    # Column names in the human activity data
    # .......................................
    
    # Activity function type column in the time-use survey data
    activity_function_type = 'Activity_function_type'
    
    # Seasonal factor column in the time-use survey data
    seasonal_factor_col = 'Seasonal_factor'
    
    # Spatial unit column in the time-use survey data
    spatial_unit_col = 'Spatial_unit'
    
    # Important Note:
    # ---------------
    # Time specific human activity percentages per function type should be named in a following manner:
    # H9t, H10t, H11t, H12t, H13t  --> where the numbers informs the hour of the day 
    
    # ........................................................
    # Column names in the disaggregated physical surface layer
    # ........................................................
    
    # Source zone column (Base Station ID) in the Disaggregated physical surface layer
    source_zone_col_dps = 'SITEID'
    
    # Target zone column (Grid Cell ID) 
    target_zone_col = 'YKR_ID'
    
    # Column with building height information in the disaggregated physical surface layer
    #building_height_col = '' #RFA already calculated at an earlier stage!
    
    # Column in the disaggregated physical surface layer that has information about building and landuse types
    #building_landuse_features = '' #SPUT already calculated at an earlier stage!
    
    # ...........................................
    # Column names in the Mobile phone data (CDR)
    # ...........................................
    
    # Source zone column (Base Station ID) in the Mobile phone dataset
    source_zone_col_cdr = 'SITEID'
    
    # Important Note:
    # ---------------
    # Time specific amount of mobile phone users per Base Station should be named in a following manner:
    # H9m, H10m, H11m, H12m, H13m  --> where the numbers informs the hour of the day 
    
    # ..............................................
    # Column names in the Target zone spatial layer 
    # ..............................................
    
    # Target zone column (Grid Cell ID) in the spatial layer 
    # --> typically should be the same name as in the disaggregated physical surface layer
    target_zone_col_spatial = 'YKR_ID'
    
    # Time and projection parameters
    # ..............................
    
    # Start hour
    start_h = 0
    
    # End hour
    end_h = 23
    
    # EPSG code for desired output projection
    epsg = 3067
    
    # ----------------------------------------------------------
    
    print("Running MFD interpolation tool ...")
    
    # Iterate over the desired hours of the day
    for xhour in range(start_h, end_h+1):
        print("Processing hour: %s" % xhour)
        
        # ------------------------------------------------------------------
        # 1. Read input data
        # -------------------------------------------------------------------
    
        # tu = time use
        # dps = disaggregated physical layer
        # cdr = mobile phone data
        # target = output spatial layer in statistical units
        tu, dps, cdr, target = readFiles(time_use_fp=hat_fp, dps_fp=dps_fp, cdr_fp=cdr_fp, tz_fp=tz_fp)
    
        # Use time window (xhour) for the whole analysis 
        # ...............................................
        time_window = 'H%s' % xhour
        
        # --------------------------------------------------------------------
        # 2. Calculate Relative share of Mobile Phone users (RMP)
        # --------------------------------------------------------------------
            
        # Calculate RMP - i.e. normalize the Mobile Phone user counts to scale 0.0 - 1.0
        # Note: In the here this part is done earlier than in the manuscript (--> chapter 3.4) for practical reasons. 
        # ..........................................................................................
        
        # Name of the mobile phone user counts per site_id in the table
        twm = time_window + 'm'
        cdr = calculateRMP(cdr, time_window=time_window)

        # --------------------------------------------------------------------
        # 3. Reclassify Landuse layer ( based on Open Street Map information )
        # --------------------------------------------------------------------
    
        """This step is done already earlier, due to requirements set by data.
        """
        # --------------------------------------------------------------------
        # 4. Join layers into same DataFrame
        # --------------------------------------------------------------------
    
        # Join necessary columns from <tu> table
        # .........................................
    
        # Columns in the time-use dataset
        # ...............................
        # time_window + 't' -command below produces e.g. 'H10t' which is a column that has the time-usage information for specific hour
        tu_cols = [time_window+'t', spatial_unit_col, activity_function_type, seasonal_factor_col]
    
        # Columns in the disaggregated physical surface layer
        # ...............................
        # Abbreviations:
        # AFT ==> Activity_function_type
        # SPUT ==> Spatial_unit
        # SF ==> Seasonal_factor
        dps_cols = ['SPUT', 'AFT', 'SF']
    
        # Join the datasets together based on dps_cols and all tu_cols except the first item (i.e. time-usage info column such as 'H10t')
        dps = dps.merge(tu[tu_cols], left_on=dps_cols, right_on=tu_cols[1:])
        #print(dps.head())
    
        # Join necessary columns from <cdr> table
        # .........................................
    
        # Source zones column ==> I.e. column that has unique IDs for mobile phone coverage areas (base stations)
        sz_col_dps = source_zone_col_dps
        sz_col_cdr = source_zone_col_cdr
    
        dps = dps.merge(cdr[[twm, 'RMP %s' % twm, sz_col_cdr]], left_on=sz_col_dps, right_on=sz_col_cdr)
    
        # ---------------------------------------------------------------------
        # 5. Calculate the Relative Floor Area (RFA)
        # ---------------------------------------------------------------------
        
        """This step is done already earlier, due to requirements set by data.
        """
        
        # ---------------------------------------------------------------------
        # 6. Calculate the Estimated Human Presences (EHP)
        # ---------------------------------------------------------------------
    
        # Abbreviations:
        # sf_col ==> Seasonal factor column
        
        # Note:
        # By default the seasonal factor is read from the human activity data (i.e. from the seasonal_factor_column)
        # However, you can also use the seasonal factor that is classified based on the physical surface layer features. Then, pass column 'SF' to sf_col below)
        
        EHP = calculateEHP(df=dps, time_window=time_window, sz_id_col=sz_col_dps, sf_col=seasonal_factor_col)
        """note!! changed rfa -> dps"""
        
        # ----------------------------------------------------------------------
        # 7. Calculate Relative Observed Population (ROP)
        # ----------------------------------------------------------------------
    
        ROP = calculateROP(df=EHP, time_window=time_window)              
    
        # -----------------------------------------------------------------------
        # 8. Aggregate spatially to desired target zones (ZROP)
        # -----------------------------------------------------------------------
    
        # Target zones column ==> I.e. a column for unique ids of desired spatial grid cells ('Grid Cell ID' in the article)
        tz_col = target_zone_col    
        ZROP = calculateZROP(df=ROP, time_window=time_window, tz_id_col=tz_col)
    
        # -----------------------------------------------------------------------
        # 9. Save result to disk in Shapefile format
        # -----------------------------------------------------------------------
        out_filename = "%s_%s.shp" % (out_prefix, time_window)
        out = os.path.join(out_dir, out_filename)
    
        # Save file to disk
        saveToShape(input_df=ZROP, grid_df=target, output_path=out, tz_id_col_spatial=target_zone_col_spatial, tz_id_col=tz_col, epsg_code=epsg)
        

def readFiles(time_use_fp=None, dps_fp=None, cdr_fp=None, tz_fp=None):
    """ 
    Read files into memory that are needed for Multi-temporal Dasymetric Interpolation 
    """
    # Read input files
    time_use = pd.read_excel(time_use_fp,sheet_name=0) #originally used param sheetname is deprecated:https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_excel.html
    dps = gpd.read_file(dps_fp)
    cdr = pd.read_excel(cdr_fp,sheet_name=0) 
    tz = gpd.read_file(tz_fp)
    return time_use, dps, cdr, tz

def calculateRMP(cdr, time_window):
    """
    Calculate Relative Mobile Phone data distribution (RMP) for each subunit within a given base station.
    See 3.4 in the article and S1 in the supplementary materials of Järv et al. 2017.
    
    Note: In the manuscript this part is done later than in this script for practical reasons. 

    """
    # Name of the mobile phone user counts per site_id in the table
    twm = time_window + 'm'
    
    # Normalize the Mobile Phone user counts to scale 0.0 - 1.0
    cdr['RMP %s' % twm] = cdr[twm] / cdr[twm].sum()
    return cdr


def calculateEHP(df, time_window, sz_id_col, sf_col):
    """
    Calculate Estimated Human Presence (EHP).
    See chapter 3.3 in the article + chapter S2.3, Figure S2 and Table S3 in the supplementary materials of Järv et al. 2017.
    
    """
    # Time Window
    tw = time_window + 't'
    
    # Calculate (absolute) estimated human presence (aEHP) for selected time window  ==> [Relative Floor Area] * [Seasonal Factor Coefficient] * [Hour Factor H]
    df['aEHP %s' % tw] = df['RFA'] * df[sf_col] * df[tw]

    # Create column for estimated human presence (EHP) that is a normalized aEHP (scale 0.0 - 1.0).
    df['EHP %s' % tw] = None

    # Group data by 'Base_station_id'
    grouped = df.groupby(sz_id_col)

    # Iterate over groups and normalize the values
    for key, values in grouped:

      # Get the indices of the values
      sz_indices = values.index

      # Get the sum of 'aEHP' values within site
      sum_aEHP = values['aEHP %s' % tw].sum()
     
      # Normalize the aEHP values by 'Site_ID' for each time unit (scale 0.0 - 1.0) ==> RMP
      EHP = values['aEHP %s' % tw] / sum_aEHP

      # Assign values to 'RMP' columns
      df.loc[sz_indices, 'EHP %s' % tw] = EHP.values

    return df

def calculateROP(df, time_window):
    """ 
    Calculate the Relative Observed Population (ROP) for each subunit within a base station. See Table E in S2. 
    See chapter 3.4 in the article + chapter S2.4 and Table S4 in the supplementary materials of Järv et al. 2017.
    
    """
    twt = time_window + 't'
    # Attribute name for normalized mobile phone users (RMP)
    twm = 'RMP %s' % time_window + 'm'
    # Calculate 'ROP' ==> 'EHP hh-hh' * 'RMP hh-hh' 
    df['ROP %s' % twt] = df['EHP %s' % twt] * df[twm]
    return df


def calculateZROP(df, time_window, tz_id_col):
    """ 
    Sum Relative Observed Population (ROP) for each target zone, i.e. calculate ZROP. 
    See chapter 3.5 in the article + chapter S2.5 and Table S5 in the supplementary materials of Järv et al. 2017.
    """
    
    tw = time_window
    rop = 'ROP ' + tw + 't'
    
    # Group data by 'Grid cell id'
    grouped = df.groupby(tz_id_col)

    # Create DataFrame for spatial units (e.g. a 100 m grid)
    ZROP_grid = pd.DataFrame()

    # Iterate over grid cells
    for key, values in grouped:

      # Sum all ROP features that belongs to the same 'Grid cell id'
      zrop = values[rop].sum()

      # Append to DataFrame
      ZROP_grid = ZROP_grid.append([[key, zrop]])

    # Set column names
    ZROP_grid.columns = [tz_id_col, 'ZROP %s' % tw]

    # Change grid cell id to numeric if possible
    try:
        ZROP_grid[tz_id_col] = ZROP_grid[tz_id_col].astype(int)
    except ValueError:
        print("Warning: Could not convert the ZROP values to numeric.")
        pass

    return ZROP_grid

def saveToShape(input_df, grid_df, output_path, tz_id_col_spatial, tz_id_col, epsg_code):
    """ Save ZROP values in <input_df> as Shapefile defined in <grid_df> to <output_path> using projection in <epsg code> """
    
    # Join the data with grid GeoDataFrame
    geo = grid_df[[tz_id_col_spatial, 'geometry']].merge(input_df, left_on=tz_id_col_spatial, right_on=tz_id_col, how='inner')
    
    # Re-project
    geo['geometry'] = geo['geometry'].to_crs(epsg=epsg_code)

    # Ensure that results is GeoDataFrame
    geo = gpd.GeoDataFrame(geo, geometry='geometry', crs=from_epsg(epsg_code))

    # Fill NaN values with 0
    geo = geo.fillna(value=0)

    # Save to disk
    geo.to_file(output_path)

    return geo

if __name__ == "__main__":
    geo = main()    
