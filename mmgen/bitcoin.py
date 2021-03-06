#!/usr/bin/env python
#
# MMGen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2017 Philemon <mmgen-py@yandex.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
bitcoin.py:  Bitcoin address/key conversion functions
"""

import ecdsa
from binascii import hexlify, unhexlify
from hashlib import sha256
from hashlib import new as hashlib_new
import sys

# From electrum:
# secp256k1, http://www.oid-info.com/get/1.3.132.0.10
_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L
_curve_secp256k1 = ecdsa.ellipticcurve.CurveFp(_p,_a,_b)
_generator_secp256k1 = ecdsa.ellipticcurve.Point(_curve_secp256k1,_Gx,_Gy,_r)
_oid_secp256k1 = (1,3,132,0,10)
_secp256k1 = ecdsa.curves.Curve('secp256k1',_curve_secp256k1,_generator_secp256k1,_oid_secp256k1)

# From en.bitcoin.it:
#  The Base58 encoding used is home made, and has some differences.
#  Especially, leading zeroes are kept as single zeroes when conversion happens.
# Test: 5JbQQTs3cnoYN9vDYaGY6nhQ1DggVsY4FJNBUfEfpSQqrEp3srk
# The 'zero address':
# 1111111111111111111114oLvT2 (pubkeyhash = '\0'*20)
_b58a='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def _numtob58(num):
	ret = []
	while num:
		ret.append(_b58a[num % 58])
		num /= 58
	return ''.join(ret)[::-1]

def _b58tonum(b58num):
	b58num = b58num.strip()
	for i in b58num:
		if not i in _b58a: return False
	return sum(_b58a.index(n) * (58**i) for i,n in enumerate(list(b58num[::-1])))

def hash160(hexnum): # take hex, return hex - OP_HASH160
	return hashlib_new('ripemd160',sha256(unhexlify(hexnum)).digest()).hexdigest()

def hash256(hexnum): # take hex, return hex - OP_HASH256
	return sha256(sha256(unhexlify(hexnum)).digest()).hexdigest()

# devdoc/ref_transactions.md:
btc_addr_ver_nums = {
	'p2pkh': { 'mainnet': ('00','1'), 'testnet': ('6f','mn') },
	'p2sh':  { 'mainnet': ('05','3'), 'testnet': ('c4','2') }
}
btc_addr_pfxs             = { 'mainnet': '13', 'testnet': 'mn2', 'regtest': 'mn2' }
btc_uncompressed_wif_pfxs = { 'mainnet':'5','testnet':'9' }
btc_privkey_pfxs          = { 'mainnet':'80','testnet':'ef' }

from mmgen.globalvars import g

def verify_addr(addr,verbose=False,return_dict=False,testnet=None):
	testnet = testnet if testnet != None else g.testnet # allow override
	for addr_fmt in ('p2pkh','p2sh'):
		for net in ('mainnet','testnet'):
			ver_num,ldigit = btc_addr_ver_nums[addr_fmt][net]
			if addr[0] not in ldigit: continue
			num = _b58tonum(addr)
			if num == False: break
			addr_hex = '{:050x}'.format(num)
			if addr_hex[:2] != ver_num: continue
			if hash256(addr_hex[:42])[:8] == addr_hex[42:]:
				return {'hex':addr_hex[2:42],'format':addr_fmt,'net':net} if return_dict else True
			else:
				if verbose: Msg("Invalid checksum in address '{}'".format(addr))
				break

	if verbose: Msg("Invalid address '{}'".format(addr))
	return False

def hexaddr2addr(hexaddr,p2sh=False,testnet=None):
	testnet = testnet if testnet != None else g.testnet # allow override
	s = btc_addr_ver_nums[('p2pkh','p2sh')[p2sh]][('mainnet','testnet')[testnet]][0] + hexaddr
	lzeroes = (len(s) - len(s.lstrip('0'))) / 2
	return ('1' * lzeroes) + _numtob58(int(s+hash256(s)[:8],16))

def wif2hex(wif,testnet=None):
	testnet = testnet if testnet != None else g.testnet # allow override
	num = _b58tonum(wif)
	if num == False: return False
	key = '{:x}'.format(num)
	compressed = wif[0] != btc_uncompressed_wif_pfxs[('mainnet','testnet')[testnet]]
	klen = (66,68)[bool(compressed)]
	if compressed and key[66:68] != '01': return False
	if (key[:2] == btc_privkey_pfxs[('mainnet','testnet')[testnet]] and key[klen:] == hash256(key[:klen])[:8]):
		return {'hex':key[2:66],'compressed':compressed,'testnet':testnet}
	else:
		return False

def hex2wif(hexpriv,compressed=False,testnet=None):
	testnet = testnet if testnet != None else g.testnet # allow override
	s = btc_privkey_pfxs[('mainnet','testnet')[testnet]] + hexpriv + ('','01')[bool(compressed)]
	return _numtob58(int(s+hash256(s)[:8],16))

# devdoc/guide_wallets.md:
# Uncompressed public keys start with 0x04; compressed public keys begin with
# 0x03 or 0x02 depending on whether they're greater or less than the midpoint
# of the curve.
def privnum2pubhex(numpriv,compressed=False):
	pko = ecdsa.SigningKey.from_secret_exponent(numpriv,_secp256k1)
	# pubkey = 32-byte X coord + 32-byte Y coord (unsigned big-endian)
	pubkey = hexlify(pko.get_verifying_key().to_string())
	if compressed: # discard Y coord, replace with appropriate version byte
		# even Y: <0, odd Y: >0 -- https://bitcointalk.org/index.php?topic=129652.0
		p = ('03','02')[pubkey[-1] in '02468ace']
		return p+pubkey[:64]
	else:
		return '04'+pubkey

def privnum2addr(numpriv,compressed=False,segwit=False): # used only by tool and testsuite
	pubhex = privnum2pubhex(numpriv,compressed)
	return pubhex2segwitaddr(pubhex) if segwit else hexaddr2addr(hash160(pubhex))

# Segwit:
def pubhex2redeem_script(pubhex):
	# https://bitcoincore.org/en/segwit_wallet_dev/
	# The P2SH redeemScript is always 22 bytes. It starts with a OP_0, followed
	# by a canonical push of the keyhash (i.e. 0x0014{20-byte keyhash})
	return '0014' + hash160(pubhex)

def pubhex2segwitaddr(pubhex):
	return hexaddr2addr(hash160(pubhex2redeem_script(pubhex)),p2sh=True)
