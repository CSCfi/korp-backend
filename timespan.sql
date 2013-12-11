SET @@session.long_query_time = 1000;
CREATE TABLE IF NOT EXISTS `timespans` (
   `corpus` varchar(64) NOT NULL DEFAULT '',
   `datefrom` char(14) NOT NULL DEFAULT '',
   `dateto` char(14) NOT NULL DEFAULT '',
   `tokens` int(11)  DEFAULT NULL,
 INDEX `corpus` (`corpus`))  default charset = `utf8` ;
DELETE FROM `timespans` WHERE `corpus` = 'TESTCORPUS';
SET NAMES utf8;
INSERT INTO `timespans` (corpus, datefrom, dateto, tokens) VALUES
('TESTCORPUS', '20130130', '20130130', 136);
