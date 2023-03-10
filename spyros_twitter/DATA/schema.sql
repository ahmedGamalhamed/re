-- That's how the db looks, the only function of this file is to remind me in the future

CREATE TABLE IF NOT EXISTS prefixes (
    g_id INTEGER,
    prefix TEXT,
    CONSTRAINT unique_g_id UNIQUE (g_id)
);

CREATE TABLE IF NOT EXISTS aff (
  domain TEXT NOT NULL,
  affLink TEXT NOT NULL,
  percentage REAL NOT NULL,
  storeName TEXT NOT NULL,
  prod_first INTEGER NOT NULL DEFAULT 0, -- prod == production
  break_at_q INTEGER NOT NULL DEFAULT 1 -- q for question mark
);

-- Used for the `embed` command
CREATE TABLE IF NOT EXISTS shoe (
    shoe_name TEXT,
    image TEXT, -- a url
    last_used TEXT, -- a datetime object
    last_price REAL
);

CREATE TABLE IF NOT EXISTS stores (
    store_name TEXT,
    image TEXT, -- a url again
    last_used TEXT
);

CREATE TABLE IF NOT EXISTS channels (
    g_id INTEGER,
    origin_id INTEGER,
    dest_id INTEGER,
    CONSTRAINT u_g_chn UNIQUE (g_id, origin_id, dest_id)
);

-- Those fine with default values:
--INSERT INTO aff (domain, affLink, percentage, storename)
--     VALUES
--     ('18montrose.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=12207&wgtarget=',8,'18montrose'),
--     ('43einhalb.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10253&wgtarget=',8,'43einhalb'),
--     ('adidas.co.uk','http://prf.hn/click/camref:111l68V/destination:',10,'adidas UK'),
--     ('adidas.de','http://prf.hn/click/camref:1100l4Kd/destination:',10,'adidas DE'),
--     ('afew-store.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10319&wgtarget=',10,'Afew'),
--     ('aphrodite1994.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=4346&wgtarget=',7,'aphrodite'),
--     ('bstn.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=12887&wgtarget=',7,'BSTN'),
--     ('drome.co.uk','https://click.linksynergy.com/fs-bin/click?id=4zHZ8lGDWpM&subid=&offerid=420782.1&type=10&tmpid=18253&RD_PARM1=',3,'Drome'),
--     ('endclothing.com/gb','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=17184&platform=dl&p=%5B%5B',10,'End Clothing'),
--     ('endclothing.com/us','https://click.linksynergy.com/deeplink?id=4zHZ8lGDWpM&mid=41750&murl=',10,'End Clothing'),
--     ('flannels.com','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=3805&p=',5,'Flannels'),
--     ('footasylum.com','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=2832&p=',4,'Footasylum'),
--     ('footdistrict.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=11969&wgtarget=',8,'Foot District'),
--     ('footpatrol.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=5824&p=',6,'Footpatrol'),
--     ('jdsports.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=1431&p=',6,'JD Sports'),
--     ('kongonline.co.uk','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=11653&wgtarget= ',5,'Kong'),
--     ('luisaviaroma.com','https://go.skimresources.com?id=87324X1540081&xs=1&url=',11,'LVR'),
--     ('mainlinemenswear.co.uk','https://click.linksynergy.com/fs-bin/click?id=4zHZ8lGDWpM&subid=&offerid=228942.1&type=10&tmpid=14432&RD_PARM1=',7,'Mainline Menswear'),
--     ('mrporter.com','https://click.linksynergy.com/fs-bin/click?id=4zHZ8lGDWpM&subid=&offerid=475660.1&type=10&tmpid=10312&RD_PARM1=',6,'Mr Porter'),
--     ('nike.com/de','https://www.awin1.com/cread.php?awinaffid=203813&awinmid=16329&platform=dl&ued=',7,'Nike DE'),
--     ('nike.com/fr','https://www.awin1.com/cread.php?awinaffid=203813&awinmid=16328&platform=dl&ued=',7,'Nike FR'),
--     ('nike.com/gb','https://www.awin1.com/cread.php?awinaffid=203813&awinmid=16327&platform=dl&ued=',10,'Nike UK'),
--     ('nike.com/nl','https://www.awin1.com/cread.php?awinaffid=203813&awinmid=16332&platform=dl&ued=',7,'Nike NL'),
--     ('nike.com/t','http://www.anrdoezrs.net/links/7607762/type/dlg/',4,'Nike US'),
--     ('office.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=2374&p=',8,'Office'),
--     ('offspring.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=5379&p=',8,'Offspring'),
--     ('overkillshop.com/en','https://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=11073&wgtarget=',8,'Overkillshop'),
--     ('scottsmenswear.com','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=2769&p=',7,'Scotts'),
--     ('size.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=2767&p=',6,'Size?'),
--     ('slamjamsocialism.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10279&wgtarget=',11,'Slam Jam'),
--     ('sneak-a-venue.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10267&wgtarget=',4,'Sneak-A-Venue'),
--     ('sneakerbaas.com/uk','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=9949&wgtarget=',10,'Sneaker Baas UK'),
--     ('sneakersnstuff.com','http://go.redirectingat.com?id=87324X1540081&xs=1&url=',6,'Sneakersnstuff'),
--     ('snipes.com','http://go.redirectingat.com?id=87324X1540081&xs=1&url=',6,'Snipes'),
--     ('solekitchen.de','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10961&wgtarget=',8,'Solekitchen'),
--     ('store.nike.com/gb','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=6373&wgtarget=',7,'Nike GB'),
--     ('store.nike.com/us','http://go.redirectingat.com?id=87324X1540081&xs=1&url=',3,'Nike US'),
--     ('the-upper-club.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10193&wgtarget=',6,'The Upper Club'),
--     ('thegoodwillout.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=11403&wgtarget=',7,'TheGoodWillOut'),
--     ('tint-footwear.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=11075&wgtarget=',8,'TiNT'),
--     ('tower-london.com','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=10431&wgtarget=',5,'Tower London'),
--     ('triads.co.uk','http://track.webgains.com/click.html?wgcampaignid=155831&wgprogramid=4113&wgtarget=',5,'Triads'),
--     ('uk.puma.com','https://click.linksynergy.com/fs-bin/click?id=4zHZ8lGDWpM&subid=&offerid=197661.1&type=10&tmpid=15443&RD_PARM1=',6,'Puma UK'),
--     ('urbanindustry.co.uk','https://click.linksynergy.com/fs-bin/click?id=4zHZ8lGDWpM&subid=&offerid=401068.1&type=10&tmpid=8096&RD_PARM1=',2,'Urban Industry'),
--     ('very.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=3090&p=',0,'Very'),
--     ('zalando.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=3356&p=',5,'Zalando UK');
--
--
---- The rest:
--INSERT INTO aff (domain, affLink, percentage, storename, break_at_q)
--     VALUES
--     ('footlocker.co.uk','http://www.awin1.com/cread.php?awinaffid=203813&awinmid=15594&p=',8,'Footlocker UK', 0);
