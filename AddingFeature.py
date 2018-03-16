#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author : Coco

# -*- coding:utf-8 -*-

import os
import gc
import time
import datetime
import pickle
import Geohash
import numpy as np
import pandas as pd


cache_path = '../cache/'
train_path = '../train/train_0521.csv'
test_path = '../test/train_after_0521.csv'
flag = True



# 计算两点之间距离
def cal_distance(lat1,lon1,lat2,lon2):
    dx = np.abs(float(lon1) - float(lon2))  # 经度差
    dy = np.abs(float(lat1) - float(lat2))  # 维度差
    b = (float(lat1) + float(lat2)) / 2.0
    Lx = 6371004.0 * (dx / 57.2958) * np.cos(b / 57.2958)
    Ly = 6371004.0 * (dy / 57.2958)
    L = (Lx**2 + Ly**2) ** 0.5
    return L






####################构造负样本##################








# 获取用户从这个路径走过几次
def get_user_sloc_eloc_count(train,result):
    user_count = train.groupby(['userid','geohashed_start_loc','geohashed_end_loc'],as_index=False)['userid'].agg({'user_sloc_eloc_count':'count'})
    result = pd.merge(result,user_count,on=['userid','geohashed_start_loc','geohashed_end_loc'],how='left')
    return result



# 计算两点之间的欧氏距离
def get_distance(result):
    locs = list(set(result['geohashed_start_loc']) | set(result['geohashed_end_loc']))
    if np.nan in locs:
        locs.remove(np.nan)
    deloc = []
    for loc in locs:
        deloc.append(Geohash.decode(loc))
    loc_dict = dict(zip(locs,deloc))
    geohashed_loc = result[['geohashed_start_loc','geohashed_end_loc']].values
    distance = []
    for i in geohashed_loc:
        if i[0] is not np.nan and i[1] is not np.nan:
            lat1, lon1 = loc_dict[i[0]]
            lat2, lon2 = loc_dict[i[1]]
            distance.append(cal_distance(float(lat1),float(lon1),float(lat2),float(lon2)))
        else:
            distance.append(np.nan)
    result.loc[:,'distance'] = distance
    #result.to_csv('distance',index=False,header=True)
    return result


# 获取每个用户的平均行驶距离
def get_user_average_distance(train,result):
    user_average_distance = train.groupby(['userid'],as_index=False)['distance'].agg({'user_average_distance':'mean'})
    result = pd.merge(result,user_average_distance,on=['userid'],how = 'left')
    #result.to_csv('user_average_distance',index=False,header=True)
    return result

# 获取每个用户的出行星期数和小时数
def get_weekday_hour(result):
    data = result['starttime'].values
    week = []
    hour = []
    for i in data:
        time1 = i
        time2 = datetime.datetime.strptime(time1, '%Y-%m-%d %H:%M:%S')
        weekday = time2.weekday()
        hour_time = time2.hour
        week.append(weekday)
        hour.append(hour_time)

    result.loc[:,'weekday'] = week
    result.loc[:,'hour'] = hour

    return result

# 获取从该候选地点出发的用户数
def get_unique_user_eloc_as_sloc_count(train,result):
    user_sloc_count = train.groupby(['geohashed_start_loc'],as_index=False)['userid'].agg({'user_sloc_count':'nunique'})
    user_sloc_count.rename(columns={'geohashed_start_loc':'geohashed_end_loc'},inplace=True)
    result = pd.merge(result, user_sloc_count, on=['geohashed_end_loc'], how='left')
    return result

# 获取去过该地点的用户数
def get_unique_user_eloc_count(train,result):
    eloc_count = train.groupby('geohashed_end_loc', as_index=False)['userid'].agg({'eloc_count': 'nunique'})
    result = pd.merge(result, eloc_count, on='geohashed_end_loc', how='left')
    return result

# 获取该单车去过该地的次数
def get_bike_eloc_count(train, result):
    user_eloc_count = train.groupby(['bikeid','geohashed_end_loc'],as_index=False)['bikeid'].agg({'bike_eloc_count':'count'})
    result = pd.merge(result,user_eloc_count,on=['bikeid','geohashed_end_loc'],how='left')
    return result

# 获取用户历史行为次数
def get_user_count(train,result):
    user_count = train.groupby('userid',as_index=False)['geohashed_end_loc'].agg({'user_count':'count'})
    result = pd.merge(result,user_count,on=['userid'],how='left')
    return result

# 获取用户去过这个地点几次
def get_user_eloc_count(train, result):
    user_eloc_count = train.groupby(['userid','geohashed_end_loc'],as_index=False)['userid'].agg({'user_eloc_count':'count'})
    result = pd.merge(result,user_eloc_count,on=['userid','geohashed_end_loc'],how='left')
    return result

# 计算两点之间Manhattan距离
def haversine(lat1, lng1, lat2, lng2):
    """function to calculate haversine distance between two co-ordinates"""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    AVG_EARTH_RADIUS = 6371  # in km
    lat = lat2 - lat1
    lng = lng2 - lng1
    d = np.sin(lat * 0.5) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(lng * 0.5) ** 2
    h = 2 * AVG_EARTH_RADIUS * np.arcsin(np.sqrt(d))
    return(h)

def manhattan(lat1, lng1, lat2, lng2):
    """function to calculate manhatten distance between pick_drop"""
    a = haversine(lat1, lng1, lat1, lng2)
    b = haversine(lat1, lng1, lat2, lng1)
    return a + b

# 获取候选地与用户最常去的地点之间的距离
def dist_user_most_eloc_eloc(train,result):
    user_most_eloc = train.groupby(['userid','geohashed_end_loc'],as_index=False)['geohashed_end_loc'].agg({'user_eloc_count':'count'})
    user_most_eloc.sort_values('user_eloc_count',inplace=True)
    user_most_eloc = user_most_eloc.groupby('userid').tail(1)
    user_most_eloc.rename(columns={'geohashed_end_loc':'user_most_eloc'},inplace=True)
    dist_user_most_eloc = pd.merge(result[['orderid','userid','geohashed_end_loc']],user_most_eloc[['userid','user_most_eloc']],on='userid',how = 'left')
    #dist_user_most_eloc.to_csv('user_most_eloc.csv',index=False,header=True)
    dist_user_most_eloc.rename(columns={'user_most_eloc':'geohashed_start_loc'},inplace=True)
    get_distance(dist_user_most_eloc)
    dist_user_most_eloc.rename(columns={'distance':'dist_user_most_eloc_eloc'},inplace=True)
    result = pd.merge(result,dist_user_most_eloc[['orderid','dist_user_most_eloc_eloc']],on='orderid',how='left')
    return result


# 训练提交

if __name__ == "__main__":
    t0 = time.time()
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)

    #result = get_bike_eloc_count(train,test)
    #train = get_distance(train)
    #result = get_user_average_distance(train,test)
    #result = get_user_average_distance(result)
    #result = get_weekday_hour(result)
    #result = get_user_count(train,result)
    #result = get_user_eloc_count(train,result)
    #result.fillna(0, inplace=True)

    #result['user_eloc_rate'] = (result['user_eloc_count'] +  result['bike_eloc_count']) / result['user_count']         # 获取用户去该地占用户出行次数的比率
    result = dist_user_most_eloc_eloc(train,test)
    result.to_csv('result.csv',index=False,header=True)


    print('一共用时{}秒'.format(time.time()-t0))


'''

import numpy as np
import pandas as pd
df = pd.DataFrame({'date': ['2013-04-01','2013-04-01','2013-04-01','2013-04-02', '2013-04-02'],
    'user_id': ['0001', '0001', '0002', '0002', '0002'],
    'duration': [30, 15, 20, 15, 0],
    'time': [100,200,300,400,0]})

#result = df.groupby(['date'])['user_id'].agg({'unique':'nunique'})
df['user_eloc_rate'] = df['duration'] / df['time']
print(df)

'''
