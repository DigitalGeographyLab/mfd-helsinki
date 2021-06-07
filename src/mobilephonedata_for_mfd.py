# -*- coding: utf-8 -*-
"""
Created on Fri Aug 24 11:30:41 2018
Author: Bergroth, Claudia

Aim of this script:
===================
Clean and process mobile phone data for MFD interpolation

Structure:
===================
This code is divided into the following main parts:
 
1) reading in data 
2) data cleaning
3) creating temporal subsets
4) aggregating data and creating data for cropping
5) cropping data to study area extent
6) aggregating cropped data 
7) writing out processed mobile phone data

Input: unprocessed mobile phone data (.csv-file)
Output: cleaned mobile phone dataset (.csv-file)

"""

import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from fiona.crs import from_epsg

#---------------------------------------------------------------------------
# SET FILEPATHS
#---------------------------------------------------------------------------

#input data - unprocessed mobile phone data
#--------------------------------
fp = r'...\MobilePhoneData.csv'

#optional steps for cropping data
#--------------------------------
#output data (optional) - non-cropped data to create voronoi polygons of the base stations
out_hspa=r'...\hourlymedian_HSPA.csv'
#input data (optional) - shapefile that contains the base stations, whose voronoi polygons intersect MFD target zones
fp_tzbs = r'...\bs_whose_voronoi_intersect_tz.shp'

#output data - processed mobile phone data 
#--------------------------------
out_hspa_tz = r'...\hourlymedian_HSPA_tz.csv'


#---------------------------------------------------------------------------
# 1. READ IN DATA
#---------------------------------------------------------------------------

#read in mobile phone data (mpd) as csv
#---------------------------------------------------------------------------
mpd = pd.read_csv(fp, sep=',') 

#convert df to GeoDataFrame
#---------------------------------------------------------------------------
geometry = [Point(xy) for xy in zip(mpd.X, mpd.Y)]
crs = {'init': 'epsg:3067'} #http://www.spatialreference.org/ref/epsg/3067/
mpd_geo = gpd.GeoDataFrame(mpd, crs=crs, geometry=geometry)

#Sort values by date
#---------------------------------------------------------------------------
#convert DATE_TIME (str) to datetime
mpd_geo['DATE_TIME'] = pd.to_datetime(mpd_geo['DATE_TIME'].astype(str), format='%Y-%m-%d %H:%M:%S')
#sort values ascending based on date
mpd_geo = mpd_geo.sort_values(by='DATE_TIME') 
#Drop and reset old index
mpd_geo = mpd_geo.reset_index(drop=True)


#---------------------------------------------------------------------------
# (2. DATA CLEANING IF NOT DONE ALREADY)
#---------------------------------------------------------------------------
# this step depends on data used. 


#------------------------------------------------------------------------
# 3. CREATE TEMPORAL SUBSETS 
#------------------------------------------------------------------------

#create new df based on weekday (mon_thu refers to Monday to Thursday)
#similar logic was used to create df for Saturday and Sunday
mon_thu=mpd_geo.loc[mpd_geo['WEEKDAY']<4] #0=MON...6=SUN 0,1,2,3,4,5,6

#------------------------------------------------------------------------
#4. AGGREGATE VALUES PER BS AND HOUR
#---------------------------------------------

aggregations = {"HSPA_CALLS":'median'}
#execute aggregation - yields median value for each hour for each siteid
hourlymedian_BSgroup=mon_thu.groupby(['SITEID','HOUR']).agg(aggregations).reset_index()

#change axis (transpose to BS * 24 hour per network indicator)
hourlymedian_HSPA=hourlymedian_BSgroup.pivot(index='SITEID',columns='HOUR',values='HSPA_CALLS').reset_index()

#4B. JOIN GEOMETRY TO AGGREGATED HOURLY DF
#--------------------------------------------------------------

#Create df with X,Y and geom for each unique BS in data
bscoords= mon_thu[['SITEID','X','Y','geometry']].copy().drop_duplicates('SITEID')

#Create funtion for joining geometry to hourly df
def joinCoordsToHourlyBsData(data):
    return data.set_index('SITEID').join(bscoords.set_index('SITEID')).reset_index()

#Call joinCoordsToHourlyBsData function:
hourlymedian_HSPA=joinCoordsToHourlyBsData(hourlymedian_HSPA)


#4C.  WRITE OUT FILE FOR CREATING VORONOI POLYGONS (used for cropping the data)
#--------------------------------------------------------------

#write out file for creating voronoi polygons
hourlymedian_HSPA.fillna(value=0).to_csv(out_hspa, sep=',', float_format="%.2f")


#------------------------------------------------------------------------
#5. CROP DATA TO STUDY AREA EXTENT
#------------------------------------------------------------------------
#The dataset created in previous step was used to calculate voronoi polygons in QGIS, followed by a spatial overlay analysis.
#Those base stations (bs), whose voroinoi polygons intersect with the MFD target zones (tz) were stored in the following file.

#read in shapefile that contains the base stations that intersect MFD target zones
tzbs = gpd.read_file(fp_tzbs)

#write site id col contents to a list
tz_siteid = tzbs['SITEID'].tolist()

#save only those rows to new df that have matching siteid with list
mon_thu_tz = mon_thu.loc[mon_thu['SITEID'].isin(tz_siteid)]


#------------------------------------------------------------------------
#6. AGGREGATE VALUES PER BS AND HOUR
#---------------------------------------------

aggregations = {"HSPA_CALLS":'median'}

#execute aggregation - yields median value for each hour for each siteid
hourlymedian_BSgroup=mon_thu_tz.groupby(['SITEID','HOUR']).agg(aggregations).reset_index()

#change axis (transpose to BS * 24 hour per network indicator)
hourlymedian_HSPA_tz=hourlymedian_BSgroup.pivot(index='SITEID',columns='HOUR',values='HSPA_CALLS').reset_index()


#6B. JOIN GEOMETRY TO AGGREGATED HOURLY DF
#--------------------------------------------------------------

#Create df with X,Y and geom for each unique BS in data
bscoords_tz= mon_thu_tz[['SITEID','X','Y','geometry']].copy().drop_duplicates('SITEID')

#Create funtion for joining geometry to hourly df
def joinCoordsToHourlyBsData(data):
    return data.set_index('SITEID').join(bscoords_tz.set_index('SITEID')).reset_index()

#Call function:
hourlymedian_HSPA_tz=joinCoordsToHourlyBsData(hourlymedian_HSPA_tz)

#------------------------------------------------------------------------
#7. WRITE OUT PROCESSED MOBILE PHONE DATA FOR MFD INTERPOLATION
#------------------------------------------------------------------------

#write out file
hourlymedian_HSPA_tz.fillna(value=0).to_csv(out_hspa_tz, sep=',', float_format="%.2f")