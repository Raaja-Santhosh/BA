import requests
import re
url = 'https://data.4tu.nl/articles/dataset/BPI_Challenge_2012/12689204'
headers = {'User-Agent': 'Mozilla/5.0'}
html = requests.get(url, headers=headers).text
links = re.findall(r'href=[\'"]([^\'"]*?)[\'"]', html)
download_links = [l for l in links if 'ndownloader/files/' in l]
print("Found download links:", download_links)
