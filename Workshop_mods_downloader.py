import urllib3, time, re, io, sys, os, json
import concurrent.futures
import threading
from collections import OrderedDict
from bs4 import BeautifulSoup as bs4

Ddir = ""  # Ddir = "Downloaded" . Directory to downloads. One for all mod pages. leave it blank to autocreate dirs for different mod pages
StartUrl = 'https://steamcommunity.com/workshop/browse/?appid=445220&requiredtags%5B0%5D=Mod&p=1&actualsort=mostrecent&browsesort=mostrecent'

steamheaders = OrderedDict({
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0'
    })

dlheaders = OrderedDict({
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Accept-Encoding': 'deflate, gzip',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0'
    })

steamModPage = "https://steamcommunity.com/sharedfiles/filedetails/?id="
requesturl = "https://backend-02-prd.steamworkshopdownloader.io/api/download/request"
statusurl = "https://backend-02-prd.steamworkshopdownloader.io/api/download/status"
downloadurl = "https://backend-02-prd.steamworkshopdownloader.io/api/download/transmit?uuid="

thrNum = 0
thrNumMax = 0
moddlcounter = 0
errcounter = 0
iCnt = 0
maxTries = 5  # max thread tries to connect to steamworkshopdownloader.io


def modDownload(modId, ntry, thrNum):
    global moddlcounter, errcounter, iCnt, maxTries

    if ntry > maxTries:
        return

    http = urllib3.PoolManager()
    data = '{"publishedFileId":' + str(modId) + ',"collectionId":null,"extract":false,"hidden":false,"direct":false,"autodownload":false}'

    try:
        r = http.request('POST', requesturl, headers=dlheaders, body=data)
    except:
        saveerror('ID POST error: ' + str(thrNum) + ':' + str(ntry), str(modId))
        errcounter += 1
        modDownload(modId, ntry+1, thrNum)
        return
    else:

        try:
            uuid = json.loads(r.data.decode('utf-8'))['uuid']
        except:
            saveerror('No UUID :: ' + str(thrNum) + ':' + str(ntry), str(modId))
            errcounter += 1
            modDownload(modId, ntry+1, thrNum)
            return

        k = 0

        while True:
            try:
                r = http.request('POST', statusurl, headers=dlheaders, body='{"uuids":["' + uuid + '"]}')
                downstatus = json.loads(r.data.decode('utf-8'))[uuid]['status']
            except:
                saveerror('Status POST error: ' + str(thrNum) + ':' + str(ntry), str(modId))
                errcounter += 1
                modDownload(modId, ntry+1, thrNum)
                return
            else:
                if downstatus == "prepared":
                    break

            time.sleep(1)
            k += 1

            if not k < 200:  # max timeout to wait till mod will be prepared to download
                saveerror('Max timeout achieved: ' + str(k) + 's', str(modId))
                errcounter += 1
                return

        try:
            r = http.request('GET', downloadurl + uuid, headers=dlheaders)
            filename = r.headers['Content-Disposition'][21:]
        except:
            saveerror('File get error: ' + str(thrNum) + ':' + str(ntry), str(modId))
            errcounter += 1
            modDownload(modId, ntry+1, thrNum)
            return
        else:
            moddir = Ddir + '\\' + filename.split('.')[0]
            filesave(moddir, filename, 'wb', r.data, thrNum)
            moddlcounter += 1

            try:
                r = http.request('GET', steamModPage + modId, headers=steamheaders)
            except:
                saveerror('Mod Description page Error :: ' + str(thrNum) + ':' + str(ntry), str(modId))
                errcounter += 1
            else:
                soup = bs4(r.data, 'html.parser')
                modName = soup.find('div', class_="workshopItemTitle").text

                if not modName:
                    modName = filename.split('.')[0]

                modName = re.sub(r'[\\/\:*"<>\|\.£]', '_', modName)
                filesave(moddir, modName+'.html', 'wb', r.data)

                imgSet = soup.select('div.highlight_strip_item.highlight_strip_screenshot > img')

                if not imgSet:
                    imgSet = soup.select('img#previewImage')

                j = 1

                for img in imgSet:
                    imgUrl = re.search(r'.*\/(?=\?)', img.get('src'))[0]

                    try:
                        r = http.request('GET', imgUrl, headers=steamheaders)
                    except:
                        saveerror('Unable to get image :: ' + str(thrNum) + ':' + str(ntry), str(modId))
                        errcounter += 1
                    else:
                        filesave(moddir, modName + '_' + str(j) + '.jpeg', 'wb', r.data)

                    j += 1
                    iCnt += 1


def saveerror(data, Id):
    global lock
    with lock:
        currtime = time.strftime("%H:%M:%S", time.localtime())
        filesave('', 'errors.txt', 'a', currtime + ' : ' + 'ModId : ' + Id + ' === ' + data + '\n')


def filesave(dirName, file, arg, data, s=None):
    global thrNumMax
    global lock

    dn = u'\\\\?\\' + os.path.dirname(sys.argv[0])

    if dirName:
        dn += '\\' + dirName

    if not os.path.exists(dn):
        print('makedir: ' + str(dirName))
        try:
            os.mkdir(dn, mode=0o777)
        except:
            with lock:
                with open('errors.txt', 'a') as f:
                    f.write('error mkdir : ' + str(dn))
                    f.write('args: ' + 'dirName: ' + str(dirName) + ' file: ' + str(file) + ' arg: ' + str(arg) + ' s:' + str(s))
                    f.close()

    if file and arg and data:
        try:
            with open(dn + '\\' + file, arg) as f:
                if s:
                    print(str(s) + ' of ' + str(thrNumMax) + '  ::  ' + 'writing file: ' + str(file))
                else:
                    print('writing file: ' + str(file))
                f.write(data)
                f.close()
        except:
            with lock:
                with open('errors.txt', 'a') as f:
                    f.write('error writing file : ' + str(dn) + ' : ' + str(file))
                    f.write('args: ' + 'dirName: ' + str(dirName) + ' file: ' + str(file) + ' arg: ' + str(arg) + ' s:' + str(s))
                    f.close()


def prepareToDownload(url, numPages):
    global errcounter, thrNumMax

    http = urllib3.PoolManager()
    modIds = []
    start_time = time.time()

    for pageNum in range(1, int(numPages)+1):
        if not re.search(r'p=\d*', url):
            print(re.search(r'p=\d*', url))
            url = url + '&p=1'
        url = re.sub(r'(?<=p=)\d*', str(pageNum), url)

        try:
            r = http.request('GET', url, headers=steamheaders)
        except:
            saveerror(url, 'SteamPageOpen Error ' + str(url))
            errcounter += 1
            return

        soup = bs4(r.data, 'html.parser')
        links_list = soup.select("div.workshopItem > a.ugc")

        for link in links_list:
            modIds.append(re.search(r'(?<=id=)\d*', link.get('href'))[0])

        print('Total mods to download  ::  ' + str(len(modIds)) + '\nIn  ::  {:.2f}s'.format(time.time()-start_time) + '\n')

    l = 0
    thrNumMax = len(modIds)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        for modId in modIds:
            l += 1
            futures.append(executor.submit(modDownload, modId=modId, ntry=1, thrNum=l))

        for future in concurrent.futures.as_completed(futures):
            pass


def GetInitialPage(url):
    global Ddir

    http = urllib3.PoolManager()

    try:
        r = http.request('GET', url, headers=steamheaders)
    except:
        saveerror(url, 'SteamInitPage')
        print('GetInitPage error')
        return

    try:
        soup = bs4(r.data, 'html.parser')
    except:
        saveerror(url, 'Wrong InitPage')
        print('~~~ Wrong Initial Page ~~~')
        return

    if not Ddir:
        try:
            Ddir = soup.title.string
            Ddir = re.sub(r'[\\/\:*"<>\|\.£]', '_', Ddir)
        except:
            saveerror(str(Ddir), 'Wrong dir name')
            return

    filesave(Ddir, None, None, None)
    page = soup.select('div.workshopBrowsePagingControls :nth-last-child(2)')

    try:
        print(page[0].get('href'))
        numPages = re.search(r'p=(\d*)', page[0].get('href'))[1]
        print(numPages)
    except IndexError:
        numPages = '1'

    prepareToDownload(url, numPages)
    print('\nDONE! ::: ' + url)
    filesave('', 'errors.txt', 'a', 'DONE! ::: ' + url)
    print('\nDownloaded ::: ' + str(moddlcounter) + '\nErrors ::: ' + str(errcounter) + '\nImage downloaded ::: ' + str(iCnt))
    filesave('', 'errors.txt', 'a', 'Downloaded ::: ' + str(moddlcounter) + '\nErrors ::: ' + str(errcounter) + '\nImages downloaded ::: ' + str(iCnt))


if __name__ == "__main__":
    lock = threading.Lock()

    try:
        with open('links.txt', 'r') as f:
            lnks = f.readlines()
            f.close
    except:
        GetInitialPage(StartUrl)
        links_test(StartUrl)
    else:
        lnks = [l.strip() for l in lnks if str(l).strip()]

        if lnks:
            for l in lnks:
                filesave('', 'errors.txt', 'a', '\n\n' + l)
                GetInitialPage(l)
        else:
            GetInitialPage(StartUrl)
