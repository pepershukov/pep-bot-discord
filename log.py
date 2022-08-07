import sqlite3

connection = sqlite3.connect('discord.db')
cursor = connection.cursor()

cursor.execute('select * from log')
for i in cursor.fetchall():
    string = "{} | {}\n".format(i[0], i[1])
    with open('log.txt', 'a') as file:
        file.write(string)