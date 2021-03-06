#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author : Coco

#thie file has added average distance,weekday,hour attributes

#


import os
import sys
import gc
import time
import pickle
import Geohash
import numpy as np
import datetime
import pandas as pd
from xgboost import plot_importance
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot

cache_path = '../cache/'
train_path = '../train/train_0521.csv'
train_feat_path = '../train/train_feat.csv'
test_path = '../test/test_0521.csv'
test_feat_path = '../test/test_feat.csv'
flag = True

########################################################################
#                                                                      #
#                               用户特征                               #
#                                                                      #
########################################################################

# 获取用户历史行为次数
def get_user_count(train,result):
    user_count = train.groupby('userid',as_index=False)['geohashed_end_loc'].agg({'user_count':'count'})
    result = pd.merge(result,user_count,on=['userid'],how='left')
    return result

# 获取用户去过某个地点历史行为次数
def get_user_eloc_count(train, result):
    user_eloc_count = train.groupby(['userid','geohashed_end_loc'],as_index=False)['userid'].agg({'user_eloc_count':'count'})
    result = pd.merge(result,user_eloc_count,on=['userid','geohashed_end_loc'],how='left')
    return result

# 获取用户从某个地点出发的行为次数
def get_user_sloc_count(train,result):
    user_sloc_count = train.groupby(['userid','geohashed_start_loc'],as_index=False)['userid'].agg({'user_sloc_count':'count'})
    user_sloc_count.rename(columns={'geohashed_start_loc':'geohashed_end_loc'},inplace=True)
    result = pd.merge(result, user_sloc_count, on=['userid', 'geohashed_end_loc'], how='left')
    return result

# 获取用户从这个路径走过几次
def get_user_sloc_eloc_count(train,result):
    user_count = train.groupby(['userid','geohashed_start_loc','geohashed_end_loc'],as_index=False)['userid'].agg({'user_sloc_eloc_count':'count'})
    result = pd.merge(result,user_count,on=['userid','geohashed_start_loc','geohashed_end_loc'],how='left')
    return result

# 获取用户从这个路径折返过几次
def get_user_eloc_sloc_count(train,result):
    user_eloc_sloc_count = train.groupby(['userid','geohashed_start_loc','geohashed_end_loc'],as_index=False)['userid'].agg({'user_eloc_sloc_count':'count'})
    user_eloc_sloc_count.rename(columns = {'geohashed_start_loc':'geohashed_end_loc','geohashed_end_loc':'geohashed_start_loc'},inplace=True)
    result = pd.merge(result,user_eloc_sloc_count,on=['userid','geohashed_start_loc','geohashed_end_loc'],how='left')
    return result

# 获取候选地与用户最常去的地点之间的距离
def dist_user_most_eloc_eloc(train,result):
    user_most_eloc = train.groupby(['userid','geohashed_end_loc'],as_index=False)['geohashed_end_loc'].agg({'user_eloc_count':'count'})
    user_most_eloc.sort_values('user_eloc_count',inplace=True)
    user_most_eloc = user_most_eloc.groupby('userid').tail(1)
    user_most_eloc.rename(columns={'geohashed_end_loc':'user_most_eloc'},inplace=True)
    dist_user_most_eloc = pd.merge(result,user_most_eloc,on='userid',how = 'left')
    dist_user_most_eloc = dist_user_most_eloc[['orderid','geohashed_end_loc','user_most_eloc']]
    dist_user_most_eloc.rename(columns={'user_most_eloc':'geohashed_start_loc'},inplace=True)
    dist_user_most_eloc = get_distance(dist_user_most_eloc)
    return dist_user_most_eloc

# 获取用户的比率特征
def get_user_rate(result):
    result['user_eloc_rate'] = result['user_eloc_count'] / result['user_count']                                             # 获取用户去往该候选地的比例
    result['user_eloc_sloc_rate'] = (result['user_eloc_count'] + result['user_sloc_count']) / result['user_count']          # 获取用户将该地作为出发地和目的地的比例
    result['user_sloc_rate'] = result['user_sloc_count'] / result['user_count']                                             # 获取用户从该地出发的比例
    result['user_sloc2eloc_rate'] = result['user_sloc_eloc_count'] / result['user_count']                                   # 获取用户走过这条路径的比例
    return  result

#-------------------------------------------------------------------------#

# 获取用户骑行距离统计数据
def get_user_distance_stat(train,result):
    user_distance = train.groupby(['userid'],as_index=False)['distance'].agg({'user_max_distance':'max','user_min_distance':'min','user_average_distance':'mean'})
    result = pd.merge(result,user_distance,on=['userid'],how = 'left')
    user_manhattan = train.groupby(['userid'],as_index=False)['manhattan'].agg({'user_max_manhattan':'max','user_min_manhattan':'min','user_average_manhattan':'mean'})
    result = pd.merge(result, user_manhattan, on=['userid'], how='left')
    return result

# 获取用户从出发地出发的骑行距离统计数据
def get_user_sloc_distance_stat(train,result):
    user_sloc_distance = train.groupby(['userid','geohashed_start_loc'],as_index=False)['distance'].agg({'user_sloc_max_distance':'max','user_sloc_min_distance':'min','user_sloc_average_distance':'mean'})
    result = pd.merge(result, user_sloc_distance, on=['userid','geohashed_start_loc'], how='left')
    user_sloc_manhattan = train.groupby(['userid', 'geohashed_start_loc'], as_index=False)['manhattan'].agg({'user_sloc_max_manhattan': 'max', 'user_sloc_min_manhattan': 'min', 'user_sloc_average_manhattan': 'mean'})
    result = pd.merge(result, user_sloc_manhattan, on=['userid', 'geohashed_start_loc'], how='left')
    return result

# 获取用户到达某目的地的骑行距离统计数据
def get_user_eloc_distance_stat(train,result):
    user_eloc_distance = train.groupby(['userid', 'geohashed_end_loc'], as_index=False)['distance'].agg({'user_eloc_max_distance': 'max', 'user_eloc_min_distance': 'min', 'user_eloc_average_distance': 'mean'})
    result = pd.merge(result, user_eloc_distance, on=['userid', 'geohashed_end_loc'], how='left')
    user_eloc_manhattan = train.groupby(['userid', 'geohashed_end_loc'], as_index=False)['manhattan'].agg({'user_eloc_max_manhattan': 'max', 'user_eloc_min_manhattan': 'min', 'user_eloc_average_manhattan': 'mean'})
    result = pd.merge(result, user_eloc_manhattan, on=['userid', 'geohashed_end_loc'], how='left')
    return result

# 获取用户从候选地出发的平均小时
def get_user_eloc_hour(train, result):
    user_eloc_hour = train.groupby(['userid','geohashed_end_loc'],as_index=False)['hour'].agg({'user_eloc_average_hour':'mean'})
    result = pd.merge(result,user_eloc_hour,on=['userid','geohashed_end_loc'],how='left')
    return result

# 获取用户从出发地出发的平均小时
def get_user_sloc_hour(train, result):
    user_sloc_hour = train.groupby(['userid','geohashed_start_loc'],as_index=False)['hour'].agg({'user_sloc_average_hour':'mean'})
    result = pd.merge(result,user_sloc_hour,on=['userid','geohashed_start_loc'],how='left')
    return result

########################################################################
#                                                                      #
#                               位置特征                               #
#                                                                      #
########################################################################

# 获取目标地点的热度(目的地)
def get_eloc_count(train,result):
    eloc_count = train.groupby('geohashed_end_loc', as_index=False)['userid'].agg({'eloc_count': 'count'})
    result = pd.merge(result, eloc_count, on='geohashed_end_loc', how='left')
    return result

# 获取出发地点的热度(出发地)
def get_sloc_count(train,result):
    sloc_count = train.groupby('geohashed_start_loc', as_index=False)['userid'].agg({'sloc_count': 'count'})
    result = pd.merge(result, sloc_count, on='geohashed_start_loc', how='left')
    return result

# 获取从该候选地点出发的用户数
def get_unique_user_eloc_as_sloc_count(train,result):
    user_sloc_count = train.groupby(['geohashed_start_loc'],as_index=False)['userid'].agg({'unique_user_eloc_as_sloc_count':'nunique'})
    user_sloc_count.rename(columns={'geohashed_start_loc':'geohashed_end_loc'},inplace=True)
    result = pd.merge(result, user_sloc_count, on=['geohashed_end_loc'], how='left')
    return result

# 获取到达该候选地点的用户数
def get_unique_user_eloc_count(train,result):
    eloc_count = train.groupby('geohashed_end_loc', as_index=False)['userid'].agg({'unique_user_eloc_count': 'nunique'})
    result = pd.merge(result, eloc_count, on='geohashed_end_loc', how='left')
    return result

# 获取目标地点的热度(出发地)
def get_eloc_as_sloc_count(train,result):
    eloc_as_sloc_count = train.groupby('geohashed_start_loc', as_index=False)['userid'].agg({'eloc_as_sloc_count': 'count'})
    eloc_as_sloc_count.rename(columns={'geohashed_start_loc':'geohashed_end_loc'},inplace=True)
    result = pd.merge(result, eloc_as_sloc_count, on='geohashed_end_loc', how='left')
    return result

# 计算两点之间的距离
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
    manhattan_distance = []
    for i in geohashed_loc:
        if i[0] is not np.nan and i[1] is not np.nan:
            lat1, lon1 = loc_dict[i[0]]
            lat2, lon2 = loc_dict[i[1]]
            distance.append(cal_distance(float(lat1),float(lon1),float(lat2),float(lon2)))
            manhattan_distance.append(manhattan(float(lat1),float(lon1),float(lat2),float(lon2)))
        else:
            distance.append(np.nan)
            manhattan_distance.append(np.nan)
    result.loc[:,'distance'] = distance
    result.loc[:,'manhattan'] = manhattan_distance
    return result

# 获取到达该候选地的平均骑行距离
def get_eloc_average_distance(train,result):
    eloc_average_distance = train.groupby(['geohashed_end_loc'],as_index=False)['distance'].agg({'eloc_average_distance':'mean'})
    result = pd.merge(result,eloc_average_distance,on=['geohashed_end_loc'],how = 'left')
    return result

# 获取从该出发地出发的平均骑行距离
def get_sloc_average_distance(train,result):
    sloc_average_distance = train.groupby(['geohashed_start_loc'],as_index=False)['distance'].agg({'sloc_average_distance':'mean'})
    result = pd.merge(result,sloc_average_distance,on=['geohashed_start_loc'],how = 'left')
    return result

# 获取经纬度特征
def get_latlon(result):
    eloc_latlon = result['geohashed_end_loc'].apply(lambda x: Geohash.decode_exactly(x))
    result['eloc_lat'] = eloc_latlon.apply(lambda x: float(x[0]))
    result['eloc_lon'] = eloc_latlon.apply(lambda x: float(x[1]))
    sloc_latlon = result['geohashed_start_loc'].apply(lambda x: Geohash.decode_exactly(x))
    result['sloc_lat'] = sloc_latlon.apply(lambda x: float(x[0]))
    result['sloc_lon'] = sloc_latlon.apply(lambda x: float(x[1]))

    result['eloc_sloc_lat_sub'] = result['eloc_lat'] - result['sloc_lat']
    result['eloc_sloc_lon_sub'] = result['eloc_lon'] - result['sloc_lon']
    return result

def get_eloc_hour(train,result):
    eloc_time = train.groupby('geohashed_end_loc', as_index=False)['hour'].agg({'eloc_average_hour': 'mean'})
    result = pd.merge(result, eloc_time, on='geohashed_end_loc', how='left')
    return result

def get_sloc_hour(train,result):
    sloc_time = train.groupby('geohashed_start_loc', as_index=False)['hour'].agg({'sloc_average_hour': 'mean'})
    result = pd.merge(result, sloc_time, on='geohashed_start_loc', how='left')
    return result

########################################################################
#                                                                      #
#                               时间特征                               #
#                                                                      #
########################################################################


# 获取每个用户的出行星期数和小时数
def get_weekday_hour(result):
    data = result['starttime'].values
    week = []
    hour = []
    for i in data:
        time1 = i
        time2 = datetime.datetime.strptime(time1.split(".")[0], '%Y-%m-%d %H:%M:%S')
        weekday = time2.weekday()
        hour_time = time2.hour
        week.append(weekday)
        hour.append(hour_time)
    
    result.loc[:,'weekday'] = week
    result.loc[:,'hour'] = hour
    return result


########################################################################
#                                                                      #
#                               单车特征                               #
#                                                                      #
########################################################################

# 获取该单车去过该地的次数
def get_bike_eloc_count(train, result):
    user_eloc_count = train.groupby(['bikeid','geohashed_end_loc'],as_index=False)['bikeid'].agg({'bike_eloc_count':'count'})
    result = pd.merge(result,user_eloc_count,on=['bikeid','geohashed_end_loc'],how='left')
    return result

########################################################################
#                                                                      #
#                               其他函数                               #
#                                                                      #
########################################################################

# 计算两点之间欧式距离
def cal_distance(lat1,lon1,lat2,lon2):
    dx = np.abs(lon1 - lon2)  # 经度差
    dy = np.abs(lat1 - lat2)  # 维度差
    b = (lat1 + lat2) / 2.0
    Lx = 6371004.0 * (dx / 57.2958) * np.cos(b / 57.2958)
    Ly = 6371004.0 * (dy / 57.2958)
    L = (Lx**2 + Ly**2) ** 0.5
    return L

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

# 相差的分钟数
def diff_of_minutes(time1, time2):
    d = {'5': 0, '6': 31, }
    try:
        days = (d[time1[6]] + int(time1[8:10])) - (d[time2[6]] + int(time2[8:10]))
        try:
            minutes1 = int(time1[11:13]) * 60 + int(time1[14:16])
        except:
            minutes1 = 0
        try:
            minutes2 = int(time2[11:13]) * 60 + int(time2[14:16])
        except:
            minutes2 = 0
        return (days * 1440 - minutes2 + minutes1)
    except:
        return np.nan

# 分组排序
def rank(data, feat1, feat2, ascending):
    data.sort_values([feat1,feat2],inplace=True,ascending=ascending)
    data['rank'] = range(data.shape[0])
    min_rank = data.groupby(feat1,as_index=False)['rank'].agg({'min_rank':'min'})
    data = pd.merge(data,min_rank,on=feat1,how='left')
    data['rank'] = data['rank'] - data['min_rank']
    del data['min_rank']
    return data

# 对结果进行整理
def reshape(pred):
    result = pred.copy()
    result = rank(result,'orderid','pred',ascending=False)
    result = result[result['rank']<3][['orderid','geohashed_end_loc','rank']]
    result = result.set_index(['orderid','rank']).unstack()
    result.reset_index(inplace=True)
    result['orderid'] = result['orderid'].astype('int')
    result.columns = ['orderid', 0, 1, 2]
    return result

# 测评函数
def evaluation(result):
    result_path = cache_path + 'true.pkl'
    if os.path.exists(result_path):
        true = pickle.load(open(result_path, 'rb+'))
    else:
        train = pd.read_csv(train_path)
        true = dict(zip(train['orderid'].values,train['geohashed_end_loc']))
        pickle.dump(true,open(result_path, 'wb+'))
    data = result.copy()
    data['true'] = data['orderid'].map(true)
    score = (sum(data['true']==data[0])
             +sum(data['true']==data[1])/2
             +sum(data['true']==data[2])/3)/data.shape[0]
    return score

# 获取真实标签
def get_label(data):
    result_path = cache_path + 'true.pkl'
    if os.path.exists(result_path):
        true = pickle.load(open(result_path, 'rb+'))
    else:
        train = pd.read_csv(train_path)
        test = pd.read_csv(test_path)
        test['geohashed_end_loc'] = np.nan
        data = pd.concat([train,test])
        true = dict(zip(data['orderid'].values, data['geohashed_end_loc']))
        pickle.dump(true, open(result_path, 'wb+'))
    data['label'] = data['orderid'].map(true)
    data['label'] = (data['label'] == data['geohashed_end_loc']).astype('int')
    return data



########################################################################
#                                                                      #
#                              构造负样本                              #
#                                                                      #
########################################################################

# 将用户骑行过目的的地点加入成样本
def get_user_end_loc(train,test):
    result_path = cache_path + 'user_end_loc_%d.hdf' %(train.shape[0]*test.shape[0])
    if os.path.exists(result_path) & flag:
        result = pd.read_hdf(result_path, 'w')
    else:
        user_eloc = train[['userid','geohashed_end_loc']].drop_duplicates()
        result = pd.merge(test[['orderid','userid']],user_eloc,on='userid',how='left')
        result = result[['orderid', 'geohashed_end_loc']]
        result.to_hdf(result_path, 'w', complib='blosc', complevel=5)
    return result

# 将用户骑行过出发的地点加入成样本
def get_user_start_loc(train,test):
    result_path = cache_path + 'user_start_loc_%d.hdf' %(train.shape[0]*test.shape[0])
    if os.path.exists(result_path) & flag:
        result = pd.read_hdf(result_path, 'w')
    else:
        user_sloc = train[['userid', 'geohashed_start_loc']].drop_duplicates()
        result = pd.merge(test[['orderid', 'userid']], user_sloc, on='userid', how='left')
        result.rename(columns={'geohashed_start_loc':'geohashed_end_loc'},inplace=True)
        result = result[['orderid', 'geohashed_end_loc']]
        result.to_hdf(result_path, 'w', complib='blosc', complevel=5)
    return result

# 筛选起始地点去向最多的3个地点
def get_loc_to_loc(train,test):
    result_path = cache_path + 'loc_to_loc_%d.hdf' %(train.shape[0]*test.shape[0])
    if os.path.exists(result_path) & flag:
        result = pd.read_hdf(result_path, 'w')
    else:
        sloc_eloc_count = train.groupby(['geohashed_start_loc', 'geohashed_end_loc'],as_index=False)['geohashed_end_loc'].agg({'sloc_eloc_count':'count'})
        sloc_eloc_count.sort_values('sloc_eloc_count',inplace=True)
        sloc_eloc_count = sloc_eloc_count.groupby('geohashed_start_loc').tail(3)
        result = pd.merge(test[['orderid', 'geohashed_start_loc']], sloc_eloc_count, on='geohashed_start_loc', how='left')
        result = result[['orderid', 'geohashed_end_loc']]
        result.to_hdf(result_path, 'w', complib='blosc', complevel=5)
    return result


# 构造样本
def get_sample(train,test):
    result_path = cache_path + 'sample_%d.hdf' % (train.shape[0] * test.shape[0])
    if os.path.exists(result_path) & flag:
        result = pd.read_hdf(result_path, 'w')
    else:
        user_end_loc = get_user_end_loc(train, test)            # 根据用户历史目的地点添加样本 ['orderid', 'geohashed_end_loc', 'n_user_end_loc']
        user_start_loc = get_user_start_loc(train, test)        # 根据用户历史起始地点添加样本 ['orderid', 'geohashed_end_loc', 'n_user_start_loc']
        loc_to_loc = get_loc_to_loc(train, test)                # 筛选起始地点去向最多的3个地点
        # 汇总样本id
        result = pd.concat([user_end_loc[['orderid','geohashed_end_loc']],
                            user_start_loc[['orderid', 'geohashed_end_loc']],
                            loc_to_loc[['orderid', 'geohashed_end_loc']],
                            ]).drop_duplicates()
        # 根据end_loc添加标签(0,1)
        test_temp = test.copy()
        test_temp.rename(columns={'geohashed_end_loc': 'label'}, inplace=True)
        result = pd.merge(result, test_temp, on='orderid', how='left')
        result['label'] = (result['label'] == result['geohashed_end_loc']).astype(int)
        # 删除起始地点和目的地点相同的样本  和 异常值
        result = result[result['geohashed_end_loc'] != result['geohashed_start_loc']]
        result = result[(~result['geohashed_end_loc'].isnull()) & (~result['geohashed_start_loc'].isnull())]
        result.to_hdf(result_path, 'w', complib='blosc', complevel=5)
    return result

# 制作训练集
def make_train_set(train,test):
    print('开始构造样本...')
    result = get_sample(train,test)                                         # 构造备选样本
    print('开始构造特征...')
    dist_most = dist_user_most_eloc_eloc(train, result)                        # 获取候选地与用户最常去的地点之间的距离
    #讲获取到的数据分成6批
    print('成功获取与最常去地点间距离!')
    
    train = get_distance(train)
    train = get_weekday_hour(train)
    gc.collect()
    result = get_user_count(train,result)                                   # 获取用户历史行为次数
    result = get_user_eloc_count(train, result)                             # 获取用户去过这个地点几次
    result = get_user_sloc_count(train, result)                             # 获取用户从目的地点出发过几次
    result = get_user_sloc_eloc_count(train, result)                        # 获取用户从这个路径走过几次
    result = get_user_eloc_sloc_count(train, result)                        # 获取用户从这个路径折返过几次
    result = get_distance(result)                                           # 获取起始点和最终地点的欧式距离
    result = get_eloc_count(train, result)                                  # 获取目的地点的热度(目的地)
    result = get_eloc_as_sloc_count(train,result)                           # 获取目的地点的热度(出发地)
    result = get_sloc_count(train, result)                                  # 获取出发地点的热度(出发地)

    result = get_unique_user_eloc_as_sloc_count(train,result)               # 获取从该目的地点出发的用户数
    result = get_unique_user_eloc_count(train,result)                       # 获取去过该地点的用户数
    result = get_weekday_hour(result)                                       # 获取用户出行礼拜和小时
    result.fillna(0, inplace=True)
    result = get_user_rate(result)                                          # 获取各比例特征
    result.fillna(0, inplace=True)
    result = get_user_distance_stat(train,result)                           # 获取用户平均出行距离
    result = get_eloc_average_distance(train,result)                        # 获取该终点平均到达距离
    result = get_sloc_average_distance(train,result)                        # 获取该起点平均到达距离
    result = get_user_sloc_distance_stat(train, result)
    result = get_user_eloc_distance_stat(train,result)
    print('1 done!')
    result = get_bike_eloc_count(train, result)  # 获取获取该单车去过该地的次数
    result['dist_user_most_eloc_eloc'] = dist_most['distance']
    result['mdist_user_most_eloc_eloc'] = dist_most['manhattan']
    result = get_latlon(result)
    
    result = get_user_eloc_hour(train, result)
    result = get_user_sloc_hour(train, result)
    result = get_eloc_hour(train,result)
    result = get_sloc_hour(train,result)
    print('result.columns:\n{}'.format(result.columns))

    print('添加真实label')
    result = get_label(result)
    return result



# 训练提交

if __name__ == "__main__":
    t0 = time.time()
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    #train1 = train[(train['orderid'] > 500000)]
    #train2 = train[(train['orderid']<= 500000)]
    train1 = train[(train['starttime'] < '2017-05-20 00:00:00')]
    train2 = train[((train['starttime'] >= '2017-05-20 00:00:00') & (train['starttime'] < '2017-05-21 00:00:00'))]
    train2.loc[:,'geohashed_end_loc'] = np.nan
    test.loc[:,'geohashed_end_loc'] = np.nan

    print('构造训练集')
    #train_feat = make_train_set(train1,train2)
    #train_feat.to_csv(train_feat_path,index = False, header= True)
    train_feat = pd.read_csv(train_feat_path)
    train_feat['weekend'] = 1
    train_feat.loc[train_feat['weekday'] < 5,'weekend'] =0
    '''if os.path.exists(train_feat_path):
        print('读取train_feat')
        train_feat = pd.read_csv(train_feat_path)
    else:
        print('构造train_feat')
        train_feat = make_train_set(train1,train2)
        train_feat.to_csv(train_feat_path,index = False, header= True)
        #exit()'''
    print('构造线上测试集')
    #test_feat = make_train_set(train,test)
    #test_feat.to_csv(test_feat_path,index = False, header= True)
    test_feat = pd.read_csv(test_feat_path)
    test_feat['weekend'] = 1
    test_feat.loc[test_feat['weekday'] < 5,'weekend'] =0
    '''if os.path.exists(test_feat_path):
        print('读取test_feat')
        test_feat = pd.read_csv(test_feat_path)
    else:
        print('构造test_feat')
        test_feat = make_train_set(train,test)
        test_feat.to_csv(test_feat_path,index = False, header = True)
        #exit()'''
    del train,test,train1,train2
    print('构造完成!')


    import xgboost as xgb
    #args = sys.argv[1]
    #predictors = args.split(',')
    #print predictors
    predictors = [ 
                    
                    'user_count','user_eloc_count','user_sloc_count'
                    ,'user_sloc_eloc_count','user_eloc_sloc_count','dist_user_most_eloc_eloc'
                    ,'mdist_user_most_eloc_eloc','user_eloc_rate','user_eloc_sloc_rate'
                    ,'user_sloc2eloc_rate','user_sloc_rate','user_average_distance'
                    ,'user_max_distance','user_min_distance','user_average_manhattan'
                    ,'user_max_manhattan','user_min_manhattan','user_sloc_max_distance'
                    ,'user_sloc_min_distance','user_sloc_average_distance','user_sloc_max_manhattan'
                    ,'user_sloc_min_manhattan','user_sloc_average_manhattan','user_eloc_max_distance'
                    ,'user_eloc_min_distance','user_eloc_average_distance','user_eloc_max_manhattan'
                    ,'user_eloc_min_manhattan','user_eloc_average_manhattan','user_eloc_average_hour'
                    ,'user_sloc_average_hour','eloc_count','sloc_count'
                    ,'eloc_lat','eloc_lon','eloc_sloc_lat_sub'
                    ,'sloc_lat','sloc_lon','eloc_sloc_lon_sub'
                    ,'unique_user_eloc_as_sloc_count','unique_user_eloc_count','eloc_as_sloc_count'
                    ,'distance','manhattan','eloc_average_distance'
                    ,'sloc_average_distance','eloc_average_hour','sloc_average_hour'
                    ,'weekday','hour','weekend'
                    ,'biketype','bike_eloc_count'
                ]
                    
                   
                    #'biketype','user_count','user_eloc_count','user_sloc_count','user_sloc_eloc_count','user_eloc_sloc_count',
                    #'distance','eloc_count','sloc_count','eloc_as_sloc_count','weekday','hour',
                    #'unique_user_eloc_as_sloc_count','unique_user_eloc_count','bike_eloc_count','user_eloc_rate','user_eloc_sloc_rate',
                    #'user_sloc_rate','user_sloc2eloc_rate','manhattan','dist_user_most_eloc_eloc','mdist_user_most_eloc_eloc',
                    #'eloc_average_distance','sloc_average_distance',
                    #'user_average_distance','user_max_distance' ,'user_min_distance',
                    #'user_average_manhattan','user_max_manhattan'
                    #,'user_min_manhattan',
                    #'user_sloc_max_distance', 'user_sloc_min_distance', 'user_sloc_average_distance',
                    #'user_sloc_max_manhattan', 'user_sloc_min_manhattan', 'user_sloc_average_manhattan',
                    #'user_eloc_max_distance', 'user_eloc_min_distance', 'user_eloc_average_distance',
                    #'user_eloc_max_manhattan', 'user_eloc_min_manhattan', 'user_eloc_average_manhattan',
                    #'eloc_lat','eloc_lon','sloc_lat','sloc_lon','eloc_sloc_lat_sub','eloc_sloc_lon_sub'
                    #,'weekend','user_eloc_average_hour','user_sloc_average_hour','eloc_average_hour','sloc_average_hour'
                  # ]

                   #'bike_eloc_count','user_sloc_rate','eloc_as_sloc_count'
                   

    params = {
        'objective': 'binary:logistic',
        'eta': 0.1,
        'colsample_bytree': 0.886,
        'min_child_weight': 2,
        'max_depth': 10,
        'subsample': 0.886,
        'alpha': 10,
        'gamma': 30,
        'lambda':50,
        'verbose_eval': True,
        #'nthread': 16,
        'eval_metric': 'auc',
        'scale_pos_weight': 10,
        'seed': 201703,
        'missing':-1,
        'silent':1
        }

    xgbtrain = xgb.DMatrix(train_feat[predictors], train_feat['label'])
    xgbtest = xgb.DMatrix(test_feat[predictors])
    print('开始训练模型')
    model = xgb.train(params, xgbtrain, num_boost_round=120)
    del train_feat,xgbtrain
    gc.collect()

    print('开始进行预测')
    test_feat.loc[:,'pred'] = model.predict(xgbtest)
    test_feat = test_feat[['orderid','geohashed_end_loc','pred']]
    #test_feat.to_csv('pred.csv', index=False, header=False)
    gc.collect()

    print('正在整理结果')
    result = reshape(test_feat)
    test = pd.read_csv(test_path)
    result = pd.merge(test[['orderid']],result,on='orderid',how='left')
    result.fillna('0',inplace=True)
    result.columns=['orderid','cand1','cand2','cand3']
    result.to_csv('../result/result.csv',index=False,header=True)
    print('重要性排名：')
    fig, ax = pyplot.subplots(figsize=(18,18))
    xgb.plot_importance(model, max_num_features=50, height=0.8, ax=ax)
    pyplot.savefig("importance.png")
    print('一共用时{}秒'.format(time.time()-t0))
    print('用到{}个特征:'.format(len(predictors)))
    print(predictors)
    exit(len(predictors))
    #os.environ['pre']=str(predictors)
    #os.environ['len']=str(len(predictors))
    #os.system("echo '共$len个参数'")
    #os.system("echo '$pre'")
    #return predictors,len(predictors)

