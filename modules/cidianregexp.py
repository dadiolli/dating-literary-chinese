# -*- coding: utf-8 -*-
import regex as re, sys
from zhon import pinyin, zhuyin

authornametaboos = re.compile('(说出于|所传之|指解释|纂辑的|自称有|所著的|所著之|所撰的|本为|例见|又因|名出|原谓|特指|我国|於是|说明|事本|事详|因此|所谓|著有|根据|相传|是为|参阅|典出|均为|原为|精研|詔號|语出|所著|所作|词人|释文|传授|初传|时著|变文|刻本|南戏|昆剧|南曲|杂剧|著名|事见|评论|隐引|编辑|先有|以爲|以为|语本|以$|见$|对$|^如|^见|^据)', re.UNICODE)
authornameguarantors = re.compile('(自称有|所著的|所著之|所撰的|所作|词人)')
citepatternyear = re.compile('(?:(?:释文引|注)[^)(*.“’””’。，；？！：、》>…】（）［］]{0,9})?(?:《[^》]+》)(?:\d{4}|注|词|诗|曲|套曲)?(?![^“]*”)', re.UNICODE)
pinyinpattern = re.compile('([ɑa\u0101\u00E0\u00E1\u01CEe\u0113\u00E9\u011B\u00E8i\u012B\u00ED\u01D0\u00ECo\u014D\u00F3\u01D2\u00F2uǖ\u016B\u00FA\u01D4\u00F9v\u00FC\u01D6\u01D8\u01DA\u01DCbcdfgɡkhjlmm̄m̌nn̄ńňpqrstwxyz]+)', re.UNICODE)
# derived from https://github.com/tsroten/zhon/blob/develop/zhon/pinyin.py, 17.05.2017, zhon by Thomas Roten
pronunciationpattern = re.compile('(［.+］)', re.UNICODE)
rhymepattern = re.compile('(［《.+》.+］)', re.UNICODE)
splitentrypattern = re.compile('((?<!([0-9\.]))\d{1,2}\.)', re.UNICODE) # use parentheses to catch the pattern as well
starentrypattern = re.compile('(\*\p{IsHan})', re.UNICODE)
# subentrypattern = re.compile('(【\p{IsHan}+ ?\d? ?\p{IsHan}+?】|\p{IsHan} [0-9]［.+］)', re.UNICODE) # also character subentries
subentrypattern = re.compile('(【[^】]+】|\p{IsHan} [0-9]［.+］)', re.UNICODE) # also character subentries
wordentrypattern = re.compile('(【\p{IsHan}+? ?\d? ?\p{IsHan}+?】)', re.UNICODE) # word entries
zhuyinpattern = re.compile('([ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄚㄛㄝㄜㄞㄟㄠㄡㄢㄣㄤㄥㄦㄧㄨㄩㄭ\u02C7\u02CA\u02CB\u02D9]+)', re.UNICODE)
# from zhon by Thomas Roten, https://github.com/tsroten/zhon/blob/develop/zhon/zhuyin.py, 17.05.2017

# original from CBDB, but simplified
nondynasty_surnamestarters_cbdb = u'土麋独麒麟麦歹淑歪圭武麹麻正劭努棸二于云亐亓势井五聿亚励森劳聊亢职交亦聂归京亮聚功力人联棍踏淡蕴柏糜柔某染糊柘查柯柴柰柳査妙焕妖如西焦麴妥路歧疋步疏闭闫闪门闵遽闰闾闽闻崧汎布求希蓉师帖汙江汜汝帛蓝汪池席汤汲酆遐道有月粟粘望朝期朔木末粲本朮精朱朵朴朶回四鹃囘囗囊撼图国固撅囯撒撖鹿团因探砥推偏砚饶掁掌蹇髙高涉涂逢巙州蔑逮逯巫逐巨差蔡通巢速适退逄逊蔼蔺巴燕奚奕奔契奎奉奈要覃燉覇好奴女奭奥燮奢仆仇剳桑什仁从格栾根介仉他校仓剧栢仝付仙剑令栖树代肇仪肃仵仲仳仰肖任栋骨骚骞骆骈李杏罗权罕杞束杜杭杨来杠松杲杰瑭訾瑺関瑞言閰瑚揭提揑插揆刘淞蕙淮淩淦畱采淸添野重释淳颉啜鸣操擖鸳能胡胤胥别利刑桓初刚创胜胆刀刁桂桃雪雷挚雅雈雍按雒驴驾马留碧熙大太夫天角熊失慈觉夺夸夹观夏复外夔多觧夙解夜琮镏詹琦镇镜琴琵琱琏理长琔琐出脱凯凡脩凤脑䵣凎凌凃净准缑悟编缃悳缴缪悦搠噶秉秋锁瓦瓮锦瓜锡锳换隆随隐捉洒洗嵇薄跃洁薛洋嵩津洪愼蘧壮士壶蘸壅灵灭火摩龄龙龚摄嘉冻冼冰展腾况冶冷冯冠腯槠军冒冉腆册槊冀腊策答翟翔惟翁翼翰惠翠墨墻虎虑虔增墙虞璥带璩璜帅郞崑浒崔浑崇济海藩郗酒浦酋浣浩羡怜怀羽羊美性怡怯斯齐断斡施方毛新斌文斛斗遇斑斐遆院陵丧陶蓬际陇陆陈陜笃笪第轩车符载常舒鄷源舟鄥鄢舍鄂溥烈塞塔烟鲍兼典养兴具兰关六公全八兪兜党光先克充兆允兀植札粱荣椿辛辜较㽜辅辉篯边辽达辨恒恺繁恽恩息恭蓨㬊督睢睦銭寇密寅寄富寒寗阿阳察阴寡阎寥寨阇阚阙阜寻寸寿阔儒楚楮楼儿岐岑鹤滑滕岛岁岂色艳岱岳艾满良喩鼐日旦无喻旺旻鼎时旷旌喀喃善喇喜致自臧臣宁它韫韩宇守安完宓宗官韶韵宛宜宝实宠宣宦宫宰宴家容宽宾战算运连迟远进过简迎媚迈迷迴述迺迸禇迦管迮箫迭蛮炳堵堂堃眭眞真眉行檀僖桥僧玥䣊魁衞縢憘魏攴改攸鳌支啇商攀鳯矾石矫矢娑皇裘鞠孔子孝孟讚孙存孛计孤季讬讷许论渝芙屈节居芈花游芳山温屯芭屠芮渠忻忽忠忒志忙蜀心必敷鲜唵敦散唤鲁敬敖教唆敏效谟谒穆谈谌阮穰谷空蔚谨谯谭谬谢谦绩绪续隗绥巩继绰绳甯绵维懿绍经赵练鬫络润德左呙徐徒猎得征猛待律洛涴傅伴傎伸伽似传伦伤伯会伟伊伏伍尝尚苟尘尔苑苗苕小苏苌尉湼封苻尼尹阖英湏苴湍苪苫湖玛湛尤生尢若纯纪约纥红线纽纶奇式哲暴哥暨暮哩鱼暗哇哀哈识评莘嬀革诚靑覩青靖静瞻诺瞿诸豁税豆程少稽豫象口叠句古只可召史叱台叶茆茅司范茂澹参澄茹友茶双受叔叚澜班彰今珠彻彦彭彬彩彪珍当珊珅彜珂融素索紫佳佴佶樊栗假使何横佘余佛健佟佀但佈偰偶站储立貊竹竺端章童慧祺颇题颙颛颜额祥颖祐祖祕慎神祝剌祃祁慕祈蒒鎻露霸霭震霅百白霍登旭苍倚侠侣候侬侯倕倒倭倪倩依橾氏侍荘厥荚濮草荆去荀厉厍厐药荫原曹曼曾曲曳咸曷咬和咎尧湘苦铿衍银衆铭铣瘦衡衣补铎铁衷窝俞突窦强玻弱弭张环弥弘蟒弓纳弋率玄异王开玉綦俺俾俱埜俨修信殷段殳保基培俊俎俆礼社护抹顔把抄顽顿顾项须顺抑投命呼呵昭周是春呢昝员星昔易昌昂沃沂沅沈沐沙沧河折韦治油益盍钰钱袁钩盛钭钮钦盖袭钝钞钟相盻盱直漫卦占卢卬卯卫却莲危印获卲卿莽定升十千莆音华漆单南卑卓卜卞博廿建廷延特牧萨廪萧营牟廖廕牛廒牙廉牀吾吴靳启君吕向后同合吉晃籍晁晆晏晓普景智宿米贡贯首质贵贲贾畹贻贺费畅呈畏负贝拨称秾移承拾拱积拉科秘拙招拜秀秃种拓拔拕拖庾庸爱爼康葯度董爨爪爕庞葛庚应底庐库庄瑛庆葆郯郭泉泊郦郤法都泠波郏郎郁郇郅郄泰嬴郝郜郑泼托比毕丽为丹毓临毘丰中毌母严毋东丛业丙丘世丕且丑不垣上三万七丁一潮潭匣匡菩区箪匹菅馨菊包潜潘化匕禹禾戢房禢戴戎戈福戚禀成禄禅皋裔裕娟的皂皁娄娃威娉皮裴娥赤赡赫田由甲申男甄赏赋赖赒赓甘赛澧耨勾耿梦耶勉勇老耀勃耆者梁梅勘勗耐勒年蒿狼蒲蒯蒨幸氾蒙狗永蒋狄林果枚枣簿坑黄买黎坚黑黔书默习坊九乞也乘乙款乔乐乌坤坦义及次久欣欢欧乃痲越超莫扰扶香扣执扩扬打硕所扈扎才邪邬邢那邦邸邹邺民邾邰邱邵邉邘水平干邝邑氿邓幼广姚姜姒姑褚煜䯄漏遮姫照姬'
# 无 taucht hier auf, prüfen warum nicht gefunden?!
hydcd_surnamefindings = u'知蕭伶徽酉窥辩锺念服遁锺廼惜虚檗感泣準灌牡張然棲圆献遯況蜕祢赞鈕揚楊炀賈芝皓禰鼓璚昙袮虱处挽弁韬梵体枕□涵戒阑至'
nondynasty_surnamestarters = set(nondynasty_surnamestarters_cbdb + hydcd_surnamefindings)
dynastysurnames = ['清', '明', '元', '金', '宋', '唐', '隋', '晋', '汉', '秦']

# some special strings typically in front of dictionary sources
sourcemappings = {u'中国近代史资料丛刊': (u'民国', None), 
 				  u'马王堆汉墓帛书乙本': (u'汉', None),
 			      u'马王堆汉墓帛书甲本': (u'汉', None),
 			      u'马王堆汉墓帛书': (u'汉', None)
 				}

# oder 圩 3［xū ㄒㄩ］
# 士 2［shì ㄕˋ］

