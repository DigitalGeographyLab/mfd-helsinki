# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 14:18:58 2018
"""
import geopandas as gpd
import pandas as pd
from scipy.stats import linregress
from functools import reduce
import matplotlib.pyplot as plt
from math import sqrt
import numpy as np
from numpy.polynomial.polynomial import polyfit

#---------------------------------------------
'''SET FILEPATHS AND READ IN DATA '''
#---------------------------------------------

#validation data
fp_val= r'...\ykr_rttk_spatjoin.shp'
#hourly mobile phone data
fp_hspa2= r'...\ZROP_results_hspa_H2.shp'
fp_hspa3= r'...\ZROP_results_hspa_H3.shp'
fp_hspa4= r'...\ZROP_results_hspa_H4.shp'
fp_hspa15= r'...\ZROP_results_hspa_H15.shp'

val =  gpd.read_file(fp_val) #val = validation df

hspa2 =  gpd.read_file(fp_hspa2)
hspa3 =  gpd.read_file(fp_hspa3)
hspa4 =  gpd.read_file(fp_hspa4)
hspa15 =  gpd.read_file(fp_hspa15)

#--------------------------------------------------------------------
'''CREATE NIGHT-TIME DF'''
#--------------------------------------------------------------------
#join data
night_hspa = hspa2.merge(hspa3,on='YKR_ID').merge(hspa4,on='YKR_ID')

#calc mean for each df
night_hspa['MEAN_hspa'] = night_hspa[['ZROP H2', 'ZROP H3', 'ZROP H4']].mean(axis=1)

#merge dfs
night_dfs = [night_hspa]
night_mpd= reduce(lambda left,right: pd.merge(left,right,on='YKR_ID'), night_dfs)

#clean data and save to new df
night_mpd_clean = night_mpd[['MEAN_hspa', 'YKR_ID', 'geometry']].copy()

#save hevaki_y and ykrid to own df
val_clean = val[['YKR_ID', 'he_vakiy']].copy()

#execute join to validation data
night_mpd_val = night_mpd_clean.merge(val_clean,left_on='YKR_ID', right_on='YKR_ID', how='outer')

#normalize population data (scale of 0-1)
night_mpd_val['pop_norm'] = night_mpd_val['he_vakiy'] /night_mpd_val['he_vakiy'].sum()

#compare po register to mpd
night_mpd_val['diff_hspa'] = night_mpd_val['pop_norm'] - night_mpd_val['MEAN_hspa'] 

night_mpd_val = night_mpd_val.fillna(0)


#----------------------------------
'''VALIDATION'''
#----------------------------------


#CALC CORRELATION COEFFICIENT & STANDARD ERROR
#----------------------------------------------------------------
night_mpd_val[['pop_norm','MEAN_hspa']].corr(method='pearson')
linregress(night_mpd_val['pop_norm'], night_mpd_val['MEAN_hspa'])

#CALC RMSE
#-----------------------------------
#rmse:
rmse = sqrt(((night_mpd_val['pop_norm'] - night_mpd_val['MEAN_hspa'])**2).sum()/13231)

#CALC MAE
#-----------------------------------
mae = (abs(night_mpd_val['pop_norm'] - night_mpd_val['MEAN_hspa'])).sum()/13231

#CALC CV based on rmse 
#-----------------------------------
# the ratio of the standard deviation to the mean 
pop = night_mpd_val['pop_norm'].sum()
rmse/pop

#---------------
'''PLOTTING'''
#---------------

#specify variables
y=night_mpd_val['pop_norm']
x1=night_mpd_val['MEAN_hspa']

#HSPA-VAL
#--------------------
#specify plot size
plt.figure(1, figsize=(9, 9))
#run plotting
plt.scatter(x1,y, s=40, alpha=0.45, label="r = 0.683***")
#Edit axis ticks
ax = plt.gca()
ax.tick_params(axis = 'both', which = 'major', labelsize = 22)
ax.tick_params(axis = 'both', which = 'minor', labelsize = 22)
ax.tick_params(axis='x', pad=5)
ax.tick_params(axis='y', pad=5)
#Edit Axis labels
label_properties = {'size':'26', 'weight':'bold'}
plt.ylabel('Residential Population', fontdict=label_properties, labelpad=35)
plt.xlabel('HSPA Calls (2 AM - 5 AM)', fontdict=label_properties, labelpad=30)
#Set r line
b, m = polyfit(x1, y, 1)
plt.plot(np.unique(x1), np.poly1d(np.polyfit(x1, y, 1))(np.unique(x1)),c='k', alpha=0.6)
#Adjust axis value range
plt.ylim(ymin=-0.00004,ymax=(y.max()+0.0005))
plt.xlim(xmin=-0.0001,xmax=(x1.max()+0.001))
#Edit Legend
legend_properties = {'size':'26'}
plt.legend(markerscale=0, frameon=False, prop=legend_properties, loc='lower right')
plt.show()