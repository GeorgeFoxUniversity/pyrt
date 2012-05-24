# pyrt/user.py
# Copyright (C) 2007, 2008 Justin Azoff JAzoff@uamail.albany.edu
#
# This module is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.php

import re
import forms

def and_(crit):
	return '(' + ' AND '.join(crit) + ')'
def or_(crit):
	return '(' + ' OR '.join(crit)  + ')'

class Field:
	def __init__(self, name):
		self.name=name

	def __eq__(self, other):
		return self._compare(self.name, other, '=')
	def __ne__(self, other):
		return self._compare(self.name, other, '!=')
	def __gt__(self, other):
		return self._compare(self.name, other, '>')
	def __lt__(self, other):
		return self._compare(self.name, other, '<')

	def __ge__(self, other):
		return self._compare(self.name, other, '>=')
	def __le__(self, other):
		return self._compare(self.name, other, '<=')

	def like(self, other):
		return self._compare(self.name, other, 'LIKE')
	contains = like


	def _compare(self, name, other, op):
		nullops = {'=': 'IS', '!=': 'IS NOT'}
		if other is None:
			other = 'NULL'
			op = nullops[op]
		t = "'%s' %s '%s'"
		return t % (name, op, other)

class FieldWrapper:
	def __init__(self, custom=False):
		self.custom=custom
		self.cf = None
	def __getattr__(self, attr):
		if self.custom:
			return Field('CF.{%s}' % attr)
		else:
			return Field(attr)

	__call__ = __getattr__

class User(object):
	def __init__(self, rtclient, id=None, fields=None):
		self.id=id
		self._fields = fields
		self.rt = rtclient
		self.c = FieldWrapper()
		self.c.cf = FieldWrapper(custom=True)

		self._dirty_fields = {}
		if fields:
			self.id = fields['id']
		if id:
			self._user_initialized = True

	def __repr__(self):
		return "[pyrt.user %s]" % self.id

	def get(self, id):
		"""Fetch a user"""
		if 'user/' in str(id):
			id = int(id.replace('user/',''))
		new_user = User(self.rt, id)
		return new_user

	def show(self, force=False):
		"""Return all the fields for this user"""

		if not force and self._fields:
			return self._fields

		fields = self.rt._do('user/show', id=self.id)
		self._fields = fields[0]
		return fields[0]
	cache = show

	def create(self, **fields):
		"""Create a new user
		   >>> rt.user.new(id='rbackman', email='rbackman@georgefox.edu',
				   cf={
					'building': building_name,
					'room':	 room_number,
				   })
		"""
		
		self.id = 'new'
		out = self.edit(**fields)
		msg = out[0]['rt_comments'][0]
		match = re.search("User (\d+) created",msg)
		if match:
			id = match.groups()[0]
			self.id = id
			self._user_initialized = True
			return self
		raise Exception("Error creating user %s" % out)

	def edit(self, **fields):
		"""Edit an existing user
		   >>> t = rt.user.get('rbackman')
		   >>> t.edit(email='email@somewhere.com')
		"""
		fields['id'] = self.id
		content = forms.generate(fields)
		page = self.rt._do('user/%s/edit' % self.id, content=content)
		return page

	def save(self):
		if not self._dirty_fields:
			return
		fields = {}
		fields['id'] = self.id
		fields.update(self._dirty_fields)
		ret = self.edit(**fields)
		self._dirty_fields = {}
		return ret

	def __getattr__(self, attr):
		if not self.id:
			raise AttributeError, "'User' object has no attribute '%s'" % attr
		self.cache()
		f = self._fields

		if attr in f:
			return f[attr]

		a = attr.replace("_","-") 
		if a in f:
			return f[a]

		raise AttributeError, "'User' object has no attribute '%s'" % attr
		
	def __getitem__(self, attr):
		f = self._fields
		return f[attr]

	def __setattr__(self, attr, val):
		if not self.__dict__.has_key('_user_initialized') or attr.startswith("_"):
			# this test allows attributes to be set in the __init__ method
			return dict.__setattr__(self, attr, val)
		self.cache()
		f = self._fields
		if attr in f:
			self._dirty_fields[attr] = val
			f[attr] = val
			return

		a = attr.replace("_","-") 
		if a in f:
			self._dirty_fields[a] = val
			f[a] = val
			return

		raise AttributeError, "'User' object has no attribute '%s'" % attr

__all__ = ["User","and_","or_"]
