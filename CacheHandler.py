import json # for cache_lookup_table
import os # remove file os.remove(filename)
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket




#  ██  ██       ██████  █████   ██████ ██   ██ ███████     ██   ██  █████  ███    ██ ██████  ██      ███████ ██████
# ████████     ██      ██   ██ ██      ██   ██ ██          ██   ██ ██   ██ ████   ██ ██   ██ ██      ██      ██   ██
#  ██  ██      ██      ███████ ██      ███████ █████       ███████ ███████ ██ ██  ██ ██   ██ ██      █████   ██████
# ████████     ██      ██   ██ ██      ██   ██ ██          ██   ██ ██   ██ ██  ██ ██ ██   ██ ██      ██      ██   ██
#  ██  ██       ██████ ██   ██  ██████ ██   ██ ███████     ██   ██ ██   ██ ██   ████ ██████  ███████ ███████ ██   ██



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
                                                            with title: `${FH}, ${encoding}`,
                                                            with raw response as payload
                                                            update lookup file correspondingly

        fetchResponse(rqp):                             param: (rqp : RequestPacket)
                                                        handle fetch request

        deleteFromCache(rqp, rsp):                      delete cache response
                                                        update lookup file correspondingly

        __updateLookup(method, FH, encoding):           param: (method: {'ADD', 'DEL'}, FH : string, encoding : string)
                                                        ADD: add entry to lookup table
                                                        DEL: delete entry from lookup table

        __entryExists(FH, entries):                     check if response ${FH} exists in entries
                                                        returns index in array if true,
                                                        returns -1 otherwise

        __generateJSON(FH):                             generate template for ${FH} object

        __getCacheFileNameFH(rqp):                      generate cache file name first half for the request
    '''

    cacheFileDirectory = 'cache_responses/'

    @staticmethod
    def cacheResponse(rqp, rsp):
        '''
        assumed request method is GET
        cache response whenever no-store, private are not specified in cache-control
        because all cached response will be revalidated by proxy anyway
        '''
        cacheOption = rsp.getHeaderInfo('cache-control').lower()
        cacheOptionSplitted = cacheOption.split(', ')
        if 'no-store' not in cacheOptionSplitted and 'private' not in cacheOptionSplitted: # specified as public or the header field is not present
            cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half
            encoding = rsp.getHeaderInfo('content-encoding')
            cacheFileName = CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding
            print('CacheHandler:: cacheFileName: ' + cacheFileName)
            origin = os.getcwd()
            try:
                os.chdir(CacheHandler.cacheFileDirectory)
            except FileNotFoundError as e:
                os.mkdir(CacheHandler.cacheFileDirectory)
                os.chdir(CacheHandler.cacheFileDirectory)

            for index in range(len(cacheFileNameSplitted) - 1): # ensure layers of directory exists
                try:
                    os.chdir(cacheFileNameSplitted[index])
                except FileNotFoundError as e:
                    os.mkdir(cacheFileNameSplitted[index])
                    os.chdir(cacheFileNameSplitted[index])
            os.chdir(origin) # go back to project root
            try:
                with open(cacheFileName, 'wb') as cacheFile: # write as byte
                    cacheFile.write(rsp.getPacketRaw())
                print('------------------------------')
                print('CacheHandler:: response cached')
                print('------------------------------')
            except Exception as e:
                raise e
            try:
                CacheHandler.__updateLookup('ADD', cacheFileNameFH, encoding)
            except Exception as e:
                raise e
        else:
            pass # do not cache response
            print('-------------------------')
            print('CacheHandler:: not cached')
            print('-------------------------')

    @staticmethod
    def fetchResponse(rqp):
        if rqp.getMethod().lower() == 'get':
            cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half, splitted is useless here

            try:
                with open('cache_lookup_table.json', 'r') as table:
                    entries = json.load(table)
            except Exception as e: # unable to open, meaning no such table, thus no cache
                return None
            idx = CacheHandler.__entryExists(cacheFileNameFH, entries) # check cache entry
            if idx == -1: # no entry of such file exists
                return None
            print('-----------------------------------')
            print('CacheHandler:: cache response found')
            print('-----------------------------------')
            encodings = rqp.getHeaderInfo('accept-encoding')
            if encodings == 'nil':
                encodings = '*'
            encodingsSplitted = encodings.split(', ')
            for encoding in encodingsSplitted:
                if encoding == '*': # accept any encoding
                    for encoding in entries[idx]: # loop through key value pairs for the entry
                        if encoding == 'cacheFileNameFH':
                            continue
                        if entries[idx][encoding] == 'True':
                            try:
                                with open(CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding, 'rb') as responseFile:
                                    responseRaw = responseFile.read()
                                print('----------------------------------------')
                                print('CacheHandler:: returning cache response:')
                                print('----------------------------------------')
                                return ResponsePacket.parsePacket(responseRaw)
                            except Exception as e:
                                raise e
                    print('this line should not appear') # there should exist an entry for the fullPath, somethin's wrong
                    raise Exception('could not find entry that should be present')

                if entries[idx][encoding] == 'True': # encoding specified is not '*'
                    try:
                        with open(CacheHandler.cacheFileDirectory + cacheFileNameFH+ ', ' + encoding, 'rb') as responseFile:
                            responseRaw = responseFile.read()
                        print('----------------------------------------')
                        print('CacheHandler:: returning cache response:')
                        print('----------------------------------------')
                        return ResponsePacket.parsePacket(responseRaw)
                    except Exception as e:
                        print('CacheHandler:: fetchResponse cacheFileName: ' + CacheHandler.cacheFileDirectory + cacheFileNameFH+ ', ' + encoding)
                        raise Exception('could not find entry that should be present')

            if entries[idx]['nil'] == 'True': # last check if uncompressed file exists
                try:
                    with open(CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + 'nil', 'rb') as responseFile:
                        responseRaw = responseFile.read()
                    return ResponsePacket.parsePacket(responseRaw)
                except Exception as e:
                    raise e
        else:
            pass # fetching from cache only applies to GET method
            return None

    @staticmethod
    def deleteFromCache(rqp, rsp):
        cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half, splitted is useless here

        if CacheHandler.__entryExists(cacheFileNameFH) != -1:
            encoding = rsp.getHeaderInfo('content-encoding')
            cacheFileName = CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding
            try:
                os.remove(cacheFileName)
            except Exception as e:
                raise Exception('CacheHandler:: deleteFromCache(): attempted to delete non-existing file')
            try:
                __updateLookup('DEL', cacheFileNameFH, encoding)
            except Exception as e:
                raise e
        else:
            pass # nothing to delete

    @staticmethod
    def __updateLookup(method, cacheFileNameFH, encoding):
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

        idx = CacheHandler.__entryExists(cacheFileNameFH, entries)

        if method == 'ADD':
            if idx == -1: # no existing entry found
                newEntry = CacheHandler.__generateJSON(cacheFileNameFH) # create new entry
                try:
                    newEntry.update({encoding : "True"})
                except Exception as e:
                    newEntry.add({encoding : "True"})
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
                    if encoding == 'cacheFileNameFH':
                        continue
                    if entries[idx][encoding] == 'True':
                        deleteEntryFlag = False
                        break
                if deleteEntryFlag: # no more cached response for this cacheFileNameFH
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
    def __entryExists(cacheFileNameFH, entries=[]):
        if entries == []:
            try:
                with open('cache_lookup_table.json', 'r') as table:
                    entries = json.load(table)
            except Exception as e: # unable to open, meaning no such table, thus no cache
                return -1
        for idx in range(len(entries)):
            if entries[idx]['cacheFileNameFH'] == cacheFileNameFH:
                return idx
        return -1

    @staticmethod
    def __generateJSON(cacheFileNameFH):
        object = {
            "cacheFileNameFH" : cacheFileNameFH,
            "gzip" : "False",
            "compress" : "False",
            "deflate" : "False",
            "br" : "False",
            "identity" : "False",
            "nil" : "False"
        }
        return object

    @staticmethod
    def __getCacheFileNameFH(rqp):
        cacheFileNameSplitted = [rqp.getHostName()]
        if rqp.getFilePath() != '/':
            filePathSplitted = rqp.getFilePath()[1:].split('/')
            for subPath in filePathSplitted:
                cacheFileNameSplitted.append(subPath)
        cacheFileNameFH = ''
        for subpart in cacheFileNameSplitted:
            cacheFileNameFH += subpart + '/'
        return cacheFileNameFH[:-1], cacheFileNameSplitted






#  ██  ██       ██████  █████   ██████ ██   ██ ███████     ████████ ██   ██ ██████  ███████  █████  ██████
# ████████     ██      ██   ██ ██      ██   ██ ██             ██    ██   ██ ██   ██ ██      ██   ██ ██   ██
#  ██  ██      ██      ███████ ██      ███████ █████          ██    ███████ ██████  █████   ███████ ██   ██
# ████████     ██      ██   ██ ██      ██   ██ ██             ██    ██   ██ ██   ██ ██      ██   ██ ██   ██
#  ██  ██       ██████ ██   ██  ██████ ██   ██ ███████        ██    ██   ██ ██   ██ ███████ ██   ██ ██████




import threading
from CacheHandler import CacheHandler

class CacheThread(threading.Thread):
    '''
    thread to cache the response

    Members:

        __rqp:                  request packet

        __rsp:                  response packet to be cached, regardless of cacheability

    Constructor:

        default:                set rqp, rsp

    Functions:

        run:                    call CacheHandler.cacheResponse(rqp, rsp)
    '''

    def __init__(self, rqp, rsp, option):
        threading.Thread.__init__(self)
        self.__rqp = rqp
        self.__rsp = rsp
        self.__option = option

    def run(self):
        if self.__option == 'ADD':
            CacheHandler.cacheResponse(self.__rqp, self.__rsp)
        elif self.__option == 'DEL':
            CacheHandler.deleteFromCache(self.__rqp, self.__rsp)
