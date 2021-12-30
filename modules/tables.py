hydcd_dynasties = """
CREATE TABLE `hydcd_dynasties` (
  `c_dy` int(11) NOT NULL,
  `western` char(255) DEFAULT NULL,
  `fanti` char(255) DEFAULT NULL,
  `jianti` char(255) DEFAULT NULL,
  `start` int(11) DEFAULT NULL,
  `end` int(11) DEFAULT NULL,
  `c_sort` int(11) DEFAULT NULL,
  PRIMARY KEY (`c_dy`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
"""

hydcd_entries = """
CREATE TABLE `hydcd_entries` (
  `id` int(5) unsigned NOT NULL AUTO_INCREMENT,
  `char` varchar(24) CHARACTER SET utf8 DEFAULT '',
  `entry` mediumtext CHARACTER SET utf8,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
"""

hydcd_words = """
CREATE TABLE `hydcd_words` (
  `id` int(6) unsigned NOT NULL AUTO_INCREMENT,
  `id_internal` int(4) DEFAULT NULL,
  `char_id` int(5) DEFAULT NULL,
  `char` varchar(24) CHARACTER SET utf8 DEFAULT NULL,
  `word` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `cleanword` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `zhuyin` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `pinyin` varchar(100) CHARACTER SET utf8 DEFAULT NULL,
  `rhyme` varchar(100) CHARACTER SET utf8 DEFAULT NULL,  
  `entry` mediumtext CHARACTER SET utf8,
  `entrytype` varchar(1) CHARACTER SET utf8,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
"""

the_books = """
CREATE TABLE `the_books` (
  `id` int(9) NOT NULL DEFAULT '0',
  `clearbook` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `cbdb_text_id` int(11) DEFAULT NULL,
  `title_py` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `title_western` varchar(200) CHARACTER SET utf8 DEFAULT NULL,
  `startyear` int(4) DEFAULT NULL,
  `endyear` int(4) DEFAULT NULL,
  `dynasty` varchar(11) CHARACTER SET utf8 DEFAULT NULL,
  `estimate` tinyint(1) DEFAULT NULL,
  `usecount` int(9) DEFAULT NULL,
  `useinfirstcount` int(9) DEFAULT NULL,  
  `source` varchar(200) DEFAULT NULL,
  `author` varchar(32) CHARACTER SET utf8 DEFAULT NULL,
  `cbdb_author_id` int(11) DEFAULT NULL,
  `dfz_id` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  index ix_book (`clearbook`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
"""

the_words = """
CREATE TABLE `the_words` (
  `id` int(7) NOT NULL DEFAULT '0',
  `cleanword` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `nakedword` varchar(128) CHARACTER SET utf8 DEFAULT NULL,
  `pinyin` varchar(100) CHARACTER SET utf8 DEFAULT NULL,
  `counter` int(4) DEFAULT NULL,
  `firstentry` varchar(200) COLLATE utf8_bin DEFAULT NULL,
  `unordered` int(1) DEFAULT NULL,
  `indirectsource` int(1) DEFAULT NULL,
  `book` varchar(100) COLLATE utf8_bin DEFAULT NULL,
  `book_id` int(9) DEFAULT NULL,
  `earliest_evidence_book_id` int(9) DEFAULT NULL,
  `earliest_evidence_dfz_id` int(9) DEFAULT NULL,
  PRIMARY KEY (`id`),
  index ix_word (`cleanword`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
"""

the_citations = """
CREATE TABLE `the_citations` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT, 
  `word_id` int(7) DEFAULT NULL,
  `sub_id` int(4) DEFAULT 1,
  `book_id` int(9) DEFAULT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`book_id`) REFERENCES the_books(`id`),
  FOREIGN KEY (`word_id`) REFERENCES the_words(`id`),
  index ix_word_id (word_id),
  index ix_book_id (book_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
"""