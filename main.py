#!/usr/bin/env python3
"""
Primitive Etherum Key Scanner
"""
import json
from pprint import pprint
from eth_keys import keys
from eth_utils import decode_hex
import time

import requests
from bs4 import BeautifulSoup, SoupStrainer
import re
import argparse

end_block = 14850581
api_key = 'JSPZK8Z6HBAG3ZHGGV6DQSBCBPJAY7UGTD'

args = argparse.ArgumentParser()
args.add_argument('-f', '--file', type=str, help='Read private keys from file')
args.add_argument('-a', '--action', type=str, choices=['balance', 'tx', 'erc20'], default='balance')
args.add_argument('-c', '--contract', type=str, help='Contract address for checking erc20 and erc721')
args.add_argument('-u', '--update_contracts', dest='update_contracts', action='store_true',
                  help='Update list of top 50 erc20 contracts')
args = args.parse_args()


def log_json(string):
    pprint(string)
    with open('log.json', 'a') as f:
        json.dump(string, fp=f)


def log(string):
    print(string)
    with open('log.txt', 'a') as f:
        f.write(string + '\n')


def get_erc20_contracts():
    parser = 'html.parser'  # or 'lxml' (preferred) or 'html5lib', if installed
    resp = requests.get("https://etherscan.io/tokens", headers={"User-Agent": "curl/7.68.0", "Accept": "*/*"})
    soup = BeautifulSoup(resp.text, parser)
    with open(args.output, 'w') as f:
        for link in soup.find_all('a', href=True):
            if re.match(r'/token/(.*)', link['href']):
                contract = link['href'].strip('/token/')
                f.write(contract + '\n')
    print('Done!')


def load_erc20_contracts():
    contracts = []
    with open('contracts.txt', 'r') as f:
        f = f.readlines()
        for _ in f:
            _ = _.strip('\r\n')
            contracts.append(_)
    return contracts


def get_balance(address):
    return requests.get(f'https://api.etherscan.io/api?module=account&action=balance&address={address}\
    &tag=latest&apikey={api_key}')


def get_balance_multi(addresses):
    add = ''
    for a in addresses:
        add += f'{a}, '
    return requests.get(f"https://api.etherscan.io/api?module=account&action=balancemulti&address={add}\
    &tag=latest&apikey={api_key}")


def get_txs(address):
    return requests.get(f'https://api.etherscan.io/api?module=account&action=txlistinternal&address={address}\
    &startblock=0&endblock={end_block}&page=1&offset=10&sort=asc&apikey={api_key}')


def get_address(priv_key):
    priv_key_bytes = decode_hex(priv_key)
    priv_key = keys.PrivateKey(priv_key_bytes)
    pub_key = priv_key.public_key.to_address()
    return pub_key


def erc20(contract_address, address):
    return requests.get(f'https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={contract_address}\
    &address={address}&page=1&offset=100&startblock=0&endblock=27025780&sort=asc&apikey={api_key}')


def erc721(contract_address, address):
    return requests.get(f'https://api.etherscan.io/api?module=account&action=tokennfttx&contractaddress={contract_address}\
    &address={address}&page=1&offset=100&startblock=0&endblock=27025780&sort=asc&apikey={api_key}')




if args.update_contracts:
    print('Getting top 50 contracts  .. ')
    get_erc20_contracts()

with open(args.file, 'r') as f:
    f = f.readlines()
    if args.action == 'balance':
        print('Getting balances .. ')
        if len(f) >= 20:
            print(f'Using the bulk api ... ')
            keys_20 = []
            while len(f):
                while len(keys_20) < 20:
                    try:
                        _line = f.pop().strip('\r\n')
                    except IndexError:
                        break
                    else:
                        pub = get_address(_line)
                        print(pub)
                        keys_20.append(pub)
                ret = get_balance_multi(keys_20)
                log_json(ret.json())
                keys_20 = []
        for line in f:
            line = line.strip('\r\n')
            pub = get_address(line)
            print(f'Fetching balance of {pub} ... ')
            bal = get_balance(pub)
            log_json(bal.json())
            time.sleep(0.25)
    elif args.action == 'tx':
        print('Getting txs')
        for line in f:
            line = line.strip('\r\n')
            pub = get_address(line)
            print(pub)
            ret = get_txs(pub).json()
            log_json(ret)
            time.sleep(0.25)
    elif args.action == 'erc20':
        print(f'Getting erc20 token transfers   .. ')

        contracts = load_erc20_contracts()
        if args.contract:
            print(f'Checking {args.contract}')
            for line in f:
                line = line.strip('\r\n')
                pub = get_address(line)
                print(f'Checking {pub}')
                ret = erc20(args.contract, pub).json()
                log(f'Contract: {args.contract}, Response: {ret}')
        else:
            print('Checking top contracts ... ')

            for contract in contracts:
                print(f'Checking {contract}')
                for line in f:
                    line = line.strip('\r\n')
                    pub = get_address(line)
                    print(f'Checking {pub}')
                    ret = erc20(contract, pub).json()
                    log(f'Contract: {contract}, Response: {ret}')
                    time.sleep(0.25)

    elif args.action == 'erc721':
        print(f'Getting erc20 token transfers for {args.contract}  .. ')
        contracts = load_erc20_contracts()
        for contract in contracts:
            for line in f:
                line = line.strip('\r\n')
                pub = get_address(line)
                print(pub, contract)
                ret = erc721(pub).json()
                log(f'Contract: {contract}, Response: {ret}')
                time.sleep(0.25)
    else:
        print('Unknown action!')
