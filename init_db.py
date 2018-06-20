#!/usr/bin/env python

import psycopg2
from config import Configuration as conf

conn = psycopg2.connect(database = conf.PG_DB, user = conf.PG_USER, password = conf.PG_PASS, host = conf.PG_HOST, port = conf.PG_PORT)
print "Opened database successfully"

cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY NOT NULL,
            subject VARCHAR(255) NOT NULL,
            text TEXT NOT NULL,
            email VARCHAR(255) NOT NULL,
            status VARCHAR(55) NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT current_timestamp
            );
            CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY NOT NULL,
            ticket_id INTEGER REFERENCES tickets(id),
            email VARCHAR(255) NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT current_timestamp
        );''')

print "Tables tickets and comments created successfully"

conn.commit()
conn.close()
