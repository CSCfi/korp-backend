SET @@session.long_query_time = 1000;
CREATE TABLE IF NOT EXISTS `timedata` (
   `corpus` varchar(64) NOT NULL DEFAULT '',
   `datefrom` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
   `dateto` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
   `tokens` int(11) NOT NULL DEFAULT 0,
 PRIMARY KEY (`corpus`, `datefrom`, `dateto`))  default charset = utf8 ;
CREATE TABLE IF NOT EXISTS `timedata_date` (
   `corpus` varchar(64) NOT NULL DEFAULT '',
   `datefrom` date NOT NULL DEFAULT '0000-00-00',
   `dateto` date NOT NULL DEFAULT '0000-00-00',
   `tokens` int(11) NOT NULL DEFAULT 0,
 PRIMARY KEY (`corpus`, `datefrom`, `dateto`))  default charset = utf8 ;
DELETE FROM `timedata` WHERE `corpus` = 'TESTCORPUS';
DELETE FROM `timedata_date` WHERE `corpus` = 'TESTCORPUS';
SET NAMES utf8;
INSERT INTO `timedata` (corpus, datefrom, dateto, tokens) VALUES
('TESTCORPUS', '20130130000000', '20130130235959', 136);
INSERT INTO `timedata_date` (corpus, datefrom, dateto, tokens) VALUES
('TESTCORPUS', '20130130', '20130130', 136);
