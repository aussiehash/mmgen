#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
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
test/test.py:  Test suite for the MMGen suite
"""

import sys,os,subprocess,shutil,time,re

pn = os.path.dirname(sys.argv[0])
os.chdir(os.path.join(pn,os.pardir))
sys.path.__setitem__(0,os.path.abspath(os.curdir))

# Import these _after_ local path's been added to sys.path
from mmgen.common import *
from mmgen.test import *

g.quiet = False # if 'quiet' was set in config file, disable here
os.environ['MMGEN_QUIET'] = '0' # and for the spawned scripts

log_file = 'test.py_log'

hincog_fn      = 'rand_data'
hincog_bytes   = 1024*1024
hincog_offset  = 98765
hincog_seedlen = 256

incog_id_fn  = 'incog_id'
non_mmgen_fn = 'btckey'
pwfile = 'passwd_file'

ref_dir = os.path.join('test','ref')

ref_wallet_brainpass = 'abc'
ref_wallet_hash_preset = '1'
ref_wallet_incog_offset = 123

from mmgen.obj import MMGenTXLabel,PrivKey,BTCAmt
from mmgen.addr import AddrGenerator,KeyGenerator,AddrList,AddrData,AddrIdxList
ref_tx_label = ''.join([unichr(i) for i in  range(65,91) +
											range(1040,1072) + # cyrillic
											range(913,939) +   # greek
											range(97,123)])[:MMGenTXLabel.max_len]
tx_fee             = '0.0001'
ref_bw_hash_preset = '1'
ref_bw_file        = 'wallet.mmbrain'
ref_bw_file_spc    = 'wallet-spaced.mmbrain'

ref_kafile_pass        = 'kafile password'
ref_kafile_hash_preset = '1'

ref_enc_fn = 'sample-text.mmenc'
tool_enc_passwd = "Scrypt it, don't hash it!"
sample_text = \
	'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks\n'

# Laggy flash media cause pexpect to crash, so create a temporary directory
# under '/dev/shm' and put datadir and temp files here.
shortopts = ''.join([e[1:] for e in sys.argv if len(e) > 1 and e[0] == '-' and e[1] != '-'])
shortopts = ['-'+e for e in list(shortopts)]
data_dir = os.path.join('test','data_dir')

if not any(e in ('--skip-deps','--resume','-S','-r') for e in sys.argv+shortopts):
	if g.platform == 'win':
		try: os.listdir(data_dir)
		except: pass
		else:
			try: shutil.rmtree(data_dir)
			except: # we couldn't remove data dir - perhaps regtest daemon is running
				try: subprocess.call(['python','mmgen-regtest','stop'])
				except: rdie(1,'Unable to remove data dir!')
				else:
					time.sleep(2)
					shutil.rmtree(data_dir)
		os.mkdir(data_dir,0755)
	else:
		d,pfx = '/dev/shm','mmgen-test-'
		try:
			subprocess.call('rm -rf %s/%s*'%(d,pfx),shell=True)
		except Exception as e:
			die(2,'Unable to delete directory tree %s/%s* (%s)'%(d,pfx,e))
		try:
			import tempfile
			shm_dir = tempfile.mkdtemp('',pfx,d)
		except Exception as e:
			die(2,'Unable to create temporary directory in %s (%s)'%(d,e))
		dd = os.path.join(shm_dir,'data_dir')
		os.mkdir(dd,0755)
		try: os.unlink(data_dir)
		except: pass
		os.symlink(dd,data_dir)

opts_data = lambda: {
	'desc': 'Test suite for the MMGen suite',
	'usage':'[options] [command(s) or metacommand(s)]',
	'options': """
-h, --help          Print this help message
--, --longhelp      Print help message for long options (common options)
-b, --buf-keypress  Use buffered keypresses as with real human input
-c, --print-cmdline Print the command line of each spawned command
-d, --debug-scripts Turn on debugging output in executed scripts
-x, --debug-pexpect Produce debugging output for pexpect calls
-D, --direct-exec   Bypass pexpect and execute a command directly (for
                    debugging only)
-e, --exact-output  Show the exact output of the MMGen script(s) being run
-g, --segwit        Generate and use Segwit addresses
-G, --segwit-random Generate and use a random mix of Segwit and Legacy addrs
-l, --list-cmds     List and describe the commands in the test suite
-L, --log           Log commands to file {lf}
-n, --names         Display command names instead of descriptions
-O, --popen-spawn   Use pexpect's popen_spawn instead of popen (always true, so ignored)
-p, --pause         Pause between tests, resuming on keypress
-P, --profile       Record the execution time of each script
-q, --quiet         Produce minimal output.  Suppress dependency info
-r, --resume=c      Resume at command 'c' after interrupted run
-s, --system        Test scripts and modules installed on system rather
                    than those in the repo root
-S, --skip-deps     Skip dependency checking for command
-u, --usr-random    Get random data interactively from user
-t, --traceback     Run the command inside the '{tbc}' script
-v, --verbose       Produce more verbose output
-W, --no-dw-delete  Don't remove default wallet from data dir after dw tests are done
""".format(tbc=g.traceback_cmd,lf=log_file),
	'notes': """

If no command is given, the whole suite of tests is run.
"""
}

sys.argv = [sys.argv[0]] + ['--data-dir',data_dir] + sys.argv[1:]

cmd_args = opts.init(opts_data)
opt.popen_spawn = True # popen has issues, so use popen_spawn always

tn_desc = ('','.testnet')[g.testnet]

def randbool():
	return hexlify(os.urandom(1))[1] in '12345678'
def get_segwit_val():
	return randbool() if opt.segwit_random else True if opt.segwit else False

cfgs = {
	'15': {
		'tmpdir':        os.path.join('test','tmp15'),
		'wpasswd':       'Dorian',
		'kapasswd':      'Grok the blockchain',
		'addr_idx_list': '12,99,5-10,5,12', # 8 addresses
		'dep_generators':  {
			pwfile:        'walletgen_dfl_wallet',
			'addrs':       'addrgen_dfl_wallet',
			'rawtx':       'txcreate_dfl_wallet',
			'sigtx':       'txsign_dfl_wallet',
			'mmseed':      'export_seed_dfl_wallet',
			'del_dw_run':  'delete_dfl_wallet',
		},
		'segwit': get_segwit_val()
	},
	'16': {
		'tmpdir':        os.path.join('test','tmp16'),
		'wpasswd':       'My changed password',
		'hash_preset':   '2',
		'dep_generators': {
			pwfile:        'passchg_dfl_wallet',
		},
		'segwit': get_segwit_val()
	},
	'17': {
		'tmpdir':        os.path.join('test','tmp17'),
	},
	'1': {
		'tmpdir':        os.path.join('test','tmp1'),
		'wpasswd':       'Dorian',
		'kapasswd':      'Grok the blockchain',
		'addr_idx_list': '12,99,5-10,5,12', # 8 addresses
		'dep_generators':  {
			pwfile:        'walletgen',
			'mmdat':       'walletgen',
			'addrs':       'addrgen',
			'rawtx':       'txcreate',
			'txbump':      'txbump',
			'sigtx':       'txsign',
			'mmwords':     'export_mnemonic',
			'mmseed':      'export_seed',
			'mmhex':       'export_hex',
			'mmincog':     'export_incog',
			'mmincox':     'export_incog_hex',
			hincog_fn:     'export_incog_hidden',
			incog_id_fn:   'export_incog_hidden',
			'akeys.mmenc': 'keyaddrgen'
		},
		'segwit': get_segwit_val()
	},
	'2': {
		'tmpdir':        os.path.join('test','tmp2'),
		'wpasswd':       'Hodling away',
		'addr_idx_list': '37,45,3-6,22-23',  # 8 addresses
		'seed_len':      128,
		'dep_generators': {
			'mmdat':       'walletgen2',
			'addrs':       'addrgen2',
			'rawtx':         'txcreate2',
			'sigtx':         'txsign2',
			'mmwords':     'export_mnemonic2',
		},
		'segwit': get_segwit_val()
	},
	'3': {
		'tmpdir':        os.path.join('test','tmp3'),
		'wpasswd':       'Major miner',
		'addr_idx_list': '73,54,1022-1023,2-5', # 8 addresses
		'dep_generators': {
			'mmdat':       'walletgen3',
			'addrs':       'addrgen3',
			'rawtx':         'txcreate3',
			'sigtx':         'txsign3'
		},
		'segwit': get_segwit_val()
	},
	'4': {
		'tmpdir':        os.path.join('test','tmp4'),
		'wpasswd':       'Hashrate good',
		'addr_idx_list': '63,1004,542-544,7-9', # 8 addresses
		'seed_len':      192,
		'dep_generators': {
			'mmdat':       'walletgen4',
			'mmbrain':     'walletgen4',
			'addrs':       'addrgen4',
			'rawtx':       'txcreate4',
			'sigtx':       'txsign4',
			'txdo':        'txdo4',
		},
		'bw_filename': 'brainwallet.mmbrain',
		'bw_params':   '192,1',
		'segwit': get_segwit_val()
	},
	'14': {
		'kapasswd':      'Maxwell',
		'tmpdir':        os.path.join('test','tmp14'),
		'wpasswd':       'The Halving',
		'addr_idx_list': '61,998,502-504,7-9', # 8 addresses
		'seed_len':      256,
		'dep_generators': {
			'mmdat':       'walletgen14',
			'addrs':       'addrgen14',
			'akeys.mmenc': 'keyaddrgen14',
		},
		'segwit': get_segwit_val()
	},
	'5': {
		'tmpdir':        os.path.join('test','tmp5'),
		'wpasswd':       'My changed password',
		'hash_preset':   '2',
		'dep_generators': {
			'mmdat':       'passchg',
			pwfile:        'passchg',
		},
		'segwit': get_segwit_val()
	},
	'6': {
		'name':            'reference wallet check (128-bit)',
		'seed_len':        128,
		'seed_id':         'FE3C6545',
		'ref_bw_seed_id':  '33F10310',
		'addrfile_chk':            ('B230 7526 638F 38CB','B64D 7327 EF2A 60FE'),
		'addrfile_segwit_chk':     ('9914 6D10 2307 F348','7DBF 441F E188 8B37'),
		'addrfile_compressed_chk': ('95EB 8CC0 7B3B 7856','629D FDE4 CDC0 F276'),
		'keyaddrfile_chk':            ('CF83 32FB 8A8B 08E2','FEBF 7878 97BB CC35'),
		'keyaddrfile_segwit_chk':     ('C13B F717 D4E8 CF59','4DB5 BAF0 45B7 6E81'),
		'keyaddrfile_compressed_chk': ('E43A FA46 5751 720A','B995 A6CF D1CD FAD0'),
		'passfile_chk':    'EB29 DC4F 924B 289F',
		'passfile32_chk':  '37B6 C218 2ABC 7508',
		'wpasswd':         'reference password',
		'ref_wallet':      'FE3C6545-D782B529[128,1].mmdat',
		'ic_wallet':       'FE3C6545-E29303EA-5E229E30[128,1].mmincog',
		'ic_wallet_hex':   'FE3C6545-BC4BE3F2-32586837[128,1].mmincox',

		'hic_wallet':       'FE3C6545-161E495F-BEB7548E[128,1].incog-offset123',
		'hic_wallet_old':   'FE3C6545-161E495F-9860A85B[128,1].incog-old.offset123',

		'tmpdir':        os.path.join('test','tmp6'),
		'kapasswd':      '',
		'addr_idx_list': '1010,500-501,31-33,1,33,500,1011', # 8 addresses
		'pass_idx_list': '1,4,9-11,1100',
		'dep_generators':  {
			'mmdat':       'refwalletgen1',
			pwfile:       'refwalletgen1',
			'addrs':       'refaddrgen1',
			'akeys.mmenc': 'refkeyaddrgen1'
		},
		'segwit': get_segwit_val()
	},
	'7': {
		'name':            'reference wallet check (192-bit)',
		'seed_len':        192,
		'seed_id':         '1378FC64',
		'ref_bw_seed_id':  'CE918388',
		'addrfile_chk':            ('8C17 A5FA 0470 6E89','0A59 C8CD 9439 8B81'),
		'addrfile_segwit_chk':     ('91C4 0414 89E4 2089','3BA6 7494 8E2B 858D'),
		'addrfile_compressed_chk': ('2615 8401 2E98 7ECA','DF38 22AB AAB0 124E'),
		'keyaddrfile_chk':            ('9648 5132 B98E 3AD9','2F72 C83F 44C5 0FAC'),
		'keyaddrfile_segwit_chk':     ('C98B DF08 A3D5 204B','25F2 AEB6 AAAC 8BBE'),
		'keyaddrfile_compressed_chk': ('6D6D 3D35 04FD B9C3','B345 9CD8 9EAE 5489'),
		'passfile_chk':    'ADEA 0083 094D 489A',
		'passfile32_chk':  '2A28 C5C7 36EC 217A',
		'wpasswd':         'reference password',
		'ref_wallet':      '1378FC64-6F0F9BB4[192,1].mmdat',
		'ic_wallet':       '1378FC64-2907DE97-F980D21F[192,1].mmincog',
		'ic_wallet_hex':   '1378FC64-4DCB5174-872806A7[192,1].mmincox',

		'hic_wallet':       '1378FC64-B55E9958-77256FC1[192,1].incog.offset123',
		'hic_wallet_old':   '1378FC64-B55E9958-D85FF20C[192,1].incog-old.offset123',

		'tmpdir':        os.path.join('test','tmp7'),
		'kapasswd':      '',
		'addr_idx_list': '1010,500-501,31-33,1,33,500,1011', # 8 addresses
		'pass_idx_list': '1,4,9-11,1100',
		'dep_generators':  {
			'mmdat':       'refwalletgen2',
			pwfile:       'refwalletgen2',
			'addrs':       'refaddrgen2',
			'akeys.mmenc': 'refkeyaddrgen2'
		},
		'segwit': get_segwit_val()
	},
	'8': {
		'name':            'reference wallet check (256-bit)',
		'seed_len':        256,
		'seed_id':         '98831F3A',
		'ref_bw_seed_id':  'B48CD7FC',
		'addrfile_chk':            ('6FEF 6FB9 7B13 5D91','3C2C 8558 BB54 079E'),
		'addrfile_segwit_chk':     ('06C1 9C87 F25C 4EE6','58D1 7B6C E9F9 9C14'),
		'addrfile_compressed_chk': ('A33C 4FDE F515 F5BC','5186 02C2 535E B7D5'),
		'keyaddrfile_chk':            ('9F2D D781 1812 8BAD','7410 8F95 4B33 B4B2'),
		'keyaddrfile_segwit_chk':     ('A447 12C2 DD14 5A9B','0690 460D A600 D315'),
		'keyaddrfile_compressed_chk': ('420A 8EB5 A9E2 7814','3243 DD92 809E FE8D'),
		'passfile_chk':    '2D6D 8FBA 422E 1315',
		'passfile32_chk':  'F6C1 CDFB 97D9 FCAE',
		'wpasswd':         'reference password',
		'ref_wallet':      '98831F3A-{}[256,1].mmdat'.format(('27F2BF93','E2687906')[g.testnet]),
		'ref_addrfile':    '98831F3A[1,31-33,500-501,1010-1011]{}.addrs'.format(tn_desc),
		'ref_segwitaddrfile':'98831F3A-S[1,31-33,500-501,1010-1011]{}.addrs'.format(tn_desc),
		'ref_keyaddrfile': '98831F3A[1,31-33,500-501,1010-1011]{}.akeys.mmenc'.format(tn_desc),
		'ref_passwdfile':  '98831F3A-фубар@crypto.org-b58-20[1,4,9-11,1100].pws',
		'ref_addrfile_chksum':    ('6FEF 6FB9 7B13 5D91','3C2C 8558 BB54 079E')[g.testnet],
		'ref_segwitaddrfile_chksum':('06C1 9C87 F25C 4EE6','58D1 7B6C E9F9 9C14')[g.testnet],
		'ref_keyaddrfile_chksum': ('9F2D D781 1812 8BAD','7410 8F95 4B33 B4B2')[g.testnet],
		'ref_passwdfile_chksum':  'A983 DAB9 5514 27FB',
#		'ref_fake_unspent_data':'98831F3A_unspent.json',
		'ref_tx_file':     'FFB367[1.234]{}.rawtx'.format(tn_desc),
		'ic_wallet':       '98831F3A-5482381C-18460FB1[256,1].mmincog',
		'ic_wallet_hex':   '98831F3A-1630A9F2-870376A9[256,1].mmincox',

		'hic_wallet':       '98831F3A-F59B07A0-559CEF19[256,1].incog.offset123',
		'hic_wallet_old':   '98831F3A-F59B07A0-848535F3[256,1].incog-old.offset123',

		'tmpdir':        os.path.join('test','tmp8'),
		'kapasswd':      '',
		'addr_idx_list': '1010,500-501,31-33,1,33,500,1011', # 8 addresses
		'pass_idx_list': '1,4,9-11,1100',

		'dep_generators':  {
			'mmdat':       'refwalletgen3',
			pwfile:       'refwalletgen3',
			'addrs':       'refaddrgen3',
			'akeys.mmenc': 'refkeyaddrgen3'
		},
		'segwit': get_segwit_val()
	},
	'9': {
		'tmpdir':        os.path.join('test','tmp9'),
		'tool_enc_infn':      'tool_encrypt.in',
#		'tool_enc_ref_infn':  'tool_encrypt_ref.in',
		'wpasswd':         'reference password',
		'dep_generators': {
			'tool_encrypt.in':            'tool_encrypt',
			'tool_encrypt.in.mmenc':      'tool_encrypt',
#			'tool_encrypt_ref.in':        'tool_encrypt_ref',
#			'tool_encrypt_ref.in.mmenc':  'tool_encrypt_ref',
		},
	},
}

from copy import deepcopy
for a,b in (('6','11'),('7','12'),('8','13')):
	cfgs[b] = deepcopy(cfgs[a])
	cfgs[b]['tmpdir'] = os.path.join('test','tmp'+b)

from collections import OrderedDict

cmd_group = OrderedDict()

cmd_group['help'] = OrderedDict([
#     test               description                  depends
	['helpscreens',     (1,'help screens',             [],1)],
	['longhelpscreens', (1,'help screens (--longhelp)',[],1)],
])

cmd_group['dfl_wallet'] = OrderedDict([
	['walletgen_dfl_wallet', (15,'wallet generation (default wallet)',[[[],15]],1)],
	['export_seed_dfl_wallet',(15,'seed export to mmseed format (default wallet)',[[[pwfile],15]],1)],
	['addrgen_dfl_wallet',(15,'address generation (default wallet)',[[[pwfile],15]],1)],
	['txcreate_dfl_wallet',(15,'transaction creation (default wallet)',[[['addrs'],15]],1)],
	['txsign_dfl_wallet',(15,'transaction signing (default wallet)',[[['rawtx',pwfile],15]],1)],
	['passchg_dfl_wallet',(16,'password, label and hash preset change (default wallet)',[[[pwfile],15]],1)],
	['walletchk_newpass_dfl_wallet',(16,'wallet check with new pw, label and hash preset',[[[pwfile],16]],1)],
	['delete_dfl_wallet',(15,'delete default wallet',[[[pwfile],15]],1)],
])

cmd_group['main'] = OrderedDict([
	['walletgen',       (1,'wallet generation',        [[['del_dw_run'],15]],1)],
#	['walletchk',       (1,'wallet check',             [[['mmdat'],1]])],
	['passchg',         (5,'password, label and hash preset change',[[['mmdat',pwfile],1]],1)],
	['walletchk_newpass',(5,'wallet check with new pw, label and hash preset',[[['mmdat',pwfile],5]],1)],
	['addrgen',         (1,'address generation',       [[['mmdat',pwfile],1]],1)],
	['addrimport',      (1,'address import',           [[['addrs'],1]],1)],
	['txcreate',        (1,'transaction creation',     [[['addrs'],1]],1)],
	['txbump',          (1,'transaction fee bumping (no send)',[[['rawtx'],1]],1)],
	['txsign',          (1,'transaction signing',      [[['mmdat','rawtx',pwfile,'txbump'],1]],1)],
	['txsend',          (1,'transaction sending',      [[['sigtx'],1]])],
	# txdo must go after txsign
	['txdo',            (1,'online transaction',       [[['sigtx','mmdat'],1]])],

	['export_hex',      (1,'seed export to hexadecimal format',  [[['mmdat'],1]])],
	['export_seed',     (1,'seed export to mmseed format',   [[['mmdat'],1]])],
	['export_mnemonic', (1,'seed export to mmwords format',  [[['mmdat'],1]])],
	['export_incog',    (1,'seed export to mmincog format',  [[['mmdat'],1]])],
	['export_incog_hex',(1,'seed export to mmincog hex format', [[['mmdat'],1]])],
	['export_incog_hidden',(1,'seed export to hidden mmincog format', [[['mmdat'],1]])],

	['addrgen_hex',     (1,'address generation from mmhex file', [[['mmhex','addrs'],1]])],
	['addrgen_seed',    (1,'address generation from mmseed file', [[['mmseed','addrs'],1]])],
	['addrgen_mnemonic',(1,'address generation from mmwords file',[[['mmwords','addrs'],1]])],
	['addrgen_incog',   (1,'address generation from mmincog file',[[['mmincog','addrs'],1]])],
	['addrgen_incog_hex',(1,'address generation from mmincog hex file',[[['mmincox','addrs'],1]])],
	['addrgen_incog_hidden',(1,'address generation from hidden mmincog file', [[[hincog_fn,'addrs'],1]])],

	['keyaddrgen',    (1,'key-address file generation', [[['mmdat',pwfile],1]])],
	['txsign_keyaddr',(1,'transaction signing with key-address file', [[['akeys.mmenc','rawtx'],1]])],

	['walletgen2',(2,'wallet generation (2), 128-bit seed',     [[['del_dw_run'],15]])],
	['addrgen2',  (2,'address generation (2)',    [[['mmdat'],2]])],
	['txcreate2', (2,'transaction creation (2)',  [[['addrs'],2]])],
	['txsign2',   (2,'transaction signing, two transactions',[[['mmdat','rawtx'],1],[['mmdat','rawtx'],2]])],
	['export_mnemonic2', (2,'seed export to mmwords format (2)',[[['mmdat'],2]])],

	['walletgen3',(3,'wallet generation (3)',                  [[['del_dw_run'],15]])],
	['addrgen3',  (3,'address generation (3)',                 [[['mmdat'],3]])],
	['txcreate3', (3,'tx creation with inputs and outputs from two wallets', [[['addrs'],1],[['addrs'],3]])],
	['txsign3',   (3,'tx signing with inputs and outputs from two wallets',[[['mmdat'],1],[['mmdat','rawtx'],3]])],

	['walletgen14', (14,'wallet generation (14)',        [[['del_dw_run'],15]],14)],
	['addrgen14',   (14,'address generation (14)',        [[['mmdat'],14]])],
	['keyaddrgen14',(14,'key-address file generation (14)', [[['mmdat'],14]],14)],
	['walletgen4',(4,'wallet generation (4) (brainwallet)',    [[['del_dw_run'],15]])],
	['addrgen4',  (4,'address generation (4)',                 [[['mmdat'],4]])],
	['txcreate4', (4,'tx creation with inputs and outputs from four seed sources, key-address file and non-MMGen inputs and outputs', [[['addrs'],1],[['addrs'],2],[['addrs'],3],[['addrs'],4],[['addrs','akeys.mmenc'],14]])],
	['txsign4',   (4,'tx signing with inputs and outputs from incog file, mnemonic file, wallet, brainwallet, key-address file and non-MMGen inputs and outputs', [[['mmincog'],1],[['mmwords'],2],[['mmdat'],3],[['mmbrain','rawtx'],4],[['akeys.mmenc'],14]])],
	['txdo4', (4,'tx creation,signing and sending with inputs and outputs from four seed sources, key-address file and non-MMGen inputs and outputs', [[['addrs'],1],[['addrs'],2],[['addrs'],3],[['addrs'],4],[['addrs','akeys.mmenc'],14],[['mmincog'],1],[['mmwords'],2],[['mmdat'],3],[['mmbrain','rawtx'],4],[['akeys.mmenc'],14]])], # must go after txsign4
	['txbump4', (4,'tx fee bump + send with inputs and outputs from four seed sources, key-address file and non-MMGen inputs and outputs', [[['akeys.mmenc'],14],[['mmincog'],1],[['mmwords'],2],[['mmdat'],3],[['akeys.mmenc'],14],[['mmbrain','sigtx','mmdat','txdo'],4]])], # must go after txsign4
])

cmd_group['tool'] = OrderedDict([
	['tool_encrypt',     (9,"'mmgen-tool encrypt' (random data)",     [],1)],
	['tool_decrypt',     (9,"'mmgen-tool decrypt' (random data)", [[[cfgs['9']['tool_enc_infn'],cfgs['9']['tool_enc_infn']+'.mmenc'],9]],1)],
#	['tool_encrypt_ref', (9,"'mmgen-tool encrypt' (reference text)",  [])],
	['tool_find_incog_data', (9,"'mmgen-tool find_incog_data'", [[[hincog_fn],1],[[incog_id_fn],1]])],
#	['pywallet', (9,"'mmgen-pywallet'", [],1)],
])

# saved reference data
cmd_group['ref'] = (
	# reading
	('ref_wallet_chk', ([],'saved reference wallet')),
	('ref_seed_chk',   ([],'saved seed file')),
	('ref_hex_chk',    ([],'saved mmhex file')),
	('ref_mn_chk',     ([],'saved mnemonic file')),
	('ref_hincog_chk', ([],'saved hidden incog reference wallet')),
	('ref_brain_chk',  ([],'saved brainwallet')),
	# generating new reference ('abc' brainwallet) files:
	('refwalletgen',   ([],'gen new refwallet')),
	('refaddrgen',     (['mmdat',pwfile],'new refwallet addr chksum')),
	('refkeyaddrgen',  (['mmdat',pwfile],'new refwallet key-addr chksum')),
	('refaddrgen_compressed',    (['mmdat',pwfile],'new refwallet addr chksum (compressed)')),
	('refkeyaddrgen_compressed', (['mmdat',pwfile],'new refwallet key-addr chksum (compressed)')),
	('refpasswdgen',   (['mmdat',pwfile],'new refwallet passwd file chksum')),
	('ref_b32passwdgen',(['mmdat',pwfile],'new refwallet passwd file chksum (base32)')),
)

# misc. saved reference data
cmd_group['ref_other'] = (
	('ref_addrfile_chk',   'saved reference address file'),
	('ref_segwitaddrfile_chk','saved reference address file (segwit)'),
	('ref_keyaddrfile_chk','saved reference key-address file'),
	('ref_passwdfile_chk', 'saved reference password file'),
#	Create the fake inputs:
#	('txcreate8',          'transaction creation (8)'),
	('ref_tx_chk',         'saved reference tx file'),
	('ref_brain_chk_spc3', 'saved brainwallet (non-standard spacing)'),
	('ref_tool_decrypt',   'decryption of saved MMGen-encrypted file'),
)

# mmgen-walletconv:
cmd_group['conv_in'] = ( # reading
	('ref_wallet_conv',    'conversion of saved reference wallet'),
	('ref_mn_conv',        'conversion of saved mnemonic'),
	('ref_seed_conv',      'conversion of saved seed file'),
	('ref_hex_conv',       'conversion of saved hexadecimal seed file'),
	('ref_brain_conv',     'conversion of ref brainwallet'),
	('ref_incog_conv',     'conversion of saved incog wallet'),
	('ref_incox_conv',     'conversion of saved hex incog wallet'),
	('ref_hincog_conv',    'conversion of saved hidden incog wallet'),
	('ref_hincog_conv_old','conversion of saved hidden incog wallet (old format)')
)

cmd_group['conv_out'] = ( # writing
	('ref_wallet_conv_out', 'ref seed conversion to wallet'),
	('ref_mn_conv_out',     'ref seed conversion to mnemonic'),
	('ref_hex_conv_out',    'ref seed conversion to hex seed'),
	('ref_seed_conv_out',   'ref seed conversion to seed'),
	('ref_incog_conv_out',  'ref seed conversion to incog data'),
	('ref_incox_conv_out',  'ref seed conversion to hex incog data'),
	('ref_hincog_conv_out', 'ref seed conversion to hidden incog data')
)

cmd_group['regtest'] = (
	('regtest_setup',              'regtest (Bob and Alice) mode setup'),
	('regtest_walletgen_bob',      'wallet generation (Bob)'),
	('regtest_walletgen_alice',    'wallet generation (Alice)'),
	('regtest_addrgen_bob',        'address generation (Bob)'),
	('regtest_addrgen_alice',      'address generation (Alice)'),
	('regtest_addrimport_bob',     "importing Bob's addresses"),
	('regtest_addrimport_alice',   "importing Alice's addresses"),
	('regtest_fund_bob',           "funding Bob's wallet"),
	('regtest_fund_alice',         "funding Alice's wallet"),
	('regtest_bob_bal1',           "Bob's balance"),
	('regtest_bob_split1',         "splitting Bob's funds"),
	('regtest_generate',           'mining a block'),
	('regtest_bob_bal2',           "Bob's balance"),
	('regtest_bob_rbf_send',       'sending funds to Alice (RBF)'),
	('regtest_get_mempool1',       'mempool (before RBF bump)'),
	('regtest_bob_rbf_bump',       'bumping RBF transaction'),
	('regtest_get_mempool2',       'mempool (after RBF bump)'),
	('regtest_generate',           'mining a block'),
	('regtest_bob_bal3',           "Bob's balance"),
	('regtest_bob_pre_import',     'sending to non-imported address'),
	('regtest_generate',           'mining a block'),
	('regtest_bob_import_addr',    'importing non-MMGen address with --rescan'),
	('regtest_bob_bal4',           "Bob's balance (after import with rescan)"),
	('regtest_bob_import_list',    'importing flat address list'),
	('regtest_bob_split2',         "splitting Bob's funds"),
	('regtest_generate',           'mining a block'),
	('regtest_bob_bal5',           "Bob's balance"),
	('regtest_bob_send_non_mmgen', 'sending funds to Alice (from non-MMGen addrs)'),
	('regtest_generate',           'mining a block'),
	('regtest_bob_alice_bal',      "Bob and Alice's balances"),
	('regtest_alice_add_label1',   'adding a label'),
	('regtest_alice_chk_label1',   'the label'),
	('regtest_alice_add_label2',   'adding a label'),
	('regtest_alice_chk_label2',   'the label'),
	('regtest_alice_edit_label1',  'editing a label'),
	('regtest_alice_chk_label3',   'the label'),
	('regtest_alice_remove_label1','removing a label'),
	('regtest_alice_chk_label4',   'the label'),
	('regtest_stop',               'stopping regtest daemon'),
)

cmd_list = OrderedDict()
for k in cmd_group: cmd_list[k] = []

cmd_data = OrderedDict()
for k,v in (
		('help', ('help screens',[])),
		('dfl_wallet', ('basic operations with default wallet',[15,16])),
		('main', ('basic operations',[1,2,3,4,5,15,16])),
		('tool', ('tools',[9]))
	):
	cmd_data['info_'+k] = v
	for i in cmd_group[k]:
		cmd_list[k].append(i)
		cmd_data[i] = cmd_group[k][i]

cmd_data['info_ref'] = 'reference data',[6,7,8]
for a,b in cmd_group['ref']:
	for i,j in ((1,128),(2,192),(3,256)):
		k = a+str(i)
		cmd_list['ref'].append(k)
		cmd_data[k] = (5+i,'%s (%s-bit)' % (b[1],j),[[b[0],5+i]])

cmd_data['info_ref_other'] = 'other reference data',[8]
for a,b in cmd_group['ref_other']:
	cmd_list['ref_other'].append(a)
	cmd_data[a] = (8,b,[[[],8]])

cmd_data['info_conv_in'] = 'wallet conversion from reference data',[11,12,13]
for a,b in cmd_group['conv_in']:
	for i,j in ((1,128),(2,192),(3,256)):
		k = a+str(i)
		cmd_list['conv_in'].append(k)
		cmd_data[k] = (10+i,'%s (%s-bit)' % (b,j),[[[],10+i]])

cmd_data['info_conv_out'] = 'wallet conversion to reference data',[11,12,13]
for a,b in cmd_group['conv_out']:
	for i,j in ((1,128),(2,192),(3,256)):
		k = a+str(i)
		cmd_list['conv_out'].append(k)
		cmd_data[k] = (10+i,'%s (%s-bit)' % (b,j),[[[],10+i]])

cmd_data['info_regtest'] = 'regtest mode',[17]
for a,b in cmd_group['regtest']:
	cmd_list['regtest'].append(a)
	cmd_data[a] = (17,b,[[[],17]])

utils = {
	'check_deps': 'check dependencies for specified command',
	'clean':      'clean specified tmp dir(s) 1,2,3,4,5 or 6 (no arg = all dirs)',
}

addrs_per_wallet = 8

# total of two outputs must be < 10 BTC
for k in cfgs:
	cfgs[k]['amts'] = [0,0]
	for idx,mod in ((0,6),(1,4)):
		cfgs[k]['amts'][idx] = '%s.%s' % ((getrandnum(2) % mod), str(getrandnum(4))[:5])

meta_cmds = OrderedDict([
	['ref1', ('refwalletgen1','refaddrgen1','refkeyaddrgen1')],
	['ref2', ('refwalletgen2','refaddrgen2','refkeyaddrgen2')],
	['ref3', ('refwalletgen3','refaddrgen3','refkeyaddrgen3')],
	['gen',  ('walletgen','addrgen')],
	['pass', ('passchg','walletchk_newpass')],
	['tx',   ('addrimport','txcreate','txsign','txsend')],
	['export', [k for k in cmd_data if k[:7] == 'export_' and cmd_data[k][0] == 1]],
	['gen_sp', [k for k in cmd_data if k[:8] == 'addrgen_' and cmd_data[k][0] == 1]],
	['online', ('keyaddrgen','txsign_keyaddr')],
	['2', [k for k in cmd_data if cmd_data[k][0] == 2]],
	['3', [k for k in cmd_data if cmd_data[k][0] == 3]],
	['4', [k for k in cmd_data if cmd_data[k][0] == 4]],

	['saved_ref1', [c[0]+'1' for c in cmd_group['ref']]],
	['saved_ref2', [c[0]+'2' for c in cmd_group['ref']]],
	['saved_ref3', [c[0]+'3' for c in cmd_group['ref']]],

	['saved_ref_other', [c[0] for c in cmd_group['ref_other']]],

	['saved_ref_conv_in1', [c[0]+'1' for c in cmd_group['conv_in']]],
	['saved_ref_conv_in2', [c[0]+'2' for c in cmd_group['conv_in']]],
	['saved_ref_conv_in3', [c[0]+'3' for c in cmd_group['conv_in']]],

	['saved_ref_conv_out1', [c[0]+'1' for c in cmd_group['conv_out']]],
	['saved_ref_conv_out2', [c[0]+'2' for c in cmd_group['conv_out']]],
	['saved_ref_conv_out3', [c[0]+'3' for c in cmd_group['conv_out']]],

	['regtest', dict(cmd_group['regtest']).keys()],
])

del cmd_group

if opt.profile: opt.names = True
if opt.resume: opt.skip_deps = True
if opt.log:
	log_fd = open(log_file,'a')
	log_fd.write('\nLog started: %s\n' % make_timestr())

usr_rand_chars = (5,30)[bool(opt.usr_random)]
usr_rand_arg = '-r%s' % usr_rand_chars
cmd_total = 0

if opt.system: sys.path.pop(0)

# Disable color in spawned scripts so we can parse their output
os.environ['MMGEN_DISABLE_COLOR'] = '1'
os.environ['MMGEN_NO_LICENSE'] = '1'
os.environ['MMGEN_MIN_URANDCHARS'] = '3'
os.environ['MMGEN_BOGUS_SEND'] = '1'

def get_segwit_arg(cfg): return ([],['--type','segwit'])[cfg['segwit']]

# Tell spawned programs they're running in the test suite
os.environ['MMGEN_TEST_SUITE'] = '1'

if opt.debug_scripts: os.environ['MMGEN_DEBUG'] = '1'

if opt.exact_output:
	def msg(s): pass
	vmsg = vmsg_r = msg_r = msg
else:
	def msg(s): sys.stderr.write(s+'\n')
	def vmsg(s):
		if opt.verbose: sys.stderr.write(s+'\n')
	def msg_r(s): sys.stderr.write(s)
	def vmsg_r(s):
		if opt.verbose: sys.stderr.write(s)

stderr_save = sys.stderr

def silence():
	if not (opt.verbose or opt.exact_output):
		f = ('/dev/null','stderr.out')[g.platform=='win']
		sys.stderr = open(f,'a')

def end_silence():
	if not (opt.verbose or opt.exact_output):
		sys.stderr = stderr_save

def errmsg(s): stderr_save.write(s+'\n')
def errmsg_r(s): stderr_save.write(s)

if opt.list_cmds:
	fs = '  {:<{w}} - {}'
	Msg(green('AVAILABLE COMMANDS:'))
	w = max([len(i) for i in cmd_data])
	for cmd in cmd_data:
		if cmd[:5] == 'info_':
			m = capfirst(cmd_data[cmd][0])
			Msg(green('  %s:' % m))
			continue
		Msg('  '+fs.format(cmd,cmd_data[cmd][1],w=w))

	w = max([len(i) for i in meta_cmds])
	Msg(green('\nAVAILABLE METACOMMANDS:'))
	for cmd in meta_cmds:
		Msg(fs.format(cmd,' '.join(meta_cmds[cmd]),w=w))

	w = max([len(i) for i in cmd_list])
	Msg(green('\nAVAILABLE COMMAND GROUPS:'))
	for g in cmd_list:
		Msg(fs.format(g,' '.join(cmd_list[g]),w=w))

	Msg(green('\nAVAILABLE UTILITIES:'))
	w = max([len(i) for i in utils])
	for cmd in sorted(utils):
		Msg(fs.format(cmd,utils[cmd],w=w))
	sys.exit(0)

NL = ('\r\n','\n')[g.platform=='linux' and bool(opt.popen_spawn)]

def get_file_with_ext(ext,mydir,delete=True,no_dot=False,return_list=False):

	dot = ('.','')[bool(no_dot)]
	flist = [os.path.join(mydir,f) for f in os.listdir(mydir)
				if f == ext or f[-len(dot+ext):] == dot+ext]

	if not flist: return False
	if return_list: return flist

	if len(flist) > 1:
		if delete:
			if not opt.quiet:
				msg("Multiple *.{} files in '{}' - deleting".format(ext,mydir))
			for f in flist:
				msg(f)
				os.unlink(f)
		return False
	else:
		return flist[0]

def find_generated_exts(cmd):
	out = []
	for k in cfgs:
		for ext,prog in cfgs[k]['dep_generators'].items():
			if prog == cmd:
				out.append((ext,cfgs[k]['tmpdir']))
	return out

def get_addrfile_checksum(display=False):
	addrfile = get_file_with_ext('addrs',cfg['tmpdir'])
	silence()
	chk = AddrList(addrfile).chksum
	if opt.verbose and display: msg('Checksum: %s' % cyan(chk))
	end_silence()
	return chk

def verify_checksum_or_exit(checksum,chk):
	if checksum != chk:
		errmsg(red('Checksum error: %s' % chk))
		sys.exit(1)
	vmsg(green('Checksums match: %s') % (cyan(chk)))

from test.mmgen_pexpect import MMGenPexpect
class MMGenExpect(MMGenPexpect):

	def __init__(self,name,mmgen_cmd,cmd_args=[],extra_desc='',no_output=False):
		desc = (cmd_data[name][1],name)[bool(opt.names)] + (' ' + extra_desc).strip()
		return MMGenPexpect.__init__(self,name,mmgen_cmd,cmd_args,desc,no_output=no_output)

def create_fake_unspent_entry(btcaddr,al_id=None,idx=None,lbl=None,non_mmgen=False,segwit=False):
	if lbl: lbl = ' ' + lbl
	spk1,spk2 = (('76a914','88ac'),('a914','87'))[segwit and btcaddr.addr_fmt=='p2sh']
	return {
		'account': 'btc:{}'.format(btcaddr) if non_mmgen else (u'{}:{}{}'.format(al_id,idx,lbl.decode('utf8'))),
		'vout': int(getrandnum(4) % 8),
		'txid': hexlify(os.urandom(32)).decode('utf8'),
		'amount': BTCAmt('%s.%s' % (10+(getrandnum(4) % 40), getrandnum(4) % 100000000)),
		'address': btcaddr,
		'spendable': False,
		'scriptPubKey': '{}{}{}'.format(spk1,btcaddr.hex,spk2),
		'confirmations': getrandnum(4) % 50000
	}

labels = [
	"Automotive",
	"Travel expenses",
	"Healthcare",
	"Freelancing 1",
	"Freelancing 2",
	"Alice's allowance",
	"Bob's bequest",
	"House purchase",
	"Real estate fund",
	"Job 1",
	"XYZ Corp.",
	"Eddie's endowment",
	"Emergency fund",
	"Real estate fund",
	"Ian's inheritance",
	"",
	"Rainy day",
	"Fred's funds",
	"Job 2",
	"Carl's capital",
]
label_iter = None

def create_fake_unspent_data(adata,tx_data,non_mmgen_input=''):

	out = []
	for d in tx_data.values():
		al = adata.addrlist(d['al_id'])
		for n,(idx,btcaddr) in enumerate(al.addrpairs()):
			while True:
				try: lbl = next(label_iter)
				except: label_iter = iter(labels)
				else: break
			out.append(create_fake_unspent_entry(btcaddr,d['al_id'],idx,lbl,segwit=d['segwit']))
			if n == 0:  # create a duplicate address. This means addrs_per_wallet += 1
				out.append(create_fake_unspent_entry(btcaddr,d['al_id'],idx,lbl,segwit=d['segwit']))

	if non_mmgen_input:
		privkey = PrivKey(os.urandom(32),compressed=True)
		btcaddr = AddrGenerator('p2pkh').to_addr(KeyGenerator().to_pubhex(privkey))
		of = os.path.join(cfgs[non_mmgen_input]['tmpdir'],non_mmgen_fn)
		write_data_to_file(of,privkey.wif+'\n','compressed bitcoin key',silent=True)
		out.append(create_fake_unspent_entry(btcaddr,non_mmgen=True,segwit=False))

#	msg('\n'.join([repr(o) for o in out])); sys.exit(0)
	return out

def write_fake_data_to_file(d):
	unspent_data_file = os.path.join(cfg['tmpdir'],'unspent.json')
	write_data_to_file(unspent_data_file,d,'Unspent outputs',silent=True)
	os.environ['MMGEN_BOGUS_WALLET_DATA'] = unspent_data_file
	bwd_msg = 'MMGEN_BOGUS_WALLET_DATA=%s' % unspent_data_file
	if opt.print_cmdline: msg(bwd_msg)
	if opt.log: log_fd.write(bwd_msg + ' ')
	if opt.verbose or opt.exact_output:
		sys.stderr.write("Fake transaction wallet data written to file '%s'\n" % unspent_data_file)

def create_tx_data(sources):
	tx_data,ad = {},AddrData()
	for s in sources:
		afile = get_file_with_ext('addrs',cfgs[s]['tmpdir'])
		al = AddrList(afile)
		ad.add(al)
		aix = AddrIdxList(fmt_str=cfgs[s]['addr_idx_list'])
		if len(aix) != addrs_per_wallet:
			errmsg(red('Address index list length != %s: %s' %
						(addrs_per_wallet,repr(aix))))
			sys.exit(0)
		tx_data[s] = {
			'addrfile': afile,
			'chk': al.chksum,
			'al_id': al.al_id,
			'addr_idxs': aix[-2:],
			'segwit': cfgs[s]['segwit']
		}
	return ad,tx_data

def make_txcreate_cmdline(tx_data):
	privkey = PrivKey(os.urandom(32),compressed=True)
	btcaddr = AddrGenerator('segwit').to_addr(KeyGenerator().to_pubhex(privkey))

	cmd_args = ['-d',cfg['tmpdir']]
	for num in tx_data:
		s = tx_data[num]
		cmd_args += [
			'{}:{},{}'.format(s['al_id'],s['addr_idxs'][0],cfgs[num]['amts'][0]),
		]
		# + one change address and one BTC address
		if num is tx_data.keys()[-1]:
			cmd_args += ['{}:{}'.format(s['al_id'],s['addr_idxs'][1])]
			cmd_args += ['{},{}'.format(btcaddr,cfgs[num]['amts'][1])]

	return cmd_args + [tx_data[num]['addrfile'] for num in tx_data]

def add_comments_to_addr_file(addrfile,outfile):
	silence()
	msg(green("Adding comments to address file '%s'" % addrfile))
	a = AddrList(addrfile)
	for n,idx in enumerate(a.idxs(),1):
		if n % 2: a.set_comment(idx,'Test address %s' % n)
	a.format(enable_comments=True)
	write_data_to_file(outfile,a.fmt_data,silent=True)
	end_silence()

def make_brainwallet_file(fn):
	# Print random words with random whitespace in between
	from mmgen.mn_tirosh import words
	wl = words.split()
	nwords,ws_list,max_spaces = 10,'    \n',5
	def rand_ws_seq():
		nchars = getrandnum(1) % max_spaces + 1
		return ''.join([ws_list[getrandnum(1)%len(ws_list)] for i in range(nchars)])
	rand_pairs = [wl[getrandnum(4) % len(wl)] + rand_ws_seq() for i in range(nwords)]
	d = ''.join(rand_pairs).rstrip() + '\n'
	if opt.verbose: msg_r('Brainwallet password:\n%s' % cyan(d))
	write_data_to_file(fn,d,'brainwallet password',silent=True)

def do_between():
	if opt.pause:
		if keypress_confirm(green('Continue?'),default_yes=True):
			if opt.verbose or opt.exact_output: sys.stderr.write('\n')
		else:
			errmsg('Exiting at user request')
			sys.exit(0)
	elif opt.verbose or opt.exact_output:
		sys.stderr.write('\n')


rebuild_list = OrderedDict()

def check_needs_rerun(
		ts,
		cmd,
		build=False,
		root=True,
		force_delete=False,
		dpy=False
	):

	rerun = (False,True)[root] # force_delete is not passed to recursive call

	fns = []
	if force_delete or not root:
		# does cmd produce a needed dependency(ies)?
		ret = ts.get_num_exts_for_cmd(cmd,dpy)
		if ret:
			for ext in ret[1]:
				fn = get_file_with_ext(ext,cfgs[ret[0]]['tmpdir'],delete=build)
				if fn:
					if force_delete: os.unlink(fn)
					else: fns.append(fn)
				else: rerun = True

	fdeps = ts.generate_file_deps(cmd)
	cdeps = ts.generate_cmd_deps(fdeps)
#	print 'cmd,fdeps,cdeps,fns: ',cmd,fdeps,cdeps,fns # DEBUG

	for fn in fns:
		my_age = os.stat(fn).st_mtime
		for num,ext in fdeps:
			f = get_file_with_ext(ext,cfgs[num]['tmpdir'],delete=build)
			if f and os.stat(f).st_mtime > my_age:
				rerun = True

	for cdep in cdeps:
		if check_needs_rerun(ts,cdep,build=build,root=False,dpy=cmd):
			rerun = True

	if build:
		if rerun:
			for fn in fns:
				if not root: os.unlink(fn)
			if not (dpy and opt.skip_deps):
				ts.do_cmd(cmd)
			if not root: do_between()
	else:
		# If prog produces multiple files:
		if cmd not in rebuild_list or rerun == True:
			rebuild_list[cmd] = (rerun,fns[0] if fns else '') # FIX

	return rerun

def refcheck(desc,chk,refchk):
	vmsg("Comparing %s '%s' to stored reference" % (desc,chk))
	if chk == refchk:
		ok()
	else:
		if not opt.verbose: errmsg('')
		errmsg(red("""
Fatal error - %s '%s' does not match reference value '%s'.  Aborting test
""".strip() % (desc,chk,refchk)))
		sys.exit(3)

def check_deps(cmds):
	if len(cmds) != 1:
		die(1,'Usage: %s check_deps <command>' % g.prog_name)

	cmd = cmds[0]

	if cmd not in cmd_data:
		die(1,"'%s': unrecognized command" % cmd)

	if not opt.quiet:
		msg("Checking dependencies for '%s'" % (cmd))

	check_needs_rerun(ts,cmd,build=False)

	w = max(len(i) for i in rebuild_list) + 1
	for cmd in rebuild_list:
		c = rebuild_list[cmd]
		m = 'Rebuild' if (c[0] and c[1]) else 'Build' if c[0] else 'OK'
		msg('cmd {:<{w}} {}'.format(cmd+':', m, w=w))
#			mmsg(cmd,c)


def clean(usr_dirs=[]):
	if opt.skip_deps: return
	all_dirs = MMGenTestSuite().list_tmp_dirs()
	dirs = (usr_dirs or all_dirs)
	for d in sorted(dirs):
		if str(d) in all_dirs:
			cleandir(all_dirs[str(d)])
		else:
			die(1,'%s: invalid directory number' % d)
	cleandir(os.path.join('test','data_dir'))

class MMGenTestSuite(object):

	def __init__(self):
		pass

	def list_tmp_dirs(self):
		d = {}
		for k in cfgs: d[k] = cfgs[k]['tmpdir']
		return d

	def get_num_exts_for_cmd(self,cmd,dpy=False): # dpy ignored here
		num = str(cmd_data[cmd][0])
		dgl = cfgs[num]['dep_generators']
#	mmsg(num,cmd,dgl)
		if cmd in dgl.values():
			exts = [k for k in dgl if dgl[k] == cmd]
			return (num,exts)
		else:
			return None

	def do_cmd(self,cmd):

		# delete files produced by this cmd
# 		for ext,tmpdir in find_generated_exts(cmd):
# 			print cmd, get_file_with_ext(ext,tmpdir)

		d = [(str(num),ext) for exts,num in cmd_data[cmd][2] for ext in exts]

		# delete files depended on by this cmd
		al = [get_file_with_ext(ext,cfgs[num]['tmpdir']) for num,ext in d]

		global cfg
		cfg = cfgs[str(cmd_data[cmd][0])]

		if opt.resume:
			if cmd == opt.resume:
				msg(yellow("Resuming at '%s'" % cmd))
				opt.resume = False
				opt.skip_deps = False
			else:
				return

		if opt.profile: start = time.time()
		self.__class__.__dict__[cmd](*([self,cmd] + al))
		if opt.profile:
			msg('\r\033[50C{:.4f}'.format(time.time() - start))
		global cmd_total
		cmd_total += 1

	def generate_file_deps(self,cmd):
		return [(str(n),e) for exts,n in cmd_data[cmd][2] for e in exts]

	def generate_cmd_deps(self,fdeps):
		return [cfgs[str(n)]['dep_generators'][ext] for n,ext in fdeps]

	def helpscreens(self,name,arg='--help'):
		scripts = (
			'walletgen','walletconv','walletchk','txcreate','txsign','txsend','txdo','txbump',
			'addrgen','addrimport','keygen','passchg','tool','passgen')
		for s in scripts:
			t = MMGenExpect(name,('mmgen-'+s),[arg],extra_desc='(mmgen-%s)'%s,no_output=True)
			t.read(); t.ok()

	def longhelpscreens(self,name): self.helpscreens(name,arg='--longhelp')

	def walletgen(self,name,del_dw_run='dummy',seed_len=None,gen_dfl_wallet=False):
		write_to_tmpfile(cfg,pwfile,cfg['wpasswd']+'\n')
		args = ['-d',cfg['tmpdir'],'-p1']
		if seed_len: args += ['-l',str(seed_len)]
		t = MMGenExpect(name,'mmgen-walletgen', args + [usr_rand_arg])
		t.license()
		t.usr_rand(usr_rand_chars)
		t.passphrase_new('new MMGen wallet',cfg['wpasswd'])
		t.label()
		global have_dfl_wallet
		if not have_dfl_wallet:
			t.expect('move it to the data directory? (Y/n): ',('n','y')[gen_dfl_wallet])
			if gen_dfl_wallet: have_dfl_wallet = True
		t.written_to_file('MMGen wallet')
		t.ok()

	def walletgen_dfl_wallet(self,name,seed_len=None):
		self.walletgen(name,seed_len=seed_len,gen_dfl_wallet=True)

	def brainwalletgen_ref(self,name):
		sl_arg = '-l%s' % cfg['seed_len']
		hp_arg = '-p%s' % ref_wallet_hash_preset
		label = "test.py ref. wallet (pw '%s', seed len %s)" \
				% (ref_wallet_brainpass,cfg['seed_len'])
		bf = 'ref.mmbrain'
		args = ['-d',cfg['tmpdir'],hp_arg,sl_arg,'-ib','-L',label]
		write_to_tmpfile(cfg,bf,ref_wallet_brainpass)
		write_to_tmpfile(cfg,pwfile,cfg['wpasswd'])
		t = MMGenExpect(name,'mmgen-walletconv', args + [usr_rand_arg])
		t.license()
		t.expect('Enter brainwallet: ', ref_wallet_brainpass+'\n')
		t.passphrase_new('new MMGen wallet',cfg['wpasswd'])
		t.usr_rand(usr_rand_chars)
		sid = os.path.basename(t.written_to_file('MMGen wallet').split('-')[0])
		refcheck('Seed ID',sid,cfg['seed_id'])

	def refwalletgen(self,name): self.brainwalletgen_ref(name)

	def passchg(self,name,wf,pf):
		silence()
		write_to_tmpfile(cfg,pwfile,get_data_from_file(pf))
		end_silence()
		t = MMGenExpect(name,'mmgen-passchg', [usr_rand_arg] +
				['-d',cfg['tmpdir'],'-p','2','-L','Changed label'] + ([],[wf])[bool(wf)])
		t.license()
		t.passphrase('MMGen wallet',cfgs['1']['wpasswd'],pwtype='old')
		t.expect_getend('Hash preset changed to ')
		t.passphrase('MMGen wallet',cfg['wpasswd'],pwtype='new') # reuse passphrase?
		t.expect('Repeat passphrase: ',cfg['wpasswd']+'\n')
		t.usr_rand(usr_rand_chars)
#		t.expect('Enter a wallet label.*: ','Changed Label\n',regex=True)
		t.expect_getend('Label changed to ')
#		t.expect_getend('Key ID changed: ')
		if not wf:
			t.expect("Type uppercase 'YES' to confirm: ",'YES\n')
			t.written_to_file('New wallet')
			t.expect('Securely deleting old wallet')
#			t.expect('Okay to WIPE 1 regular file ? (Yes/No)','Yes\n')
			t.expect('Wallet passphrase has changed')
			t.expect_getend('has been changed to ')
		else:
			t.written_to_file('MMGen wallet')
		t.ok()

	def passchg_dfl_wallet(self,name,pf):
		return self.passchg(name=name,wf=None,pf=pf)

	def walletchk(self,name,wf,pf,desc='MMGen wallet',add_args=[],sid=None,pw=False,extra_desc=''):
		args = []
		hp = cfg['hash_preset'] if 'hash_preset' in cfg else '1'
		wf_arg = ([],[wf])[bool(wf)]
		t = MMGenExpect(name,'mmgen-walletchk',
				add_args+args+['-p',hp]+wf_arg,
				extra_desc=extra_desc)
		if desc != 'hidden incognito data':
			t.expect("Getting %s from file '" % (desc))
		if pw:
			t.passphrase(desc,cfg['wpasswd'])
			t.expect(
				['Passphrase is OK', 'Passphrase.* are correct'],
				regex=True
				)
		chk = t.expect_getend('Valid %s for Seed ID ' % desc)[:8]
		if sid: t.cmp_or_die(chk,sid)
		else: t.ok()

	def walletchk_newpass(self,name,wf,pf):
		return self.walletchk(name,wf,pf,pw=True)

	def walletchk_newpass_dfl_wallet(self,name,pf):
		return self.walletchk_newpass(name,wf=None,pf=pf)

	def delete_dfl_wallet(self,name,pf):
		with open(os.path.join(cfg['tmpdir'],'del_dw_run'),'w') as f: pass
		if opt.no_dw_delete: return True
		for wf in [f for f in os.listdir(g.data_dir) if f[-6:]=='.mmdat']:
			os.unlink(os.path.join(g.data_dir,wf))
		MMGenExpect(name,'')
		global have_dfl_wallet
		have_dfl_wallet = False
		ok()

	def addrgen(self,name,wf,pf=None,check_ref=False,ftype='addr',id_str=None,extra_args=[],mmtype=None):
		if cfg['segwit'] and ftype[:4] != 'pass' and not mmtype: mmtype = 'segwit'
		cmd_pfx = (ftype,'pass')[ftype[:4]=='pass']
		t = MMGenExpect(name,'mmgen-{}gen'.format(cmd_pfx),
				['-d',cfg['tmpdir']] +
				extra_args +
				([],['--type='+str(mmtype)])[bool(mmtype)] +
				([],[wf])[bool(wf)] +
				([],[id_str])[bool(id_str)] +
				[cfg['{}_idx_list'.format(cmd_pfx)]])
		t.license()
		t.passphrase('MMGen wallet',cfg['wpasswd'])
		t.expect('Passphrase is OK')
		desc = ('address','password')[ftype[:4]=='pass']
		chk = t.expect_getend(r'Checksum for {} data .*?: '.format(desc),regex=True)
		if check_ref:
			k = 'passfile32_chk' if ftype == 'pass32' \
					else 'passfile_chk' if ftype == 'pass' \
						else '{}file{}_chk'.format(ftype,'_'+mmtype if mmtype else '')
			chk_ref = cfg[k] if ftype[:4] == 'pass' else cfg[k][g.testnet]
			refcheck('address data checksum',chk,chk_ref)
			return
		t.written_to_file('Addresses',oo=True)
		t.ok()

	def addrgen_dfl_wallet(self,name,pf=None,check_ref=False):
		return self.addrgen(name,wf=None,pf=pf,check_ref=check_ref)

	def refaddrgen(self,name,wf,pf):
		self.addrgen(name,wf,pf=pf,check_ref=True)

	def refaddrgen_compressed(self,name,wf,pf):
		self.addrgen(name,wf,pf=pf,check_ref=True,mmtype='compressed')

	def addrimport(self,name,addrfile):
		outfile = os.path.join(cfg['tmpdir'],'addrfile_w_comments')
		add_comments_to_addr_file(addrfile,outfile)
		t = MMGenExpect(name,'mmgen-addrimport', [outfile])
		t.expect_getend(r'Checksum for address data .*\[.*\]: ',regex=True)
		t.expect("Type uppercase 'YES' to confirm: ",'\n')
		vmsg('This is a simulation, so no addresses were actually imported into the tracking\nwallet')
		t.ok(exit_val=1)

	def txcreate_common(self,name,sources=['1'],non_mmgen_input='',do_label=False,txdo_args=[],add_args=[]):
		if opt.verbose or opt.exact_output:
			sys.stderr.write(green('Generating fake tracking wallet info\n'))

		silence()
		ad,tx_data = create_tx_data(sources)
		dfake = create_fake_unspent_data(ad,tx_data,non_mmgen_input)
		write_fake_data_to_file(repr(dfake))
		cmd_args = make_txcreate_cmdline(tx_data)
		end_silence()

		if opt.verbose or opt.exact_output: sys.stderr.write('\n')

		t = MMGenExpect(name,'mmgen-'+('txcreate','txdo')[bool(txdo_args)],['--rbf','-f',tx_fee] + add_args + cmd_args + txdo_args)
		t.license()

		if txdo_args and add_args: # txdo4
			t.hash_preset('key-address data','1')
			t.passphrase('key-address data',cfgs['14']['kapasswd'])
			t.expect('Check key-to-address validity? (y/N): ','y')

		for num in tx_data:
			t.expect_getend('Getting address data from file ')
			chk=t.expect_getend(r'Checksum for address data .*?: ',regex=True)
			verify_checksum_or_exit(tx_data[num]['chk'],chk)

		# not in tracking wallet warning, (1 + num sources) times
		if t.expect(['Continue anyway? (y/N): ',
				'Unable to connect to bitcoind']) == 0:
			t.send('y')
		else:
			errmsg(red('Error: unable to connect to bitcoind.  Exiting'))
			sys.exit(1)

		for num in tx_data:
			t.expect('Continue anyway? (y/N): ','y')
		t.expect(r"'q'=quit view, .*?:.",'M', regex=True)
		t.expect(r"'q'=quit view, .*?:.",'q', regex=True)
		outputs_list = [(addrs_per_wallet+1)*i + 1 for i in range(len(tx_data))]
		if non_mmgen_input: outputs_list.append(len(tx_data)*(addrs_per_wallet+1) + 1)
		t.expect('outputs to spend: ',' '.join([str(i) for i in outputs_list])+'\n')
		if non_mmgen_input and not txdo_args: t.expect('Accept? (y/N): ','y')
		t.expect('OK? (Y/n): ','y') # fee OK?
		t.expect('OK? (Y/n): ','y') # change OK?
		if do_label:
			t.expect('Add a comment to transaction? (y/N): ','y')
			t.expect('Comment: ',ref_tx_label.encode('utf8')+'\n')
		else:
			t.expect('Add a comment to transaction? (y/N): ','\n')
		t.tx_view()
		if txdo_args: return t
		t.expect('Save transaction? (y/N): ','y')
		t.written_to_file('Transaction')
		t.ok()

	def txcreate(self,name,addrfile):
		self.txcreate_common(name,sources=['1'])

	def txbump(self,name,txfile,prepend_args=[],seed_args=[]):
		args = prepend_args + ['-q','-d',cfg['tmpdir'],txfile] + seed_args
		t = MMGenExpect(name,'mmgen-txbump',args)
		if seed_args:
			t.hash_preset('key-address data','1')
			t.passphrase('key-address data',cfgs['14']['kapasswd'])
			t.expect('Check key-to-address validity? (y/N): ','y')
		t.expect('deduct the fee from (Hit ENTER for the change output): ','1\n')
		# Fee must be > tx_fee + network relay fee (currently 0.00001)
		t.expect('OK? (Y/n): ','\n')
		t.expect('Enter transaction fee: ','124s\n')
		t.expect('OK? (Y/n): ','\n')
		if seed_args: # sign and send
			t.expect('Edit transaction comment? (y/N): ','\n')
			for cnum,desc in (('1','incognito data'),('3','MMGen wallet'),('4','MMGen wallet')):
				t.passphrase(('%s' % desc),cfgs[cnum]['wpasswd'])
			t.expect("Type uppercase 'YES' to confirm: ",'YES\n')
		else:
			t.expect('Add a comment to transaction? (y/N): ','\n')
			t.expect('Save transaction? (y/N): ','y')
			t.written_to_file('Transaction')
		os.unlink(txfile) # our tx file replaces the original
		os.system('touch ' + os.path.join(cfg['tmpdir'],'txbump'))
		t.ok()

	def txdo(self,name,addrfile,wallet):
		t = self.txcreate_common(name,sources=['1'],txdo_args=[wallet])
		self.txsign(name,'','',pf='',save=True,has_label=False,txdo_handle=t)
		self.txsend(name,'',txdo_handle=t)

	def txcreate_dfl_wallet(self,name,addrfile):
		self.txcreate_common(name,sources=['15'])

	def txsign_end(self,t,tnum=None,has_label=False):
		t.expect('Signing transaction')
		cprompt = ('Add a comment to transaction','Edit transaction comment')[has_label]
		t.expect('%s? (y/N): ' % cprompt,'\n')
		t.expect('Save signed transaction.*?\? \(Y/n\): ','y',regex=True)
		add = ' #' + tnum if tnum else ''
		t.written_to_file('Signed transaction' + add, oo=True)

	def txsign(self,name,txfile,wf,pf='',bumpf='',save=True,has_label=False,txdo_handle=None):
		if txdo_handle:
			t = txdo_handle
		else:
			t = MMGenExpect(name,'mmgen-txsign', ['-d',cfg['tmpdir'],txfile]+([],[wf])[bool(wf)])
			t.license()
			t.tx_view()
		t.passphrase('MMGen wallet',cfg['wpasswd'])
		if txdo_handle: return
		if save:
			self.txsign_end(t,has_label=has_label)
			t.ok()
		else:
			cprompt = ('Add a comment to transaction','Edit transaction comment')[has_label]
			t.expect('%s? (y/N): ' % cprompt,'\n')
			t.expect('Save signed transaction? (Y/n): ','n')
			t.ok(exit_val=1)

	def txsign_dfl_wallet(self,name,txfile,pf='',save=True,has_label=False):
		return self.txsign(name,txfile,wf=None,pf=pf,save=save,has_label=has_label)

	def txsend(self,name,sigfile,txdo_handle=None):
		if txdo_handle:
			t = txdo_handle
		else:
			t = MMGenExpect(name,'mmgen-txsend', ['-d',cfg['tmpdir'],sigfile])
			t.license()
			t.tx_view()
			t.expect('Add a comment to transaction? (y/N): ','\n')
		t.expect('Are you sure you want to broadcast this')
		m = 'YES, I REALLY WANT TO DO THIS'
		t.expect("'%s' to confirm: " % m,m+'\n')
		t.expect('BOGUS transaction NOT sent')
		t.written_to_file('Sent transaction')
		t.ok()

	def walletconv_export(self,name,wf,desc,uargs=[],out_fmt='w',pf=None,out_pw=False):
		opts = ['-d',cfg['tmpdir'],'-o',out_fmt] + uargs + \
			([],[wf])[bool(wf)] + ([],['-P',pf])[bool(pf)]
		t = MMGenExpect(name,'mmgen-walletconv',opts)
		t.license()
		if not pf:
			t.passphrase('MMGen wallet',cfg['wpasswd'])
		if out_pw:
			t.passphrase_new('new '+desc,cfg['wpasswd'])
			t.usr_rand(usr_rand_chars)

		if ' '.join(desc.split()[-2:]) == 'incognito data':
			t.expect('Generating encryption key from OS random data ')
			t.expect('Generating encryption key from OS random data ')
			ic_id = t.expect_getend('New Incog Wallet ID: ')
			t.expect('Generating encryption key from OS random data ')
		if desc == 'hidden incognito data':
			write_to_tmpfile(cfg,incog_id_fn,ic_id)
			ret = t.expect(['Create? (Y/n): ',"'YES' to confirm: "])
			if ret == 0:
				t.send('\n')
				t.expect('Enter file size: ',str(hincog_bytes)+'\n')
			else:
				t.send('YES\n')
		if out_fmt == 'w': t.label()
		return t.written_to_file(capfirst(desc),oo=True),t

	def export_seed(self,name,wf,desc='seed data',out_fmt='seed',pf=None):
		f,t = self.walletconv_export(name,wf,desc=desc,out_fmt=out_fmt,pf=pf)
		silence()
		msg('%s: %s' % (capfirst(desc),cyan(get_data_from_file(f,desc))))
		end_silence()
		t.ok()

	def export_hex(self,name,wf,desc='hexadecimal seed data',out_fmt='hex',pf=None):
		self.export_seed(name,wf,desc=desc,out_fmt=out_fmt,pf=pf)

	def export_seed_dfl_wallet(self,name,pf,desc='seed data',out_fmt='seed'):
		self.export_seed(name,wf=None,desc=desc,out_fmt=out_fmt,pf=pf)

	def export_mnemonic(self,name,wf):
		self.export_seed(name,wf,desc='mnemonic data',out_fmt='words')

	def export_incog(self,name,wf,desc='incognito data',out_fmt='i',add_args=[]):
		uargs = ['-p1',usr_rand_arg] + add_args
		f,t = self.walletconv_export(name,wf,desc=desc,out_fmt=out_fmt,uargs=uargs,out_pw=True)
		t.ok()

	def export_incog_hex(self,name,wf):
		self.export_incog(name,wf,desc='hex incognito data',out_fmt='xi')

	# TODO: make outdir and hidden incog compatible (ignore --outdir and warn user?)
	def export_incog_hidden(self,name,wf):
		rf = os.path.join(cfg['tmpdir'],hincog_fn)
		add_args = ['-J','%s,%s'%(rf,hincog_offset)]
		self.export_incog(
			name,wf,desc='hidden incognito data',out_fmt='hi',add_args=add_args)

	def addrgen_seed(self,name,wf,foo,desc='seed data',in_fmt='seed'):
		stdout = (False,True)[desc=='seed data'] #capture output to screen once
		add_args = ([],['-S'])[bool(stdout)] + get_segwit_arg(cfg)
		t = MMGenExpect(name,'mmgen-addrgen', add_args +
				['-i'+in_fmt,'-d',cfg['tmpdir'],wf,cfg['addr_idx_list']])
		t.license()
		t.expect_getend('Valid %s for Seed ID ' % desc)
		vmsg('Comparing generated checksum with checksum from previous address file')
		chk = t.expect_getend(r'Checksum for address data .*?: ',regex=True)
		if stdout: t.read()
		verify_checksum_or_exit(get_addrfile_checksum(),chk)
		if in_fmt == 'seed':
			t.ok()
		else:
			t.no_overwrite()
			t.ok(exit_val=1)

	def addrgen_hex(self,name,wf,foo,desc='hexadecimal seed data',in_fmt='hex'):
		self.addrgen_seed(name,wf,foo,desc=desc,in_fmt=in_fmt)

	def addrgen_mnemonic(self,name,wf,foo):
		self.addrgen_seed(name,wf,foo,desc='mnemonic data',in_fmt='words')

	def addrgen_incog(self,name,wf=[],foo='',in_fmt='i',desc='incognito data',args=[]):
		t = MMGenExpect(name,'mmgen-addrgen', args + get_segwit_arg(cfg) + ['-i'+in_fmt,'-d',cfg['tmpdir']]+
				([],[wf])[bool(wf)] + [cfg['addr_idx_list']])
		t.license()
		t.expect_getend('Incog Wallet ID: ')
		t.hash_preset(desc,'1')
		t.passphrase('%s \w{8}' % desc, cfg['wpasswd'])
		vmsg('Comparing generated checksum with checksum from address file')
		chk = t.expect_getend(r'Checksum for address data .*?: ',regex=True)
		verify_checksum_or_exit(get_addrfile_checksum(),chk)
		t.no_overwrite()
		t.ok(exit_val=1)

	def addrgen_incog_hex(self,name,wf,foo):
		self.addrgen_incog(name,wf,'',in_fmt='xi',desc='hex incognito data')

	def addrgen_incog_hidden(self,name,wf,foo):
		rf = os.path.join(cfg['tmpdir'],hincog_fn)
		self.addrgen_incog(name,[],'',in_fmt='hi',desc='hidden incognito data',
			args=['-H','%s,%s'%(rf,hincog_offset),'-l',str(hincog_seedlen)])

	def keyaddrgen(self,name,wf,pf=None,check_ref=False,mmtype=None):
		if cfg['segwit'] and not mmtype: mmtype = 'segwit'
		args = ['-d',cfg['tmpdir'],usr_rand_arg,wf,cfg['addr_idx_list']]
		t = MMGenExpect(name,'mmgen-keygen',
				([],['--type='+str(mmtype)])[bool(mmtype)] + args)
		t.license()
		t.passphrase('MMGen wallet',cfg['wpasswd'])
		chk = t.expect_getend(r'Checksum for key-address data .*?: ',regex=True)
		if check_ref:
			k = 'keyaddrfile{}_chk'.format('_'+mmtype if mmtype else '')
			refcheck('key-address data checksum',chk,cfg[k][g.testnet])
			return
		t.expect('Encrypt key list? (y/N): ','y')
		t.usr_rand(usr_rand_chars)
		t.hash_preset('new key list','1')
#		t.passphrase_new('new key list','kafile password')
		t.passphrase_new('new key list',cfg['kapasswd'])
		t.written_to_file('Encrypted secret keys',oo=True)
		t.ok()

	def refkeyaddrgen(self,name,wf,pf):
		self.keyaddrgen(name,wf,pf,check_ref=True)

	def refkeyaddrgen_compressed(self,name,wf,pf):
		self.keyaddrgen(name,wf,pf,check_ref=True,mmtype='compressed')

	def refpasswdgen(self,name,wf,pf):
		self.addrgen(name,wf,pf,check_ref=True,ftype='pass',id_str='alice@crypto.org')

	def ref_b32passwdgen(self,name,wf,pf):
		ea = ['--base32','--passwd-len','17']
		self.addrgen(name,wf,pf,check_ref=True,ftype='pass32',id_str='фубар@crypto.org',extra_args=ea)

	def txsign_keyaddr(self,name,keyaddr_file,txfile):
		t = MMGenExpect(name,'mmgen-txsign', ['-d',cfg['tmpdir'],'-M',keyaddr_file,txfile])
		t.license()
		t.hash_preset('key-address data','1')
		t.passphrase('key-address data',cfg['kapasswd'])
		t.expect('Check key-to-address validity? (y/N): ','y')
		t.tx_view()
		self.txsign_end(t)
		t.ok()

	def walletgen2(self,name,del_dw_run='dummy'):
		self.walletgen(name,seed_len=128)

	def addrgen2(self,name,wf):
		self.addrgen(name,wf,pf='')

	def txcreate2(self,name,addrfile):
		self.txcreate_common(name,sources=['2'])

	def txsign2(self,name,txf1,wf1,txf2,wf2):
		t = MMGenExpect(name,'mmgen-txsign', ['-d',cfg['tmpdir'],txf1,wf1,txf2,wf2])
		t.license()
		for cnum in ('1','2'):
			t.tx_view()
			t.passphrase('MMGen wallet',cfgs[cnum]['wpasswd'])
			self.txsign_end(t,cnum)
		t.ok()

	def export_mnemonic2(self,name,wf):
		self.export_mnemonic(name,wf)

	def walletgen3(self,name,del_dw_run='dummy'):
		self.walletgen(name)

	def addrgen3(self,name,wf):
		self.addrgen(name,wf,pf='')

	def txcreate3(self,name,addrfile1,addrfile2):
		self.txcreate_common(name,sources=['1','3'])

	def txsign3(self,name,wf1,wf2,txf2):
		t = MMGenExpect(name,'mmgen-txsign', ['-d',cfg['tmpdir'],wf1,wf2,txf2])
		t.license()
		t.tx_view()
		for cnum in ('1','3'):
#			t.expect_getend('Getting MMGen wallet data from file ')
			t.passphrase('MMGen wallet',cfgs[cnum]['wpasswd'])
		self.txsign_end(t)
		t.ok()

	def walletgen4(self,name,del_dw_run='dummy'):
		bwf = os.path.join(cfg['tmpdir'],cfg['bw_filename'])
		make_brainwallet_file(bwf)
		seed_len = str(cfg['seed_len'])
		args = ['-d',cfg['tmpdir'],'-p1',usr_rand_arg,'-l'+seed_len,'-ib']
		t = MMGenExpect(name,'mmgen-walletconv', args + [bwf])
		t.license()
		t.passphrase_new('new MMGen wallet',cfg['wpasswd'])
		t.usr_rand(usr_rand_chars)
		t.label()
		t.written_to_file('MMGen wallet')
		t.ok()

	def addrgen4(self,name,wf):
		self.addrgen(name,wf,pf='')

	def txcreate4(self,name,f1,f2,f3,f4,f5,f6):
		self.txcreate_common(name,sources=['1','2','3','4','14'],non_mmgen_input='4',do_label=1)

	def txdo4(self,name,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12):
		non_mm_fn = os.path.join(cfg['tmpdir'],non_mmgen_fn)
		add_args = ['-d',cfg['tmpdir'],'-i','brain','-b'+cfg['bw_params'],'-p1','-k',non_mm_fn,'-M',f12]
		t = self.txcreate_common(name,sources=['1','2','3','4','14'],non_mmgen_input='4',do_label=1,txdo_args=[f7,f8,f9,f10],add_args=add_args)
		os.system('rm -f %s/*.sigtx' % cfg['tmpdir'])
		self.txsign4(name,f7,f8,f9,f10,f11,f12,txdo_handle=t)
		self.txsend(name,'',txdo_handle=t)
		os.system('touch ' + os.path.join(cfg['tmpdir'],'txdo'))

	def txbump4(self,name,f1,f2,f3,f4,f5,f6,f7,f8,f9): # f7:txfile,f9:'txdo'
		non_mm_fn = os.path.join(cfg['tmpdir'],non_mmgen_fn)
		self.txbump(name,f7,prepend_args=['-p1','-k',non_mm_fn,'-M',f1],seed_args=[f2,f3,f4,f5,f6,f8])

	def txsign4(self,name,f1,f2,f3,f4,f5,f6,txdo_handle=None):
		if txdo_handle:
			t = txdo_handle
		else:
			non_mm_fn = os.path.join(cfg['tmpdir'],non_mmgen_fn)
			a = ['-d',cfg['tmpdir'],'-i','brain','-b'+cfg['bw_params'],'-p1','-k',non_mm_fn,'-M',f6,f1,f2,f3,f4,f5]
			t = MMGenExpect(name,'mmgen-txsign',a)
			t.license()
			t.hash_preset('key-address data','1')
			t.passphrase('key-address data',cfgs['14']['kapasswd'])
			t.expect('Check key-to-address validity? (y/N): ','y')
			t.tx_view()

		for cnum,desc in (('1','incognito data'),('3','MMGen wallet')):
			t.passphrase(('%s' % desc),cfgs[cnum]['wpasswd'])

		if txdo_handle: return
		self.txsign_end(t,has_label=True)
		t.ok()

	def tool_encrypt(self,name,infile=''):
		if infile:
			infn = infile
		else:
			d = os.urandom(1033)
			tmp_fn = cfg['tool_enc_infn']
			write_to_tmpfile(cfg,tmp_fn,d,binary=True)
			infn = get_tmpfile_fn(cfg,tmp_fn)
		t = MMGenExpect(name,'mmgen-tool',['-d',cfg['tmpdir'],usr_rand_arg,'encrypt',infn])
		t.usr_rand(usr_rand_chars)
		t.hash_preset('user data','1')
		t.passphrase_new('user data',tool_enc_passwd)
		t.written_to_file('Encrypted data')
		t.ok()

# Generate the reference mmenc file
# 	def tool_encrypt_ref(self,name):
# 		infn = get_tmpfile_fn(cfg,cfg['tool_enc_ref_infn'])
# 		write_data_to_file(infn,cfg['tool_enc_reftext'],silent=True)
# 		self.tool_encrypt(name,infn)

	def tool_decrypt(self,name,f1,f2):
		of = name + '.out'
		pre = []
		t = MMGenExpect(name,'mmgen-tool',
			pre+['-d',cfg['tmpdir'],'decrypt',f2,'outfile='+of,'hash_preset=1'])
		t.passphrase('user data',tool_enc_passwd)
		t.written_to_file('Decrypted data')
		d1 = read_from_file(f1,binary=True)
		d2 = read_from_file(get_tmpfile_fn(cfg,of),binary=True)
		cmp_or_die(d1,d2,skip_ok=False)

	def tool_find_incog_data(self,name,f1,f2):
		i_id = read_from_file(f2).rstrip()
		vmsg('Incog ID: %s' % cyan(i_id))
		t = MMGenExpect(name,'mmgen-tool',
				['-d',cfg['tmpdir'],'find_incog_data',f1,i_id])
		o = t.expect_getend('Incog data for ID %s found at offset ' % i_id)
		os.unlink(f1)
		cmp_or_die(hincog_offset,int(o))

	# Saved reference file tests
	def ref_wallet_conv(self,name):
		wf = os.path.join(ref_dir,cfg['ref_wallet'])
		self.walletconv_in(name,wf,'MMGen wallet',pw=True,oo=True)

	def ref_mn_conv(self,name,ext='mmwords',desc='Mnemonic data'):
		wf = os.path.join(ref_dir,cfg['seed_id']+'.'+ext)
		self.walletconv_in(name,wf,desc,oo=True)

	def ref_seed_conv(self,name):
		self.ref_mn_conv(name,ext='mmseed',desc='Seed data')

	def ref_hex_conv(self,name):
		self.ref_mn_conv(name,ext='mmhex',desc='Hexadecimal seed data')

	def ref_brain_conv(self,name):
		uopts = ['-i','b','-p','1','-l',str(cfg['seed_len'])]
		self.walletconv_in(name,None,'brainwallet',uopts,oo=True)

	def ref_incog_conv(self,name,wfk='ic_wallet',in_fmt='i',desc='incognito data'):
		uopts = ['-i',in_fmt,'-p','1','-l',str(cfg['seed_len'])]
		wf = os.path.join(ref_dir,cfg[wfk])
		self.walletconv_in(name,wf,desc,uopts,oo=True,pw=True)

	def ref_incox_conv(self,name):
		self.ref_incog_conv(name,in_fmt='xi',wfk='ic_wallet_hex',desc='hex incognito data')

	def ref_hincog_conv(self,name,wfk='hic_wallet',add_uopts=[]):
		ic_f = os.path.join(ref_dir,cfg[wfk])
		uopts = ['-i','hi','-p','1','-l',str(cfg['seed_len'])] + add_uopts
		hi_opt = ['-H','%s,%s' % (ic_f,ref_wallet_incog_offset)]
		self.walletconv_in(name,None,'hidden incognito data',uopts+hi_opt,oo=True,pw=True)

	def ref_hincog_conv_old(self,name):
		self.ref_hincog_conv(name,wfk='hic_wallet_old',add_uopts=['-O'])

	def ref_wallet_conv_out(self,name):
		self.walletconv_out(name,'MMGen wallet','w',pw=True)

	def ref_mn_conv_out(self,name):
		self.walletconv_out(name,'mnemonic data','mn')

	def ref_seed_conv_out(self,name):
		self.walletconv_out(name,'seed data','seed')

	def ref_hex_conv_out(self,name):
		self.walletconv_out(name,'hexadecimal seed data','hexseed')

	def ref_incog_conv_out(self,name):
		self.walletconv_out(name,'incognito data',out_fmt='i',pw=True)

	def ref_incox_conv_out(self,name):
		self.walletconv_out(name,'hex incognito data',out_fmt='xi',pw=True)

	def ref_hincog_conv_out(self,name,extra_uopts=[]):
		ic_f = os.path.join(cfg['tmpdir'],hincog_fn)
		hi_parms = '%s,%s' % (ic_f,ref_wallet_incog_offset)
		sl_parm = '-l' + str(cfg['seed_len'])
		self.walletconv_out(name,
			'hidden incognito data', 'hi',
			uopts=['-J',hi_parms,sl_parm] + extra_uopts,
			uopts_chk=['-H',hi_parms,sl_parm],
			pw=True
		)

	def ref_wallet_chk(self,name):
		wf = os.path.join(ref_dir,cfg['ref_wallet'])
		self.walletchk(name,wf,pf=None,pw=True,sid=cfg['seed_id'])

	def ref_ss_chk(self,name,ss=None):
		wf = os.path.join(ref_dir,'%s.%s' % (cfg['seed_id'],ss.ext))
		self.walletchk(name,wf,pf=None,desc=ss.desc,sid=cfg['seed_id'])

	def ref_seed_chk(self,name):
		from mmgen.seed import SeedFile
		self.ref_ss_chk(name,ss=SeedFile)

	def ref_hex_chk(self,name):
		from mmgen.seed import HexSeedFile
		self.ref_ss_chk(name,ss=HexSeedFile)

	def ref_mn_chk(self,name):
		from mmgen.seed import Mnemonic
		self.ref_ss_chk(name,ss=Mnemonic)

	def ref_brain_chk(self,name,bw_file=ref_bw_file):
		wf = os.path.join(ref_dir,bw_file)
		add_args = ['-l%s' % cfg['seed_len'], '-p'+ref_bw_hash_preset]
		self.walletchk(name,wf,pf=None,add_args=add_args,
			desc='brainwallet',sid=cfg['ref_bw_seed_id'])

	def ref_brain_chk_spc3(self,name):
		self.ref_brain_chk(name,bw_file=ref_bw_file_spc)

	def ref_hincog_chk(self,name,desc='hidden incognito data'):
		for wtype,edesc,of_arg in ('hic_wallet','',[]), \
								('hic_wallet_old','(old format)',['-O']):
			ic_arg = ['-H%s,%s' % (
						os.path.join(ref_dir,cfg[wtype]),
						ref_wallet_incog_offset
					)]
			slarg = ['-l%s ' % cfg['seed_len']]
			hparg = ['-p1']
			if wtype == 'hic_wallet_old' and opt.profile: msg('')
			t = MMGenExpect(name,'mmgen-walletchk',
				slarg + hparg + of_arg + ic_arg,
				extra_desc=edesc)
			t.passphrase(desc,cfg['wpasswd'])
			if wtype == 'hic_wallet_old':
				t.expect('Is the Seed ID correct? (Y/n): ','\n')
			chk = t.expect_getend('Seed ID: ')
			t.close()
			cmp_or_die(cfg['seed_id'],chk)

	def ref_addrfile_chk(self,name,ftype='addr'):
		wf = os.path.join(ref_dir,cfg['ref_'+ftype+'file'])
		t = MMGenExpect(name,'mmgen-tool',[ftype.replace('segwit','')+'file_chksum',wf])
		if ftype == 'keyaddr':
			w = 'key-address data'
			t.hash_preset(w,ref_kafile_hash_preset)
			t.passphrase(w,ref_kafile_pass)
			t.expect('Check key-to-address validity? (y/N): ','y')
		o = t.read().strip().split('\n')[-1]
		cmp_or_die(cfg['ref_'+ftype+'file_chksum'],o)

	def ref_keyaddrfile_chk(self,name):
		self.ref_addrfile_chk(name,ftype='keyaddr')

	def ref_passwdfile_chk(self,name):
		self.ref_addrfile_chk(name,ftype='passwd')

	def ref_segwitaddrfile_chk(self,name):
		self.ref_addrfile_chk(name,ftype='segwitaddr')

#	def txcreate8(self,name,addrfile):
#		self.txcreate_common(name,sources=['8'])

	def ref_tx_chk(self,name):
		tf = os.path.join(ref_dir,cfg['ref_tx_file'])
		wf = os.path.join(ref_dir,cfg['ref_wallet'])
		write_to_tmpfile(cfg,pwfile,cfg['wpasswd'])
		pf = get_tmpfile_fn(cfg,pwfile)
		self.txsign(name,tf,wf,pf,save=False,has_label=True)

	def ref_tool_decrypt(self,name):
		f = os.path.join(ref_dir,ref_enc_fn)
		t = MMGenExpect(name,'mmgen-tool', ['-q','decrypt',f,'outfile=-','hash_preset=1'])
		t.passphrase('user data',tool_enc_passwd)
#		t.expect("Type uppercase 'YES' to confirm: ",'YES\n') # comment out with popen_spawn
		t.expect(NL,nonl=True)
		import re
		o = re.sub('\r\n','\n',t.read())
		cmp_or_die(sample_text,o)

	# wallet conversion tests
	def walletconv_in(self,name,infile,desc,uopts=[],pw=False,oo=False):
		opts = ['-d',cfg['tmpdir'],'-o','words',usr_rand_arg]
		if_arg = [infile] if infile else []
		d = '(convert)'
		t = MMGenExpect(name,'mmgen-walletconv',opts+uopts+if_arg,extra_desc=d)
		t.license()
		if desc == 'brainwallet':
			t.expect('Enter brainwallet: ',ref_wallet_brainpass+'\n')
		if pw:
			t.passphrase(desc,cfg['wpasswd'])
			if name[:19] == 'ref_hincog_conv_old':
				t.expect('Is the Seed ID correct? (Y/n): ','\n')
			else:
				t.expect(['Passphrase is OK',' are correct'])
		# Output
		wf = t.written_to_file('Mnemonic data',oo=oo)
		t.close()
		t.ok()
		# back check of result
		if opt.profile: msg('')
		self.walletchk(name,wf,pf=None,
				desc='mnemonic data',
				sid=cfg['seed_id'],
				extra_desc='(check)'
				)

	def walletconv_out(self,name,desc,out_fmt='w',uopts=[],uopts_chk=[],pw=False):
		opts = ['-d',cfg['tmpdir'],'-p1','-o',out_fmt] + uopts
		infile = os.path.join(ref_dir,cfg['seed_id']+'.mmwords')
		t = MMGenExpect(name,'mmgen-walletconv',[usr_rand_arg]+opts+[infile],extra_desc='(convert)')

		add_args = ['-l%s' % cfg['seed_len']]
		t.license()
		if pw:
			t.passphrase_new('new '+desc,cfg['wpasswd'])
			t.usr_rand(usr_rand_chars)
		if ' '.join(desc.split()[-2:]) == 'incognito data':
			for i in (1,2,3):
				t.expect('Generating encryption key from OS random data ')
		if desc == 'hidden incognito data':
			ret = t.expect(['Create? (Y/n): ',"'YES' to confirm: "])
			if ret == 0:
				t.send('\n')
				t.expect('Enter file size: ',str(hincog_bytes)+'\n')
			else:
				t.send('YES\n')
		if out_fmt == 'w': t.label()
		wf = t.written_to_file(capfirst(desc),oo=True)
		pf = None
		t.ok()

		if desc == 'hidden incognito data':
			add_args += uopts_chk
			wf = None
		if opt.profile: msg('')
		self.walletchk(name,wf,pf=pf,
			desc=desc,sid=cfg['seed_id'],pw=pw,
			add_args=add_args,
			extra_desc='(check)')

	def regtest_setup(self,name):
		try: shutil.rmtree(os.path.join(data_dir,'regtest'))
		except: pass
		os.environ['MMGEN_TEST_SUITE'] = '' # mnemonic is piped to stdin, so stop being a terminal
		t = MMGenExpect(name,'mmgen-regtest',['-n','setup'])
		os.environ['MMGEN_TEST_SUITE'] = '1'
		for s in 'Starting setup','Creating','Mined','Creating','Creating','Setup complete':
			t.expect(s)
		t.ok()

	def regtest_walletgen(self,name,user):
		t = MMGenExpect(name,'mmgen-walletgen',['-q','-r0','-p1','--'+user])
		t.passphrase_new('new MMGen wallet','abc')
		t.label()
		t.expect('move it to the data directory? (Y/n): ','y')
		t.written_to_file('MMGen wallet')
		t.ok()

	def regtest_walletgen_bob(self,name):   return self.regtest_walletgen(name,'bob')
	def regtest_walletgen_alice(self,name): return self.regtest_walletgen(name,'alice')

	@staticmethod
	def regtest_user_dir(user):
		return os.path.join(data_dir,'regtest',user)

	def regtest_user_sid(self,user):
		return os.path.basename(get_file_with_ext('mmdat',self.regtest_user_dir(user)))[:8]

	def regtest_addrgen(self,name,user):
		for mmtype in ('legacy','compressed','segwit'):
			t = MMGenExpect(name,'mmgen-addrgen',
				['--quiet','--'+user,'--type='+mmtype,
				'--outdir={}'.format(self.regtest_user_dir(user)),
				'1-5'],extra_desc='({})'.format(mmtype))
			t.passphrase('MMGen wallet','abc')
			t.written_to_file('Addresses')
			t.ok()

	def regtest_addrgen_bob(self,name):   self.regtest_addrgen(name,'bob')
	def regtest_addrgen_alice(self,name): self.regtest_addrgen(name,'alice')

	def regtest_addrimport(self,name,user):
		id_strs = { 'legacy':'', 'compressed':'-C', 'segwit':'-S' }
		sid = self.regtest_user_sid(user)
		for desc in ('legacy','compressed','segwit'):
			fn = os.path.join(self.regtest_user_dir(user),'{}{}[1-5].addrs'.format(sid,id_strs[desc]))
			t = MMGenExpect(name,'mmgen-addrimport', ['--quiet','--'+user,'--batch',fn],extra_desc='('+desc+')')
			t.expect('Importing')
			t.expect('5 addresses imported')
			t.ok()

	def regtest_addrimport_bob(self,name):   self.regtest_addrimport(name,'bob')
	def regtest_addrimport_alice(self,name): self.regtest_addrimport(name,'alice')

	def regtest_fund_wallet(self,name,user,mmtype,amt):
		fn = get_file_with_ext('-{}[1-5].addrs'.format(mmtype),self.regtest_user_dir(user),no_dot=True)
		silence()
		addr = AddrList(fn).data[0].addr
		end_silence()
		t = MMGenExpect(name,'mmgen-regtest', ['send',str(addr),str(amt)])
		t.expect('Sending {} BTC'.format(amt))
		t.expect('Mined 1 block')
		t.ok()

	def regtest_fund_bob(self,name):   self.regtest_fund_wallet(name,'bob','C',500)
	def regtest_fund_alice(self,name): self.regtest_fund_wallet(name,'alice','S',500)

	def regtest_user_bal(self,name,user,bal):
		t = MMGenExpect(name,'mmgen-tool',['--'+user,'listaddresses','showempty=1'])
		total = t.expect_getend('TOTAL: ')
		cmp_or_die(total,'{} BTC'.format(bal))

	def regtest_alice_bal1(self,name):
		return self.regtest_user_bal(name,'alice','500')

	def regtest_bob_bal1(self,name):
		return self.regtest_user_bal(name,'bob','500')

	def regtest_bob_bal2(self,name):
		return self.regtest_user_bal(name,'bob','499.999942')

	def regtest_bob_bal3(self,name):
		return self.regtest_user_bal(name,'bob','399.9998214')

	def regtest_bob_bal4(self,name):
		return self.regtest_user_bal(name,'bob','399.9998079')

	def regtest_bob_bal5(self,name):
		return self.regtest_user_bal(name,'bob','399.9996799')

	def regtest_bob_alice_bal(self,name):
		t = MMGenExpect(name,'mmgen-regtest',['get_balances'])
		t.expect('Switching')
		ret = t.expect_getend("Bob's balance:").strip()
		cmp_or_die(ret,'13.00000000',skip_ok=True)
		ret = t.expect_getend("Alice's balance:").strip()
		cmp_or_die(ret,'986.99957990',skip_ok=True)
		t.ok()

	def regtest_user_txdo(self,name,user,fee,outputs_cl,outputs_prompt,extra_args=[],no_send=False):
		os.environ['MMGEN_BOGUS_SEND'] = ''
		t = MMGenExpect(name,'mmgen-txdo',
			['-d',cfg['tmpdir'],'-B','--'+user,'--tx-fee='+fee] + extra_args + outputs_cl)
		os.environ['MMGEN_BOGUS_SEND'] = '1'

		t.expect(r"'q'=quit view, .*?:.",'M',regex=True) # sort by mmid
		t.expect(r"'q'=quit view, .*?:.",'q',regex=True)
		t.expect('outputs to spend: ',outputs_prompt+'\n')
		t.expect('OK? (Y/n): ','y') # fee OK?
		t.expect('OK? (Y/n): ','y') # change OK?
		t.expect('Add a comment to transaction? (y/N): ','\n')
		t.expect('View decoded transaction\? .*?: ','t',regex=True)
		t.expect('to continue: ','\n')
		t.passphrase('MMGen wallet','abc')
		t.written_to_file('Signed transaction')
		if not no_send:
			t.expect('to confirm: ','YES, I REALLY WANT TO DO THIS\n')
			t.expect('Transaction sent')
		t.read()
		t.ok()

	def regtest_bob_split1(self,name):
		sid = self.regtest_user_sid('bob')
		outputs_cl = [sid+':C:1,100', sid+':L:2,200',sid+':S:2']
		return self.regtest_user_txdo(name,'bob','20s',outputs_cl,'1')

	def create_tx_outputs(self,user,data):
		o,sid = [],self.regtest_user_sid(user)
		for id_str,idx,amt_str in data:
			fn = get_file_with_ext('{}{}[1-5].addrs'.format(sid,id_str),self.regtest_user_dir(user),no_dot=True)
			silence()
			addr = AddrList(fn).data[idx-1].addr
			end_silence()
			o.append(addr+amt_str)
		return o

	def regtest_bob_rbf_send(self,name):
		outputs_cl = self.create_tx_outputs('alice',(('',1,',60'),('-C',1,',40'))) # alice_sid:L:1, alice_sid:C:1
		outputs_cl += [self.regtest_user_sid('bob')+':S:2']
		return self.regtest_user_txdo(name,'bob','10s',outputs_cl,'3',extra_args=['--rbf'])

	def regtest_bob_send_non_mmgen(self,name):
		outputs_cl = self.create_tx_outputs('alice',(('-S',2,',10'),('-S',3,''))) # alice_sid:S:2, alice_sid:S:3
		fn = os.path.join(cfg['tmpdir'],'non-mmgen.keys')
		return self.regtest_user_txdo(name,'bob','0.0001',outputs_cl,'3-9',extra_args=['--keys-from-file='+fn])

	def regtest_user_txbump(self,name,user,txfile,fee,red_op,no_send=False):
		os.environ['MMGEN_BOGUS_SEND'] = ''
		t = MMGenExpect(name,'mmgen-txbump',
			['-d',cfg['tmpdir'],'--send','--'+user,'--tx-fee='+fee,'--output-to-reduce='+red_op] + [txfile])
		os.environ['MMGEN_BOGUS_SEND'] = '1'
		t.expect('OK? (Y/n): ','y') # output OK?
		t.expect('OK? (Y/n): ','y') # fee OK?
		t.expect('Add a comment to transaction? (y/N): ','n')
		t.passphrase('MMGen wallet','abc')
		t.written_to_file('Signed transaction')
		if not no_send:
			t.expect('to confirm: ','YES, I REALLY WANT TO DO THIS\n')
			t.expect('Transaction sent')
			t.written_to_file('Signed transaction')
		t.read()
		t.ok()

	def regtest_bob_rbf_bump(self,name):
		txfile = get_file_with_ext(',10].sigtx',cfg['tmpdir'],delete=False,no_dot=True)
		return self.regtest_user_txbump(name,'bob',txfile,'60s','c')

	def regtest_generate(self,name):
		t = MMGenExpect(name,'mmgen-regtest',['generate'])
		t.expect('Mined 1 block')
		t.ok()

	def regtest_get_mempool(self,name):
		t = MMGenExpect(name,'mmgen-regtest',['show_mempool'])
		return eval(t.read())

	def regtest_get_mempool1(self,name):
		mp = self.regtest_get_mempool(name)
		if len(mp) != 1:
			rdie(2,'Mempool has more or less than one TX!')
		write_to_tmpfile(cfg,'rbf_txid',mp[0]+'\n')
		ok()

	def regtest_get_mempool2(self,name):
		mp = self.regtest_get_mempool(name)
		if len(mp) != 1:
			rdie(2,'Mempool has more or less than one TX!')
		chk = read_from_tmpfile(cfg,'rbf_txid')
		if chk.strip() == mp[0]:
			rdie(2,'TX in mempool has not changed!  RBF bump failed')
		ok()

	@staticmethod
	def gen_pairs(n):
		return [subprocess.check_output(
					['python','mmgen-tool','--testnet=1','-r0','randpair','compressed={}'.format((i+1)%2)]).split()
						for i in range(n)]

	def regtest_bob_pre_import(self,name):
		pairs = self.gen_pairs(5)
		write_to_tmpfile(cfg,'non-mmgen.keys','\n'.join([a[0] for a in pairs])+'\n')
		write_to_tmpfile(cfg,'non-mmgen.addrs','\n'.join([a[1] for a in pairs])+'\n')
		return self.regtest_user_txdo(name,'bob','10s',[pairs[0][1]],'3')

	def regtest_user_import(self,name,user,args):
		t = MMGenExpect(name,'mmgen-addrimport',['--quiet','--'+user]+args)
		t.expect('Importing')
		t.expect('OK')
		t.ok()

	def regtest_bob_import_addr(self,name):
		addr = read_from_tmpfile(cfg,'non-mmgen.addrs').split()[0]
		return self.regtest_user_import(name,'bob',['--rescan','--address='+addr])

	def regtest_bob_import_list(self,name):
		fn = os.path.join(cfg['tmpdir'],'non-mmgen.addrs')
		return self.regtest_user_import(name,'bob',['--addrlist',fn])

	def regtest_bob_split2(self,name):
		addrs = read_from_tmpfile(cfg,'non-mmgen.addrs').split()
		amts = (a for a in (1.12345678,2.87654321,3.33443344,4.00990099,5.43214321))
		outputs1 = ['{},{}'.format(a,amts.next()) for a in addrs]
		sid = self.regtest_user_sid('bob')
		outputs2 = [sid+':C:2,6', sid+':L:3,7',sid+':S:3']
		return self.regtest_user_txdo(name,'bob','20s',outputs1+outputs2,'1-2')

	def regtest_user_add_label(self,name,user,addr,label):
		t = MMGenExpect(name,'mmgen-tool',['--'+user,'add_label',addr,label])
		t.expect('Added label.*in tracking wallet',regex=True)
		t.ok()

	def regtest_user_remove_label(self,name,user,addr):
		t = MMGenExpect(name,'mmgen-tool',['--'+user,'remove_label',addr])
		t.expect('Removed label.*in tracking wallet',regex=True)
		t.ok()

	def regtest_alice_add_label1(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_add_label(name,'alice',sid+':S:1','Original Label')

	def regtest_alice_add_label2(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_add_label(name,'alice',sid+':S:1','Replacement Label')

	def regtest_alice_remove_label1(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_remove_label(name,'alice',sid+':S:1')

	def regtest_user_chk_label(self,name,user,addr,label):
		t = MMGenExpect(name,'mmgen-tool',['--'+user,'listaddresses','all_labels=1'])
		t.expect('{}\s+\S{{30}}\S+\s+{}\s+'.format(addr,label),regex=True)
		t.ok()

	def regtest_alice_chk_label1(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_chk_label(name,'alice',sid+':S:1','Original Label')

	def regtest_alice_chk_label2(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_chk_label(name,'alice',sid+':S:1','Replacement Label')

	def regtest_alice_chk_label3(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_chk_label(name,'alice',sid+':S:1','Edited Label')

	def regtest_alice_chk_label4(self,name):
		sid = self.regtest_user_sid('alice')
		return self.regtest_user_chk_label(name,'alice',sid+':S:1','-')

	def regtest_user_edit_label(self,name,user,output,label):
		t = MMGenExpect(name,'mmgen-txcreate',['-B','--'+user,'-i'])
		t.expect(r"'q'=quit view, .*?:.",'M',regex=True)
		t.expect(r"'q'=quit view, .*?:.",'l',regex=True)
		t.expect(r"Enter unspent.*return to main menu\):.",output+'\n',regex=True)
		t.expect(r"Enter label text.*return to main menu\):.",label+'\n',regex=True)
		t.expect(r"'q'=quit view, .*?:.",'q',regex=True)
		t.ok()

	def regtest_alice_edit_label1(self,name):
		return self.regtest_user_edit_label(name,'alice','3','Edited Label')

	def regtest_stop(self,name):
		t = MMGenExpect(name,'mmgen-regtest',['stop'])
		t.ok()

	# END methods
	for k in (
			'ref_wallet_conv',
			'ref_mn_conv',
			'ref_seed_conv',
			'ref_hex_conv',
			'ref_brain_conv',
			'ref_incog_conv',
			'ref_incox_conv',
			'ref_hincog_conv',
			'ref_hincog_conv_old',
			'ref_wallet_conv_out',
			'ref_mn_conv_out',
			'ref_seed_conv_out',
			'ref_hex_conv_out',
			'ref_incog_conv_out',
			'ref_incox_conv_out',
			'ref_hincog_conv_out',
			'ref_wallet_chk',
			'refwalletgen',
			'ref_seed_chk',
			'ref_hex_chk',
			'ref_mn_chk',
			'ref_brain_chk',
			'ref_hincog_chk',
			'refaddrgen',
			'refkeyaddrgen',
			'refaddrgen_compressed',
			'refkeyaddrgen_compressed',
			'refpasswdgen',
			'ref_b32passwdgen'
		):
		for i in ('1','2','3'):
			locals()[k+i] = locals()[k]

	for k in ('walletgen','addrgen','keyaddrgen'): locals()[k+'14'] = locals()[k]

# create temporary dirs
if not opt.resume and not opt.skip_deps:
	if g.platform == 'win':
		for cfg in sorted(cfgs):
			mk_tmpdir(cfgs[cfg]['tmpdir'])
	else:
		for cfg in sorted(cfgs):
			src = os.path.join(shm_dir,cfgs[cfg]['tmpdir'].split('/')[-1])
			mk_tmpdir(src)
			try:
				os.unlink(cfgs[cfg]['tmpdir'])
			except OSError as e:
				if e.errno != 2: raise
			finally:
				os.symlink(src,cfgs[cfg]['tmpdir'])

have_dfl_wallet = False

# main()
if opt.pause:
	import termios,atexit
	fd = sys.stdin.fileno()
	old = termios.tcgetattr(fd)
	def at_exit():
		termios.tcsetattr(fd, termios.TCSADRAIN, old)
	atexit.register(at_exit)

start_time = int(time.time())

def end_msg():
	t = int(time.time()) - start_time
	m = '{} tests performed.  Elapsed time: {:02d}:{:02d}\n'
	sys.stderr.write(green(m.format(cmd_total,t/60,t%60)))

ts = MMGenTestSuite()

try:
	if cmd_args:
		for arg in cmd_args:
			if arg in utils:
				globals()[arg](cmd_args[cmd_args.index(arg)+1:])
				sys.exit(0)
			elif 'info_'+arg in cmd_data:
				dirs = cmd_data['info_'+arg][1]
				if dirs: clean(dirs)
				for cmd in cmd_list[arg]:
					check_needs_rerun(ts,cmd,build=True)
			elif arg in meta_cmds:
				for cmd in meta_cmds[arg]:
					check_needs_rerun(ts,cmd,build=True)
			elif arg in cmd_data:
				check_needs_rerun(ts,arg,build=True)
			else:
				die(1,'%s: unrecognized command' % arg)
	else:
		clean()
		for cmd in cmd_data:
			if cmd == 'info_regtest': break # don't run these by default
			if cmd[:5] == 'info_':
				msg(green('%sTesting %s' % (('\n','')[bool(opt.resume)],cmd_data[cmd][0])))
				continue
			ts.do_cmd(cmd)
			if cmd is not cmd_data.keys()[-1]: do_between()
except KeyboardInterrupt:
	die(1,'\nExiting at user request')
except opt.traceback and Exception:
	with open('my.err') as f:
		t = f.readlines()
		if t: msg_r('\n'+yellow(''.join(t[:-1]))+red(t[-1]))
	die(1,blue('Test script exited with error'))
except:
	sys.stderr = stderr_save
	raise

end_msg()
