# -*- coding: utf-8 -*-
"""
Created on Thu Aug 23 11:06:43 2018

calculate areas and necessary cols for mfd
"""

import geopandas as gpd
import numpy as np

#----------------------------------------------------------------------------
#READ IN DATA
#----------------------------------------------------------------------------
fp_disaggregated_physica_surface = r'...\data\PhysicalSurfaceData\unioned_physical_surface_calculations_needed.shp'
dpsl = gpd.read_file(fp_disaggregated_physica_surface) #dpsl stands for disaggregated physical surface layer

#project to 3067
dpsl= dpsl.to_crs({'init': 'epsg:3067'})

dpsl.dtypes
dpsl.tail()
dpsl.head()

#ASSIGN SPATIAL UNIT TYPE (building/land)
#----------------------------------------------------------------------------
dpsl['SPUT'] = np.where((dpsl['AFT'].isnull()), 'land', 'building')
#dpsl = dpsl.rename(index=str, columns={"S_UNIT": "SPUT"}) change to sput according to mfd.py

#ASSIGN ACTIVITY FUNCTION TYPE
#----------------------------------------------------------------------------
#reclassify AFT_1 (aft of land parcels)

def landuse_reclassifier(df):
    """
    reclassifies landuse data
    """
    #execute reclassification
    df.loc[df['AFT_1'] == 1, 'AFT_1'] = "residential"
    df.loc[df['AFT_1'] == 2, 'AFT_1'] = "work"
    df.loc[df['AFT_1'] == 4, 'AFT_1'] = "transport"
    df.loc[df['AFT_1'] == 5, 'AFT_1'] = "restricted"
    df.loc[df['AFT_1'] == 6, 'AFT_1'] = "other"
    
    return df

dpsl = landuse_reclassifier(dpsl)  #reclassify and rename col to aft

#collect aft of land parcels to common AFT column
dpsl.loc[(dpsl['AFT'].isnull()), 'AFT'] = dpsl['AFT_1']

#drop landuse AFT column
dpsl = dpsl.drop(columns=['AFT_1'])


#ASSIGN SEASONAL FACTOR M (buildings 0.9, land 0.1)
#----------------------------------------------------------------------------
dpsl['SF'] = np.where((dpsl['SPUT']=='land'), 0.1, 0.9)
dpsl.loc[dpsl['AFT'] == 'restricted', 'SF'] = 0.0
dpsl.loc[dpsl['AFT'] == 'service', 'SF'] = 1.0
dpsl.loc[dpsl['AFT'] == 'transport', 'SF'] = 1.0



#CALCULATE FLOOR AREA
#----------------------------------------------------------------------------
#calculate area of each parcel created by the union
dpsl['AREA_union'] = dpsl['geometry'].area

dpsl['FA_union'] = np.where((dpsl['SPUT']=='building'), 
                   dpsl['AREA_union']/dpsl['AREA']*dpsl['FA'], #if building
                   dpsl['AREA_union']) # if land


#CALCULATE RELATIVE FLOOR AREA 
#----------------------------------------------------------------------------

# SSFA ==> Sum Site Floor Area (i.e. Sum 'FA' ("Floor Area") by 'Site_ID' of mobile phone cells)
# --------
dpsl['SSFA'] = 0.0

# Group data by source zones
grouped = dpsl.groupby('SITEID')

# Iterate over groups and sum the values
for key, values in grouped:
  # Sum the 'Area Floor'
  ssaf = values['FA_union'].sum()

  # Get the indices of the values
  siteid_indices = values.index

  # Assign value to column 'SSFA'
  dpsl.loc[siteid_indices, 'SSFA'] = ssaf

# RFA ==> Relative Floor Area for each subunit within a base station (scale 0.0 - 1.0)
dpsl['RFA'] = 0.0
dpsl['RFA'] = dpsl['FA_union'] / dpsl['SSFA']


#CALCULATE SIMPLE AREAL WEIGHT

#create col for storing area (not fa) of BS voronoi
dpsl['SSA'] = 0.0

# Group data by source zones
grouped = dpsl.groupby('SITEID')

# Iterate over groups and sum the values
for key, values in grouped:
  # Sum the 'Area Floor'
  ssaw = values['AREA_union'].sum()

  # Get the indices of the values
  siteid_indices = values.index

  # Assign value to column 'SSFA'
  dpsl.loc[siteid_indices, 'SSA'] = ssaw

# RFA ==> Relative Floor Area for each subunit within a base station (scale 0.0 - 1.0)
dpsl['AW'] = 0.0
dpsl['AW'] = dpsl['AREA_union'] / dpsl['SSA']


#SORT DF BY SITEID
#----------------------------------------------------------------------------
#sort df by siteid
dpsl=dpsl.sort_values(by=['SITEID'])
#reset index and drop previous index column
dpsl = dpsl.reset_index(drop=True)

#WRITE OUT FILE
#----------------------------------------------------------------------------
out=r'...\data\PhysicalSurfaceData\Disaggregated_physical_surface_250m_raw.shp'
#out=r'...\data\PhysicalSurfaceData\Disaggregated_physical_surface_even_transport_250m_raw.shp'
dpsl.to_file(out)

#copy needed cols to new df
dpsl_cleaned = dpsl.drop(columns=['FA', 'AREA'])
dpsl_cleaned = dpsl_cleaned.rename(index=str, columns={"FA_union": "FA", 
                                                       "AREA_union": "AREA"})
    
out=r'...\data\PhysicalSurfaceData\Disaggregated_physical_surface_250m.shp'
#out=r'...\data\PhysicalSurfaceData\Disaggregated_physical_surface_even_transport_250m.shp'
dpsl_cleaned.to_file(out)
