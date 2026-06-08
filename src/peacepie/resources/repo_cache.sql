
CREATE TABLE json_responses (
    id INTEGER PRIMARY KEY,
    index_url TEXT NOT NULL,
    package_name TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    data TEXT NOT NULL,
    UNIQUE (index_url, package_name)
);

CREATE TABLE metadata (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    data TEXT NOT NULL,
    UNIQUE (url, package_name, package_version)
);

CREATE TABLE wheels (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    data TEXT NOT NULL,
    UNIQUE (url, package_name, package_version)
);

