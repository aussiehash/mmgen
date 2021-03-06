#!/usr/bin/env python
#
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
test/tooltest.py:  Tests for the 'mmgen-tool' utility
"""

import sys,os,subprocess
pn = os.path.dirname(sys.argv[0])
os.chdir(os.path.join(pn,os.pardir))
sys.path.__setitem__(0,os.path.abspath(os.curdir))

# Import this _after_ local path's been added to sys.path
from mmgen.common import *

from collections import OrderedDict
cmd_data = OrderedDict([
	('util', {
			'desc': 'base conversion, hashing and file utilities',
			'cmd_data': OrderedDict([
				('Strtob58',     ()),
				('B58tostr',     ('Strtob58','io')),
				('Hextob58',     ()),
				('B58tohex',     ('Hextob58','io')),
				('B58randenc',   ()),
				('Hextob32',     ()),
				('B32tohex',     ('Hextob32','io')),
				('Randhex',      ()),
				('Id6',          ()),
				('Id8',          ()),
				('Str2id6',      ()),
				('Hash160',      ()),
				('Hash256',      ()),
				('Hexreverse',   ()),
				('Hexlify',      ()),
				('Hexdump',      ()),
				('Unhexdump',    ('Hexdump','io')),
				('Rand2file',    ()),
			])
		}
	),
	('bitcoin', {
			'desc': 'Bitcoin address/key commands',
			'cmd_data': OrderedDict([
				('Randwif',        ()),
				('Randpair',       ()), # create 3 pairs: uncomp,comp,segwit
				('Wif2addr',       ('Randpair','o3')),
				('Wif2hex',        ('Randpair','o3')),

				('Privhex2pubhex', ('Wif2hex','o3')),
				('Pubhex2addr',    ('Privhex2pubhex','o3')),
				('Pubhex2redeem_script', ('Privhex2pubhex','o3')),
				('Wif2redeem_script', ('Randpair','o3')),
				('Wif2segwit_pair',   ('Randpair','o2')),

				('Privhex2addr',   ('Wif2hex','o3')), # compare with output of Randpair
				('Hex2wif',        ('Wif2hex','io2')),
				('Addr2hexaddr',   ('Randpair','o2')),
				('Hexaddr2addr',   ('Addr2hexaddr','io2')),

				('Pipetest',       ('Randpair','o3')),
			])
		}
	),
	('mnemonic', {
			'desc': 'mnemonic commands',
			'cmd_data': OrderedDict([
				('Hex2mn',       ()),
				('Mn2hex',       ('Hex2mn','io3')),
				('Mn_rand128',   ()),
				('Mn_rand192',   ()),
				('Mn_rand256',   ()),
				('Mn_stats',     ()),
				('Mn_printlist', ()),
			])
		}
	),
	('rpc', {
			'desc': 'Bitcoind RPC commands',
			'cmd_data': OrderedDict([
#				('keyaddrfile_chksum', ()), # interactive
				('Addrfile_chksum', ()),
				('Getbalance',      ()),
				('Listaddresses',   ()),
				('Twview',          ()),
				('Txview',          ()),
			])
		}
	),
])

cfg = {
	'name':          'the tool utility',
	'enc_passwd':    'Ten Satoshis',
	'tmpdir':        'test/tmp10',
	'tmpdir_num':    10,
	'refdir':        'test/ref',
	'txfile':        'FFB367[1.234].rawtx',
	'addrfile':      '98831F3A[1,31-33,500-501,1010-1011].addrs',
	'addrfile_chk':  '6FEF 6FB9 7B13 5D91',
}

opts_data = lambda: {
	'desc': "Test suite for the 'mmgen-tool' utility",
	'usage':'[options] [command]',
	'options': """
-h, --help          Print this help message
--, --longhelp      Print help message for long options (common options)
-l, --list-cmds     List and describe the tests and commands in this test suite
-L, --list-names    List the names of all tested 'mmgen-tool' commands
-s, --system        Test scripts and modules installed on system rather than
                    those in the repo root
-v, --verbose       Produce more verbose output
""",
	'notes': """

If no command is given, the whole suite of tests is run.
"""
}

sys.argv = [sys.argv[0]] + ['--skip-cfg-file'] + sys.argv[1:]

cmd_args = opts.init(opts_data,add_opts=['exact_output','profile'])
spawn_cmd = ['python',os.path.join(os.curdir,'mmgen-tool') if not opt.system else 'mmgen-tool']
add_spawn_args = ' '.join(['{} {}'.format(
	'--'+k.replace('_','-'),
	getattr(opt,k) if getattr(opt,k) != True else ''
	) for k in ('testnet','rpc_host','regtest') if getattr(opt,k)]).split()
add_spawn_args += [ '--data-dir', cfg['tmpdir']] # ignore ~/.mmgen

if opt.system: sys.path.pop(0)

if opt.list_cmds:
	fs = '  {:<{w}} - {}'
	Msg('Available commands:')
	w = max([len(i) for i in cmd_data])
	for cmd in cmd_data:
		Msg(fs.format(cmd,cmd_data[cmd]['desc'],w=w))
	Msg('\nAvailable utilities:')
	Msg(fs.format('clean','Clean the tmp directory',w=w))
	sys.exit(0)
if opt.list_names:
	acc = []
	for v in cmd_data.values():
		acc += v['cmd_data'].keys()
	tc = sorted(c.lower() for c in acc)
	msg('{}\n{}'.format(green('Tested commands:'),'\n'.join(tc)))
	import mmgen.tool
	tested_in_tool = ('Encrypt','Decrypt','Find_incog_data','Keyaddrfile_chksum','Passwdfile_chksum')
	ignore = ('Help','Usage')
	uc = sorted(c.lower() for c in set(mmgen.tool.cmd_data.keys()) - set(acc) - set(ignore) - set(tested_in_tool))
	msg('\n{}\n{}'.format(yellow('Untested commands:'),'\n'.join(uc)))
	die()

import binascii
from mmgen.test import *
from mmgen.tx import is_wif,is_btc_addr

msg_w = 35
def test_msg(m):
	m2 = 'Testing {}'.format(m)
	msg_r(green(m2+'\n') if opt.verbose else '{:{w}}'.format(m2,w=msg_w+8))

class MMGenToolTestSuite(object):

	def __init__(self):
		pass

	def gen_deps_for_cmd(self,cmd,cdata):
		fns = []
		if cdata:
			name,code = cdata
			io,count = (code[:-1],int(code[-1])) if code[-1] in '0123456789' else (code,1)

			for c in range(count):
				fns += ['%s%s%s' % (
					name,
					('',c+1)[count > 1],
					('.out','.in')[ch=='i']
				) for ch in io]
		return fns

	def get_num_exts_for_cmd(self,cmd,dpy): # dpy required here
		num = str(tool_cfgs['tmpdir_num'])
		# return only first file - a hack
		exts = gen_deps_for_cmd(dpy)
		return num,exts

	def do_cmds(self,cmd_group):
		cdata = cmd_data[cmd_group]['cmd_data']
		for cmd in cdata: self.do_cmd(cmd,cdata[cmd])

	def do_cmd(self,cmd,cdata):
		fns = self.gen_deps_for_cmd(cmd,cdata)
		file_list = [os.path.join(cfg['tmpdir'],fn) for fn in fns]
		self.__class__.__dict__[cmd](*([self,cmd] + file_list))

	def run_cmd(self,name,tool_args,kwargs='',extra_msg='',silent=False,strip=True):
		sys_cmd = (
			spawn_cmd +
			add_spawn_args +
			['-r0','-d',cfg['tmpdir'],name.lower()] +
			tool_args +
			kwargs.split()
		)
		if extra_msg: extra_msg = '({})'.format(extra_msg)
		full_name = ' '.join([name.lower()]+kwargs.split()+extra_msg.split())
		if not silent:
			if opt.verbose:
				sys.stderr.write(green('Testing {}\nExecuting '.format(full_name)))
				sys.stderr.write(cyan(' '.join(sys_cmd)+'\n'))
			else:
				msg_r('Testing {:{w}}'.format(full_name+':',w=msg_w))

		p = subprocess.Popen(sys_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		a,b = p.communicate()
		retcode = p.wait()
		if retcode != 0:
			msg('%s\n%s\n%s'%(red('FAILED'),yellow('Command stderr output:'),b))
			die(1,red('Called process returned with an error (retcode %s)' % retcode))
		return (a,a.rstrip())[bool(strip)]

	def run_cmd_chk(self,name,f1,f2,kwargs='',extra_msg='',strip_hex=False):
		idata = read_from_file(f1).rstrip()
		odata = read_from_file(f2).rstrip()
		ret = self.run_cmd(name,[odata],kwargs=kwargs,extra_msg=extra_msg)
		vmsg('In:   ' + repr(odata))
		vmsg('Out:  ' + repr(ret))
		def cmp_equal(a,b):
			return (a.lstrip('0') == b.lstrip('0')) if strip_hex else (a == b)
		if cmp_equal(ret,idata): ok()
		else:
			die(3,red(
	"Error: values don't match:\nIn:  %s\nOut: %s" % (repr(idata),repr(ret))))
		return ret

	def run_cmd_nochk(self,name,f1,kwargs=''):
		odata = read_from_file(f1).rstrip()
		ret = self.run_cmd(name,[odata],kwargs=kwargs)
		vmsg('In:   ' + repr(odata))
		vmsg('Out:  ' + repr(ret))
		return ret

	def run_cmd_out(self,name,carg=None,Return=False,kwargs='',fn_idx='',extra_msg='',literal=False,chkdata='',hush=False):
		if carg: write_to_tmpfile(cfg,'%s%s.in' % (name,fn_idx),carg+'\n')
		ret = self.run_cmd(name,([],[carg])[bool(carg)],kwargs=kwargs,extra_msg=extra_msg)
		if carg: vmsg('In:   ' + repr(carg))
		vmsg('Out:  ' + (repr(ret),ret.decode('utf8'))[literal])
		if ret or ret == '':
			write_to_tmpfile(cfg,'%s%s.out' % (name,fn_idx),ret+'\n')
			if chkdata:
				cmp_or_die(ret,chkdata)
				return
			if Return: return ret
			else:
				if not hush: ok()
		else:
			die(3,red("Error for command '%s'" % name))

	def run_cmd_randinput(self,name,strip=True):
		s = os.urandom(128)
		fn = name+'.in'
		write_to_tmpfile(cfg,fn,s,binary=True)
		ret = self.run_cmd(name,[get_tmpfile_fn(cfg,fn)],strip=strip)
		fn = name+'.out'
		write_to_tmpfile(cfg,fn,ret+'\n')
		ok()
		vmsg('Returned: %s' % ret)

	# Util
	def Strtob58(self,name):       self.run_cmd_out(name,getrandstr(16))
	def B58tostr(self,name,f1,f2): self.run_cmd_chk(name,f1,f2)
	def Hextob58(self,name):       self.run_cmd_out(name,getrandhex(32))
	def B58tohex(self,name,f1,f2): self.run_cmd_chk(name,f1,f2,strip_hex=True)
	def B58randenc(self,name):
		ret = self.run_cmd_out(name,Return=True)
		ok_or_die(ret,is_b58_str,'base 58 string')
	def Hextob32(self,name):       self.run_cmd_out(name,getrandhex(24))
	def B32tohex(self,name,f1,f2): self.run_cmd_chk(name,f1,f2,strip_hex=True)
	def Randhex(self,name):
		ret = self.run_cmd_out(name,Return=True)
		ok_or_die(ret,binascii.unhexlify,'hex string')
	def Id6(self,name):     self.run_cmd_randinput(name)
	def Id8(self,name):     self.run_cmd_randinput(name)
	def Str2id6(self,name):
		s = getrandstr(120,no_space=True)
		s2 = ' %s %s %s %s %s ' % (s[:3],s[3:9],s[9:29],s[29:50],s[50:120])
		ret1 = self.run_cmd(name,[s],extra_msg='unspaced input'); ok()
		ret2 = self.run_cmd(name,[s2],extra_msg='spaced input')
		cmp_or_die(ret1,ret2)
		vmsg('Returned: %s' % ret1)
	def Hash160(self,name):        self.run_cmd_out(name,getrandhex(16))
	def Hash256(self,name):        self.run_cmd_out(name,getrandstr(16))
	def Hexreverse(self,name):     self.run_cmd_out(name,getrandhex(24))
	def Hexlify(self,name):        self.run_cmd_out(name,getrandstr(24))
	def Hexdump(self,name): self.run_cmd_randinput(name,strip=False)
	def Unhexdump(self,name,fn1,fn2):
		ret = self.run_cmd(name,[fn2],strip=False)
		orig = read_from_file(fn1,binary=True)
		cmp_or_die(orig,ret)
	def Rand2file(self,name):
		of = name + '.out'
		dlen = 1024
		self.run_cmd(name,[of,str(1024),'threads=4','silent=1'],strip=False)
		d = read_from_tmpfile(cfg,of,binary=True)
		cmp_or_die(dlen,len(d))

	# Bitcoin
	def Randwif(self,name):
		for n,k in enumerate(['','compressed=1']):
			ret = self.run_cmd_out(name,kwargs=k,Return=True,fn_idx=n+1)
			ok_or_die(ret,is_wif,'WIF key')
	def Randpair(self,name):
		for n,k in enumerate(['','compressed=1','segwit=1 compressed=1']):
			wif,addr = self.run_cmd_out(name,kwargs=k,Return=True,fn_idx=n+1).split()
			ok_or_die(wif,is_wif,'WIF key',skip_ok=True)
			ok_or_die(addr,is_btc_addr,'Bitcoin address')
	def Wif2addr(self,name,f1,f2,f3):
		for n,f,k,m in ((1,f1,'',''),(2,f2,'','compressed'),(3,f3,'segwit=1','compressed')):
			wif = read_from_file(f).split()[0]
			self.run_cmd_out(name,wif,kwargs=k,fn_idx=n,extra_msg=m)
	def Wif2hex(self,name,f1,f2,f3):
		for n,f,m in ((1,f1,''),(2,f2,'compressed'),(3,f3,'compressed for segwit')):
			wif = read_from_file(f).split()[0]
			self.run_cmd_out(name,wif,fn_idx=n,extra_msg=m)
	def Privhex2addr(self,name,f1,f2,f3):
		keys = [read_from_file(f).rstrip() for f in (f1,f2,f3)]
		for n,k in enumerate(('','compressed=1','compressed=1 segwit=1')):
			ret = self.run_cmd(name,[keys[n]],kwargs=k).rstrip()
			iaddr = read_from_tmpfile(cfg,'Randpair{}.out'.format(n+1)).split()[-1]
			cmp_or_die(iaddr,ret)
	def Hex2wif(self,name,f1,f2,f3,f4):
		for n,fi,fo,k in ((1,f1,f2,''),(2,f3,f4,'compressed=1')):
			ret = self.run_cmd_chk(name,fi,fo,kwargs=k)
	def Addr2hexaddr(self,name,f1,f2):
		for n,f,m in ((1,f1,''),(2,f2,'from compressed')):
			addr = read_from_file(f).split()[-1]
			self.run_cmd_out(name,addr,fn_idx=n,extra_msg=m)
	def Hexaddr2addr(self,name,f1,f2,f3,f4):
		for n,fi,fo,m in ((1,f1,f2,''),(2,f3,f4,'from compressed')):
			self.run_cmd_chk(name,fi,fo,extra_msg=m)
	def Privhex2pubhex(self,name,f1,f2,f3): # from Hex2wif
		addr = read_from_file(f3).strip()
		self.run_cmd_out(name,addr,kwargs='compressed=1',fn_idx=3)
	def Pubhex2redeem_script(self,name,f1,f2,f3): # from above
		addr = read_from_file(f3).strip()
		self.run_cmd_out(name,addr,fn_idx=3)
		rs = read_from_tmpfile(cfg,name+'3.out').strip()
		self.run_cmd_out('pubhex2addr',rs,kwargs='p2sh=1',fn_idx=3,hush=True)
		addr1 = read_from_tmpfile(cfg,'pubhex2addr3.out').strip()
		addr2 = read_from_tmpfile(cfg,'Randpair3.out').split()[1]
		cmp_or_die(addr1,addr2)
	def Wif2redeem_script(self,name,f1,f2,f3): # compare output with above
		wif = read_from_file(f3).split()[0]
		ret1 = self.run_cmd_out(name,wif,fn_idx=3,Return=True)
		ret2 = read_from_tmpfile(cfg,'Pubhex2redeem_script3.out').strip()
		cmp_or_die(ret1,ret2)
	def Wif2segwit_pair(self,name,f1,f2): # does its own checking, so just run
		wif = read_from_file(f2).split()[0]
		self.run_cmd_out(name,wif,fn_idx=2)

	def Pubhex2addr(self,name,f1,f2,f3):
		addr = read_from_file(f3).strip()
		self.run_cmd_out(name,addr,fn_idx=3)

	def Pipetest(self,name,f1,f2,f3):
		test_msg('command piping')
		wif = read_from_file(f3).split()[0]
		cmd = '{tc} {sa} wif2hex {wif} | {tc} privhex2pubhex - compressed=1 | {tc} pubhex2redeem_script - | {tc} {sa} pubhex2addr - p2sh=1'.format(wif=wif,sa=' '.join(add_spawn_args),tc=' '.join(spawn_cmd))
		p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
		res = p.stdout.read().strip()
		addr = read_from_tmpfile(cfg,'Wif2addr3.out').strip()
		cmp_or_die(res,addr)


	# Mnemonic
	def Hex2mn(self,name):
		for n,size,m in ((1,16,'128-bit'),(2,24,'192-bit'),(3,32,'256-bit')):
			hexnum = getrandhex(size)
			self.run_cmd_out(name,hexnum,fn_idx=n,extra_msg=m)
	def Mn2hex(self,name,f1,f2,f3,f4,f5,f6):
		for f_i,f_o,m in ((f1,f2,'128-bit'),(f3,f4,'192-bit'),(f5,f6,'256-bit')):
			self.run_cmd_chk(name,f_i,f_o,extra_msg=m)
	def Mn_rand128(self,name): self.run_cmd_out(name)
	def Mn_rand192(self,name): self.run_cmd_out(name)
	def Mn_rand256(self,name): self.run_cmd_out(name)
	def Mn_stats(self,name):   self.run_cmd_out(name)
	def Mn_printlist(self,name):
		self.run_cmd(name,[])
		ok()

	# RPC
	def Addrfile_chksum(self,name):
		fn = os.path.join(cfg['refdir'],cfg['addrfile'])
		self.run_cmd_out(name,fn,literal=True,chkdata=cfg['addrfile_chk'])
	def Getbalance(self,name):
		self.run_cmd_out(name,literal=True)
	def Listaddresses(self,name):
		self.run_cmd_out(name,literal=True)
	def Twview(self,name):
		self.run_cmd_out(name,literal=True)
	def Txview(self,name):
		fn = os.path.join(cfg['refdir'],cfg['txfile'])
		self.run_cmd_out(name,fn,literal=True)

# main()
import time
start_time = int(time.time())
ts = MMGenToolTestSuite()
mk_tmpdir(cfg['tmpdir'])

if cmd_args:
	if len(cmd_args) != 1:
		die(1,'Only one command may be specified')
	cmd = cmd_args[0]
	if cmd in cmd_data:
		msg('Running tests for %s:' % cmd_data[cmd]['desc'])
		ts.do_cmds(cmd)
	elif cmd == 'clean':
		cleandir(cfg['tmpdir'])
		sys.exit(0)
	else:
		die(1,"'%s': unrecognized command" % cmd)
else:
	cleandir(cfg['tmpdir'])
	for cmd in cmd_data:
		msg('Running tests for %s:' % cmd_data[cmd]['desc'])
		ts.do_cmds(cmd)
		if cmd is not cmd_data.keys()[-1]: msg('')

t = int(time.time()) - start_time
msg(green(
	'All requested tests finished OK, elapsed time: %02i:%02i' % (t/60,t%60)))
