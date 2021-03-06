import json # for cache_lookup_table
import os # remove file os.remove(filename)
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
from TimeComparator import TimeComparator
import threading
import PrimeFinder


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
    '''

    origin = '' # initialized by proxy_main
    cacheFileDirectory = 'cache_responses/'
    lookupTable = None
    lookupTableLock = threading.Semaphore() # require sequential read/ write, otherwise may occur corruption/ data loss
    chdirLock = threading.Semaphore()
    hashedLocks = None
    NUMSLOTS = 0

    @staticmethod
    def initHashedLocks(numThreads):
        '''
        called by Proxy object
        based on number of Threads, create sufficient amount of locks for cache file IO
        '''
        CacheHandler.NUMSLOTS = PrimeFinder.findNextPrime(numThreads * 2)
        CacheHandler.hashedLocks = []
        for i in range(CacheHandler.NUMSLOTS):
            CacheHandler.hashedLocks.append(threading.Semaphore())

    @staticmethod
    def exitRoutine():
        '''
        called by Proxy
        clean up lookup table and write to file
        delete entries with all 0s in encoding
        delete directories with no files, using DFS
        '''
        if os.path.isdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory):
            CacheHandler.deleteUnusedPaths(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
        CacheHandler.purgeLookupTable()
        CacheHandler.writeLookupTableToFile()

    @staticmethod
    def deleteUnusedPaths(origin, releaseChdirLock=True):
        '''
        called by exitRoutine()
        recursively delete directories that contains 0 file
        ie the previously stored cache has already been deleted,
        so there is no need to keep that directory
        implemented using DFS, should be replaceable by os.removedirs()
        '''

        if CacheHandler.origin == '':
            CacheHandler.origin = os.getcwd()

        if releaseChdirLock: # lock needs to be acquired
            CacheHandler.chdirLock.acquire()

        for d in os.listdir(origin):
            if os.path.isdir(d):
                os.chdir(d)
                deleteUnusedPaths(os.getcwd(), releaseChdirLock=False)
                os.chdir('..')
                if len(os.listdir(d)) == 0:
                    os.rmdir(d)

        if releaseChdirLock:
            CacheHandler.chdirLock.release()

    @staticmethod
    def purgeLookupTable():
        '''
        called by exitRoutine()
        if an entry doesn't have any file stored (all entry[encoding] == 0),
        then remove the entry to save space
        '''
        CacheHandler.lookupTableLock.acquire()

        if CacheHandler.lookupTable is None or len(CacheHandler.lookupTable) == 0:
            CacheHandler.lookupTableLock.release()
            return

        purgedTable = []
        for entry in CacheHandler.lookupTable:
            entryFound = False
            for encoding in entry:
                if encoding == 'cacheFileNameFH' or encoding == 'expiry': # this is not an encoding key-value pair, continue
                    continue
                elif entry[encoding] != 0:
                    entryFound = True
                    break
            if entryFound:
                purgedTable.append(entry)
        CacheHandler.lookupTable = purgedTable

        CacheHandler.lookupTableLock.release()

    @staticmethod
    def writeLookupTableToFile():
        '''
        called by exitRoutine()
        when proxy program quits, write the lookup table back to cache_lookup_table.json
        '''
        if CacheHandler.origin == '':
            CacheHandler.origin = os.getcwd()

        CacheHandler.lookupTableLock.acquire()
        if CacheHandler.lookupTable is not None: # directly access instead of calling __getLookupTable
            with open(CacheHandler.origin + '/' + 'cache_lookup_table.json', 'w') as table: # write new lookup table
                json.dump(CacheHandler.lookupTable, table, indent=4)
        CacheHandler.lookupTableLock.release()
        print('cache table written to file')

    def __init__(self, rqp, rsps=None):
        '''
        origin:                     @static
                                    project root directory

        cacheFileDirectory:         @static
                                    cache responses storage directory

        lookupTable:                @static

        lookupTableLock:            @static

        chdirLock:                  @static

        hashedLocks:                @static

        NUMSLOTS:                   @static

        holdingLookupTableLock:

        holdingChdirLock:

        holdingHashedLock:

        rqp:                        request packet

        rsps:                       response packets
        '''
        self.holdingLookupTableLock = False
        self.holdingChdirLock = False
        self.holdingHashedLock = -1
        self.rqp = rqp
        self.rsps = rsps

    def cacheResponses(self):
        '''
        handle cache request
        determine if the responses should be cached/ updated in cache file
        if no, then simply return
        if yes,
            write the responses to cached_responses/ directory,
            with title: `${FH}, ${encoding}, ${order}`,
            with raw response as payload
            update lookup file correspondingly

        assumed request method is GET
        cache response whenever no-store, private are not specified in cache-control
        because all cached response will be revalidated by proxy anyway
        '''
        if self.rsps is None:
            return

        cacheOption = self.rsps[0].getHeaderInfo('cache-control').lower()
        cacheOptionSplitted = cacheOption.split(',')
        for i in range(len(cacheOptionSplitted)):
            cacheOptionSplitted[i] = cacheOptionSplitted[i].strip()

        if 'no-store' not in cacheOptionSplitted and 'private' not in cacheOptionSplitted: # specified as public or the header field is not present
            cacheFileNameFH, cacheFileNameSplitted = self.__getCacheFileNameFH() # cache response file name first half

            if '' in cacheFileNameSplitted or len(cacheFileNameFH) > 255:
                return

            # starting from this point, the entry should be chacheable
            CacheHandler.lookupTableLock.acquire() # put deleteFromCache in this critical section to make sure the file is not being manipulated
            self.holdingLookupTableLock = True
            idx = self.__entryExists(cacheFileNameFH, releaseLookupTableLock=False) # remove previous cache files
            if idx != -1: # entry found, delete file
                try:
                    self.deleteFromCache(releaseLookupTableLock=False)
                except Exception as e:
                    raise e
            CacheHandler.lookupTableLock.release()
            self.holdingLookupTableLock = False

            encoding = self.rsps[0].getHeaderInfo('content-encoding')
            expiry = self.__getExpiry(cacheOptionSplitted)

            self.__createDirectories(cacheFileNameSplitted)

            fileHash = self.__getFileHash(cacheFileNameFH)
            CacheHandler.hashedLocks[fileHash].acquire()
            self.holdingHashedLock = fileHash

            index = 0
            for rsp in self.rsps: # cache each responses
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
                except Exception as e:
                    CacheHandler.lookupTableLock.release()
                    self.holdingLookupTableLock = False

                    CacheHandler.hashedLocks[fileHash].release()
                    self.holdingHashedLock = -1

                    raise e

            CacheHandler.lookupTableLock.acquire() # add file operation, make sure lookup table is not modified
            self.holdingLookupTableLock = True
            try:
                self.__updateLookup('ADD', cacheFileNameFH, encoding, numFiles=index, expiry=expiry)
            except Exception as e:
                CacheHandler.lookupTableLock.release()
                self.holdingLookupTableLock = False
                raise e

            CacheHandler.hashedLocks[fileHash].release()
            self.holdingHashedLock = -1

    def fetchResponses(self): # fetch all related responses, return list of response packets (not raw)
        '''
        handle fetch request
        returns list of response packets fetched and expiration time
        if nothing fetched, return (None, None)
        '''
        if self.rqp.getMethod().lower() == 'get':
            cacheFileNameFH, cacheFileNameSplitted = self.__getCacheFileNameFH() # cache response file name first half, splitted is useless here

            CacheHandler.lookupTableLock.acquire()
            self.holdingLookupTableLock = True

            idx = self.__entryExists(cacheFileNameFH, releaseLookupTableLock=False) # get index of entry, -1 if none; no need to lock entire function since the index will not change until Proxy closes
            if idx == -1: # no entry of such file exists
                CacheHandler.lookupTableLock.release()
                self.holdingLookupTableLock = False
                return (None, None)

            entry = self.__getLookupTable()[idx]

            CacheHandler.lookupTableLock.release()
            self.holdingLookupTableLock = False

            expiry = entry['expiry']
            print('CacheHandler:: fetchResponses: expiry: ' + expiry)

            encodings = self.rqp.getHeaderInfo('accept-encoding')
            if encodings == 'nil':
                encodings = ['*']
            encodingsSplitted = encodings.split(',')
            for i in range(len(encodingsSplitted)):
                encodingsSplitted[i] = encodingsSplitted[i].strip()

            for encoding in encodingsSplitted:
                print('CacheHandler:: fetchResponses: in loop: ' + encoding)
                if encoding == '*': # accept any encoding
                    for encoding in entry: # loop through key value pairs for the entry
                        if encoding == 'cacheFileNameFH' or encoding == 'expiry': # this is not an encoding key-value pair, continue
                            continue
                        if entry[encoding] != 0: # any one encoding that cached file is not 0, including 'nil'
                            numFiles = entry[encoding]
                            rsps = [] # list of response packets

                            fileHash = self.__getFileHash(cacheFileNameFH)
                            CacheHandler.hashedLocks[fileHash].acquire()
                            self.holdingHashedLock = fileHash

                            for i in range(1, numFiles + 1):
                                try:
                                    with open(CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i), 'rb') as responseFile:
                                        responseRaw = responseFile.read()
                                    try:
                                        rsps.append(ResponsePacket.parsePacket(responseRaw))
                                    except TypeError as e:
                                        rsps.append(responseRaw)
                                except Exception as e:
                                    CacheHandler.hashedLocks[fileHash].release()
                                    self.holdingHashedLock = -1
                                    print('could not find entry that should be present')
                                    raise e

                            CacheHandler.hashedLocks[fileHash].release()
                            self.holdingHashedLock = -1

                            return (rsps, expiry)
                    raise Exception('could not find entry that should be present')

                if entry[encoding] != 0: # encoding specified is not '*'
                    numFiles = int(entry[encoding])
                    rsps = []

                    fileHash = self.__getFileHash(cacheFileNameFH)
                    CacheHandler.hashedLocks[fileHash].acquire()
                    self.holdingHashedLock = fileHash

                    for i in range(1, numFiles + 1):
                        try:
                            with open(CacheHandler.cacheFileDirectory + cacheFileNameFH+ ', ' + encoding + ', ' + str(i), 'rb') as responseFile:
                                responseRaw = responseFile.read()
                            try:
                                rsps.append(ResponsePacket.parsePacket(responseRaw))
                            except TypeError as e:
                                rsps.append(responseRaw)
                        except Exception as e:
                            CacheHandler.hashedLocks[fileHash].release()
                            self.holdingHashedLock = -1
                            # raise Exception('could not find entry that should be present')
                            print('could not find entry that should be present')
                            return (None, None)
                            # raise e

                    CacheHandler.hashedLocks[fileHash].release()
                    self.holdingHashedLock = -1
                    return (rsps, expiry)
            return (None, None)
        else: # fetching from cache only applies to GET method
            return (None, None)

    def deleteFromCache(self, releaseLookupTableLock=True): # get number of files cached, delete them all
        '''
        delete all cache responses matching file url
        update lookup file correspondingly
        '''
        cacheFileNameFH, cacheFileNameSplitted = self.__getCacheFileNameFH() # cache response file name first half, splitted is useless here

        if not self.holdingLookupTableLock:
            CacheHandler.lookupTableLock.acquire()
            self.holdingLookupTableLock = True
            releaseLookupTableLock = True

        idx = self.__entryExists(cacheFileNameFH, releaseLookupTableLock=False)
        if idx == -1:
            if releaseLookupTableLock:
                CacheHandler.lookupTableLock.release()
                self.holdingLookupTableLock = False
            return
        entry = self.__getLookupTable()[idx]

        if releaseLookupTableLock:
            CacheHandler.lookupTableLock.release()
            self.holdingLookupTableLock = False

        for encoding in entry: # delete every encoding for the file name
            if encoding == 'cacheFileNameFH' or encoding == 'expiry': # not encodings
                continue
            numFiles = entry[encoding] # number of files stored for this encoded file
            if numFiles == '0':
                continue

            fileHash = self.__getFileHash(cacheFileNameFH)
            CacheHandler.hashedLocks[fileHash].acquire()
            self.holdingHashedLock = fileHash

            for i in range(1, int(numFiles) + 1):
                cacheFileName = CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory + cacheFileNameFH + ', ' + encoding + ', ' + str(i)
                try:
                    os.remove(cacheFileName)
                except Exception as e:
                    CacheHandler.hashedLocks[fileHash].release()
                    self.holdingHashedLock = -1
                    raise Exception('CacheHandler:: deleteFromCache: lookup table and data mismatch -> Corruption detected')

            CacheHandler.hashedLocks[fileHash].release()
            self.holdingHashedLock = -1
        try:
            if not self.holdingLookupTableLock:
                CacheHandler.lookupTableLock.acquire()
                self.holdingLookupTableLock = True

            self.__updateLookup('DEL', cacheFileNameFH) # delete entire entry, because all encodings are deleted

            if releaseLookupTableLock:
                CacheHandler.lookupTableLock.release()
                self.holdingLookupTableLock = False
        except Exception as e:
            raise e

    def __updateLookup(self, method, cacheFileNameFH, encoding='', numFiles=1, expiry='nil', releaseLookupTableLock=True):
        '''
        update lookup table according to method
        ADD: add record/ entry to lookup table
        DEL: delete record/ entry from lookup table, ignores encoding, numFiles
        '''
        if not self.holdingLookupTableLock:
            CacheHandler.lookupTableLock.acquire()
            self.holdingLookupTableLock = True
            releaseLookupTableLock = True

        if CacheHandler.origin is None: # unlikely
            CacheHandler.origin = os.getcwd()

        idx = self.__entryExists(cacheFileNameFH, releaseLookupTableLock=False)


        if method == 'ADD':
            if idx == -1: # no existing entry found
                newEntry = self.__generateJSON(cacheFileNameFH) # create new entry
                try:
                    newEntry.update({encoding : numFiles})
                    if expiry != 'nil':
                        newEntry.update({'expiry' : expiry})
                except Exception as e:
                    if releaseLookupTableLock:
                        CacheHandler.lookupTableLock.release()
                        releaseLookupTableLock = False
                    raise e
                self.__getLookupTable().append(newEntry)
            else: # entry found
                try:
                    entry = self.__getLookupTable()[idx]
                    entry.update({encoding : numFiles})
                    if expiry != 'nil':
                        entry.update({'expiry' : expiry})
                    CacheHandler.lookupTable[idx] = entry
                except Exception as e:
                    if releaseLookupTableLock:
                        CacheHandler.lookupTableLock.release()
                        releaseLookupTableLock = False
                    raise e

        elif method == 'DEL':
            if idx == -1: # something wrong
                if releaseLookupTableLock:
                    CacheHandler.lookupTableLock.release()
                    releaseLookupTableLock = False
                raise Exception('CacheHandler:: __updateLookup(): attempted to delete non-existing entry')
            else:
                entry = self.__getLookupTable()[idx]
                for encoding in entry:
                    if encoding == 'cacheFileNameFH' or encoding == 'expiry': # this is not an encoding key-value pair, continue
                        continue
                    entry.update({encoding : 0})
                CacheHandler.lookupTable[idx] = entry
        else:
            if releaseLookupTableLock:
                CacheHandler.lookupTableLock.release()
                releaseLookupTableLock = False
            raise Exception('CacheHandler:: __updateLookup(): invalid method: ' + method)

        if releaseLookupTableLock:
            CacheHandler.lookupTableLock.release()
            releaseLookupTableLock = False

    def __entryExists(self, cacheFileNameFH, releaseLookupTableLock=True):
        '''
        check if an entry with name: cacheFileNameFH exists
        if yes then return the index of entry
        else return -1
        '''
        if not self.holdingLookupTableLock:
            CacheHandler.lookupTableLock.acquire()
            self.holdingLookupTableLock = True

        entries = self.__getLookupTable()

        if releaseLookupTableLock:
            CacheHandler.lookupTableLock.release()
            self.holdingLookupTableLock = False

        for idx in range(len(entries)):
            if entries[idx]['cacheFileNameFH'] == cacheFileNameFH:
                return idx

        return -1

    def __generateJSON(self, cacheFileNameFH):
        '''
        generate template for entry with name: cacheFileNameFH
        '''
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

    def __getCacheFileNameFH(self):
        '''
        from rqp, generate entry name
        '''
        cacheFileNameSplitted = [self.rqp.getHostName()]
        if self.rqp.getFilePath() != '/':
            filePathSplitted = self.rqp.getFilePath()[1:].split('/')
            for subPath in filePathSplitted:
                cacheFileNameSplitted.append(subPath)
        cacheFileNameFH = ''
        for subpart in cacheFileNameSplitted:
            cacheFileNameFH += subpart + '/'
        return cacheFileNameFH[:-1], cacheFileNameSplitted

    def __getExpiry(self, cacheOptionSplitted):
        '''
        get the expiration time from cacheOptionSplitted
        calculated from current time
        '''
        expiry = 'nil' # default expiration is nil

        for option in cacheOptionSplitted:
            if option[0:len('max-age')].lower() == 'max-age':
                secondStr = option.split('=')[1]
                responseDate = self.rsps[0].getHeaderInfo('date')
                if responseDate == 'nil': # date of retrieval not specified
                    expiry = (TimeComparator.currentTime() + secondStr).toString() # use current time
                else:
                    expiry = (TimeComparator(responseDate) + secondStr).toString()
                break

        for option in cacheOptionSplitted: # overwrite expiry from max-age with s-maxage
            if option[0:len('s-maxage')].lower() == 's-maxage':
                secondStr = option.split('=')[1]
                responseDate = self.rsps[0].getHeaderInfo('date')
                if responseDate == 'nil':
                    expiry = (TimeComparator.currentTime() + secondStr).toString()
                else:
                    expiry = (TimeComparator(responseDate) + secondStr).toString()
                break

        for option in cacheOptionSplitted: # don't do anything on expiry if must revalidate
            if option == 'must-revalidate' or option == 'proxy-revalidate' or option == 'no-cache':
                expiry = 'nil' # overwrite expiry back to 'nil'
                break

        return expiry

    def __createDirectories(self, cacheFileNameSplitted):
        '''
        called by cacheResponses
        creates necessary directories to store necessary files
        '''
        if CacheHandler.origin is None: # unlikely
            CacheHandler.origin = os.getcwd()

        completeDirectory = CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory + ''.join(cacheFileNameSplitted[:-1])
        if not os.path.exists(completeDirectory):
            CacheHandler.chdirLock.acquire()
            self.holdingChdirLock = True
            try: # ensure cache directory exists
                os.chdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
            except FileNotFoundError as e:
                os.mkdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
                os.chdir(CacheHandler.origin + '/' + CacheHandler.cacheFileDirectory)
            for idx in range(len(cacheFileNameSplitted) - 1): # ensure layers of directory exists
                try:
                    os.chdir(cacheFileNameSplitted[idx])
                except FileNotFoundError as e:
                    os.mkdir(cacheFileNameSplitted[idx])
                    os.chdir(cacheFileNameSplitted[idx])
            os.chdir(CacheHandler.origin) # go back to project root
            CacheHandler.chdirLock.release()
            self.holdingChdirLock = False

    def __getFileHash(self, cacheFileNameFH):
        '''
        hash function for obtaining a lock before writing/ deleting a cache file
        '''
        return abs(hash(cacheFileNameFH))%CacheHandler.NUMSLOTS

    def __getLookupTable(self, releaseLookupTableLock=True):
        '''
        returns lookupTable

        if CacheHandler.lookupTable is None,
            open file and fetch, put to variable

            if file not found/ has error, reset as empty list
        '''
        if not self.holdingLookupTableLock:
            CacheHandler.lookupTableLock.acquire()
            self.holdingLookupTableLock = True
            releaseLookupTableLock = True

        if CacheHandler.lookupTable is None:
            try:
                with open('cache_lookup_table.json', 'r') as table:
                    CacheHandler.lookupTable = json.load(table)
            except Exception as e:
                CacheHandler.lookupTable = []

        if releaseLookupTableLock:
            CacheHandler.lookupTableLock.release()
            self.holdingLookupTableLock = False

        return CacheHandler.lookupTable



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
    '''

    def __init__(self, option, rqp, rsps):
        '''
        __option:               'ADD' / 'DEL'

        __rqp:                  request packet

        __rsps:                 response packets
        '''
        threading.Thread.__init__(self)
        self.__option = option
        self.cacher = CacheHandler(rqp, rsps)

    def run(self):
        '''
        'ADD': call CacheHandler.cacheResponse(rqp, rsp)
        'DEL': call CacheHandler.deleteFromCache(rqp)
        '''
        if self.__option == 'ADD':
            self.cacher.cacheResponses()
        elif self.__option == 'DEL':
            self.cacher.deleteFromCache()
