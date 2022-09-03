import requests

from ini import *


def get_cookies(headers):
    session = requests.session()
    response = session.get(SHOP_URL, headers=headers)
    if response.status_code in range(200, 300):
        return session.cookies.get_dict()
    else:
        raise Exception


def get_cookies_from_client(client):
    if hasattr(client, 'transport'):
        transport = getattr(client, 'transport')
        if hasattr(transport, 'response_headers'):
            response_headers = getattr(transport, 'response_headers')
            dictionary = dict(response_headers)
            if 'Set-Cookie' in dictionary.keys():
                cookies_str = dictionary['Set-Cookie']
                from http.cookies import SimpleCookie
                cookie = SimpleCookie()
                cookie.load(cookies_str)
                return {key: value.value for key, value in cookie.items()}
    return False
