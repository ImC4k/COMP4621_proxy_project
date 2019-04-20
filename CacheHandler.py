import json # for cache_lookup_table
import os # remove file os.remove(filename)
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
from TimeComparator import TimeComparator

class CacheHandler:
    '''
    cache handler offers only static functions
    it acts as a global singleton to handle cache for all threads

    records responses to local files,
    returns a cached response

    Members:

        cacheFileDirectory:             directory name of all cached responses to be stored into

    Constructor:

    Functions:

        cacheResponse(rqp, rsp):                        param: (rsp : ResponsePacket)
                                                        handle cache request
                                                        determine if the response should be cached/ updated in cache file
                                                        if no, then simply return
                                                        if yes,
                                                            write the response to cached_responses/ directory,
                                                            with title: `${fullPath}, ${encoding}`,
                                                            with raw response as payload
                                                            update lookup file correspondingly

        fetchResponse(rqp):                             param: (rqp : RequestPacket)
                                                        handle fetch request

        deleteFromCache(rqp, rsp):                      delete cache response
                                                        update lookup file correspondingly

        updateLookup(method, fullPath, encoding):       param: (method: {'ADD', 'DEL'}, fullPath : string, encoding : string)
                                                        ADD: add entry to lookup table
                                                        DEL: delete entry from lookup table

        entryExists(fullPath):                          check if response ${fullPath} exists in lookup table
                                                        returns index in array if true,
                                                        returns -1 otherwise

        generateJSON(fullPath):                         generate template for ${fullPath} object
    '''

    cacheFileDirectory = 'cache_responses/'

    @staticmethod
    def cacheResponse(rqp, rsp):
        '''
        assumed request method is GET
        '''
        cacheOption = rsp.getHeaderInfo('cache-control').lower()
        if cacheOption == 'public' or cacheOption == 'nil': # specified as public or the header field is not present
            fullPath = rqp.getFullPath()
            encoding = rsp.getHeaderInfo('content-encoding')
            if encoding == 'nil':
                encoding = 'uncompressed'
            cacheFileName = CacheHandler.cacheFileDirectory + fullPath + ', ' + encoding
            try:
                cacheFile = open(cacheFileName, 'w')
                cacheFile.write(rsp.getPacketRaw())
            except FileNotFoundError as e: # no directory found, create directory and retry
                os.mkdir(CacheHandler.cacheFileDirectory)
                cacheFile = open(cacheFileName, 'w')
                cacheFile.write(rsp.getPacketRaw())
            except Exception as e:
                raise e
            try:
                CacheHandler.__updateLookup('ADD', fullPath, encoding)
            except Exception as e:
                raise e
        else:
            pass # do not cache response

    @staticmethod
    def fetchResponse(rqp):
        if rqp.getMethod().lower() == 'get':
            fullPath = rqp.getFullPath()

            try:
                with open('cache_lookup_table.json', 'r') as table:
                    entries = json.load(table)
            except FileNotFoundError as e:
                return None
            except Exception as e:
                return None
            idx = CacheHandler.__entryExists(fullPath, entries)
            if idx == -1: # no entry of such file exists
                return None
            encodings = rqp.getHeaderInfo('accept-encoding')
            if encodings == 'nil':
                encodings = '*'
            encodingsSplitted = encodings.split(', ')
            for encoding in encodingsSplitted:
                if encoding == '*': # accept any encoding
                    for encoding in entries[idx]:
                        if encoding == 'fullPath':
                            continue
                        if entries[idx][key] == 'True':
                            try:
                                with open(CacheHandler.cacheFileDirectory + fullPath + ', ' + encoding, 'r') as responseFile:
                                    response = response.read()
                                return response
                            except Exception as e:
                                raise e
                    print('this line should not appear') # there should exist an entry for the fullPath, somethin's wrong
                    raise Exception('could not find entry that should be present')
                    return None
                if entries[idx][encoding] == 'True':
                    try:
                        with open(CacheHandler.cacheFileDirectory + fullPath + ', ' + encoding, 'r') as responseFile:
                            response = response.read()
                        return response
                    except Exception as e:
                        raise e
            if entries[idx]['uncompressed'] == 'True': # last check if uncompressed file exists
                try:
                    with open(CacheHandler.cacheFileDirectory + fullPath + ', ' + 'uncompressed', 'r') as responseFile:
                        response = response.read()
                    return response
                except Exception as e:
                    raise e
        else:
            pass # fetching from cache only applies to GET method
            return None

    @staticmethod
    def deleteFromCache(rqp, rsp):
        cacheOption = rsp.getHeaderInfo('cache-control').lower()
        if cacheOption == 'public':
            fullPath = rqp.getFullPath()
            encoding = rsp.getHeaderInfo('accept-encoding')
            cacheFileName = CacheHandler.cacheFileDirectory + fullPath + ', ' + encoding
            try:
                os.remove(CacheHandler.cacheFileDirectory + fullPath + ', ' + encoding)
            except Exception as e:
                raise Exception('CacheHandler:: deleteFromCache(): attempted to delete non-existing file')
            try:
                __updateLookup('DEL', fullPath, encoding)
            except Exception as e:
                raise e
        else:
            pass # nothing to delete

    @staticmethod
    def __updateLookup(method, fullPath, encoding):
        '''
        ADD: add record/ entry to lookup table
        DEL: delete record/ entry from lookup table
        '''
        try:
            with open('cache_lookup_table.json', 'r') as table:
                entries = json.load(table)
        except FileNotFoundError as e: # first write to lookup table
            entries = []
        except Exception as e:
            raise e

        idx = __entryExists(fullPath, entries)

        if method == 'ADD':
            if idx == -1: # no existing entry found
                newEntry = __generateJSON(fullPath) # create new entry
                try:
                    entries[idx].update({encoding : "True"})
                except Exception as e:
                    entries[idx].add({encoding : "True"})
                entries.append(newEntry)
            else: # entry found
                try:
                    entries[idx].update({encoding : "True"})
                except Exception as e:
                    entries[idx].add({encoding : "True"})
        elif method == 'DEL':
            if idx == -1: # something wrong
                raise Exception('CacheHandler:: __updateLookup(): attempted to delete non-existing entry')
            else:
                deleteEntryFlag = True
                entries[idx].update({encoding : "False"})
                for encoding in entries[idx]: # if there exists a record with an encoding stored in cache, no need to delete
                    if encoding == 'fullPath':
                        continue
                    if entries[idx][encoding] == 'True':
                        deleteEntryFlag = False
                        break
                if deleteEntryFlag: # no more cached response for this fullPath
                    del entries[idx]
        else:
            print('CacheHandler:: __updateLookup(): invalid method: ' + method)
            return

        # replace lookup table
        try:
            os.remove('cache_lookup_table.json') # delete if exists
        except FileNotFoundError as e:
            pass # no deletion if not found
        except Exception as e: # raise exception for other exceptions
            raise e
        with open('cache_lookup_table.json', 'w') as table: # write new lookup table
            json.dump(entries, table, indent=4)

    @staticmethod
    def __entryExists(fullPath, entries):
        for idx in range(len(entries)):
            if entries[idx]['fullPath'] == fullPath:
                return idx
        return -1

    @staticmethod
    def __generateJSON(fullPath):
        object = {
            "fullPath" : fullPath,
            "gzip" : "False",
            "compress" : "False",
            "deflate" : "False",
            "br" : "False",
            "identity" : "False",
            "uncompressed" : "False"
        }
        return object
