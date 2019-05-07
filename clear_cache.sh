#! /bin/bash

# this script deletes cache related files and directories

echo "clearing cache"
cache_table="cache_lookup_table.json"
cache_responses="cache_responses/"

if [ -a $cache_table ]
then
	rm $cache_table
	echo "deleted $cache_table"
else
	echo "$cache_table does not exist"
fi

if [ -d $cache_responses ]
then
	rm -rf $cache_responses
	echo "deleted $cache_responses"
else
	echo "$cache_responses does not exist"
fi
