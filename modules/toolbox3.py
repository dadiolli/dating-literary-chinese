import logging, math, mysql.connector, regex as re
from collections import namedtuple
from mysql.connector import errorcode

# mysql configuration
# config = {
#   'user': 'root',
#   'password': 'Evolution2014',
#   'unix_socket': '/private/var/mysql/mysql.sock',
#   'database': 'hydcd2021',
# }

config = {
  'user': 'root',
  'password': 'Evolution2014',
  'unix_socket': '/private/var/mysql/mysql.sock',
  'database': 'hydcd2019',
}

# original version
markus = {
	'nianhao': "(大中祥符|天冊萬歲|天安禮定|天祐民安|天祐垂聖|天儀治平|太平真君|太平興國|太初元將|延嗣寧國|建中靖國|建武中元|萬歲通天|萬歲登封|福聖承道|中大同|中大通|年開元|人慶|上元|久視|大中|大同|大安|大成|大足|大和|大定|大明|大康|大統|大通|大象|大順|大業|大寧|大德|大慶|大曆|大寶|大觀|中平|中和|中統|中興|五鳳|仁壽|元平|元光|元初|元和|元始|元延|元封|元狩|元貞|元朔|元祐|元康|元符|元統|元象|元鼎|元嘉|元壽|元熙|元鳳|元德|元興|元徽|元豐|天元|天冊|天平|天正|天安|天成|天命|天和|天保|天紀|天祐|天啟|天康|天授|天盛|天眷|天統|天復|天順|天會|天祿|天聖|天嘉|天漢|天監|天福|天輔|天德|天慶|天賜|天曆|天興|天禧|天聰|天璽|天贊|天寶|天顯|太元|太平|太安|太初|太和|太始|太延|太昌|太建|太康|太清|太極|太寧|太熙|太興|文明|文德|弘光|弘治|弘道|本初|本始|正大|正元|正平|正光|正始|正統|正隆|正德|永元|永平|永光|永安|永初|永和|永始|永定|永昌|永明|永建|永貞|永泰|永康|永淳|永隆|永嘉|永壽|永寧|永漢|永熙|永樂|永曆|永興|永徽|甘露|先天|光大|光化|光宅|光和|光定|光啟|光熙|光緒|光熹|同光|同治|地節|如意|成化|收國|至大|至元|至正|至和|至治|至順|至道|至寧|至德|孝昌|孝建|赤烏|初元|初平|和平|始元|始光|延平|延光|延和|延昌|延祐|延康|延載|延熙|延熹|延興|征和|承平|承光|承安|承明|承聖|昇平|昇明|明昌|明道|武平|武成|武定|武泰|武德|河平|河清|治平|炎興|長安|長壽|長慶|長興|青龍|保大|保定|保寧|咸平|咸安|咸亨|咸和|咸康|咸淳|咸通|咸雍|咸寧|咸熙|咸豐|垂拱|宣光|宣和|宣政|宣統|宣德|建中|建元|建文|建平|建光|建安|建初|建和|建始|建明|建武|建炎|建昭|建國|建康|建隆|建義|建寧|建德|建興|建衡|後元|拱化|政和|昭寧|洪武|洪熙|皇始|皇建|皇泰|皇祐|皇健|皇統|皇慶|皇興|致和|貞元|貞明|貞祐|貞觀|重和|重熙|唐隆|泰和|泰始|泰定|泰昌|泰常|泰豫|神冊|神功|神瑞|神鳳|神龍|神龜|神爵|神麚|乾元|乾化|乾亨|乾定|乾明|乾封|乾祐|乾符|乾統|乾隆|乾道|乾寧|乾德|乾興|崇寧|崇禎|崇德|崇慶|康定|康熙|淳化|淳祐|淳熙|清泰|清寧|祥興|竟寧|章和|章武|紹定|紹武|紹泰|紹聖|紹熙|紹興|統和|普泰|普通|景元|景平|景初|景和|景定|景明|景炎|景泰|景祐|景雲|景福|景德|景龍|景耀|登國|開平|開成|開皇|開泰|開運|開慶|開興|開禧|開寶|開耀|陽朔|陽嘉|隆化|隆安|隆和|隆昌|隆武|隆慶|隆興|順治|黃初|黃武|黃龍|嗣聖|會同|會昌|祺祥|綏和|義寧|義熙|聖歷|萬曆|載初|道光|雍正|雍寧|雍熙|靖康|嘉平|嘉禾|嘉定|嘉泰|嘉祐|嘉靖|嘉熙|嘉慶|壽昌|壽隆|寧康|漢安|熙平|熙寧|禎明|端平|端拱|鳳凰|鳳曆|儀鳳|廣明|廣順|廣運|廣德|德昌|德祐|慶元|慶曆|調露|熹平|興元|興平|興光|興安|興和|興定|興寧|龍紀|龍朔|龍德|應天|應順|應曆|總章|鴻嘉|證聖|寶元|寶祐|寶義|寶鼎|寶慶|寶曆|寶應|奲都|顯道|顯德|顯慶|麟德)",
	'number': "[元正𨳝閏一二三四五六七八九十廿卅]{1,}",
	'period': "[年載月日初中末閏祐]",
	'season': "[春夏秋冬]{1,}",
	'tgdz': "(辛巳|壬午|癸未|甲申|乙酉|丙戌|丁亥|戊子|己丑|庚寅|辛卯|壬辰|癸巳|甲午|乙未|丙申|丁酉|戊戌|己亥|庚子|辛丑|壬寅|癸卯|甲辰|乙巳|丙午|丁未|戊申|己酉|庚戌|辛亥|壬子|癸丑|甲寅|乙卯|丙辰|丁巳|戊午|己未|庚申|辛酉|壬戌|癸亥|甲子|乙丑|丙寅|丁卯|戊辰|己巳|庚午|辛未|壬申|癸酉|甲戌|乙亥|丙子|丁丑|戊寅|己卯|庚辰)"
}

#
monomarkus = {
	#'nianhao': "(神瑞|元始|淳祐|天德|天盛|廣順|天成|景和|麟德|太延|光和|正德|建元|嘉平|洪武|中大通|建衡|元嘉|建安|崇寧|建明|太建|寶慶|明昌|元封|乾統|延光|黃龍|乾興|五鳳|天禧|昭寧|元初|建昭|永明|咸寧|調露|永定|中大同|景德|福聖承道|永熙|乾寧|永淳|陽嘉|唐隆|宣統|元象|洪熙|熙寧|至德|熙平|貞元|建義|義寧|景祐|元祐|永泰|嘉定|景明|延嗣寧國|義熙|崇慶|天順|征和|神鳳|延祐|天漢|永徽|久視|建興|陽朔|萬歲登封|興平|和平|天康|宣和|延興|永寧|太平真君|建寧|元鼎|元豐|孝建|泰定|孝昌|大慶|永嘉|拱化|大和|泰始|咸康|景福|太寧|本始|開寶|開運|元鳳|乾隆|昇明|年開元|皇建|建平|元狩|淳熙|黃武|乾道|咸亨|萬歲通天|始元|紹熙|禎明|紹泰|景平|元康|天冊萬歲|建光|延和|永興|皇健|大定|天冊|皇興|天璽|寶曆|咸和|元壽|延熙|廣運|建炎|乾祐|乾化|寶祐|永康|崇禎|鴻嘉|正始|皇慶|祺祥|開耀|乾亨|壽隆|隆昌|永平|德祐|地節|建初|章和|雍寧|天慶|神冊|宣光|上元|永壽|永始|元延|元平|黃初|本初|天儀治平|咸熙|天寶|保大|大同|竟寧|泰豫|大安|大寶|延載|元熙|皇祐|河平|正隆|昇平|太興|咸雍|大中祥符|太始|重和|太平|興寧|永和|寶應|太熙|太平興國|普泰|天興|太初元將|天安禮定|永建|泰昌|延平|初元|天祐垂聖|乾定|紹武|證聖|咸豐|太和|咸淳|太安|嘉泰|永漢|武泰|寶義|太初|開禧|後元|炎興|熹平|咸安|建康|漢安|元朔|永元|綏和|慶曆|永光|貞祐|咸平|隆安|延康|龍朔|靖康|元和|聖歷|建中靖國|元興|奲都|天元|太昌|普通|元光|保定|乾明|建武|康定|永初|光熹|永樂|青龍|嘉熙|承光|皇泰|登國|建和|康熙|天祐民安|永隆|大足|永曆|神麚|咸通|鳳凰|神爵|建武中元|大德|太元|延熹)",
	'nianhao': "(人慶|上元|久視|大中|大同|大安|大成|大足|大和|大定|大明|大康|大統|大通|大象|大順|大業|大寧|大德|大慶|大曆|大寶|大觀|中平|中和|中統|中興|五鳳|仁壽|元平|元光|元初|元和|元始|元延|元封|元狩|元貞|元朔|元祐|元康|元符|元統|元象|元鼎|元嘉|元壽|元熙|元鳳|元德|元興|元徽|元豐|天元|天冊|天平|天正|天安|天成|天命|天和|天保|天紀|天祐|天啟|天康|天授|天盛|天眷|天統|天復|天順|天會|天祿|天聖|天嘉|天漢|天監|天福|天輔|天德|天慶|天賜|天曆|天興|天禧|天聰|天璽|天贊|天寶|天顯|太元|太平|太安|太初|太和|太始|太延|太昌|太建|太康|太清|太極|太寧|太熙|太興|文明|文德|弘光|弘治|弘道|本初|本始|正大|正元|正平|正光|正始|正統|正隆|正德|永元|永平|永光|永安|永初|永和|永始|永定|永昌|永明|永建|永貞|永泰|永康|永淳|永隆|永嘉|永壽|永寧|永漢|永熙|永樂|永曆|永興|永徽|甘露|先天|光大|光化|光宅|光和|光定|光啟|光熙|光緒|光熹|同光|同治|地節|如意|成化|收國|至大|至元|至正|至和|至治|至順|至道|至寧|至德|孝昌|孝建|赤烏|初元|初平|和平|始元|始光|延平|延光|延和|延昌|延祐|延康|延載|延熙|延熹|延興|征和|承平|承光|承安|承明|承聖|昇平|昇明|明昌|明道|武平|武成|武定|武泰|武德|河平|河清|治平|炎興|長安|長壽|長慶|長興|青龍|保大|保定|保寧|咸平|咸安|咸亨|咸和|咸康|咸淳|咸通|咸雍|咸寧|咸熙|咸豐|垂拱|宣光|宣和|宣政|宣統|宣德|建中|建元|建文|建平|建光|建安|建初|建和|建始|建明|建武|建炎|建昭|建國|建康|建隆|建義|建寧|建德|建興|建衡|後元|拱化|政和|昭寧|洪武|洪熙|皇始|皇建|皇泰|皇祐|皇健|皇統|皇慶|皇興|致和|貞元|貞明|貞祐|貞觀|重和|重熙|唐隆|泰和|泰始|泰定|泰昌|泰常|泰豫|神冊|神功|神瑞|神鳳|神龍|神龜|神爵|神麚|乾元|乾化|乾亨|乾定|乾明|乾封|乾祐|乾符|乾統|乾隆|乾道|乾寧|乾德|乾興|崇寧|崇禎|崇德|崇慶|康定|康熙|淳化|淳祐|淳熙|清泰|清寧|祥興|竟寧|章和|章武|紹定|紹武|紹泰|紹聖|紹熙|紹興|統和|普泰|普通|景元|景平|景初|景和|景定|景明|景炎|景泰|景祐|景雲|景福|景德|景龍|景耀|登國|開平|開成|開皇|開泰|開運|開慶|開興|開禧|開寶|開耀|陽朔|陽嘉|隆化|隆安|隆和|隆昌|隆武|隆慶|隆興|順治|黃初|黃武|黃龍|嗣聖|會同|會昌|祺祥|綏和|義寧|義熙|聖歷|萬曆|載初|道光|雍正|雍寧|雍熙|靖康|嘉平|嘉禾|嘉定|嘉泰|嘉祐|嘉靖|嘉熙|嘉慶|壽昌|壽隆|寧康|漢安|熙平|熙寧|禎明|端平|端拱|鳳凰|鳳曆|儀鳳|廣明|廣順|廣運|廣德|德昌|德祐|慶元|慶曆|調露|熹平|興元|興平|興光|興安|興和|興定|興寧|龍紀|龍朔|龍德|應天|應順|應曆|總章|鴻嘉|證聖|寶元|寶祐|寶義|寶鼎|寶慶|寶曆|寶應|奲都|顯道|顯德|顯慶|麟德)",
	'number': "[元正𨳝閏一二三四五六七八九十廿卅]{1,}",
	'period': "[年載月日初中末閏祐]",
	'season': "[春夏秋冬]{1,}",
	'tgdz': "(辛巳|壬午|癸未|甲申|乙酉|丙戌|丁亥|戊子|己丑|庚寅|辛卯|壬辰|癸巳|甲午|乙未|丙申|丁酉|戊戌|己亥|庚子|辛丑|壬寅|癸卯|甲辰|乙巳|丙午|丁未|戊申|己酉|庚戌|辛亥|壬子|癸丑|甲寅|乙卯|丙辰|丁巳|戊午|己未|庚申|辛酉|壬戌|癸亥|甲子|乙丑|丙寅|丁卯|戊辰|己巳|庚午|辛未|壬申|癸酉|甲戌|乙亥|丙子|丁丑|戊寅|己卯|庚辰)"
}

def create_truncate_table(cursor, conn, statement, name):
	"Create a table if not exists, truncate it, if it does."
	try:
		logging.info("Creating table %s: " % name)
		cursor.execute(statement)
	except mysql.connector.Error as err:
		if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
			logging.info("❎  already exists, truncating the table.")
			cursor.execute("truncate table " + name) # clear if exists
		else:
			logging.warning(err.msg)
	else:
		logging.info("✅ .")	

def database_connect(conn=False, cursor=False):
	if (conn and cursor):
		print('🤖 Already connected.')
		return(conn,cursor)
	else:
		try:
			conn = mysql.connector.connect(**config)
		except:
			print('🤖 No connection to the database. Please check mySQL server.')
			exit()
		if conn.is_connected():
			if __name__ == '__main__':
				print('✅ Connected to the mySQL database.')
		cursor = conn.cursor()
		return(conn, cursor)	

def find_ngrams(input_list, n):
	"Will return a list of n-grams found in the input_list"
	# as seen on http://locallyoptimal.com/blog/2013/01/20/elegant-n-gram-generation-in-python/
	# written by Scott Triglia, retrieved 27.07.2016
	return zip(*[input_list[i:] for i in range(n)])

def mae(frame, known_column, projected_column, chronon_length, mode="chronon"):
	"Calculate mean average error for a dataframe"
	# Calculate "direct" distance from chronon medium, with minimum distance of 0
	if mode == "direct":
		return abs(frame[known_column]-(frame[projected_column]+chronon_length/2)).mean()
	if mode == "chronon":
	# Calculate avg distance from chronon start and end, with minimum distance of half of chronon length
		return ((abs(frame[known_column]-(frame[projected_column])) + abs(frame[known_column]-(frame[projected_column]+chronon_length))) / 2).mean()

def regex_builder(tagrex):
	# inspired by MARKUS regex.translate method in dist/automarkup.html
	tagrex_pattern = r"<([^>]{1,})>"
	tags = re.findall(tagrex_pattern, tagrex)
	# print(tagrex)
	# print(tags)
	if tags:
		for t in tags:
			tagrex = tagrex.replace("<" + t + ">", markus[t])
	return(tagrex)

def grams_regex_builder(tagrex):
	# inspired by MARKUS regex.translate method in dist/automarkup.html
	tagrex_pattern = r"<([^>]{1,})>"
	tags = re.findall(tagrex_pattern, tagrex)
	# print(tagrex)
	# print(tags)
	if tags:
		for t in tags:
			tagrex = tagrex.replace("<" + t + ">", monomarkus[t])
	return(tagrex)	

def simplifieddetector(input, diagnose=False):
	# 2017-02-28 removed simplified characters that were used as 異體字 before the reform, such as 况 for 況, 灾 for 災 source http://dict.revised.moe.edu.tw
	"Determines if there is a simplified character intercept a given unicode string"
	simplified = set("谈厍随锎馑鲓徕芗贞钣嘤骧悫弪戬临犷电场宽线盏镎㧑鼹鳓鹔麸话滟赞铣卢饦巩惫扬闹嗫绿辊阏颐缕应戗赅颛涞吣厢鲨薮谳讲纟爷锹钸砻鸿胀视赉飐绔跞靥荭晓诲轵铸须广铔缪殇渊频蚂缔㻘谞箧鲩鸪亵馈钹锸箪笼胁诇浈鸼飑绕䁖赋槛虚迟鹪荬潴号铹啸筼鱾态节袆刍厌璎堑馐骒褛伟黪锣劢颦纪术贳鲾顷裆汉牍双铎嫒鹕雏诜镣㱩酽廪闸饻驽导齿辉库尔沟伞删嚣颧鸨舆讱谴锺岿讴摄颍勋浊铏篑结渎学鹨诱践秽胫锝撄标琏骐馒鲔镮袜谟辞猡锥钤箦缩纨悬贵圹䍁识鹓鳔䝙连癣镥铤绨扫腭惬驼赵驻闺饽宫屿忾怂榇争压谊阎窑鲕鸮涟务钥唤毂纩缨馆悭鲪贴礼鸾苁䍀聂觇鳕诛㓥镤绩躏惭迳寻饼鹾搅辈册锏缓颒昙负窦鸩粪骜樱记谵状驵钺纾权摅迈银镏穑当飒鸦赟滞叠饧鹩荫蛮橱诰轳铕铺顽绾搀肃莅榉栈钋阌颓缒挚东疡级妩枭趱谰讵锶鲻区帼杂浆觉铋飓归荚违继孪轲毵镶饾怃阘眍鲐笕骔谛躜唡钠帧宪蚬戯贱玺聋畴裈诊鳐锢嫔䗖觞镡铠鹧饩飨闶兹郸类综驿秾辇谆缃鲑馓䢂骕笔涛匮钡唠贰邹纽砾担过郧鳑鹒潜诟铡镠卤忧屦饨瑶牺绽寿顾搁暂栉榈锋誊阍蜗抚丝澜疠鲚鳇缧鲦媪悮谱亲殴钶鸽潇览镋协鼍绒赛远团剥峦药惮赒说枨怄猎帐骓馕战脚涝谜唢鲧缦箩断悯飔贲钷纻㶽笾潆诉郏华鹐镢彦饪惯荮买铷叹绻籼签蚀氇辆阋锍钌缑庐颔丛贝霡尧蹰骝妪龟犸帻鲼宾汇觊镍铌灏绐赏荙赝诞雠鱼轱瑷矶顿蚁搂誉栊钍锌庑箓颕蘖䲝厣傥谇带枫讳氲褴喷阶犹债岽杀获铍镌减绑齐篓飕晖进赜槟弑鹦轰诳闷驾螀怅溆鬓鲒堕馔伛谝椟钢紧约箨鲜锷赈刹邺尽饷浇诈鹂鹑鳒硕铢遥凤绦乱彻雾鱽饿䦁栀辅颋铙钓缂阔谘会鲣鸤训躯贮邻强锾见苇摈经踌凑哓鸻峣鹤酦闩语饶叽㛿椁调验帏吓䴙辚挝芜绪颠弥纤锩钨踯脱莲鲸逻瘿喾检诂髌鹏郐呓赙捝齑绤剧镩铨韪蛴穷偻闾溅怆蒉馋窍阅业挜颡纥缤逦钩锨瘪谮鲹冻鸺棁跃仅㛠䙊郑诗赘钎荜绥铩镨豮顶击矿䦀辄镭缏鲎颤锓阕镴谙诅骢鸥讬嬷纺刽钾浃胆奋蛊鳎镓陕滚擞鹥烦㑩痨跸诬软谩壶养绺链殁溃谄骋馍鲏缎玑辙抛审纣傧匦瞩锪莱舰鸸钿毁荆髋鳏发剐这赚蓟绣祢烧韩陨镪衬轮艰蛳铿阖颌阓锕钔饮枞骠鸣粤厦鲝椭谯弹纸炼观浅蝉镕哔诖鹣峤痪赓诵䇲硷绸酾兽矾较戆碍递钕锔谚骡鲥讫袭谲撵纹炽瘾资蝈摊鹎哕镔馎峥牦鲽诫贼垒蕴婶绹闿仪谅馌厐辘挛宠缣颢钪贯舱鸹医鲺锿难诀棂跄响铗绎剑珐靓呕还荛臜闪险韨铪祷长图谀鲋骏琐邓厕䴖隶抟缢锦踬纷钻笺势䯅䩄坠鳋鹌祎郓钏滗赖拟罢镦俭绷姹顸铻韫谔辂鳀缍镬锑钐瞒猕渗瘘殚鲠骤储谫樯鸷㶶夹刿赁鳣䅉绌镑铐单诚鳠陧烨轭们辩恳饹壸贪㺍缌钑锐阒辗谖訚鲡鸢窥傩讯隽县倾赀觃摆绍哑镐峡鹢韧烩转误衮蕰㲿惨祸闻驺国谁龌颎众挟红钦贫侬莴鲶画赊评蝇鹍风敛荟屡饣绢铦麦葱蛲项辁鲁榅蒇颏鞑阐锒谢挞鸠骣钧厩谬袯鲷夺喽琼錾迁赂觅绋飏镒掸毙鲿荞鹠鸱铧迩蕲闲对驸饺闽袄芈鲌隐焕铯谗辖䘛缡纠稣赇垦动购议锽钼摇苈鹋鳌睑盐骥槚绠奥韦诮蛰艳筹铼灿谂袅龋鲍馏税皑渖纡缠颥辫贬莳鸶砺钽锼诃装鳍捣监睐呒蓝绡饤俫觯蛱顺铽凿辀栅榄缋鹜窎阑钒䴗萝鸡鲢锧厨伫谭颜纶顼衅规瓒赗诘鹡铑鳢啧轫絷绶驹闼酿冁垅阄骇㶉缊辕渔焖碛宝废挢枥涩谨伪刬键鲳鸴脶讽亿贾鳡铃蛏觑馇乔兖员坚寝统蓣换烫轪啮鹴诽橼炀娇妆鲈龊谓殒错钘窜鸟肠䜥数贩侪疮缵纴蔹撸参秆鳈恋苌虏诒饸镙铘埚筝鹟来俪獭独问饱声维偾湿鲉咙锘阚窝闫羟愠讧沩质个猬鞯碱娲纵缴掷烁荡剂鳉鹊苍蟏哙镘筜属诧桦凫狭埯饰驲绵罴恶歼锃瘅垄领鲖树䴓辔锛缟鲞抢鞒欧梦氩涨刭钮鸵䌷讼净镃际魇屉绊觐浓㻏呙赎鳞拢滪铓铮称鱿胶旸诼轿泾颇龉师嘘骛锚砜鲟缞萤侩娆钯纳尴䌶蔺玮掴叁剀酂鹈苋职译仓卖埙镚锻鳟骑俩赪偬瓯驰绳饲籴轾阃锅缉戋脍专䴕碜䯄挡抠讦邬启鸳鲴莶梼达畅铄终赕遗静盘锤捡桧详轩滨烬鹳匀钅锄妇稆缈锠输䴔额抡挠枣耢亩谪疯锉鲵损讻携举铅镄绉届浔鹞荠蓥滩轨热闯嫱读楼湾备骆龈鲊谕鲘阙钚庞䜣营温侨沪锯黉缳撺贿烂鹉鳊聍蛎诐缥筛铚绞俨卫泪灭镯驱赔龁厅馉蒋䞍骃谐锖写馅岛帜骟产账钫铰缲娴耸䌺辽烃织苏毕盗镖铥鳛总桨铫狯鳁黩壳婴恸泻锁鲗颈戏辒瘗疖玚缝黄枢挥护丧润讪霭鲰铈掺镁铀鹇轴浑濒痖络蓠荥诪时载销阂龇将颉斋焘刚缜报挤侧谦横眬环鲱鸲脸访栾铁镀浐蹒呖绝拥荤痫园鹲跻艺轼诿缇鲆妈骊䞌茏谑钖颞伧沦锫邮纲贻丽颙梾驷鳆诔块铖勚鹝飞轧桩镫骦韬饳绲婵恹阀锂鲇缆娈茎辑渐钗刘颟沧伦让疭献鸰撷莹捞梿镂糇骍濑乐浒衔哗叙绛桤拣车诩闭鹰霁龆骈馊蒌鲙吗䴘粜实舣肤谧侦瘫锭钬缱纰稳䌹贽设睁忆魉晋呗鹛嵝鳜漤条俦癫啭铬灯绰婳饵泼课骉殓谒疗埘龛粝愤涧檩垫瞆钭锬冯纱缰头䌸着鹆敌仑诓鳝㧟书矫铭啬凯绱饴旷恺泽阁猃庆颊脏渑辐锗则缛尝够骞挣货讨疬銮帱鲲䲞蔷莸铂细苎蹑运镗盖变竞柠荣滦诨闬狮鹱页轻黾䥿馁砀鲃龅亏膑骗尘缚锞沣欢侥两愦斩萨纯钳阴础鳃鹄痉词济懑晔奖烛罚㛟镞桠拧马绯铳韵跹轺揽颀缅㔉针栋脑蜕岘龚鲛队㖞谣订伥枪闳鸯费耻䌽奁屃组镉赍慑鳘询佥滤执鹯酱珲围泸恻虿颁缄钉锈阊辏谎脐斓砖岙军劝龄椠涣伤妫窭铜讷贸为䌼绅铉镈觋藓硖鳙嵘凛鹚狝滥㱮兰嗳囵请码馀崃骂帅径颖钞责严悦赆弯粮锳劲阵垴趸掼硁鹅诙痈诌晕飖绚坟铞桡槠赣荧饫驭钛狲偿汹试腻开阈锊栌缯颗龙鲮钟计谤挦阆鲯缮玱边贺怼铒练奂巅陈镊觍飗鹘嵚哟坞毡汤惧荦莼雳闵恼蝾骀馂历㖊赃谏辎茑砗缙创炜败沤耧钝㨫阳锵钴样讶亸舻驴鹃峄张䙓懒硗绘酝杩饭狰镵铴诶轹腽骁龃鲅崄残庙缘玛炝疟沥贤箫掳帮励钵锴显鳅诋䓕姗给癞俣桢杨郦饬巯狱铵啴门轸腼虾简弃颂阗阉钊䯃镅鹀骖岚农锟讠伣谥涤芦螨镳纮爱现锡陉铊觌浏从竖鹙翘鳚镟诠裢鸧拦绮珰间泺恽颃娄锆辍渌咛涡谠讥暧铝鲫鸬疱贶昼黡罂镆乌绗铛筚噜裣莺该荪鹬纼闱鉴柽腾鲀龂骄阇谋茕题贡缭纬锱钰垲论煴殡陇潍觎鹗飘呛坝赡赑档胨绬驯镱垩鳄跶诺岁馃骅炉趋栎撑鲂茔簖墙驳馄没贠欤枧萦纭缬钱锰决谶鼋糁秃幂髅诏飙骎坜钙赠惩扪续铱镰蝼揿证娅钆选冈犊渍辌脓缗岖唛骚谡涠认䜧鸭皲昽肾籁祃绂铆测罗鳖硙镛珑滢橥诤蓦聩鹭壮闰关牵轷泶虽羁窃崂禅钇圆厉谌攒岗编财纫垱劳锲铟讹肿䌾诡铇蹿联鳗呜习赢胧绫邝镲泷轶诹缁预垆栏骘阛唝钜萧鸫崭鲬鲤怿绀㟆狈释浍诎饥孙镝哜滠裤荩拨鹫篮哒揾缀颅处瘆辋逊脔骙砚咝锜鲄传讣氢椤鲭皱蔼绁层陆餍赌觏点驶鹖桥哝镜满诣裥镧旧择荨聪积驮兴跷币龀笃岂禄锇谍䞐饯颚办侠缫嘱钲贷许鹁鳂镇潋虑懔绖坛飚狞乡补赐扩胪祯铲灵橹诸")
	inputcharacters = set(input)
	intersect = simplified & inputcharacters
	if len(intersect) > 0:
		if diagnose:
			print("🤖 There\'s simplified characters in the text, such as: " + ",".join(intersect) + ".")
		else:
			print("🤖 There\'s simplified characters in the text.", end="\r")
		return(True)
	else: 
		print("✅ Nothing to be afraid of: the text passed a check for simplified characters.")
		return(False)

def select_builder(words, settings, textname=False, type=None):
	sql = "SELECT w.id, cleanword, " if settings['Punctuation'] else "SELECT w.id, nakedword, "
	if settings['UseDFZTraining']:
		sql += "clearbook, startyear, endyear, usecount, estimate, dynasty " # ⚠️ might want to use startyear to startyear instead
	else:
		sql += "clearbook, startyear, endyear, usecount, estimate, dynasty "
	sql += "FROM the_words w left join the_books b ON "
	if settings['UseDFZTraining']:
		sql+= "coalesce(w.earliest_evidence_dfz_id,coalesce(w.earliest_evidence_book_id, w.book_id)) = b.id"
	elif settings['UseNonHYDCDEvidence']:
		sql += "coalesce(w.earliest_evidence_book_id, w.book_id) = b.id"	
	else:
		sql += "w.book_id = b.id"
	sql += " WHERE " 
	if words:
		sql += "cleanword in ('" + "', '".join(words) + "') and " 
	sql += "book is not null AND startyear is not null "
	if textname:
		sql += "and b.clearbook != '%s' " % (textname) if settings['ExcludeSelf'] else ""
	sql += "and length(cleanword) <= 3 * %s " % (settings['MaxGram']) if settings['Punctuation'] else "and length(nakedword) <= 3 * %s " % (settings['MaxGram'])
	# sql += "and b.clearbook != '清史稿' " # really dirty fix!!
	sql += "ORDER BY ((startyear+endyear) / 2) desc"
	return(sql)

def select_builder_cbdb(names, settings, ner="names"):
	dfz = settings['UseDFZTraining']
	if ner == "names":
		sql = "SELECT c_personid, c_name_chn, "
		if dfz:
			sql += "coalesce(earliest_evidence_firstyear, if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`)) as startyear, "
			sql += "coalesce(earliest_evidence_firstyear, if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`)) as endyear "
		else:
			sql += "if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`) as startyear, "
			sql += "if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`) as endyear "
		
		sql += "FROM biog_main "
		sql += "WHERE c_name_chn in ('" + "', '".join(names) + "') and occurs = 1 " 
		# sql += "and length(c_name_chn) >= 6 " # use only names with two or more chars
		sql += "and length(c_name_chn) >= 9 " # use only names with THREE or more chars, because of ambiguity risk!
		sql += "HAVING startyear != 0 and endyear != 0 and endyear >= startyear "			 
		sql += "ORDER BY ((startyear+endyear) / 2) desc"
	
	elif ner == "places":
		if dfz:
			sql = "SELECT c_addr_id, c_name_chn, coalesce(earliest_evidence_firstyear, c_firstyear), coalesce(earliest_evidence_firstyear, c_firstyear) "
		else: 
			sql = "SELECT c_addr_id, c_name_chn, c_firstyear, c_firstyear " # use only firstyear because of long temporal range of place names!
		sql += "FROM addresses "
		sql += "WHERE c_name_chn in ('" + "', '".join(names) + "') and occurs = 1 " 
		sql += "and length(c_name_chn) >= 6 " # use only names with two or more chars
		sql += "and ifnull(c_firstyear,0) > 0 and ifnull(c_lastyear,0) > 0 "		 
		sql += "ORDER BY c_firstyear desc"
	
	else:
		print("🤖 Unsupported call to select_builder.")
		return(False)
	return(sql)	

def term_frequency(tokens, totaltokens, maxtokens, vocsize):
	"Calculate term term frequency relative to tokens in given text."
	return tokens / totaltokens
	# return tokens / maxtokens
	# return tokens / (totaltokens + vocsize)

def unbreak(string):
	"Removes all kinds of breaks and regular space from a string in an old school way"
	string = string.replace('\n', '').replace('\t','').replace('\f','').replace('\r','').replace('\v','').replace(' ','')
	return string
