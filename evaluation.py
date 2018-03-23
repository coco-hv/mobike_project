#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author : Coco

from time import sleep
#import tqdm
import  pandas as pd
import os
import pickle


train_path = '../train/train.csv'
cache_path = '../cache/'
result_path = cache_path + 'true.pkl'
result=pd.read_csv('../result/result.csv')

if __name__ == "__main__":
    if os.path.exists(result_path):
        true = pickle.load(open(result_path, 'rb+'))
    else:
        train = pd.read_csv(train_path)
        true = dict(zip(train['orderid'].values,train['geohashed_end_loc']))
        pickle.dump(true,open(result_path, 'wb+'))
    data = result.copy()
    data['true'] = data['orderid'].map(true)

    result = data[['true','cand1','cand2','cand3']]

    #result.to_csv('true&candidates.csv',index=False,header=True)

    score = float((sum(data['true']==data['cand1'])
            +float(sum(data['true']==data['cand2'])/2)
            +float(sum(data['true']==data['cand3'])/3))/data.shape[0])

    print('MAP result:')
    print score
    exit(score)
    #os.environ['score']=str(score)
    #os.system("echo 'MAP score is $score'")
   # return score
