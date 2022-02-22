#!/usr/bin/bash
ps -o pid,cmd | grep '[s]erver.py' | while read line
do
  echo $line
  pid=`echo $line | sed 's/^ *//g' | cut -d ' ' -f 1`
  kill $pid
done