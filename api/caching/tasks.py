import urlparse

import requests
import logging

from website import settings

logger = logging.getLogger(__name__)

def get_varnish_servers():
    #  TODO: this should get the varnish servers from HAProxy or a setting
    return settings.VARNISH_SERVERS

def ban_url_from_varnish(url, host, timeout, ):
    try:
        response = requests.request('BAN', url, timeout=timeout, headers=dict(
            Host=host
        ))
    except Exception as ex:
        logger.error('Banning {} failed: {}'.format(
            url,
            ex.message
        ))
    else:
        if not response.ok:
            logger.error('Banning {} failed: {}'.format(
                url,
                response.text
            ))

def ban_object_instances_from_varnish(url, url_patterns=None):
    timeout = 0.3  # 500ms timeout for bans
    if url_patterns is None:
        url_patterns = []
    if settings.ENABLE_VARNISH: 
        parsed_url = urlparse.urlparse(url)

        for host in get_varnish_servers():
            varnish_parsed_url = urlparse.urlparse(host)
            url_to_ban = '{scheme}://{netloc}{path}.*'.format(
                scheme=varnish_parsed_url.scheme,
                netloc=varnish_parsed_url.netloc,
                path=parsed_url.path
            )
            ban_url_from_varnish(url_to_ban, parsed_url.hostname, timeout)

        for pattern in url_patterns:
            for host in get_varnish_servers():
                varnish_parsed_url = urlparse.urlparse(host)
                url_to_ban = '{scheme}://{netloc}{pattern}'.format(
                    scheme=varnish_parsed_url.scheme,
                    netloc=varnish_parsed_url.netloc,
                    pattern=pattern
                )
                ban_url_from_varnish(url_to_ban, parsed_url.hostname, timeout)
