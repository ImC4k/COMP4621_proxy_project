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

        cacheResponses(rqp, rsps):                      param: (rqp: RequestPacket, rsps : list of ResponsePacket)
                                                        handle cache request
                                                        determine if the responses should be cached/ updated in cache file
                                                        if no, then simply return
                                                        if yes,
                                                            write the responses to cached_responses/ directory,
                                                            with title: `${FH}, ${encoding}, ${order}`,
                                                            with raw response as payload
                                                            update lookup file correspondingly

        fetchResponse(rqp):                             param: (rqp : RequestPacket)
                                                        handle fetch request
                                                        returns list of response packets fetched
                                                        if nothing fetched, return None

        deleteFromCache(rqp, rsp):                      delete all cache responses matching file url
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
    def cacheResponses(rqp, rsps):
        '''
        assumed request method is GET
        cache response whenever no-store, private are not specified in cache-control
        because all cached response will be revalidated by proxy anyway
        '''
        # TODO delete previous version if exist because new data may not overwrite all related files

        cacheOption = rsps[0].getHeaderInfo('cache-control').lower()
        cacheOptionSplitted = cacheOption.split(', ')
        if 'no-store' not in cacheOptionSplitted and 'private' not in cacheOptionSplitted: # specified as public or the header field is not present
            cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half
            encoding = rsps[0].getHeaderInfo('content-encoding')
            origin = os.getcwd()
            try: # ensure cache directory exists
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

            index = 0
            for rsp in rsps: # cache each responses
                index += 1
                cacheFileName = CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(index)
                print('CacheHandler:: cacheFileName: ' + cacheFileName)
                try:
                    with open(cacheFileName, 'wb') as cacheFile: # write as byte
                        try:
                            cacheFile.write(rsp.getPacketRaw())
                        except AttributeError as e:
                            cacheFile.write(rsp)
                    print('---------------------------------------------------------------')
                    print('CacheHandler:: response: ' + cacheFileNameFH + ', ' + str(index) + ' is cached')
                    print('---------------------------------------------------------------')
                except Exception as e:
                    raise e
            try:
                CacheHandler.__updateLookup('ADD', cacheFileNameFH, encoding, index)
            except Exception as e:
                raise e
        else:
            pass # do not cache response
            print('-------------------------')
            print('CacheHandler:: not cached')
            print('-------------------------')

    @staticmethod
    def fetchResponses(rqp): # fetch all related responses, return list of response packets (not raw)
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
                        if entries[idx][encoding] != 0:
                            numFiles = entries[idx][encoding]
                            rsps = [] # list of response packets
                            for i in range(1, numFiles + 1):
                                try:
                                    with open(CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i), 'rb') as responseFile:
                                        responseRaw = responseFile.read()
                                    print('---------------------------------------------------------------')
                                    print('CacheHandler:: ' + CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i))
                                    print('---------------------------------------------------------------')
                                    if rsps == []:
                                        rsps.append(ResponsePacket.parsePacket(responseRaw))
                                    else:
                                        if rsps[0].responseCode() != '206':
                                            rsps.append(responseRaw)
                                except Exception as e:
                                    raise e
                            print('----------------------------------------')
                            print('CacheHandler:: returning cache response:')
                            print('----------------------------------------')
                            return rsps
                    print('this line should not appear') # there should exist an entry for the fullPath, somethin's wrong
                    raise Exception('could not find entry that should be present')

                if entries[idx][encoding] != 0: # encoding specified is not '*'
                    numFiles = entries[idx][encoding]
                    rsps = []
                    for i in range(1, numFiles + 1):
                        try:
                            with open(CacheHandler.cacheFileDirectory + cacheFileNameFH+ ', ' + encoding + ', ' + str(i), 'rb') as responseFile:
                                responseRaw = responseFile.read()
                            print('---------------------------------------------------------------')
                            print('CacheHandler:: ' + CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i))
                            print('---------------------------------------------------------------')
                            if rsps == []:
                                rsps.append(ResponsePacket.parsePacket(responseRaw))
                            else:
                                if rsps[0].responseCode() != '206':
                                    rsps.append(responseRaw)
                        except Exception as e:
                            print('CacheHandler:: fetchResponse cacheFileName: ' + CacheHandler.cacheFileDirectory + cacheFileNameFH+ ', ' + encoding + ', ' + str(i))
                            raise Exception('could not find entry that should be present')
                    print('----------------------------------------')
                    print('CacheHandler:: returning cache response:')
                    print('----------------------------------------')
                    return rsps

            if entries[idx]['nil'] != 0: # last check if uncompressed file exists
                numFiles = entries[idx]['nil']
                rsps = []
                for i in range(1, numFiles + 1):
                    try:
                        with open(CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + 'nil' + ', ' + str(i), 'rb') as responseFile:
                            responseRaw = responseFile.read()
                        print('---------------------------------------------------------------')
                        print('CacheHandler:: ' + CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + 'nil' + ', ' + str(i))
                        print('---------------------------------------------------------------')
                        if rsps == []:
                            rsps.append(ResponsePacket.parsePacket(responseRaw))
                        else:
                            if rsps[0].responseCode() != '206':
                                rsps.append(responseRaw)
                    except Exception as e:
                        raise e
                return rsps
        else:
            pass # fetching from cache only applies to GET method
            return None

    @staticmethod
    def deleteFromCache(rqp): # TODO get number of files cached, delete them all
        cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half, splitted is useless here
        try:
            with open('cache_lookup_table.json', 'r') as table:
                entries = json.load(table)
        except Exception as e: # unable to open, meaning no such table, thus no cache
            raise Exception('CacheHandler:: deleteFromCache(): attempted to delete non-existing file')

        idx = CacheHandler.__entryExists(cacheFileNameFH, entries)
        if idx != -1:
            for encoding in entries[idx]:
                if encoding == 'cacheFileNameFH':
                    continue
                numFiles = entries[idx][encoding] # number of files stored for this encoded file
                if numFiles == 0:
                    continue
                for i in range(1, numFiles + 1):
                    cacheFileName = CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i)
                    try:
                        os.remove(cacheFileName)
                    except Exception as e:
                        raise Exception('CacheHandler:: deleteFromCache(): attempted to delete non-existing file')
            try:
                __updateLookup('DEL', cacheFileNameFH) # delete entire entry, because all encodings are deleted
            except Exception as e:
                raise e
        else:
            pass # nothing to delete

    @staticmethod
    def __updateLookup(method, cacheFileNameFH, encoding='', numFiles=''):
        '''
        ADD: add record/ entry to lookup table
        DEL: delete record/ entry from lookup table, ignores encoding, numFiles
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
                    newEntry.update({encoding : numFiles})
                except Exception as e:
                    newEntry.add({encoding : numFiles})
                entries.append(newEntry)
            else: # entry found
                try:
                    entries[idx].update({encoding : numFiles})
                except Exception as e:
                    entries[idx].add({encoding : numFiles})
        elif method == 'DEL':
            if idx == -1: # something wrong
                raise Exception('CacheHandler:: __updateLookup(): attempted to delete non-existing entry')
            else:
                # deleteEntryFlag = True
                # entries[idx].update({encoding : 0})
                # for encoding in entries[idx]: # if there exists a record with an encoding stored in cache, no need to delete
                #     if encoding == 'cacheFileNameFH':
                #         continue
                #     if entries[idx][encoding] != 0:
                #         deleteEntryFlag = False
                #         break
                # if deleteEntryFlag: # no more cached response for this cacheFileNameFH
                #     del entries[idx]
                del entries[idx] # delete entire entry
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
            "gzip" : 0,
            "compress" : 0,
            "deflate" : 0,
            "br" : 0,
            "identity" : 0,
            "nil" : 0
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

        __option:               'ADD' / 'DEL'

        __rqp:                  request packet

        __rsps:                 response packets

    Constructor:

        default:                set rqp, rsps

    Functions:

        run:                    'ADD': call CacheHandler.cacheResponse(rqp, rsp)
                                'DEL': call CacheHandler.deleteFromCache(rqp)
    '''

    def __init__(self, option, rqp, rsps):
        threading.Thread.__init__(self)
        self.__option = option
        self.__rqp = rqp
        self.__rsps = rsps

    def run(self):
        if self.__option == 'ADD':
            CacheHandler.cacheResponses(self.__rqp, self.__rsps)
        elif self.__option == 'DEL':
            CacheHandler.deleteFromCache(self.__rqp)
