# -*- coding: utf-8 -*-
"""
Created on Tue Jul  3 16:58:45 2018
Author: Bergroth, Claudia


Aim of this script:
===================
Retrieval of OpenStreetMap (OSM) data for the MFD interpolation. 

Using building data from OpenStreetMap, the building classification was expanded to cover also retail and service and transport activity function types, 
which could not be extracted from the original building dataset.


Structure:
===================
This code is divided into 4 main parts: 
1) Retrieving building polygon data from OSM
2) Classifying buildings based on their estimated primary Activity Function Type (AFT)
3) Cropping data to study area extent
4) Writing out cropped building data as shapefile

Input: Study area extent (.shp-file)
Output: Reclassified building dataset (.shp-file)

"""
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, Polygon

#------------------------------------------------------------
'''SET FILEPATHS'''
#------------------------------------------------------------

#input paths
fp_tz_wgs= r'...\targetzonesdissolve_wgs.shp'
fp_tz_3067= r'...\targetzonesdissolve_3067.shp'

#output paths
out_buildings = r'...\osmnx_buildings_reclassified.shp'


#------------------------------------------------------------
'''1. RETRIEVING BUILDING POLYGONS FROM OSM '''
#------------------------------------------------------------

#read in data
study_area = gpd.read_file(fp_tz_wgs)
study_area_3067 = gpd.read_file(fp_tz_3067)

#extract the geometry of the study area polygon to a variable
polygon = study_area['geometry'].iloc[0]

#retrieve buildings from OSM within study area polygon
buildings = ox.buildings_from_polygon(polygon)
buildings['building'].value_counts()


#------------------------------------------------------------
'''2. CLASSIFYING BUILDINGS '''
#------------------------------------------------------------

#create lists for building classification (values based on value counts)
buildings_residential = ['residential', 'apartments', 'cabin', 'duplex','triplex', 
                         'house', 'detached', 'semidetached_house', 'semi', 'prison', 
                         'bungalow',  'hotel', 'hostel', 'dormitory', 'farm', 'garage',
                         'manor', 'mansion', 'villa', 'estate', 'terrace', 'terraced']

buildings_work = ['industrial', 'warehouse', 'school', 'office', 'public', 'civic',
                  'public_building', 'childcare', 'education','townhouse', 
                  'university', 'construction', 'utility', 'roundhouse', 'commercial', 'Commercial',
                  'hospital', 'kindergarten', 'logistics', 'storage', 'PK-yritykset', 
                  'hangar', 'gatehouse', 'greenhouse','glasshouse', 'farm_auxiliary', 
                  'cowshed', 'barn', 'stable', 'silo', 'stables', 'guard_booth', 'guard', 'manufacture']

buildings_service = ['retail', 'shop', 'mall', 'service', 'carwash', 'store', 
                     'supermarket', 'kiosk']

buildings_other = ['library', 'stadium', 'cafe', 'Cafe', 'sports_centre', 'swimming hall',
                   'sauna', 'museum', 'sport', 'horse arena', 'event_space', 'pavilion', 'hall',
                   'cathedral', 'church', 'chapel', 'social_facility', 'hut', 'shed', 'workshop', 
                   'play_hut','playhut', 'manege', 'outhouse', 'bird_hide']

buildings_transport =['parking', 'train_station', 'station', 'transportation', 'underground_entrance'] 

buildings_irrelevant = ['yes', 'bunker', 'ruins', 'block','garages', 'garage_shed','bike_shed', 'carport',
                        'tent', 'container', 'disused kiosk', 'atrium', 'basement',
                        'canopy', 'roof', 'antenna', 'hidden', 'wall', 'cage',
                        'transformer_tower', 'transformer',  'bridge', 'ship', 'barge', 
                        'storage_tank', 'tank', 'tanks',  'garbage_shed', 'waste_disposal',
                        'extension','foundations', 'hovel', 'shelter_entrance',
                        'tunnelexit', 'tunnel_entry', 'underpass_entrance', 
                        'entrance', 'tunnel_entrance?', 'passage', 'chimney', 
                        'collapsed', 'tower', 'undefined', 'abandoned', 'burned',
                        'interdimensional portal cabinet out of plywood']
						

#create new df and use lists to reclassify the rows
reclassified_buildings = buildings

#create new column that will later be used to store the new class (activity types)
reclassified_buildings['activity_type']= ""

#assign new column values based on list -column matches
reclassified_buildings.loc[reclassified_buildings['building'].isin(buildings_transport), 'activity_type'] = 'transport'
reclassified_buildings.loc[reclassified_buildings['building'].isin(buildings_residential), 'activity_type'] = 'residential'
reclassified_buildings.loc[reclassified_buildings['building'].isin(buildings_service), 'activity_type'] = 'service'
reclassified_buildings.loc[reclassified_buildings['building'].isin(buildings_work), 'activity_type'] = 'work'
reclassified_buildings.loc[reclassified_buildings['building'].isin(buildings_other), 'activity_type'] = 'other'

#calculate value counts for new classification
reclassified_buildings['activity_type'].value_counts()

#remove rows that were not classified
reclassified_buildings = reclassified_buildings[reclassified_buildings.activity_type != ""]   

#copy geometry column and old and new classification columns to new df
reclassified_buildings_cleaned = reclassified_buildings[['activity_type', 'name','amenity', 'geometry', 'building']].copy()

#------------------------------------------------------------
'''3. CROPPING DATA TO STUDY AREA EXTENT '''
#------------------------------------------------------------

#save classified buildings to shp
df_buildings = gpd.GeoDataFrame(reclassified_buildings_cleaned, geometry='geometry')

#set native crs
df_buildings.crs={'init':'epsg:4326'}

#reproject study area and building layer to 3067
df_buildings_3067=df_buildings.to_crs({'init': 'epsg:3067'})
study_area_3067 = study_area_3067.to_crs({'init': 'epsg:3067'})

#crop to study area extent
df_buildings_clip = gpd.sjoin(df_buildings_3067, study_area_3067, how = "inner")

#check value counts for clipped data
df_buildings_clip['activity_type'].value_counts()

#drop unnecessary columns
df_buildings_clip = df_buildings_clip.drop(['x','y','YKR_ID','index_right'],axis=1)

#------------------------------------------------------------
'''4. WRITE OUT DATA '''
#------------------------------------------------------------

#write out buildings
#-------------------------------------------------------------------------------
df_buildings_clip.to_file(out_buildings) 