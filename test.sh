#!/bin/bash

nohup  python mobike.py >> dist.log
score=`python evaluation.py >> dist.log`
echo "MAP score is: "
echo ${score}
echo "The script is finished"
