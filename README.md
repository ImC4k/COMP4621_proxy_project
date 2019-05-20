# COMP4621 PROXY PROJECT
>2019Spring, HKUST, COMP4621: Computer Communication Networks (I) final project, simple proxy to support http/ https forwarding, caching, access control

## Running the proxy (python 3)
```
python proxy_main.py [max_connection=numThread] [port=portNumber]
```

### Clearing cache lookup table and cache directory
```
./clear_cache.sh
```

### Create access control website file
```
./create_banned_sites_file.sh
```

- NOTE:
to specify access control, create a file called banned_sites and put to project root directory
put host name to a new line
to break between the file, add '***'
