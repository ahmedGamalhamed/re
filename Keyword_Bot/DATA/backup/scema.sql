-- That's how the db looks, the only function of this file is to remind me in the future

CREATE TABLE prefixes(
    g_id INTEGER,
    prefix TEXT,
    CONSTRAINT unique_g_id UNIQUE (g_id)
);

CREATE TABLE words(
    g_id INTEGER,
    word TEXT,
    to_notify_id INTEGER PRIMARY KEY,
    chn_id INTEGER
);

CREATE TABLE to_notify(
    id INTEGER,
    type INTEGER, -- 0: member 1: role
    id_to_notify INTEGER
);
