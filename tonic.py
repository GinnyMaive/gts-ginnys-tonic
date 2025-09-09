import argparse
import json
import os
import re
import requests
import time
import webbrowser

from datetime import datetime
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib import parse

# Configuration
INSTANCE_BASE_URL = 'https://transister.social/'
DELAY_BETWEEN_REQUESTS = 2 # seconds
DRY_RUN = True
BASE_DIR = './'

AUTHORIZATION_URL = '/oauth/authorize'
TOKEN_URL = '/oauth/token'
FOLLOWERS_URL = '/api/v1/accounts/{user_id}/followers'
FOLLOWING_URL = '/api/v1/accounts/{user_id}/following'
RELATIONSHIP_URL = '/api/v1/accounts/relationships'
UNFOLLOW_URL = '/api/v1/accounts/{unfollow_user_id}/unfollow'
VERIFY_CREDENTIALS_URL = '/api/v1/accounts/verify_credentials'
# ACCOUNTS_URL = f'{INSTANCE_BASE_URL}api/v1/accounts'
# STATUS_URL = f'{INSTANCE_BASE_URL}api/v1/statuses'
# MEDIA_URL = f'{INSTANCE_BASE_URL}api/v1/media'

CREDENTIALS_FILE = f'{BASE_DIR}credentials.json'
APPLICATION_FILE = f'{BASE_DIR}application.json'
LOG_FILE = f'{BASE_DIR}tonic.log'

# These will be read and set from APPLICATION_FILE
CLIENT_ID = ''
CLIENT_SECRET = ''
REDIRECT_URI = 'http://localhost:8080/callback'


def save_credentials(token_data):
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(token_data, f)

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            query = self.path.split('?', 1)[-1]
            params = dict(qc.split('=') for qc in query.split('&'))
            self.server.auth_code = params.get('code')
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Authorization successful. You can close this window.')
        else:
            self.send_response(404)
            self.end_headers()

def get_auth_code():
    server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
    auth_url = (
        f'{api_url(AUTHORIZATION_URL)}?response_type=code&client_id={CLIENT_ID}'
        f'&redirect_uri={REDIRECT_URI}&scope=read%20write'
    )
    webbrowser.open(auth_url)
    print('Please authorize in the browser...')
    server.handle_request()
    return server.auth_code

def set_app_config():
    if os.path.exists(APPLICATION_FILE):
        global CLIENT_ID, CLIENT_SECRET, INSTANCE_BASE_URL
        with open(APPLICATION_FILE, 'r') as f:
            app_config = json.load(f)[0]
            domain = app_config.get('base_url', INSTANCE_BASE_URL)
            INSTANCE_BASE_URL = domain_make_url(domain)
            CLIENT_ID = app_config.get('client_id', CLIENT_ID)
            CLIENT_SECRET = app_config.get('client_secret', CLIENT_SECRET)
            log_to_logfile(f'Loaded application credentials for {domain} at {INSTANCE_BASE_URL}')
    else:
        print(f'{APPLICATION_FILE} should exist with your client_id and client_secret!')

class RequestType(Enum):
    GET = requests.get
    POST = requests.post

def api_request(request_type, url, access_token, data=None, params=None):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    full_url = api_url(url)
    return request_type(full_url, headers=headers, data=data, params=params)

def get_token(auth_code):
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scopes': 'read write',
    }
    response = requests.post(api_url(TOKEN_URL), data=data)
    response.raise_for_status()
    return response.json()

def authorize():
    creds = load_credentials()
    if creds:
        log_to_logfile('Credentials loaded')
    else:
        auth_code = get_auth_code()
        token_data = get_token(auth_code)
        save_credentials(token_data)
        log_to_logfile('Credentials saved')
        creds = load_credentials()
    return creds

def log_to_logfile(message):
    full_message = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}'
    print(full_message)
    with open(LOG_FILE, 'a+') as f:
        f.write(full_message + '\n')

def api_url(endpoint):
    return f'{INSTANCE_BASE_URL}/{endpoint.lstrip("/")}'

def parse_link_header(link_header):
    # Find all URL and rel pairs
    pattern = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')
    matches = pattern.findall(link_header)

    links = {}
    for url, rel in matches:
        query_params = parse.parse_qs(parse.urlparse(url).query)
        links[rel] = {
            'url': url,
            'max_id': query_params.get('max_id', [None])[0],
            'min_id': query_params.get('min_id', [None])[0],
        }
    return links

def unfollow_user(access_token, unfollow_user_id):
    get_current_relationship(access_token, unfollow_user_id)

    full_url = str.format(UNFOLLOW_URL, unfollow_user_id=unfollow_user_id)
    response = api_request(RequestType.POST, full_url, access_token)
    log_to_logfile(f'Unfollow response: {response.status_code}: {response.reason}; {response.json()}')
    if response.status_code != 200:
        error_str = response.json().get('error', '')
        log_to_logfile(f'''API error: {response.status_code} {error_str} {response}''')

def get_user_id(access_token):
    response = api_request(RequestType.GET, VERIFY_CREDENTIALS_URL, access_token)
    log_to_logfile(f'Post status response: {response.status_code}: {response.reason}; {response.json()}')
    if response.status_code != 200:
      error_str = response.json().get('error', '')
      log_to_logfile(f'''API error: {response.status_code} {error_str} {response}''')
      return None
    return response.json().get('id')

def get_current_relationship(access_token, target_user_id):
    response = api_request(RequestType.GET, RELATIONSHIP_URL, access_token, params={'id[]': target_user_id})
    if response.status_code != 200:
        error_str = response.json().get('error', '')
        log_to_logfile(f'''API error: {response.status_code} {error_str} {response}''')
        return None
    relationships = response.json()
    if relationships and len(relationships) > 0:
        log_to_logfile(f'Current relationship with {target_user_id}: {relationships[0]}')
        return relationships[0]
    return None

def get_paginated_results(access_token, url):
    max_id = None
    results = []
    for _ in range(20):  # Limit to 20 pages to avoid infinite loops
        payload = {
            'limit': 50,
            'max_id': max_id,
        }
        response = api_request(RequestType.GET, url, access_token, params=payload)
        if len(response.json()) == 0:
            log_to_logfile('No more to fetch.')
            break
        log_to_logfile(f'Fetched {len(response.json())} items')
        time.sleep(DELAY_BETWEEN_REQUESTS)
        links = parse_link_header(response.headers.get('Link', ''))

        if response.status_code != 200:
            error_str = response.json().get('error', '')
            log_to_logfile(f'''API error: {response.status_code} {error_str} {response}''')
            return None
        results.extend(response.json())
        max_id = links.get('next', {}).get('max_id')
        log_to_logfile(f'Next max_id: {max_id}')

    log_to_logfile(f'Total fetched from <${url}>: {len(results)}')
    return results

def log_user_info(user):
    log_to_logfile(f'''User info:\n  ID: {user.get('id')}\n'''
        f'''  Account: {user.get('acct')} Display name: {user.get('display_name')}\n'''
        f'''  URL: {user.get('url')} Created: {user.get('created_at')}\n'''
        f'''  Followers: {user.get('followers_count')} Following: {user.get('following_count')}\n'''
        f'''  Statuses: {user.get('statuses_count')} Most recent status: {user.get('last_status_at')}\n'''
        )

def get_following(access_token, user_id):
    the_url = str.format(FOLLOWERS_URL, user_id=user_id)
    followers = get_paginated_results(access_token, the_url)
    log_to_logfile(f'Fetched {len(followers)} total followers')
    the_url = str.format(FOLLOWING_URL, user_id=user_id)
    following = get_paginated_results(access_token, the_url)
    log_to_logfile(f'Fetched {len(following)} total following')

    following_indexes = {f['id']: f for f in following}
    followers_indexes = {f['id']: f for f in followers}
    log_to_logfile(f'Following but not followed by: {len(set(following_indexes) - set(followers_indexes))}')
    log_to_logfile(f'Followers but not following: {len(set(followers_indexes) - set(following_indexes))}')
    for follow in set(following_indexes) - set(followers_indexes):
        log_user_info(following_indexes[follow])

    return following

# Turn a simply-specified domain name (eg, 'transister.social') into URL (eg, 'https://transister.social')
def domain_make_url(domain_name):
    # Validate this is a simple url kinda.
    parsed_url = parse.urlparse(domain_name)
    full_url = parse.urlunsplit(('https', domain_name, '', '', ''))
    # When parsing something like transister.social, it thinks it's a path, so we need to check all the other parts are empty.
    if full_url.endswith('/') or parsed_url.scheme or parsed_url.netloc or parsed_url.params or parsed_url.query or parsed_url.fragment:
        raise ValueError(f'Invalid domain name: {domain_name}; specify just the domain name without a trailing slash, eg, transister.social')
    return full_url

# Turn a full URL into a simply-specified domain name (eg, 'https://transister.social/anything/whatever' -> 'transister.social')
def domain_from_url(url):
    return parse.urlparse(url).netloc

def main():
    log_to_logfile('''Starting ginny's tonic''')
    parser = argparse.ArgumentParser(description="ginny's tonic")
    subparsers = parser.add_subparsers(required=True, dest='command')
    
    # unfollow command
    unfollow_parser = subparsers.add_parser('unfollow', help='Unfollow a user')
    unfollow_parser.add_argument("unfollow_user_id", help="User ID to unfollow")

    # moots command
    subparsers.add_parser('moots', help='Get detail on moots/non-moots')

    # application command
    application_parser = subparsers.add_parser('application', help='Set application credentials')
    application_subcommand_parser = application_parser.add_subparsers(required=True, dest='application_command')
    application_subcommand_parser.add_parser('list', help='List all application credentials')
    application_subcommand_parser.add_parser('create', help='Create new application credentials') \
        .add_argument("base_url", help="Base URL of the instance")
    application_subcommand_parser.add_parser('delete', help='Delete existing application credentials') \
        .add_argument("base_url", help="Base URL of the instance")

    # parse!
    args = parser.parse_args()

    if args.command == 'application':
        if args.application_command == 'list':
            if os.path.exists(APPLICATION_FILE):
                with open(APPLICATION_FILE, 'r') as f:
                    app_config = json.load(f)
                    for entry in app_config:
                        log_to_logfile(f"Application ID for {entry.get('base_url')}: {entry.get('client_id')}")
            else:
                print('No application credentials found.')
            return
        elif args.application_command == 'delete':
            if os.path.exists(APPLICATION_FILE):
                with open(APPLICATION_FILE, 'r') as f:
                    app_config = json.load(f)
                new_app_config = []
                removed = False
                for entry in app_config:
                    if entry.get('base_url') == args.base_url:
                        log_to_logfile(f"Deleting application credentials for {args.base_url}")
                        removed = True
                    else:
                        log_to_logfile(f"Keeping application credentials for {entry.get('base_url')}")
                        new_app_config.append(entry)
                
                if not removed:
                    log_to_logfile(f'No application credentials found for {args.base_url}.')
                    return

                with open(APPLICATION_FILE, 'w') as f:
                    json.dump(new_app_config, f, indent=4)
            else:
                print('No application credentials found.')
            return

    set_app_config()
    creds = authorize()
    if not creds:
        print('No credentials found. Please authorize first.')
        return
    access_token = creds.get('access_token')
    if not access_token:
        raise ValueError('No access token found in credentials.')

    if args.command == 'unfollow':
        unfollow_user(access_token, args.unfollow_user_id)
    elif args.command == 'moots':
        user_id = get_user_id(access_token)
        get_following(access_token, user_id)
    log_to_logfile(f'Log file: {LOG_FILE}')

if __name__ == '__main__':
    main()