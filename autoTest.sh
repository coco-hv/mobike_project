#!/bin/bash

#
Foo=('user_count'   'user_eloc_count'   'user_sloc_count'   'user_sloc_eloc_count'  'user_eloc_sloc_count'  'dist_user_most_eloc_eloc'  'mdist_user_most_eloc_eloc' 'user_eloc_rate'    'user_eloc_sloc_rate'   'user_sloc2eloc_rate'   'user_sloc_rate'    'user_average_distance' 'user_max_distance' 'user_min_distance' 'user_average_manhattan'    'user_max_manhattan'    'user_min_manhattan'    'user_sloc_max_distance'    'user_sloc_min_distance'    'user_sloc_average_distance'    'user_sloc_max_manhattan'   'user_sloc_min_manhattan'   'user_sloc_average_manhattan'   'user_eloc_max_distance'    'user_eloc_min_distance'    'user_eloc_average_distance'    'user_eloc_max_manhattan'   'user_eloc_min_manhattan'   'user_eloc_average_manhattan'   'user_eloc_average_hour'    'user_sloc_average_hour'    'eloc_count'    'sloc_count'    'eloc_lat'  'eloc_lon'  'eloc_sloc_lat_sub' 'sloc_lat'  'sloc_lon'  'eloc_sloc_lon_sub' 'unique_user_eloc_as_sloc_count'    'unique_user_eloc_count'    'eloc_as_sloc_count'    'distance'  'manhattan' 'eloc_average_distance' 'sloc_average_distance' 'eloc_average_hour' 'sloc_average_hour' 'weekday'   'hour'  'weekend'   'biketype'  'bike_eloc_count')

c=","
d="'"
tmp="user_count,user_eloc_count,user_sloc_count,user_sloc_eloc_count,user_eloc_sloc_count,dist_user_most_eloc_eloc,mdist_user_most_eloc_eloc,user_eloc_rate,user_eloc_sloc_rate,user_sloc2eloc_rate,user_sloc_rate,user_average_distance,user_max_distance,user_min_distance,user_average_manhattan,user_max_manhattan,user_min_manhattan,user_sloc_max_distance,user_sloc_min_distance,user_sloc_average_distance,user_sloc_max_manhattan,user_sloc_min_manhattan,user_sloc_average_manhattan,user_eloc_max_distance,user_eloc_min_distance,user_eloc_average_distance,user_eloc_max_manhattan,user_eloc_min_manhattan,user_eloc_average_manhattan,user_eloc_average_hour,user_sloc_average_hour,eloc_count,sloc_count,eloc_lat,eloc_lon,eloc_sloc_lat_sub,sloc_lat,sloc_lon"
for (( i = 38 ; i < ${#Foo[@]} ; i++ ))
do
  tmp="$tmp,${Foo[$i]}"
  echo $tmp
  nohup  python mobike.py $tmp >> new.log
  score=`python evaluation.py >> new.log`
  echo "MAP score is:$score "
  echo "The script is finished $(($i+1)) times"
done
