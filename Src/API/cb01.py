import re
from bs4 import BeautifulSoup,SoupStrainer
from Src.Utilities.info import is_movie,get_info_tmdb,get_info_imdb
from Src.Utilities.convert import get_TMDb_id_from_IMDb_id
from fake_headers import Headers
import Src.Utilities.config as config
from Src.Utilities.loadenv import load_env
from Src.API.extractors.mixdrop import mixdrop
from Src.API.extractors.maxstream import maxstream
from Src.API.extractors.uprot import bypass_uprot
import logging
from Src.Utilities.config import setup_logging
level = config.LEVEL
logger = setup_logging(level)
CB_DOMAIN = config.CB_DOMAIN
CB_PROXY = config.CB_PROXY
MX_PROXY = config.MX_PROXY
Icon = config.Icon
Name = config.Name
proxies = {}
proxies2 = {}
env_vars = load_env()
import random
import json
from Src.Utilities.mfp import build_mfp
if MX_PROXY == "1":
    PROXY_CREDENTIALS = env_vars.get('PROXY_CREDENTIALS')
    proxy_list = json.loads(PROXY_CREDENTIALS)
    proxy = random.choice(proxy_list)
    if proxy == "":
        proxies2 = {}
    else:
        proxies2 = {
            "http": proxy,
            "https": proxy
        }      
if CB_PROXY == "1":
    PROXY_CREDENTIALS = env_vars.get('PROXY_CREDENTIALS')
    proxy_list = json.loads(PROXY_CREDENTIALS)
    proxy = random.choice(proxy_list)
    if proxy == "":
        proxies = {}
    else:
        proxies = {
            "http": proxy,
            "https": proxy
        }   
        proxies2 = proxies
 
CB_ForwardProxy = config.CB_ForwardProxy
MX_ForwardProxy = config.MX_ForwardProxy
if CB_ForwardProxy == "1":
    ForwardProxy = env_vars.get('ForwardProxy')
    ForwardProxy2 = ForwardProxy
    if MX_ForwardProxy == "1":
        ForwardProxy2 = ForwardProxy
elif MX_ForwardProxy == "1":
    ForwardProxy2 = env_vars.get('ForwardProxy')
else:
    ForwardProxy2 = ""
    ForwardProxy = ""


fake_headers = Headers()

async def get_stayonline(link,client):
    headers = {
                    'origin': 'https://stayonline.pro',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0',
                    'x-requested-with': 'XMLHttpRequest',
                }
    parts = link.split("/")
    if len(parts) < 2:
        logger.warning("CB01 get_stayonline: missing link parts for stayonline id")
        return ""
    data = {'id': parts[-2], 'ref': ''}
    response = await client.post('https://stayonline.pro/ajax/linkEmbedView.php', headers=headers, data=data, proxies = proxies2)
    try:
        data = response.json()
    except Exception:
        logger.info("CB01 get_stayonline: invalid json response")
        return ""
    real_url = data.get('data', {}).get('value')
    if not real_url:
        logger.warning("CB01 get_stayonline: missing real url in response")
        return ""
    return real_url

async def get_maxstream(link,streams,client):
    if 'stayonline' in link:
        uprot_link = await get_stayonline(link,client)
        if not uprot_link:
            logger.warning("CB01 get_maxstream: stayonline link missing redirect")
            return streams
    else:
        uprot_link = link
    maxstream_link = await bypass_uprot(client,uprot_link)
    if  maxstream_link:
        streams = await maxstream(maxstream_link,client,streams,'CB01','',proxies2,ForwardProxy)
    else:
        if  maxstream_link == False:
            return streams 
        else:
            streams['streams'].append({'name': f"{Name}",'title': f'{Icon}CB01\n▶️ Please do the captcha at /uprot in order to be able to play this content! \n Remember to refresh the sources!\nIf you recently did the captcha then dont worry, just refresh the sources', 'url': 'https://github.com/UrloMythus/MammaMia', 'behaviorHints': { 'bingeGroup': 'cb01'}})

    return streams
async def search_movie(showname,date,client):
    try:
        showname = showname.replace(" ","+").replace("ò","o").replace("è","e").replace("à","a").replace("ù","u").replace("ì","i")  
        headers = fake_headers.generate()
        headers['Referer'] = f'{CB_DOMAIN}/'
        query = f'{CB_DOMAIN}/?s={showname}'
        response = await client.get(ForwardProxy + query,headers=headers, proxies = proxies)
        if response.status_code != 200:
            logger.warning(f"CB01 Failed to fetch search results: {response.status_code}")
        soup = BeautifulSoup(response.text, 'lxml',parse_only=SoupStrainer('div', class_='card-content'))
        cards = soup.find_all('div', class_='card-content')
        year_pattern = re.compile(r'(19|20)\d{2}')
        for card in cards:
    # Find the link inside the current card
            title_tag = card.find('h3', class_='card-title')
            if not title_tag:
                logger.info("CB01 search_movie: missing title tag in card")
                continue
            link_tag = title_tag.find('a')
            if not link_tag or 'href' not in link_tag.attrs:
                logger.info("CB01 search_movie: missing href in title link")
                continue
            href = link_tag['href']
    # Find the date span and extract possible years

            parts = href.split("/")
            if len(parts) < 2:
                logger.info("CB01 search_movie: missing date segment in href")
                continue
            date_text = parts[-2]
                # Search for the first occurrence of a year (starting with 19 or 20)
            match = year_pattern.search(date_text)
            if match:
                year = match.group(0)
                if year == date :
                    return href
    except Exception as e:
        logger.warning(f'MammaMia: Error in search_series cb01: {e}')


async def search_series(showname,date,client):
    try:
        showname = showname.replace(" ","+")
        headers = fake_headers.generate()
        headers['Referer'] = f'{CB_DOMAIN}/serietv/'
        query = f'{CB_DOMAIN}/serietv/?s={showname}'
        response = await client.get(ForwardProxy + query,headers=headers, proxies = proxies)
        if response.status_code != 200:
            logger.warning(f"CB01 Failed to fetch search results: {response.status_code}")
        soup = BeautifulSoup(response.text, 'lxml',parse_only=SoupStrainer('div', class_='card-content'))
        cards = soup.find_all('div', class_='card-content')
        year_pattern = re.compile(r'(19|20)\d{2}')
        for card in cards:
    # Find the link inside the current card
            title_tag = card.find('h3', class_='card-title')
            if not title_tag:
                logger.info("CB01 search_series: missing title tag in card")
                continue
            link_tag = title_tag.find('a')
            if not link_tag or 'href' not in link_tag.attrs:
                logger.info("CB01 search_series: missing href in title link")
                continue
            href = link_tag['href']
    # Find the date span and extract possible years
            date_span = card.find('span', style=re.compile('color'))
            if date_span:
                date_text = date_span.text
                # Search for the first occurrence of a year (starting with 19 or 20)
                match = year_pattern.search(date_text)
                if match:
                    year = match.group(0)
                    if (int(year) - int(date)) == 0 or (int(year)-int(date)) == 1 or (int(year)-int(date)) == -1 :  # Check if the year is 2011
                        return href
    except Exception as e:
        logger.warning(f'MammaMia: Error in search_series cb01: {e}')

async def movie_redirect_url(link,client,MFP,MFP_CREDENTIALS,streams):
        headers = fake_headers.generate()
        response = await client.get(ForwardProxy + link, headers=headers, allow_redirects=True, timeout=10, proxies = proxies)
        # Extract the redirect URL from the HTML
        soup = BeautifulSoup(response.text, "lxml",parse_only=SoupStrainer('div'))
        redirect_div = soup.find("div", id="iframen2")
        redirect_div_2 = soup.find("div", id="iframen1")
        if not redirect_div or not redirect_div.get("data-src"):
            logger.warning("CB01 movie_redirect_url: missing iframen2 data-src")
            return streams
        if not redirect_div_2 or not redirect_div_2.get("data-src"):
            logger.warning("CB01 movie_redirect_url: missing iframen1 data-src")
            return streams
        redirect_url = redirect_div.get("data-src")
        redirect_url_2 = redirect_div_2.get("data-src")
        if "stayonline" in redirect_url:
            mixdrop_real_link = await get_stayonline(redirect_url,client)
            if not mixdrop_real_link:
                logger.warning("CB01 movie_redirect_url: stayonline missing real link")
                return streams
            streams,status = await mixdrop(mixdrop_real_link,client,MFP,MFP_CREDENTIALS,streams,"CB01",proxies,ForwardProxy,"")
            if status == False:
                streams = await get_maxstream(redirect_url_2,streams,client)
        return streams

async def series_search_streams(text,search_text,response_text,headers,season,episode,client,MFP,MFP_CREDENTIALS,streams):
    if "A" in text:
        captcha = re.search(rf'{search_text}.*?href="([^"]+)',response_text,re.DOTALL)
        if captcha:
            response = await client.get(ForwardProxy + captcha.group(1), headers = headers, allow_redirects = True, proxies = proxies)
            season = season.zfill(2)
            match = re.search(rf"(S{season}E{episode}|{season}x{episode}).+?href='([^']+)",response.text)
            if match:
                streams = await get_maxstream(match.group(2),streams,client)
            else:
                logger.info("CB01 series_search_streams: episode link not found in captcha page")
    else:
        match = re.search(rf'{season}&#215;{episode}\s*&#8211;\s*<a[^>]*href="[^"]*"[^>]*>[^<]*</a>\s&#8211; <a[^>]*href="[^"]*',response_text)
        if match:
            links = match.group(0)
            soup = BeautifulSoup(links,'lxml',parse_only=SoupStrainer('a'))
            host_links = soup.find_all('a')
            if len(host_links) < 2:
                logger.info("CB01 series_search_streams: missing host links for episode")
                return streams
            if 'href' not in host_links[1].attrs or 'href' not in host_links[0].attrs:
                logger.info("CB01 series_search_streams: missing href in host links")
                return streams
            mixdrop_real_link = await get_stayonline(host_links[1]['href'],client)
            status = False
            #streams,status = await mixdrop(mixdrop_real_link,client,MFP,MFP_CREDENTIALS,streams,"CB01",proxies,ForwardProxy,"")  
            if status == False:
                streams = await get_maxstream(host_links[0]['href'],streams,client)
    return streams
async def series_redirect_url(link,season,episode,client,MFP,MFP_CREDENTIALS,streams):
        episode = episode.zfill(2)
        headers = fake_headers.generate()
        response = await client.get(ForwardProxy + link, headers=headers, allow_redirects=True, timeout=10, proxies = proxies)
        soup = BeautifulSoup(response.text, "lxml")    
        seasons_text = soup.find_all('div', class_='sp-head')
        for season_text in seasons_text:
            text = season_text.text
            search_text = season_text.text
            if f'STAGIONE' in text and f'{season}' in text:
                text = text.replace("STAGIONE","").replace("ITA", "")
                streams = await series_search_streams(text,search_text,response.text,headers,season,episode,client,MFP,MFP_CREDENTIALS,streams)
            elif f'STAGIONE' in text and 'A' in text.replace("STAGIONE","").replace("ITA", ""):
                parts = text.split('STAGIONE ')
                if len(parts) < 2:
                    logger.info("CB01 series_redirect_url: missing STAGIONE range text")
                    continue
                range_parts = parts[1].split(' A ')
                if len(range_parts) < 2:
                    logger.info("CB01 series_redirect_url: missing season range delimiter")
                    continue
                try:
                    num1 = int(range_parts[0])
                    if not range_parts[1]:
                        logger.info("CB01 series_redirect_url: missing range end")
                        continue
                    num2 = int(range_parts[1][0])
                except (ValueError, IndexError):
                    logger.info("CB01 series_redirect_url: invalid season range")
                    continue
                if int(season)  in range(num1,num2):
                    streams = await series_search_streams(text,search_text,response.text,headers,season,episode,client,MFP,MFP_CREDENTIALS,streams)
        return streams






async def cb01(streams,id,MFP,MFP_CREDENTIALS,client):
    try:
        general = await is_movie(id)
        if not general or len(general) < 2:
            logger.warning("CB01: missing media info from is_movie")
            return streams
        ismovie = general[0]
        real_id = general[1]
        type = "Cb01"
        if "tt" in id:
            showname, date = await get_info_imdb(real_id,ismovie,type,client)
        elif  "tmdb" in real_id:
            showname, date = get_info_tmdb(real_id,ismovie,type)
        if ismovie == 0:
            if len(general) < 4:
                logger.warning("CB01: missing season/episode in id")
                return streams
            season = general[2]
            episode = general[3]
            link = await search_series(showname,date,client)
            if not link:
                logger.warning("CB01: series search returned no link")
                return streams
            streams = await series_redirect_url(link,season,episode,client,MFP,MFP_CREDENTIALS,streams)
            return streams
        elif ismovie == 1:
            season = None
            episode = None
            link = await search_movie(showname,date,client)
            if not link:
                logger.warning("CB01: movie search returned no link")
                return streams
            streams = await movie_redirect_url(link,client,MFP,MFP_CREDENTIALS,streams)
            return streams
    except Exception as e:
        logger.warning(f'MammaMia: Error in cb01: {e}')
        return streams



















async def test_animeworld():
    from curl_cffi.requests import AsyncSession
    async with AsyncSession() as client:
        test_id = "tt0158552:1:2"  # This is an example ID format
        MFP = "0"
        results = await cb01({'streams': []},test_id,MFP,['test','test'],client)
        print(results)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_animeworld())
