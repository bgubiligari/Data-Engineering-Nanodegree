import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
    Processes a song file and loads data in to songs and artists dimension tables
    :param cur: database cursor
    :param filepath: song file path
    """
    # open song file
    df = pd.read_json(filepath, typ='series')

    # insert song record
    song_data = df[["song_id", "title", "artist_id", "year", "duration"]]
    song_data = list(song_data.values)
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artist_data = df[["artist_id", "artist_name", "artist_location", "artist_latitude", "artist_longitude"]]
    artist_data = list(artist_data.values)
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
    Processes a log file and loads data in to users,time dimension tables and songplays fact table
    :param cur: database cursor
    :param filepath: log file path
    """
    # open log file
    df = pd.read_json(filepath,lines = True)

    # filter by NextSong action
    data_filter = (df['page'] == 'NextSong')
    df = df[data_filter]

    # convert timestamp column to datetime
    df["ts"] = pd.to_datetime(df["ts"], unit='ms')
    t = df["ts"]
    
    # insert time data records
    timestamps = t.dt.time
    hours = t.dt.hour
    days = t.dt.day
    weeks = t.dt.week
    months = t.dt.month
    years = t.dt.year
    weekday = t.dt.weekday
    time_df = pd.DataFrame({"timestamp": timestamps, "hour": hours, "day": days, "week": weeks, "month": months, "year": years, "weekdays": weekday})

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[["userId", "firstName", "lastName", "gender", "level"]]
    user_df = user_df.dropna(how='all')
    user_df= user_df.drop_duplicates()

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (row.ts, row.userId, row.level, songid, artistid, row.sessionId, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    Processes either logs or songs file depending on the function
    :param cur: database cursor
    :param conn: database connection
    :param filepath: the path to the data directory
    :param func: function name
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """
    Inserts songs and logs data in to Facts and dimension tables
    """
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()