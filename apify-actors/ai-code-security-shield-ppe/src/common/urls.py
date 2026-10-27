import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


TRACKING = {'fbclid', 'gclid', 'dclid', 'msclkid', 'spm', 'scm', 'scm_id',
            'ali_trackid', 'pvid', 'share_token', 'share_app_id', 'share_id',
            'xsec_token', 'xsec_source', 'from', 'ref', 'referrer', 'igshid', '_t'}


def clean_url(value):
    if not isinstance(value, str) or re.search(r'[\x00-\x20\\]', value):
        raise ValueError('Invalid URL')
    parts = urllib.parse.urlsplit(value)
    if parts.scheme.lower() not in {'https', 'http'} or not parts.hostname:
        raise ValueError('Only HTTP(S) URLs are allowed')
    if parts.username or parts.password:
        raise ValueError('Credentials in URLs are forbidden')
    host = parts.hostname.encode('idna').decode('ascii').lower()
    if ':' in host:
        host = '[' + host + ']'
    port = parts.port
    netloc = host + (f':{port}' if port and (parts.scheme.lower(), port) not in {('https', 443), ('http', 80)} else '')
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in TRACKING]
    return urllib.parse.urlunsplit((parts.scheme.lower(), netloc, parts.path or '/',
                                   urllib.parse.urlencode(sorted(query)), ''))


def validate_public_url(url):
    cleaned = clean_url(url)
    parts = urllib.parse.urlsplit(cleaned)
    if parts.scheme != 'https':
        raise ValueError('Public collection requires HTTPS')
    addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Private, loopback and reserved network addresses are forbidden')
    return cleaned


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(urllib.parse.urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(url, timeout=10, attempts=2):
    validate_public_url(url)
    opener = urllib.request.build_opener(PublicRedirectHandler())
    request = urllib.request.Request(url, headers={
        'User-Agent': 'ApifyPainTrendCampaign/1.0', 'Accept': 'application/json,text/html,application/atom+xml'})
    for attempt in range(attempts):
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(5 * 1024 * 1024 + 1)
                if len(raw) > 5 * 1024 * 1024:
                    raise ValueError('Response exceeds 5 MiB')
                return raw
        except urllib.error.HTTPError as exc:
            retry = exc.code in {429, 500, 502, 503, 504}
            delay = exc.headers.get('Retry-After', '') if exc.headers else ''
            exc.close()
            if not retry or attempt + 1 == attempts or (delay and (not delay.isdigit() or int(delay) > 5)):
                raise
            time.sleep(max(1, int(delay or 0)))
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(1)


def fetch_json(url):
    return json.loads(fetch_bytes(url).decode('utf-8'))
