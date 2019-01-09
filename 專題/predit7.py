



import json
import math
import fiona
import folium
import branca.colormap as cm
import requests
import numpy as np
import pandas as pd
import geopandas as gp
from shapely.geometry import Polygon 
#======================================================================================================
#idw functuion


def idw(lat , lon , ref_point , ref_number):     
    total_out = 0
    total_dis = 0
    # optional normalize
    size = 0.01
    sort_list = []
    # sort distance
    for index,row in ref_point.iterrows():           # 使用.iterrows() 一列一列讀取資料
        ref_lon = row['Longitude']
        ref_lat = row['Latitude']
        distance = math.sqrt(((ref_lon - lon)/size) ** 2 + ((ref_lat - lat)/size) ** 2)
        sort_list.append([ref_lon,ref_lat,row['PM25_pred'],distance])
    sort_list = sorted(sort_list,key=lambda l:l[3], reverse=False) # 根據距離近到遠排序
    count = 0
    # top ref_number point 找出距離最近的幾個測站，把1/distance累加
    for s in sort_list: # sort_list : [ref_lon,ref_lat,row['PM2.5'],distance] s[2] : pm2.5 , s[3]:distance
        if count == ref_number:
            break
        count += 1
        total_dis += 1 / s[3] #s[3] = distance 1/總距離 (1/distance 1 + 1/distance 2 + ..... 1/distance n)
    count = 0
    # idw : 
    # total out : idw預估的pm2.5 -> sigma(前n個測站的pm2.5 * ((1/distance) / 總距離))
    # 這個測站的pm2.5 * 這個測站多重要（權重）
    # 權重：(1/測站離預估點的距離) / (1/總距離) （總距離：前n個測站的距離倒數的和）
    for s in sort_list:
        if count == ref_number:
            break
        count += 1
        total_out += ((1 / s[3]) / total_dis) * s[2] #權重 * pm2.5
    return total_out # 預估的pm2.5
#========================================================================================================
#爬蟲 (環保署測站預測) + idw
data = requests.get(url='https://aqi.thu.edu.tw/echarts/getjf') 
js = json.loads(data.text)
df = pd.DataFrame(js)
predict1 = df.iloc[0:16]
predict1['Longitude']=[120.498566,120.715064,120.741711,120.616917,
                       120.646629,120.576421,120.568794,120.538839,
                       120.607070,120.597876,120.641092,120.715064,
                       120.615358,120.540877,120.615358,120.714881] 

predict1['Latitude']=[24.201030,24.139564,24.256586,24.162200,
                      24.094264,24.269233,24.225628,24.250388,
                      24.182055,24.139008,24.151958,24.139564,
                      24.350426,24.150919,24.350426,24.307036] 


predict1['PM25_pred'] = predict1.PM25_pred.astype(float)
predict1['PM25_pred'] = predict1['PM25_pred'].round()
predict1 = predict1.reset_index()
#predict1 未來一小時預測値
keep=predict1['Time']
Times=str(keep[0:1])
Times=Times[5:9]+'年 '+Times[10:12]+'月 '+Times[13:15]+'日 '+Times[16:18]+'時'
#Times 時間
#taichung = gp.read_file("C:\\final_project\\z.geojson")           #台中邊界
taichungmap_1x1 = gp.read_file("/home/hpc/7taichung1x1.geojson")         #台中1*1網格

lon_max=taichungmap_1x1.bounds.maxx
lon_min=taichungmap_1x1.bounds.minx    
lat_max=taichungmap_1x1.bounds.maxy
lat_min=taichungmap_1x1.bounds.miny
predict1_idw = pd.DataFrame(columns=['Latitude', 'Longitude', 'PM2.5' , 'Id'])
Id = 0
ref_point_number = 16      # edit here to change ref_number
for i,j,k,l in zip(lat_max,lat_min,lon_max,lon_min):
    Id += 1
    df_append = pd.DataFrame([[(i+j)/2 , (k+l)/2 , idw((i+j)/2 , (k+l)/2 , predict1 , ref_point_number) , Id]],columns=['Latitude', 'Longitude', 'PM2.5' , 'Id'])
    predict1_idw = predict1_idw.append(df_append)        #合併
predict1_idw['Id'] = predict1_idw.Id.astype(int)
#predict1_idw 預測値跑 idw 結果
taichungmap_1x1 = taichungmap_1x1.merge(predict1_idw, on='Id')
taichungmap_1x1['PM2.5']=taichungmap_1x1['PM2.5'].round()
#=============================================================================================================
#folium

fmap=folium.Map(location=[24.2,120.9], zoom_start=10.5) 
fmap.choropleth(
                geo_data=taichungmap_1x1, 
                name='pm2.5',             
                columns=['Id', 'PM2.5'],  
                key_on='feature.properties.Id',                        
                data=predict1_idw,
               #threshold_scale=[],
                fill_color='BuGn',
                legend_name='pm2.5',                             
                line_opacity=0.5,
                fill_opacity=0.8
                )

folium.GeoJson(
               taichungmap_1x1,
               name='touch',
               style_function=lambda x: {"weight":0.5, 'color':'#00000000'},
               highlight_function=lambda x: {'weight':3, 'color':'black'},  
               tooltip=folium.GeoJsonTooltip(fields=['Id','PM2.5'],aliases=['Id','PM2.5'],labels=True,sticky=True)
              ).add_to(fmap)

#環保署 logo
epa_icon_url = 'https://www.epa.gov.tw/public/MMO/epa/Epa_Logo_01_LOGO.gif' 

station=folium.FeatureGroup(name="環保署",show = False)
for i in(range(16)):
    station.add_child(
                        folium.Marker(
                                        location=[predict1['Latitude'][i],predict1['Longitude'][i]],
                                        popup=("<b>NAME:</b> {NAME}<br>""<b>PM2.5:</b> {PM25}<br>""<b>TIME:</b> {TIME}<br>")
                                                .format(NAME=str(predict1['sitename'][i]),PM25=str(predict1['PM25_pred'][i]),TIME=str(Times)),
                                        icon=folium.CustomIcon(epa_icon_url,icon_size=(23,23))  # Creating a custom Icon
                                      )
                      )


fmap.add_child(station)    
folium.LayerControl().add_to(fmap)
fmap.save('/var/www/html/predict7')#存成 final.html

