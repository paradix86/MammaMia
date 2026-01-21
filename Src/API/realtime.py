from Src.Utilities.info import get_info_tmdb, is_movie, get_info_imdb
import Src.Utilities.config as config
from fake_headers import Headers  
from Src.Utilities.loadenv import load_env  
from urllib.parse import quote
import logging
from Src.Utilities.config import setup_logging
level = config.LEVEL
import random
Icon = config.Icon
Name = config.Name
logger = setup_logging(level)
env_vars = load_env()
random_headers = Headers()
RT_PROXY = config.RT_PROXY
proxies = {}
if RT_PROXY == "1":
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
RT_ForwardProxy = config.RT_ForwardProxy
if RT_ForwardProxy == "1":
    ForwardProxy = env_vars.get('ForwardProxy')
else:
    ForwardProxy = ""


endpoints = {
    'it' : 'https://public.aurora.enhanced.live',
    'dplay' : 'https://eu1-prod.disco-api.com'
}
async def search(showname,date,client):
    showname = showname.split('-')[0]
    showname = quote(showname)
    response = await client.get(ForwardProxy + f'https://public.aurora.enhanced.live/site/search/page/?include=default&filter[environment]=realtime&v=2&q={showname}&page[number]=1&page[size]=20', proxies = proxies)
    try:
        data = response.json()
    except Exception:
        logger.info("RT search: invalid json response")
        return None
    items = data.get('data', [])
    if not items:
        logger.info("RT search: no results in data list")
        return None
    for item in items:
        return item.get('slug')



async def program_info(slug,season,episode,client):
    headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://realtime.it/',
    'Origin': 'https://realtime.it',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'DNT': '1',
    'Priority': 'u=4',
    }
    link = f'https://public.aurora.enhanced.live/site/page/{slug}/?include=default&filter[environment]=realtime&v=2&parent_slug=programmi-real-time'
    
    response = await client.get(ForwardProxy + link,headers = headers, proxies = proxies)
    try:
        data = response.json()
    except Exception:
        logger.info("RT program_info: invalid json response")
        return None,None,None,None
    blocks = data.get('blocks', [])
    if len(blocks) < 2 or 'items' not in blocks[1]:
        logger.info("RT program_info: missing blocks/items for program")
        return None,None,None,None
    for item in reversed(blocks[1]['items']):
        if season ==  item['seasonNumber'] and episode == item['episodeNumber']:
            if len(blocks) < 1 or 'item' not in blocks[0]:
                logger.info("RT program_info: missing poster block")
                return None,None,None,None
            poster_src = blocks[0]['item'].get('poster', {}).get('src', '')
            if 'aurora' in poster_src:
                platform = 'IT'
            elif 'eu1-prod' in poster_src:
                platform = 'DPLAY'
            else:
                logger.info("RT program_info: unknown platform in poster src")
                return None,None,None,None
            x_realm_it = ''
            x_realm_dplay = ''
            if 'X-REALM-IT' in data['userMeta']['realm']:
                x_realm_it = data['userMeta']['realm']['X-REALM-IT']
            if 'X-REALM-DPLAY' in data['userMeta']['realm']:
                x_realm_dplay = data['userMeta']['realm']['X-REALM-DPLAY']
            return item['id'],x_realm_it,x_realm_dplay, platform
    return None,None,None,None

async def get_token(client):
    headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://realtime.it/',
    'Content-Type': 'application/json',
    'X-disco-client': 'WEB:UNKNOWN:wbdatv:2.1.9',
    'X-disco-params': 'realm=dplay',
    'X-Device-Info': 'STONEJS/1 (Unknown/Unknown; Linux/undefined; Unknown)',
    'Origin': 'https://realtime.it',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'DNT': '1',
    'Priority': 'u=4',
    }
    response = await client.get(ForwardProxy + 'https://public.aurora.enhanced.live/site/page/casa-a-prima-vista/?include=default&filter[environment]=realtime&v=2&parent_slug=programmi-real-time', headers = headers, proxies = proxies)
    try:
        data = response.json()
    except Exception:
        logger.info("RT get_token: invalid json response")
        return None, None
    realm = data.get('userMeta', {}).get('realm', {})
    x_realm_it = realm.get('X-REALM-IT')
    x_realm_dplay = realm.get('X-REALM-DPLAY')
    if not x_realm_it or not x_realm_dplay:
        logger.info("RT get_token: missing realm tokens")
    return x_realm_it,x_realm_dplay



async def get_url(id, endpoint, x_realm_it,x_realm_dplay,streams,client):
    endpoint_norm = (endpoint or "").upper()
    if 'DPLAY' in endpoint_norm:
        base_url = endpoints['dplay']
        token = x_realm_dplay
    elif 'IT' in endpoint_norm:
        base_url = endpoints['it']
        token = x_realm_it
    else:
        logger.warning("RT get_url: missing endpoint platform")
        return streams
    if not token:
        logger.warning("RT get_url: missing auth token")
        return streams
    headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://realtime.it/',
    'Content-Type': 'application/json',
    'X-disco-client': 'WEB:UNKNOWN:wbdatv:2.1.9',
    'X-disco-params': 'realm=dplay',
    'X-Device-Info': 'STONEJS/1 (Unknown/Unknown; Linux/undefined; Unknown)',
    'Authorization': f'Bearer {token}',
    'Origin': 'https://realtime.it',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'DNT': '1',
    'Priority': 'u=4',
    }


    json_data = {
    'deviceInfo': {
        'adBlocker': False,
        'drmSupported': True,
        'hdrCapabilities': [
            'SDR',
        ],
        'hwDecodingCapabilities': [],
        'soundCapabilities': [
            'STEREO',
        ],
    },
    'wisteriaProperties': {},
    'videoId': id,
    }
    response = await client.post(ForwardProxy + f'{base_url}/playback/v3/videoPlaybackInfo', headers=headers, json=json_data, proxies = proxies)
    try:
        data = response.json()
    except Exception:
        logger.info("RT get_url: invalid json response")
        return streams
    streaming = data.get('data', {}).get('attributes', {}).get('streaming', [])
    if not streaming:
        logger.info("RT get_url: no streaming entries")
        return streams
    for item in streaming:
        if item['type'] == 'hls':
            m3u8 = item['url']
            streams['streams'].append({'name': f"{Name}",'title': f'{Icon}▶️ Realtime\n HLS', 'url': m3u8, 'behaviorHints': {'bingeGroup': f'realtimehls'}})

        elif item['type'] == 'dash':
            mpd = item['url']
            streams['streams'].append({'name': f"{Name}",'title': f'{Icon}▶️ Realtime\n MPD', 'url': mpd, 'behaviorHints': {'bingeGroup': f'realtimempd'}})

    return streams




async def search_catalog(query,catalog,client):
    showname = quote(query)
    response = await client.get(f'https://public.aurora.enhanced.live/site/search/page/?include=default&filter[environment]=realtime&v=2&q={showname}&page[number]=1&page[size]=20')
    try:
        data = response.json()
    except Exception:
        logger.info("RT search_catalog: invalid json response")
        return catalog
    items = data.get('data', [])
    if not items:
        logger.info("RT search_catalog: empty search results")
        return catalog
    for item in items:
        title = item['title']
        description = item['subtitle']
        date_parts = item.get('datePublished', '').split('-')
        if not date_parts or not date_parts[0]:
            logger.info("RT search_catalog: missing datePublished")
            continue
        date = date_parts[0]
        id = item['slug']
        image = item['image']['url']
        typeof = item['type']
        catalog['metas'].append({'id': f'realtime{typeof}:'+id, 'type': "series",'name': f'{title}', 'description': description, 'releaseInfo': date, 'background': image, 'poster': image })
    return catalog

async def meta_catalog(id,catalog,client):
    try:
        headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://realtime.it/',
        'Origin': 'https://realtime.it',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'DNT': '1',
        'Priority': 'u=4',
        }
        parts = id.split(':')
        if len(parts) < 2:
            logger.warning("RT meta_catalog: invalid id format")
            return catalog
        slug = parts[1]
        parts2 = parts[0].split('realtime')
        if len(parts2) < 2:
            logger.warning("RT meta_catalog: invalid id prefix")
            return catalog
        typeof= parts2[1]
        if typeof == 'showpage':
            link = f'https://public.aurora.enhanced.live/site/page/{slug}/?include=default&filter[environment]=realtime&v=2&parent_slug=programmi-real-time'
        elif typeof == 'article':
            link = f'https://public.aurora.enhanced.live/site/page/{slug}/?include=default&filter[environment]=realtime&v=2'
        else:
            logger.warning("RT meta_catalog: unknown type")
            return catalog

        response = await client.get(ForwardProxy + link,headers = headers, proxies = proxies)
        try:
            data = response.json()
        except Exception:
            logger.info("RT meta_catalog: invalid json response")
            return catalog
        title = data['title']
        subtitle = data['subtitle']
    
        if  data['type'] == 'articlepage':
            blocks = data.get('blocks', [])
            if len(blocks) < 2:
                logger.info("RT meta_catalog: missing blocks for article")
                return catalog
            if blocks[1].get('sonicOverrideEnabled') == True:
                platform = 'IT'
            else:
                platform = 'DPLAY'
        elif data['type'] == 'showpage':
            blocks = data.get('blocks', [])
            if len(blocks) < 1:
                logger.info("RT meta_catalog: missing blocks for showpage")
                return catalog
            poster_src = blocks[0].get('item', {}).get('poster', {}).get('src', '')
            if 'aurora' in poster_src:
                platform = 'IT'
            elif 'eu1-prod' in poster_src:
                platform = 'DPLAY'
            else:
                logger.info("RT meta_catalog: unknown platform in poster src")
                return catalog
        if typeof == 'showpage':
            if len(blocks) < 2 or 'items' not in blocks[1]:
                logger.info("RT meta_catalog: missing items in showpage blocks")
                return catalog
            for item in reversed(blocks[1]['items']):
                id = item['id']
                description = item['description']
                episode = item['episodeNumber']
                season = item['seasonNumber']
                poster = item['poster']
                date = item['publishStart']
                catalog['meta']['videos'].append({'title': f'S{season}'+ f'E{episode}','season': season, 'episode': episode,'firstAired':date,'overview': description, 'thumbnail': poster['src'], 'id': f'realtime{platform}:id:'+id})
        elif typeof == 'article':
            if len(blocks) < 2 or 'item' not in blocks[1]:
                logger.info("RT meta_catalog: missing item in article blocks")
                return catalog
            item = blocks[1]['item']
            id = item['id']
            description = item['description']
            episode = item['episodeNumber']
            season = item['seasonNumber']
            poster = item['poster']
            date = item['publishStart']
            catalog['meta']['videos'].append({'title': f'{title}','season': season, 'episode': episode,'firstAired':date,'overview': description, 'thumbnail': poster['src'], 'id': f'realtime{platform}:id:'+id})

        catalog['meta']['name'] = title
        catalog['meta']['description'] = subtitle 
        date_parts = data.get('datePublished', '').split('-')
        if date_parts and date_parts[0]:
            catalog['meta']['releaseInfo'] = '-' + date_parts[0]
        meta_media = data.get('metaMedia', [])
        if meta_media:
            catalog['meta']['background'] = meta_media[0].get('media', {}).get('url')
        return catalog
    except Exception as e:
        logger.warning(f"RT meta_catalog: {e}")
        return catalog
async def realtime(streams,id,client):
    try:
        if 'realtime' in id:
            parts = id.split('id:')
            if len(parts) < 2:
                logger.warning("RT realtime: invalid realtime id format")
                return streams
            id = parts[1]
            endpoint = parts[0]
            x_realm_it,x_realm_dplay = await get_token(client)
            if not x_realm_it or not x_realm_dplay:
                logger.warning("RT realtime: missing realm tokens")
                return streams
            streams = await get_url(id, endpoint, x_realm_it,x_realm_dplay,streams,client)
        else:
            general = await is_movie(id)
            if not general or len(general) < 2:
                logger.warning("RT realtime: missing media info from is_movie")
                return streams
            ismovie = general[0]
            clean_id = general[1]
            type = "Realtime"
            if ismovie == 0 : 
                if len(general) < 4:
                    logger.warning("RT realtime: missing season/episode in id")
                    return streams
                season = int(general[2])
                episode = int(general[3])
            elif ismovie == 1:
                season = None
                episode = None
            if "tmdb" in id:
                showname,date = get_info_tmdb(clean_id,ismovie,type)
            else:
                showname,date = await get_info_imdb(clean_id,ismovie,type,client)
            logger.info(f'RT {showname}')
            slug = await search(showname,date,client)
            if not slug:
                logger.warning("RT realtime: search returned no slug")
                return streams
            id,x_realm_it,x_realm_dplay,platform = await program_info(slug,season,episode,client)
            if not id or not platform:
                logger.warning("RT realtime: program info missing id/platform")
                return streams
            streams = await get_url(id,platform,x_realm_it,x_realm_dplay,streams,client)
        return streams
    except Exception as e:
        logger.warning(f'RT {e}')
        return streams




async def test_realtime():
    from curl_cffi.requests import AsyncSession
    async with AsyncSession() as client:
        results = await realtime({'streams': []},"tt5684368:13:10",client)
        print(results)

        
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_realtime()) 
