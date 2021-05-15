# Steam Workshop downloader
Steam Workshop downloader through steamworkshopdownloader.io

for win systems (unique filepaths)

usage: 
- in Ddir variable you can specify one directory for all files
- if Ddir empty then script create dir for each game (title from game workshop page)
- write mod pages in file links.txt (1 link per line), otherwise you can specify one in script in StartUrl variable 
- script grabs ALL mods from specified page. i.g., for https://steamcommunity.com/workshop/browse/?appid=445220&requiredtags%5B0%5D=Mod&p=1&actualsort=mostrecent&browsesort=mostrecent it download all 773 mods on 26 pages (atm)
