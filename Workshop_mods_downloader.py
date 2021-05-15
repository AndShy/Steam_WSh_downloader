import urllib3, time, re, io, sys, os, json
import _thread as thread
from collections import OrderedDict
from bs4 import BeautifulSoup as bs4

# Ddir = "Downloaded"
Ddir = ""
StartUrl = 'https://steamcommunity.com/workshop/browse/?appid=445220&requiredtags%5B0%5D=Mod&p=1&actualsort=mostrecent&browsesort=mostrecent'

steamheaders = OrderedDict({
    'Host': 'steamcommunity.com',
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

    
def modDownload(thread, modId):
    http = urllib3.PoolManager()
    data = '{"publishedFileId":' + str(modId) + ',"collectionId":null,"extract":false,"hidden":false,"direct":false,"autodownload":false}'
    try:
        r = http.request('POST', requesturl, headers=dlheaders, body=data)
    except:
        saveerror('ID POST error: ' + str(r.status), str(modId))
        return
    else:
        try:
            uuid = json.loads(r.data.decode('utf-8'))['uuid']
        except:
            saveerror('No UUID :: ', str(modId))
            return
        k=0
        while True:
            try:
                r = http.request('POST', statusurl, headers=dlheaders, body='{"uuids":["' + uuid + '"]}')
                downstatus = json.loads(r.data.decode('utf-8'))[uuid]['status']
            except:
                saveerror('Status POST error: ' + str(r.status), str(modId))
                break
            else:
                if downstatus == "prepared":
                    break
            time.sleep(1)
            k += 1
            if not k<60:
                saveerror('Max tryes achieved: ' + str(k), str(modId))
                break
        try:
            r = http.request('GET', downloadurl + uuid, headers=dlheaders)
            filename = r.headers['Content-Disposition'][21:]
        except:
            saveerror('File get error: ' + str(r.status), str(modId))
        else:
            moddir = Ddir + '\\' + filename.split('.')[0]
            filesave(moddir, filename, 'wb', r.data)
            try:
                r = http.request('GET', steamModPage + modId, headers=steamheaders)
            except:
                saveerror('Mod Description page Error :: ' + str(r.status), str(modId))
            else:
                soup = bs4(r.data, 'html.parser')
                modName = soup.find('div', class_="workshopItemTitle").text
                if not modName:
                    modName = filename.split('.')[0]
                modName = re.sub(r'[\\/\:*"<>\|\.£]', '_', modName)
                filesave(moddir, modName+'.html', 'wb', r.data)


def saveerror(data, Id):
    with lock:
        currtime = time.strftime("%H:%M:%S", time.localtime())
        filesave('', 'errors.txt', 'a', currtime + ' : ' + 'ModId : ' + Id + ' === ' + data + '\n')

def filesave(dirName, file, arg, data):
    dn = u'\\\\?\\' + os.path.dirname(sys.argv[0])
    if dirName: dn+= '\\' + dirName
    if not os.path.exists(dn):
        print('makedir: ' + str(dirName))
        os.mkdir(dn, mode = 0o777)
    if file and arg and data:
        with open (dn + '\\' + file, arg) as f:
            print('writing file: ' + str(file))
            f.write(data)
            f.close()
    
def prepareToDownload(url, pageNum):
    http = urllib3.PoolManager()
    try:
        r = http.request('GET', url, headers=steamheaders)
    except:
        saveerror(str(r.status), 'SteamPageOpen Error ' + str(url))
        return
    soup = bs4(r.data, 'html.parser')
    links_list = soup.select("div.workshopItem > a.ugc")
    i = 1
    for link in links_list:
        modId = re.search(r'(?<=id=)\d*', link.get('href'))[0]
        try:
            thread.start_new_thread(modDownload, (i, modId))
            print('starting ModDownload thread : ' + str(i) + ' ModId == ' + str(modId))
        except:
            print('Error starting thread ' + str(i) + ' ModId == ' + str(modId))
        time.sleep(6)
        i+=1

def GetInitialPage(url):
    global Ddir
    http = urllib3.PoolManager()
    try:
        r = http.request('GET', url, headers=steamheaders)
    except:
        saveerror(str(r.status), 'SteamInitPage')
        print('GetInitPage error')
        return
    try:
        soup = bs4(r.data, 'html.parser')
    except:
        saveerror(str(url), 'Wrong InitPage')
        print('~~~ Wrong Initial Page ~~~')
        return
    if not Ddir:
        try:
            Ddir = soup.title.string
            Ddir = re.sub(r'[\\/\:*"<>\|\.£]', '_', Ddir)
        except:
            saveerror(str(Ddir),'Wrong dir name')
            return
    filesave(Ddir,None,None,None)
    page = soup.select('div.workshopBrowsePagingControls :nth-last-child(2)')
    try:
        print(page[0].get('href'))
        numPages = re.search(r'p=(\d*)',page[0].get('href'))[1]
        print(numPages)
    except IndexError:
        numPages = '1'
    for pageNum in range(1, int(numPages)+1):
        if not re.search(r'p=\d*', url):
            print(re.search(r'p=\d*', url))
            url = url + '&p=1'
        prepareToDownload((re.sub(r'(?<=p=)(\d*)', str(pageNum), url)), str(pageNum))
    print('\n DONE! ::: ' + url)
    saveerror(url, 'DONE')


if __name__ == "__main__": 
    global lock

    lock = thread.allocate_lock()
    try:
        with open ('links.txt', 'r') as f:
            lnks = f.readlines()
            f.close
    except:
        GetInitialPage(StartUrl)
        links_test(StartUrl)
    else:
        lnks = [l.strip() for l in lnks if str(l).strip()]
        # print(lnks)
        if lnks:
            for l in lnks:
                GetInitialPage(l)
        else:
            GetInitialPage(StartUrl)