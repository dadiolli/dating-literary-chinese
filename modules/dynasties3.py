import math, pandas as pd, regex as re
from collections import namedtuple

dynastylist = ['太平天囯', '南朝陈', '南朝梁', '南朝齐', '南朝宋', '三国吴', '三国蜀', '三国魏', '战国燕', '战国楚', '民国', '前蜀', '五代', '北周', '北齐', '南齐', '北涼', '北魏', '前秦', '东汉','汉代','战国', '清', '明', '元', '金', '宋', '辽', '唐', '隋', '晋', '汉', '秦', '商']
dynastytuples = [('太平天囯', 1851, 1864), ('南朝陈', 557, 589), ('南朝梁', 502, 587), ('南朝齐', 479, 502), ('南朝宋', 420, 479), ('三国吴', 222, 280), ('三国蜀', 221, 263), ('三国魏', 220, 265), ('战国燕', -1030, -223), ('战国楚', -1030, -223), ('民国', 1912, 1998), ('前蜀', 903, 925), ('五代', 907, 960), ('北周', 557, 581), ('北齐', 550, 578), ('南齐', 479, 502), ('北涼', 401, 439), ('北魏', 386, 534), ('前秦', 350, 394), ('东汉', 25, 220), ('汉代', -206, 220), ('战国', -1030, -223), ('清', 1644, 1911), ('明', 1368, 1644), ('元', 1234, 1367), ('金', 1115, 1234), ('宋', 960, 1279), ('辽', 947, 1115), ('唐', 618, 907), ('隋', 581, 618), ('晋', 265, 420), ('汉', -206, 220), ('秦', -221, -206), ('商',-1600,-1046)]

dynastylist_fanti = ['太平天國', '南朝陳', '南朝梁', '南朝齊', '南朝宋', '三國呉', '三國蜀', '三國魏', '戰國燕', '戰國楚', '民國', '前蜀', '五代', '北周', '北齊', '南齊', '北涼', '北魏', '前秦', '東漢','漢代','戰國', '清', '明', '元', '金', '宋', '遼', '唐', '隋', '晉', '漢', '秦', '商']
dynastytuples_fanti = [('太平天國', 1851, 1864), ('南朝陳', 557, 589), ('南朝梁', 502, 587), ('南朝齊', 479, 502), ('南朝宋', 420, 479), ('三國呉', 222, 280), ('三國蜀', 221, 263), ('三國魏', 220, 265), ('戰國燕', -1030, -223), ('戰國楚', -1030, -223), ('民國', 1912, 1998), ('前蜀', 903, 925), ('五代', 907, 960), ('北周', 557, 581), ('北齊', 550, 578), ('南齊', 479, 502), ('北涼', 401, 439), ('北魏', 386, 534), ('前秦', 350, 394), ('東漢', 25, 220), ('漢代', -206, 220), ('戰國', -1030, -223), ('清', 1644, 1911), ('明', 1368, 1644), ('元', 1234, 1367), ('金', 1115, 1234), ('宋', 960, 1279), ('遼', 947, 1115), ('唐', 618, 907), ('隋', 581, 618), ('晉', 265, 420), ('漢', -206, 220), ('秦', -221, -206), ('商',-1600,-1046)]

hydcd_dynasties = [('太平天囯', 1851, 1864), ('南朝陈', 557, 589), ('南朝梁', 502, 587), ('南朝齐', 479, 502), ('南朝宋', 420, 479), ('三国吴', 222, 280), ('三国蜀', 221, 263), ('三国魏', 220, 265), ('战国燕', -1030, -223), ('战国楚', -1030, -223), ('民国', 1912, 1998), ('前蜀', 903, 925), ('五代', 907, 960), ('北周', 557, 581), ('北齐', 550, 578), ('南齐', 479, 502), ('北涼', 401, 439), ('北魏', 386, 534), ('前秦', 350, 394), ('东汉', 25, 220), ('汉代', -206, 220), ('战国', -1030, -223), ('清', 1644, 1911), ('明', 1368, 1644), ('元', 1234, 1367), ('金', 1115, 1234), ('宋', 960, 1279), ('辽', 947, 1115), ('唐', 618, 907), ('隋', 581, 618), ('晋', 265, 420), ('汉', -206, 220), ('秦', -221, -206)]
dynastydict = {dyn:(start, end) for dyn, start, end in dynastytuples}

dynasties = "("+ "|".join(dynastylist) + ")"
startswithdynasties = "(^"+ "|^".join(dyn[0] for dyn in hydcd_dynasties) + ")"
dynastyregex = re.compile(r'' + dynasties, re.UNICODE)
startswithdynastyregex = re.compile(r'' + startswithdynasties, re.UNICODE)

# print('We have ' + str(len(dynastylist)) + ' dynasties used in the 漢語大詞典 citations: ' + ','.join(dynastylist) + '.')

historystart, historyend = min(hydcd_dynasties, key=lambda x: x[1])[1], max(hydcd_dynasties, key=lambda x: x[2])[2]
# print('We have %s dynasties (%s–%s) used in the 漢語大詞典 citations.' % (len(hydcd_dynasties), historystart, historyend))

def century_dict(start, end):
	"Returns a dictionary with all centuries in the given timespan"
	centurydict = dict()
	for century in range(int((math.floor((start/100.0))) * 100),int((math.ceil((end/100.0))) * 100),100):
		centurydict[century] = 0.0
	return centurydict

def chronon_dict(start, end, step, span):
	"Returns a dictionary with all chronons in the given timespan"
	chronon_dict = {}
	for chronon in range(int((math.floor((start/100.0))) * span),int((math.ceil((end/100.0))) * span)):
		chronon_dict[chronon] = ''
	return sorted(chronon_dict)	

def get_chronon_for_year(year, chrononlength):
	try: 
		year = int(year)
	except:
		print("%s can't be converted to integer." % (year))
	return(round(math.floor(year/chrononlength),0) * chrononlength)

def century_profile_df(start=historystart, end=historyend, maxgrams=17):
	"Returns a pandas.DataFrame with century rows, for text lexeme timeline."
	allcenturies = century_dict(start, end)
	profile = pd.DataFrame.from_dict(allcenturies, orient='index', columns=['count']).rename(columns={0:'century'})
	profile['century'] = profile.index
	profile['typelist'] = [[] for _ in range(len(profile))]
	profile['centurylabel'] = profile.apply(lambda row: str(int(row.century)) + "–" + str(int(row.century) + 100), axis = 1)
	profile['dynasty'], profile['dynstart'], profile['dynend'] = zip(*profile['century'].map(dynasty_handler))
	if maxgrams:
		for wordlength in range(1,maxgrams+1):
			profile['X' + str(wordlength)] = 0.0
	return profile

def dynasty_handler(handle):
	"Returns a tuple of dynasty, start, end if given year or dynasty"
	"Returns a tuple of the oldest dynasty when given a list of dynasties"
	cdyn = namedtuple('Dynasty', 'name startyear endyear')
	# dynasties = dynastylist
	if isinstance(handle, int):
		foundyn = [(x, y, z) for x, y, z in dynastytuples if y <= handle and z >= handle]
		if foundyn:
			return cdyn(*foundyn[0])
		elif handle > 1998:
			return cdyn('民国', 1912, handle)
		elif handle < -1030:
			return cdyn('商', handle, -1030)
		else:
			print("\n❎ No dynasty found for year: " + str(handle))
			return(None)
	if handle in dynastylist:
		foundyn = [(x, y, z) for x, y, z in dynastytuples if x == handle]
		if foundyn: return cdyn(*foundyn[0])
		else: 
			print("\n❎ No year found for dynasty: " + handle)
			return(None)
	if isinstance(handle, list):
		foundyns = []
		for d in handle:
			foundyns += [(x, y, z) for x, y, z in dynastytuples if x == d]
		if len(foundyns) >= 1: 
			foundyn = min(foundyns,key=lambda item:item[2])
			return cdyn(*foundyn)
		else: 
			print("\n❎ Don't know how to lookup %s as a dynasty." % (handle))
			return(None)
	else: 
		return(None)

def dynasty_handler_fanti(handle):
	"Returns a tuple of dynasty, start, end if given year or dynasty"
	"Returns a tuple of the oldest dynasty when given a list of dynasties"
	cdyn = namedtuple('Dynasty', 'name startyear endyear')
	# dynasties = dynastylist
	if isinstance(handle, int):
		foundyn = [(x, y, z) for x, y, z in dynastytuples_fanti if y <= handle and z >= handle]
		if foundyn:
			return cdyn(*foundyn[0])
		elif handle > 1998:
			return cdyn('民國', 1912, handle)
		elif handle < -1030:
			return cdyn('商', handle, -1030)
		else:
			print("\n❎ No dynasty found for year: " + str(handle))
			return(None)
	if handle in dynastylist_fanti:
		foundyn = [(x, y, z) for x, y, z in dynastytuples_fanti if x == handle]
		if foundyn: return cdyn(*foundyn[0])
		else: 
			print("\n❎ No year found for dynasty: " + handle)
			return(None)
	if isinstance(handle, list):
		foundyns = []
		for d in handle:
			foundyns += [(x, y, z) for x, y, z in dynastytuples_fanti if x == d]
		if len(foundyns) >= 1: 
			foundyn = min(foundyns,key=lambda item:item[2])
			return cdyn(*foundyn)
		else: 
			print("\n❎ Don't know how to lookup %s as a dynasty." % (handle))
			return(None)
	else: 
		return(None)		