import glob
import hashlib
import os
import sqlite3
import tempfile
from csv import reader

import git

EXTENSION = ['txt', 'css', 'js']
def clone_git(name, url, path):
    print("clonning repo {} ...".format(url))
    git.Git(path).clone(url)
    repo = git.Repo("{}/{}".format(path, name))
    return repo

def get_hash(file) :
    if os.path.exists(file) :
        with open(file, "rb") as f:
            bytes = f.read() # read entire file as bytes
            readable_hash = hashlib.sha256(bytes).hexdigest()
            return readable_hash

def get_tags(tech, repo):

    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    conn = sqlite3.connect('collected_data.db')  #You can create a new database by changing the name
    c = conn.cursor() # The database will be saved in the location where your 'py' file is saved

    c.execute('''CREATE TABLE IF NOT EXISTS TAGS
               (TECHNO text, TAG text)''')

    for i in range(0, len(tags)) :
        #write to DB name / tag
        c.execute('''SELECT * FROM TAGS WHERE (TECHNO='{}' AND TAG='{}')'''.format(tech, tags[i]))
        entry = c.fetchone()
        print(entry)
        if entry is None:

            print(tags[i])
            c.execute("INSERT INTO TAGS VALUES ('{}','{}')".format(tech, tags[i]))
            conn.commit()
        else:
            print("Entry already exists")

    conn.close()

def get_path_to_files(tech, my_dir, repo, tag):
    repo.git.checkout('tags/{}'.format(tag))
    conn = sqlite3.connect('collected_data.db')
    c = conn.cursor() # The database will be saved in the location where your 'py' file is saved
    c.execute('''CREATE TABLE IF NOT EXISTS FILES
                (TECHNO text, PATH text)''')

    for root, files, dirs in os.walk(my_dir):

        for ext in EXTENSION:

            for file_name in glob.glob('{}/**/*.{}'.format(root, ext), recursive = True):
                index = file_name.find(tech)
                path = file_name[index:].lstrip(tech)

                print("Current tag : {}".format(tag))
                c.execute('''SELECT * FROM FILES
                WHERE (TECHNO='{}' AND PATH='{}')'''.format(tech, path))
                entry = c.fetchone()

                if entry is None:
                    c.execute('''INSERT INTO FILES
                    VALUES ('{}','{}')'''.format(tech, path))
                else:
                    print("Entry already exists")

                path_to_file = "{}{}".format(my_dir, path)
                print(path_to_file)
                hash_value = get_hash(path_to_file)
                print("hash_value = {}".format(hash_value))
                c.execute('''SELECT * FROM HASHES WHERE (HASH='{}')'''.format(hash_value))
                check = c.fetchone()

                if check is None:
                    c.execute('''INSERT INTO HASHES
                    VALUES ('{}','{}','{}')'''.format(hash_value, tech, tag))
                else :
                    new_version = "{},{}".format(check[2], tag)
                    c.execute('''UPDATE HASHES
                        SET versions = '{}'
                        WHERE HASH = '{}' '''.format(new_version, hash_value))

            conn.commit()
    conn.close()



conn = sqlite3.connect('collected_data.db')
c = conn.cursor() # The database will be saved in the location where your 'py' file is saved

c.execute('''CREATE TABLE IF NOT EXISTS HASHES
            (HASH text, TECHNO text, VERSIONS text)''')

with open('src/tech_list.csv', 'r') as read_obj:
    csv_reader = reader(read_obj)
    header = next(csv_reader)
    csv_reader = reader(read_obj)

    if header != None:
        for row in csv_reader:
            with tempfile.TemporaryDirectory() as tmpdirname:
                name = row[0]
                url = row[1]
                repo = clone_git(name, url, tmpdirname)
                path = "{}/{}/".format(tmpdirname, name)
                get_tags(name, repo)
                conn = sqlite3.connect('collected_data.db')
                c = conn.cursor() #The DB will be saved in the location where your 'py' file is saved
                c.execute('''SELECT TAG FROM TAGS WHERE (TECHNO='{}')'''.format(name))
                tags = c.fetchall()
                
                for tag in tags :
                    get_path_to_files(name, path, repo, tag[0])
