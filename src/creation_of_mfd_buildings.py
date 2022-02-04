# -*- coding: utf-8 -*-
"""
Created on Thu Aug  2 19:25:18 2018

Applying vertical dimension to AFT-refined NLS buildings - Floor area estimation
-Data with floor areas and floor amounts is extracted from municipalities
    
"""
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

#read in building data
#----------------------------------------------------------------------------
fp_municipal = r'...\data\PhysicalSurfaceData\OriginalData\Buildings\municipal_buildings.shp'
fp_nls =r'... \data\PhysicalSurfaceData\OriginalData\Buildings\nls_buildings_refined_with_osmx_buildings.shp'

bjoin = gpd.read_file(fp_municipal)
bnls = gpd.read_file(fp_nls)


#calculate geometry area for buildings 
#----------------------------------------------------------------------------
bjoin['AREA'] = bjoin['geometry'].area

#clean buildings with geom area below 20 m2 
#----------------------------------------------------------------------------
bjoin = bjoin.loc[bjoin['AREA']>=20]

#clean buildings with join distance of >= 20m
#----------------------------------------------------------------------------
bjoin=bjoin.loc[(bjoin['dist']<20)]

#remove outlier row from data (has 930 floors and is a duplex house)
outliers=bjoin.loc[bjoin['FLCOUNT']>=930]
bjoin=bjoin.loc[bjoin['FLCOUNT']!=930]

#clean columns for joining
#----------------------------------------------------------------------------
bjoin_clean = bjoin[['FLAREA', 'FLCOUNT', 'AREA', 'dist', 'join_UID', 'join_AFT_1', 'geometry']].copy()


#----------------------------------------------------------------------------
# JOIN FA/FCOUNT data to refined nls buildings
#----------------------------------------------------------------------------

# join municipality data to nls data usind uid col
nls_FA = pd.merge(bnls, bjoin_clean, how='left', left_on=['UID'], right_on=['join_UID'])

#save duplicate cases to list
multimatches = nls_FA.loc[nls_FA['UID'].duplicated(), 'UID'].tolist()
multimatches = list(sorted(set(multimatches)))

#drop unnecessary cols
nls_FA = nls_FA.drop(['join_UID', 'status','amenity_os', 'name_osm'],axis=1)
nls_FA['dist'].describe()

#create copy of df for looping
nls_FACpy = nls_FA.copy(deep=True) 

#create a subset for testing loop
nls_FA_1000=nls_FA[0:1000]
#create a copy of subset
nls_FA_1000Cpy = nls_FA_1000.copy(deep=True) 

#Calculate FA to NLS data
'''distance is in input data already <20m'''
def areaMatcher(iterdf,origdf):

    checked=[] #create list for keeping track of checked multimatches
    origdf['FA'] = 0.0 #add new col for new area
    origdf['MM'] =0 #multimatch recognition
    arearule = 0

    for index, row in iterdf.iterrows():

        #in case row is a multimatch
        if (row['UID'] in (multimatches)):
            #check if UID is already checked
            if (row['UID'] not in (checked)): #if not, add to list
                checked.append(row['UID'])
            else:
                origdf.drop(index, inplace=True) #else drop row
                continue
            
            #create df for same UID cases and var for storing FA sum
            sameUIDdf= iterdf.loc[(iterdf['UID']==row['UID'])]
            sameUIDsum=0 
        
            #loop through all same UID cases 
            for jindex, jrow in sameUIDdf.iterrows():        
                if not (np.isnan(jrow['FLAREA'])): #if row has FA, add to sum
                    sameUIDsum+=jrow['FLAREA']
                else: # if row does not have FA, use FC to calc estimated FA
                    sameUIDsum+=jrow['FLCOUNT']*jrow['AREA_x']*FACoefficient(jrow)
            
            #set sum to original dataframe
            origdf.at[index,'MM']= 1
            origdf.at[index,'FA']=sameUIDsum
            #set total geom to original dataframe
            origdf.at[index,'AREA_y'] = sameUIDdf['AREA_y'].sum()
            
        #if row not in multimatches    
        else: 
            if not (np.isnan(row['FLAREA'])):
                origdf.at[index,'FA'] = origdf.at[index,'FLAREA']
            elif not (np.isnan(row['FLCOUNT'])):
                origdf.at[index,'FA'] = origdf.at[index,'FLCOUNT'] * origdf.at[index,'AREA_x']* FACoefficient(row)
            else:
                origdf.at[index,'FA'] = origdf.at[index,'AREA_x'] * FACoefficient(row) * meanFC(row)        
        
        #if nls area is significantly larger than area sum of matching municpal buildings
        if (origdf.at[index,'AREA_y'] >= 0):
            currentFA= origdf.at[index,'FA']
            if (origdf.at[index,'AREA_y'] < (origdf.at[index,'AREA_x'] * 0.8)): #not counted for cases | (row['AREA_y'] > (row['AREA_x'] * 1.2))):
                origdf.at[index,'FA'] =currentFA + ((origdf.at[index,'AREA_x'] - origdf.at[index,'AREA_y']) * FACoefficient(row) * meanFC(row))
                arearule +=1
            else:
                continue


def FACoefficient(row):
    if (row['AFT_nls_os'] == 'residential'):
        return 0.95
    elif (row['AFT_nls_os'] == 'service'):
        return 0.91    
    else:
        return 0.98
    
def meanFC(row):
    if (row['AFT_nls_os'] == 'residential') | (row['AFT_nls_os'] == 'service'):
        return 2
    else:
        return 1


#run function
areaMatcher(nls_FACpy,nls_FA)

# CLEAN DATA
#---------------------------------------------------------------------------
#rename columns 
nls_FA = nls_FA.rename(index=str, columns={"geometry_x": "geometry", 
                                  "AREA_x": "AREA", 
                                  "AFT_nls_os": "AFT"})
#drop unncesessary cols    
nls_FA = nls_FA.drop(['geometry_y', 'join_AFT_1'],axis=1)   



#CLEAN DATA FOR MFD METHOD
#----------------------------------------------------------------------------

#mfd copy
mfd_buildings = nls_FA[['AFT', 'FA', 'AREA', 'geometry']].copy()

#remove restricted type buildings
mfd_buildings = mfd_buildings.loc[(mfd_buildings['AFT']!='restricted')] 
#273 restricted rows were removed, left 153357 buildings for MFD                
    
#write out files
#----------------------------------------------------------------------------

#mfd-cleaned version
out=r'...\data\PhysicalSurfaceData\OriginalData\Buildings\mfd_buildings.shp'
mfd_buildings.to_file(out)




'''

#----------------------------------
#*****Supplementary part*****
#----------------------------------


#AREA RATIO CALCULATION FOR EACH AFT
#----------------------------------------------------------------------------

#create subsets for all AFTs
#----------------------------------------------------------------------------
bjoin_residential = bjoin.loc[(bjoin['join_AFT_1']=='residential')]
bjoin_allbutresidential = bjoin.loc[(bjoin['join_AFT_1']!='residential')]
bjoin_other = bjoin.loc[(bjoin['join_AFT_1']=='other')]
bjoin_work = bjoin.loc[(bjoin['join_AFT_1']=='work')]
bjoin_service = bjoin.loc[(bjoin['join_AFT_1']=='service')]
bjoin_transport = bjoin.loc[(bjoin['join_AFT_1']=='transport')]

bjoin_allbutresidential_service = bjoin_allbutresidential.loc[(bjoin_allbutresidential['join_AFT_1']!='service')]


#calculate area ratio
#----------------------------------------------------------------------------
#calculates area ratio of df and returns median    
def areaRatioCalculator(df):
    df['AREA_RATIO']=df['FLAREA']/(df['AREA']*df['FLCOUNT'])  
    return df['AREA_RATIO'].median()

#create list of dfs for area calculation
#----------------------------------------------------------------------------
dflist = [bjoin, bjoin_residential, bjoin_allbutresidential, bjoin_work, bjoin_service, bjoin_other]
dflist = [bjoin_allbutresidential_service, bjoin_transport]


for i in dflist:
    areaRatioCalculator(i)
    print('Calculating Area Ratio of %s' % (i))

#----------------------------------------------------------------------------
#COMPARE AFT TYPES (measure used is median if not told otherwise)
#-----------------------------------------------------------------------------

#see area ratio value distribution
#------------------------------------------------------------
bjoin['AREA_RATIO'].count() 

bjoin['AREA_RATIO'].describe()
bjoin_residential['AREA_RATIO'].describe()
bjoin_allbutresidential['AREA_RATIO'].describe()

bjoin_allbutresidential_service['AREA_RATIO'].describe() 

bjoin_other['AREA_RATIO'].describe()
bjoin_work['AREA_RATIO'].describe()
bjoin_service['AREA_RATIO'].describe()


#histograms with log scale
plt.hist(bjoin_residential['AREA_RATIO'].dropna(), log=True)
plt.hist(bjoin_allbutresidential_service['AREA_RATIO'].dropna(), log=True)
plt.hist(bjoin_service['AREA_RATIO'].dropna(), log=True)
plt.hist(bjoin['AREA_RATIO'].dropna(), log=True)

bjoin['AREA_RATIO'].max() 

bjoin.loc[(bjoin['AREA_RATIO'])>100]

#compare FLOOR_COUNT for AFT types
#------------------------------------------------------------
bjoin['FLCOUNT'].describe()
bjoin_residential['FLCOUNT'].describe() 
bjoin_allbutresidential['FLCOUNT'].describe() 
bjoin_allbutresidential_service['FLCOUNT'].describe()


bjoin_other['FLCOUNT'].describe() 
bjoin_work['FLCOUNT'].describe() 
bjoin_service['FLCOUNT'].describe()


#compare FLOOR_AREA for AFT types
#------------------------------------------------------------
bjoin['FLAREA'].describe() 
bjoin_residential['FLAREA'].describe() 
bjoin_allbutresidential['FLAREA'].describe() 

bjoin_other['FLAREA'].describe() 
bjoin_work['FLAREA'].describe() 
bjoin_service['FLAREA'].describe() 


#compare GEOM_AREA for AFT types
#------------------------------------------------------------
bjoin['AREA'].describe() 
bjoin_residential['AREA'].describe() 
bjoin_allbutresidential['AREA'].describe()

'''
