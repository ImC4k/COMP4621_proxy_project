import json # for cache_lookup_table
import os # remove file os.remove(filename)
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
from TimeComparator import TimeComparator
import threading



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

        lookupTableRWLock:              a lock for lookup table, must acquire it before reading/ writing

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

    origin = '' # initialized by proxy_main
    cacheFileDirectory = 'cache_responses/'
    lookupTableRWLock = threading.Semaphore() # require sequential read/ write, otherwise may occur corruption/ data loss

    @staticmethod
    def cacheResponses(rqp, rsps):
        '''
        assumed request method is GET
        cache response whenever no-store, private are not specified in cache-control
        because all cached response will be revalidated by proxy anyway
        '''

        cacheOption = rsps[0].getHeaderInfo('cache-control').lower()
        cacheOptionSplitted = cacheOption.split(',')
        for i in range(len(cacheOptionSplitted)):
            cacheOptionSplitted[i] = cacheOptionSplitted[i].strip()
        print('CacheHandler:: cacheResponses: cacheOptionSplitted: ' + str(cacheOptionSplitted))
        if 'no-store' not in cacheOptionSplitted and 'private' not in cacheOptionSplitted: # specified as public or the header field is not present
            cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half

            if len(cacheFileNameFH) > 255:
                print('CacheHandler:: cacheResponses: file name too long, not caching')
                return

            idx = CacheHandler.__entryExists(cacheFileNameFH) # remove previous cache files
            if idx != -1:
                try:
                    CacheHandler.deleteFromCache(rqp)
                except Exception as e:
                    raise e

            encoding = rsps[0].getHeaderInfo('content-encoding')

            expiry = 'nil' # default expiration is nil

            if '' in cacheFileNameSplitted:
                print('CacheHandler:: cacheResponses: \'//\' detected, not supported')
                print('-------------------------')
                print('CacheHandler:: not cached')
                print('-------------------------')
                return
            else:
                for option in cacheOptionSplitted:
                    if option[0:len('max-age')].lower() == 'max-age':
                        secondStr = option.split('=')[1]
                        responseDate = rsps[0].getHeaderInfo('date')
                        if responseDate == 'nil': # date of retrieval not specified
                            expiry = (TimeComparator.currentTime() + secondStr).toString() # use current time
                            print('CacheHandler:: cacheResponses: expiry: ' + expiry)
                        else:
                            expiry = (TimeComparator(responseDate) + secondStr).toString()
                            print('CacheHandler:: cacheResponses: expiry: ' + expiry)
                        break

                for option in cacheOptionSplitted: # overwrite expiry from max-age with s-maxage
                    if option[0:len('s-maxage')].lower() == 's-maxage':
                        secondStr = option.split('=')[1]
                        responseDate = rsps[0].getHeaderInfo('date')
                        if responseDate == 'nil':
                            expiry = (TimeComparator.currentTime() + secondStr).toString()
                            print('CacheHandler:: cacheResponses: expiry: ' + expiry)
                        else:
                            expiry = (TimeComparator(responseDate) + secondStr).toString()
                            print('CacheHandler:: cacheResponses: expiry: ' + expiry)
                        break

                for option in cacheOptionSplitted: # don't do anything on expiry if must revalidate
                    if option == 'must-revalidate' or option == 'proxy-revalidate' or option == 'no-cache':
                        expiry = 'nil' # overwrite expiry back to 'nil'
                        break

            CacheHandler.lookupTableRWLock.acquire() # make sure no one is writing to a lookup table when changing directory
            if CacheHandler.origin is None:
                CacheHandler.origin = os.getcwd()
            try: # ensure cache directory exists
                os.chdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
            except FileNotFoundError as e:
                os.mkdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
                os.chdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
            for index in range(len(cacheFileNameSplitted) - 1): # ensure layers of directory exists
                try:
                    os.chdir(cacheFileNameSplitted[index])
                except FileNotFoundError as e:
                    os.mkdir(cacheFileNameSplitted[index])
                    os.chdir(cacheFileNameSplitted[index])
            os.chdir(CacheHandler.origin) # go back to project root
            CacheHandler.lookupTableRWLock.release()

            index = 0
            for rsp in rsps: # cache each responses
                index += 1
                cacheFileName = CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(index)
                try:
                    with open(cacheFileName, 'wb') as cacheFile: # write as byte
                        try:
                            cacheFile.write(rsp.getPacketRaw())
                        except AttributeError as e:
                            cacheFile.write(rsp)
                        except OSError as e:
                            print(e)
                            print('CacheHandler:: cacheResponses(): fail to cache file')
                except Exception as e:
                    raise e
            print('---------------------------------------------------------------')
            print('CacheHandler:: cacheResponse(): file(s) are cached')
            print('---------------------------------------------------------------')

            try:
                CacheHandler.__updateLookup('ADD', cacheFileNameFH, encoding, numFiles=index, expiry=expiry)
            except Exception as e:
                raise e
        else: # do not cache response
            print('-------------------------')
            print('CacheHandler:: not cached')
            print('-------------------------')

    @staticmethod
    def fetchResponses(rqp): # fetch all related responses, return list of response packets (not raw)
        if rqp.getMethod().lower() == 'get':
            cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half, splitted is useless here

            try:
                CacheHandler.lookupTableRWLock.acquire()
                with open('cache_lookup_table.json', 'r') as table:
                    entries = json.load(table)
                CacheHandler.lookupTableRWLock.release()
            except Exception as e: # unable to open, meaning no such table, thus no cache
                CacheHandler.lookupTableRWLock.release()
                return (None, None)

            idx = CacheHandler.__entryExists(cacheFileNameFH, entries) # check cache entry
            if idx == -1: # no entry of such file exists
                return (None, None)

            print('-----------------------------------')
            print('CacheHandler:: cache response found')
            print('-----------------------------------')

            expiry = entries[idx]['expiry']
            print('CacheHandler:: fetchResponses: expiry: ' + expiry)

            encodings = rqp.getHeaderInfo('accept-encoding')
            if encodings == 'nil':
                encodings = ['*']
            encodingsSplitted = encodings.split(',')
            for i in range(len(encodingsSplitted)):
                encodingsSplitted[i] = encodingsSplitted[i].strip()

            for encoding in encodingsSplitted:
                print('CacheHandler:: fetchResponses: in loop: ' + encoding)
                if encoding == '*': # accept any encoding
                    for encoding in entries[idx]: # loop through key value pairs for the entry
                        if encoding == 'cacheFileNameFH' or encoding == 'expiry': # this is not an encoding key-value pair, continue
                            continue
                        if entries[idx][encoding] != 0: # any one encoding that cached file is not 0, including 'nil'
                            numFiles = entries[idx][encoding]
                            rsps = [] # list of response packets
                            for i in range(1, numFiles + 1):
                                try:
                                    with open(CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i), 'rb') as responseFile:
                                        responseRaw = responseFile.read()
                                    try:
                                        rsps.append(ResponsePacket.parsePacket(responseRaw))
                                    except TypeError as e:
                                        rsps.append(responseRaw)
                                except Exception as e:
                                    raise e
                            print('----------------------------------------')
                            print('CacheHandler:: returning cache response:')
                            print('----------------------------------------')
                            return (rsps, expiry)
                    raise Exception('could not find entry that should be present')

                if entries[idx][encoding] != 0: # encoding specified is not '*'
                    print('CacheHandler:: fetchResponses: found matching encoding: ' + encoding)
                    numFiles = int(entries[idx][encoding])
                    rsps = []
                    for i in range(1, numFiles + 1):
                        try:
                            with open(CacheHandler.cacheFileDirectory + cacheFileNameFH+ ', ' + encoding + ', ' + str(i), 'rb') as responseFile:
                                responseRaw = responseFile.read()
                            try:
                                rsps.append(ResponsePacket.parsePacket(responseRaw))
                            except TypeError as e:
                                rsps.append(responseRaw)
                        except Exception as e:
                            raise Exception('could not find entry that should be present')

                    print('----------------------------------------')
                    print('CacheHandler:: returning cache response:')
                    print('----------------------------------------')
                    return (rsps, expiry)
            return (None, None)
        else: # fetching from cache only applies to GET method
            return (None, None)

    @staticmethod
    def deleteFromCache(rqp): # get number of files cached, delete them all
        cacheFileNameFH, cacheFileNameSplitted = CacheHandler.__getCacheFileNameFH(rqp) # cache response file name first half, splitted is useless here

        try:
            CacheHandler.lookupTableRWLock.acquire()
            with open('cache_lookup_table.json', 'r') as table:
                entries = json.load(table)
            CacheHandler.lookupTableRWLock.release()
        except Exception as e: # unable to open, meaning no such table, thus no cache
            CacheHandler.lookupTableRWLock.release()
            print('CacheHandler:: deleteFromCache: attempted to delete non-existing file')
            raise e

        idx = CacheHandler.__entryExists(cacheFileNameFH, entries)
        if idx != -1:
            for encoding in entries[idx]: # delete every encoding for the file name
                if encoding == 'cacheFileNameFH' or encoding == 'expiry': # not encodings
                    continue
                numFiles = entries[idx][encoding] # number of files stored for this encoded file
                if numFiles == '0':
                    continue
                for i in range(1, int(numFiles) + 1):
                    cacheFileName = CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i)
                    try:
                        os.remove(cacheFileName)
                    except Exception as e:
                        print('CacheHandler:: deleteFromCache: FH: ' + cacheFileNameFH)
                        raise Exception('CacheHandler:: deleteFromCache: lookup table and data mismatch -> Corruption detected')
            try:
                CacheHandler.__updateLookup('DEL', cacheFileNameFH) # delete entire entry, because all encodings are deleted
            except Exception as e:
                raise e
        else:
            pass # nothing to delete

    @staticmethod
    def __updateLookup(method, cacheFileNameFH, encoding='', numFiles=1, expiry='nil'):
        '''
        ADD: add record/ entry to lookup table
        DEL: delete record/ entry from lookup table, ignores encoding, numFiles
        '''
        CacheHandler.lookupTableRWLock.acquire()

        if CacheHandler.origin is None:
            CacheHandler.origin = os.getcwd()

        try:
            with open('cache_lookup_table.json', 'r') as table:
                entries = json.load(table)
            idx = CacheHandler.__entryExists(cacheFileNameFH, entries)
        except FileNotFoundError as e: # first write to lookup table
            entries = [] # create new entry list
            idx = -1 # no previous entry found
        except Exception as e:
            CacheHandler.lookupTableRWLock.release()
            raise e

        if method == 'ADD':
            if idx == -1: # no existing entry found
                newEntry = CacheHandler.__generateJSON(cacheFileNameFH) # create new entry
                try:
                    newEntry.update({encoding : numFiles})
                    if expiry != 'nil':
                        newEntry.update({'expiry' : expiry})
                except Exception as e:
                    CacheHandler.lookupTableRWLock.release()
                    raise e
                entries.append(newEntry)
            else: # entry found
                try:
                    entries[idx].update({encoding : numFiles})
                    if expiry != 'nil':
                        entries[idx].update({'expiry' : expiry})
                except Exception as e:
                    CacheHandler.lookupTableRWLock.release()
                    raise e

        elif method == 'DEL':
            if idx == -1: # something wrong
                CacheHandler.lookupTableRWLock.release()
                raise Exception('CacheHandler:: __updateLookup(): attempted to delete non-existing entry')
            else:
                del entries[idx] # delete entire entry
        else:
            CacheHandler.lookupTableRWLock.release()
            raise Exception('CacheHandler:: __updateLookup(): invalid method: ' + method)

        # replace lookup table
        try:
            os.remove('cache_lookup_table.json') # delete if exists
        except FileNotFoundError as e: # originally no such file
            pass # no deletion if not found
        except Exception as e: # raise exception for other exceptions
            CacheHandler.lookupTableRWLock.release()
            raise e

        with open(CacheHandler.origin + '/cache_lookup_table.json', 'w') as table: # write new lookup table
            json.dump(entries, table, indent=4)

        CacheHandler.lookupTableRWLock.release()

    @staticmethod
    def __entryExists(cacheFileNameFH, entries=[]):
        if entries == []:
            try:
                CacheHandler.lookupTableRWLock.acquire()
                with open('cache_lookup_table.json', 'r') as table:
                    entries = json.load(table)
                CacheHandler.lookupTableRWLock.release()
            except FileNotFoundError as e: # unable to open, meaning no such table, thus no cache
                CacheHandler.lookupTableRWLock.release()
                return -1

        for idx in range(len(entries)):
            if entries[idx]['cacheFileNameFH'] == cacheFileNameFH:
                return idx

        return -1

    @staticmethod
    def __generateJSON(cacheFileNameFH):
        object = {
            "cacheFileNameFH" : cacheFileNameFH,
            "expiry" : "nil",
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
