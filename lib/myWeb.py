# -*- coding: utf-8 -*-
# This module constains some commom classes about web object and page
# Author: chenxm 2012-05-22
#from __future__ import division
import re, math, datetime, random
import utilities

feature_name_file = 'conf/fnames'

class WebObject(object):
	""" Defining the class for web objects.
	"""
	def __init__(self):
		self.start_time = None	# datetime
		self.total_time = None	# timedelta
		self.receiving_time = None	#int (ms)
		self.url = None
		self.status = None
		self.size = None	#int (Byte)
		self.type = None
		self.referrer = None
		self.re_url = None
		self.user_agent = None
		self.user_ip = None
		
		self.pageid = None

	def is_root(self):
		""" Check if the object is a HTML file. 
		"""
		if self.type is None:
			return False
		ct_re = re.compile(r'\w+\/(\w+)')
		ct_mch = ct_re.match(self.type)
		sub_t = None
		if ct_mch:
			sub_t = ct_mch.group(1)
		if sub_t in ['html', 'xhtml', 'xxhtml', 'shtml']:
			return True
		else:
			return False
							
class WebPage(object):
	""" Page candidate insists of a HTML file as root and following referring non-HTML objects.
	"""
	def __init__(self):
		""" root_obj: a HTML object of :WebObject
		"""
		self.root = None
		self.ref = None
		self.urls = []
		self.objs = []
		self.junk_objs = []		# objects without referrer

		self.isvalid = False

	def own_this(self, obj, rule = 'strict'):
		""" Checking if the obj belongs to this page.
		obj: an object of :WebObject
		"""
		if rule == 'strict':
			for url in self.urls:
				if obj.referrer and utilities.remove_url_prefix(obj.referrer) == utilities.remove_url_prefix(url):
					return True
		elif rule == 'loose':
			pure_url = re.compile(r'^(\w+://)?([^#\?]+)#?\??')
			if obj.referrer:
				match_ref = pure_url.match(obj.referrer)
				if match_ref:
					for url in self.urls:
						if url:
							match_url = pure_url.match(url)
							if match_url:
								if match_ref.group(2) == match_url.group(2):
									return True
		return False

	def add_obj(self, obj, root = False):
		""" Add new object to this page
		obj: an object of :WebObject
		"""
		if obj not in self.objs:
			if root:
				self.root = obj
			self.urls.append(obj.url)
			self.objs.append(obj)
			
	def total_seconds(self):
		all_objs = self.objs + self.junk_objs
		all_objs.sort(lambda x,y: cmp(x,y), lambda x: x.start_time, False)
		obj0 = all_objs[0]
		start_time = obj0.start_time
		end_time = start_time + obj0.total_time
		for obj in all_objs[1:]:
			obj_start = obj.start_time
			obj_end = obj_start + obj.total_time
			if obj_end >= end_time:
				end_time = obj_end
		ret = (end_time - start_time).total_seconds()
		return ret
		
class PageFeature(object):
	""" Extracting features of web page.
	"""
	def __init__(self, pc):
		""" pc: object of :WebPage
		"""
		self.owner = pc
		self.f_dict = {}
		self.__page_gaps = [float(line) for line in open('conf/sgap.txt', 'rb')]
		self.__server_info()
		self.__object_info()
		self.__ref_info()

	def assemble_instance(self, label):
		""" Assembling instances for learning and testing which would be used by LIBSVM.
		One instance looks like:
			<lable> <index1>:<value1> <index2>:<value2> ...
		label: the label of this instance which can be any real number
		"""
		global feature_name_file

		all_lines = open(feature_name_file, 'rb').readlines()
		attributes = []
		for i in all_lines:
			line_strip = i.strip(' \n\t\r')
			if line_strip != '' and line_strip[0] != '#':
				attributes.append(line_strip)
		instance = str(label)
		for att in attributes:
			att_v = self.f_dict[att]
			instance += ' %d:%f' % (attributes.index(att)+1, att_v)
		instance += '\n'
		return instance
		
	def __ref_info(self):
		parent = self.owner.ref
		child = self.owner.root
		time_gap = random.sample(self.__page_gaps, 1)[0]	# seconds
		if None not in (parent, child):
			parent_time = parent.start_time
			child_time = child.start_time
			time_gap = (child_time - parent_time).total_seconds()
		self.f_dict['tm_of_ref_frt'] = time_gap
		self.f_dict['tm_of_ref_max'] = 0  	# tmp
		self.f_dict['tm_of_ref_min'] = 0  	# tmp
		self.f_dict['tm_of_ref_med'] = 0  	# tmp
		self.f_dict['tm_of_ref_avg'] = 0  	# tmp
		self.f_dict['tm_of_ref_var'] = 0  	# tmp


		referrer_type_is_html = 0
		referrer_type_is_image = 0
		referrer_type_is_css = 0
		referrer_type_is_flash = 0
		referrer_type_is_javascript = 0
		referrer_type_is_unidentified = 0
		referrer_type_is_none = 0
		if parent is not None:
			subtype = self.__which_type(parent)
			if subtype == 'image':
				referrer_type_is_image = 1
			elif subtype == 'html':
				referrer_type_is_html = 1
			elif subtype == 'css':
				referrer_type_is_css = 1
			elif subtype == 'flash':
				referrer_type_is_flash = 1
			elif subtype == 'js':
				referrer_type_is_javascript = 1
			else:
				referrer_type_is_unidentified = 1
		else:
			# trick: define successive click ratio (SCR) as 
			# 1 / number of pages in a click stream
			# For train data was collected automatically
			# which had this ratio as 1, so we 
			# define this ratio manually as 1/3 to stay
			# the same as test data.
			if self.owner.isvalid:
				if random.randint(0, 2) == 0:
					referrer_type_is_none = 1
				else:
					referrer_type_is_html = 1
			else:
				referrer_type_is_none = 1
			# pass

		self.f_dict['typ_of_ref_htm'] = referrer_type_is_html
		self.f_dict['typ_of_ref_img'] = referrer_type_is_image
		self.f_dict['typ_of_ref_css'] = referrer_type_is_css
		self.f_dict['typ_of_ref_fsh'] = referrer_type_is_flash
		self.f_dict['typ_of_ref_jst'] = referrer_type_is_javascript
		self.f_dict['typ_of_ref_unk'] = referrer_type_is_unidentified
		self.f_dict['typ_of_ref_nan'] = referrer_type_is_none

	def __server_info(self):
		""" Extracting featrues about server
		"""
		def get_servername(data):
			"""
			"""
			server_re = re.compile(r'^(\w+://)?([^\\/]+)/?')
			match_server = server_re.match(data)
			if match_server:
				return match_server.group(2)
			else:
				return None
							
		def get_main_domain(servername):
			"""
			"""
			domain_re = re.compile(r'([\w-]+\.(?:net|org|hk|cn|com\.cn|com\.hk|com|net\.cn|org\.cn|biz|info|cc|tv|mobi|name|asia|tw|sh|ac|io|tm|travel|ws|us|sc|in|jp|it|la|in|cm|co|so|ru|[a-z]+))(:\d*)?$')
			match_domain = domain_re.search(servername)
			if match_domain:
				return match_domain.group(1)
			else:
				return None
			
		def is_origin(servername):
			"""
			"""
			root = self.owner.root
			if root and root.url:
				root_server = get_servername(root.url)
				if root_server and servername:
					server_domain = get_main_domain(servername)
					root_domain = get_main_domain(root_server)
					if server_domain and root_domain:
						if root_domain == server_domain:
							return True
					else:
						if root_server == servername:
							return True
						else:
							#print 'Error to match domains: %s, %s' % (root_server, servername)
							pass
				else:
					#print 'Error to match servername: %s' % root.url
					pass
			return False
			
		origin_servers = set()
		nonorigin_servers = set()
		for obj in self.owner.objs:
			obj_server = get_servername(obj.url)
			if obj_server is not None:
				isori = is_origin(obj_server)
				if isori:
					origin_servers.add(obj_server)
				else:
					nonorigin_servers.add(obj_server)
			
		self.f_dict['num_of_svrs'] = len(origin_servers) + len(nonorigin_servers)
		self.f_dict['num_of_orisvrs'] = len(origin_servers)
		self.f_dict['rat_of_nonori_svrs'] = float(len(nonorigin_servers)) / (len(origin_servers) + len(nonorigin_servers))

	def __which_type(self, obj):
		subtype_re = {
			r'.*(jpeg|jpg|gif|png|bmp|ppm|pgm|pbm|pnm|tiff|exif|cgm|svg).*': 'image',
			r'.*(flash|flv).*': 'flash',
			r'.*(css).*': 'css',
			r'.*(javascript|js).*': 'js',
			r'.*(html|htm).*': 'html',
		}
		if obj.type != None:
			for regex in subtype_re.keys():
				if re.match(re.compile(regex, re.I), obj.type):
					return subtype_re[regex]
				else:
					continue
		return 'others'
			
	def __object_info(self):
		""" Extracting features about every kind of objects
		"""
		all_objects = self.owner.objs

		type_obj_dict = {
		'others': [],
		'image': [],
		'flash': [],
		'css': [],
		'js': [],
		'html': []
		}

		# Classifying objects
		for obj in all_objects:
			subtype = self.__which_type(obj)
			type_obj_dict[subtype].append(obj)

		(number, total_size, max_size, min_size, median_size, average_size, var_size, \
				total_time, max_time, min_time, median_time, average_time, var_time) \
							= self.__pro_subtype_objects(all_objects)
		self.f_dict['dt_of_page'] = self.owner.total_seconds()
		self.f_dict['num_of_obj_ttl'] = number
		self.f_dict['dt_of_page_obj_avg'] = self.f_dict['dt_of_page']/self.f_dict['num_of_obj_ttl']
		self.f_dict['sz_of_all_obj_ttl'] = total_size
		self.f_dict['sz_of_all_obj_max'] = max_size
		self.f_dict['sz_of_all_obj_min'] = min_size
		self.f_dict['sz_of_all_obj_med'] = median_size
		self.f_dict['sz_of_all_obj_avg'] = average_size
		self.f_dict['sz_of_all_obj_var'] = var_size
		self.f_dict['dt_of_all_obj_ttl'] = total_time
		self.f_dict['dt_of_all_obj_max'] = max_time
		self.f_dict['dt_of_all_obj_min'] = min_time
		self.f_dict['dt_of_all_obj_med'] = median_time
		self.f_dict['dt_of_all_obj_avg'] = average_time
		self.f_dict['dt_of_all_obj_var'] = var_time
		
		cnt_of_all_objs = number
		size_of_all_objs = total_size

		(number, total_size, max_size, min_size, median_size, average_size, var_size, \
				total_time, max_time, min_time, median_time, average_time, var_time) \
								= self.__pro_subtype_objects(type_obj_dict['others'])
		self.f_dict['num_of_obj_unk'] = number
		self.f_dict['sz_of_unk_obj_ttl'] = total_size
		self.f_dict['sz_of_unk_obj_max'] = max_size
		self.f_dict['sz_of_unk_obj_min'] = min_size
		self.f_dict['sz_of_unk_obj_med'] = median_size
		self.f_dict['sz_of_unk_obj_avg'] = average_size
		self.f_dict['sz_of_unk_obj_var'] = var_size
		self.f_dict['dt_of_unk_obj_ttl'] = total_time
		self.f_dict['dt_of_unk_obj_max'] = max_time
		self.f_dict['dt_of_unk_obj_min'] = min_time
		self.f_dict['dt_of_unk_obj_med'] = median_time
		self.f_dict['dt_of_unk_obj_avg'] = average_time
		self.f_dict['dt_of_unk_obj_var'] = var_time
		self.f_dict['rat_num_of_unk'] = float(number)/cnt_of_all_objs
		self.f_dict['rat_size_of_unk'] = size_of_all_objs != 0 and float(total_size)/size_of_all_objs or 0

		(number, total_size, max_size, min_size, median_size, average_size, var_size, \
				total_time, max_time, min_time, median_time, average_time, var_time) \
								= self.__pro_subtype_objects(type_obj_dict['image'])
		self.f_dict['num_of_obj_img'] = number
		self.f_dict['sz_of_img_obj_ttl'] = total_size
		self.f_dict['sz_of_img_obj_max'] = max_size
		self.f_dict['sz_of_img_obj_min'] = min_size
		self.f_dict['sz_of_img_obj_med'] = median_size
		self.f_dict['sz_of_img_obj_avg'] = average_size
		self.f_dict['sz_of_img_obj_var'] = var_size
		self.f_dict['dt_of_img_obj_ttl'] = total_time
		self.f_dict['dt_of_img_obj_max'] = max_time
		self.f_dict['dt_of_img_obj_min'] = min_time
		self.f_dict['dt_of_img_obj_med'] = median_time
		self.f_dict['dt_of_img_obj_avg'] = average_time
		self.f_dict['dt_of_img_obj_var'] = var_time
		self.f_dict['rat_num_of_img'] = float(number)/cnt_of_all_objs
		self.f_dict['rat_size_of_img'] = size_of_all_objs != 0 and float(total_size)/size_of_all_objs or 0

		(number, total_size, max_size, min_size, median_size, average_size, var_size, \
				total_time, max_time, min_time, median_time, average_time, var_time) \
								= self.__pro_subtype_objects(type_obj_dict['flash'])
		self.f_dict['num_of_obj_fsh'] = number
		self.f_dict['sz_of_fsh_obj_ttl'] = total_size
		self.f_dict['sz_of_fsh_obj_max'] = max_size
		self.f_dict['sz_of_fsh_obj_min'] = min_size
		self.f_dict['sz_of_fsh_obj_med'] = median_size
		self.f_dict['sz_of_fsh_obj_avg'] = average_size
		self.f_dict['sz_of_fsh_obj_var'] = var_size
		self.f_dict['dt_of_fsh_obj_ttl'] = total_time
		self.f_dict['dt_of_fsh_obj_max'] = max_time
		self.f_dict['dt_of_fsh_obj_min'] = min_time
		self.f_dict['dt_of_fsh_obj_med'] = median_time
		self.f_dict['dt_of_fsh_obj_avg'] = average_time
		self.f_dict['dt_of_fsh_obj_var'] = var_time
		self.f_dict['rat_num_of_fsh'] = float(number)/cnt_of_all_objs
		self.f_dict['rat_size_of_fsh'] = size_of_all_objs != 0 and float(total_size)/size_of_all_objs or 0

		(number, total_size, max_size, min_size, median_size, average_size, var_size, \
				total_time, max_time, min_time, median_time, average_time, var_time) \
								= self.__pro_subtype_objects(type_obj_dict['css'])
		self.f_dict['num_of_obj_css'] = number
		self.f_dict['sz_of_css_obj_ttl'] = total_size
		self.f_dict['sz_of_css_obj_max'] = max_size
		self.f_dict['sz_of_css_obj_min'] = min_size
		self.f_dict['sz_of_css_obj_med'] = median_size
		self.f_dict['sz_of_css_obj_avg'] = average_size
		self.f_dict['sz_of_css_obj_var'] = var_size
		self.f_dict['dt_of_css_obj_ttl'] = total_time
		self.f_dict['dt_of_css_obj_max'] = max_time
		self.f_dict['dt_of_css_obj_min'] = min_time
		self.f_dict['dt_of_css_obj_med'] = median_time
		self.f_dict['dt_of_css_obj_avg'] = average_time
		self.f_dict['dt_of_css_obj_var'] = var_time
		self.f_dict['rat_num_of_css'] = float(number)/cnt_of_all_objs
		self.f_dict['rat_size_of_css'] = size_of_all_objs != 0 and float(total_size)/size_of_all_objs or 0

		(number, total_size, max_size, min_size, median_size, average_size, var_size,\
				total_time, max_time, min_time, median_time, average_time, var_time) \
								= self.__pro_subtype_objects(type_obj_dict['js'])
		self.f_dict['num_of_obj_jst'] = number
		self.f_dict['sz_of_jst_obj_ttl'] = total_size
		self.f_dict['sz_of_jst_obj_max'] = max_size
		self.f_dict['sz_of_jst_obj_min'] = min_size
		self.f_dict['sz_of_jst_obj_med'] = median_size
		self.f_dict['sz_of_jst_obj_avg'] = average_size
		self.f_dict['sz_of_jst_obj_var'] = var_size
		self.f_dict['dt_of_jst_obj_ttl'] = total_time
		self.f_dict['dt_of_jst_obj_max'] = max_time
		self.f_dict['dt_of_jst_obj_min'] = min_time
		self.f_dict['dt_of_jst_obj_med'] = median_time
		self.f_dict['dt_of_jst_obj_avg'] = average_time
		self.f_dict['dt_of_jst_obj_var'] = var_time
		self.f_dict['rat_num_of_jst'] = float(number)/cnt_of_all_objs
		self.f_dict['rat_size_of_jst'] = size_of_all_objs != 0 and float(total_size)/size_of_all_objs or 0
		
		(number, total_size, max_size, min_size, median_size, average_size, var_size,\
				total_time, max_time, min_time, median_time, average_time, var_time) \
								= self.__pro_subtype_objects(type_obj_dict['html'])
		self.f_dict['num_of_obj_htm'] = number
		self.f_dict['sz_of_htm_obj_ttl'] = total_size
		self.f_dict['sz_of_htm_obj_max'] = max_size
		self.f_dict['sz_of_htm_obj_min'] = min_size
		self.f_dict['sz_of_htm_obj_med'] = median_size
		self.f_dict['sz_of_htm_obj_avg'] = average_size
		self.f_dict['sz_of_htm_obj_var'] = var_size
		self.f_dict['dt_of_htm_obj_ttl'] = total_time
		self.f_dict['dt_of_htm_obj_max'] = max_time
		self.f_dict['dt_of_htm_obj_min'] = min_time
		self.f_dict['dt_of_htm_obj_med'] = median_time
		self.f_dict['dt_of_htm_obj_avg'] = average_time
		self.f_dict['dt_of_htm_obj_var'] = var_time
		self.f_dict['rat_num_of_htm'] = float(number)/cnt_of_all_objs
		self.f_dict['rat_size_of_htm'] = size_of_all_objs != 0 and float(total_size)/size_of_all_objs or 0


	def __pro_subtype_objects(self, obj_list):
		""" Processing objects of subtype.
		obj_list: the list of :WebObject instances
		Return: a tuple of (number_of_objects, median_size, average_size)
		"""
		def median(numbers):
			n = len(numbers)
			copy = numbers[:]
			copy.sort()
			if n & 1:
				return copy[n/2]
			else:
				return (copy[n/2-1] + copy[n/2]) / 2

		def average(numbers):
			return math.fsum(numbers)/len(numbers)

		def variance(numbers):
			ave = average(numbers)
			return len(numbers) > 1 and math.fsum([math.pow(i-ave, 2) for i in numbers]) / (len(numbers)-1) or 0.0

		count = len(obj_list)
		sizes = [i.size for i in obj_list if i.size >= 0]
		timings = [i.receiving_time for i in obj_list if i.receiving_time >= 0]
		if len(sizes) == 0:
			max_size = 0
			min_size = 0
			med_size = 0
			ave_size = 0
			var_size = 0
			total_size = 0
		else:
			max_size = max(sizes)
			min_size = min(sizes)
			med_size = median(sizes)
			ave_size = average(sizes)
			var_size = variance(sizes)
			total_size = sum(sizes)
		if len(timings) == 0:
			max_time = 0
			min_time = 0
			med_time = 0
			ave_time = 0
			var_time = 0
			total_time = 0
		else:
			max_time = max(timings)
			min_time = min(timings)
			med_time = median(timings)
			ave_time = average(timings)
			var_time = variance(timings)
			total_time = sum(timings)
		return (count, total_size, max_size, min_size, med_size, ave_size, var_size, \
						total_time,	max_time, min_time, med_time, ave_time, var_time)
		
def main():
	all_lines = open('./conf/fnames', 'rb').readlines()
	attributes = []
	for i in all_lines:
		line_strip = i.strip(' \n\t\r')
		if line_strip != '' and line_strip[0] != '#':
			attributes.append(line_strip)
	print attributes
	pass
	
if __name__ == '__main__':
	main()
