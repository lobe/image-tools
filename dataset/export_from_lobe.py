"""
Export your dataset from a Lobe project
"""
import argparse
from sys import platform
import os
import json
import sqlite3
from shutil import copyfile
from tqdm import tqdm


PROJECTS_DIR_WINDOWS = os.path.join(os.getenv('APPDATA'), 'lobe', 'projects')
PROJECTS_DIR_MAC = '~/Library/Application Support/lobe/projects'
PROJECTS_DIR = os.path.realpath(PROJECTS_DIR_MAC) if platform == 'darwin' else os.path.realpath(PROJECTS_DIR_WINDOWS)
PROJECT_JSON_FILE = 'project.json'
PROJECT_ID_KEY = 'id'
PROJECT_META_KEY = 'meta'
PROJECT_NAME_KEY = 'name'
PROJECT_DB_FILE = 'db.sqlite'
PROJECT_BLOBS = os.path.join('data', 'blobs')


def get_projects():
    """
    Generator that returns tuples of (project name, project id) from Lobe's appdata directory
    """
    for project in os.listdir(PROJECTS_DIR):
        project_dir = os.path.join(PROJECTS_DIR, project)
        if os.path.isdir(project_dir):
            try:
                with open(os.path.join(project_dir, PROJECT_JSON_FILE), 'r') as f:
                    project_json = json.load(f)
                    project_id = project_json.get(PROJECT_ID_KEY)
                    project_name = project_json.get(PROJECT_META_KEY, {}).get(PROJECT_NAME_KEY)
                    yield (project_name, project_id)
            except Exception:
                # didn't have the project.json file (old alpha projects)
                pass


def export_dataset(project_id, destination_dir, progress_hook=None):
    """
    Given a project id and a destination export parent directory, copy the images into a subfolder structure
    """
    # make the desired destination if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)
    # project directory doesn't include the '-' from the project uuid
    project_dir = os.path.join(PROJECTS_DIR, project_id.replace('-', ''))
    blob_dir = os.path.join(project_dir, PROJECT_BLOBS)
    # connect to our project db
    db_file = os.path.join(project_dir, PROJECT_DB_FILE)
    conn = None
    try:
        # db connection
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        # walk through our data blobs, find a corresponding label, and save to the appropriate location
        blobs = [os.path.join(blob_dir, name_) for name_ in os.listdir(blob_dir) if os.path.isfile(os.path.join(blob_dir, name_))]
        num_processed = 0
        for blob_path in tqdm(blobs):
            _export_blob(blob_path=blob_path, destination_dir=destination_dir, cursor=cursor)
            num_processed += 1
            if progress_hook:
                progress_hook(num_processed, len(blobs))
    except Exception as e:
        print(f"Error exporting project {project_id} to {destination_dir}:\n{e}")
    finally:
        if conn:
            conn.close()


def _export_blob(blob_path, destination_dir, cursor):
    """
    Given an image blob and a db connection, export the image to the correct destination based on the label
    """
    # get the blob id from the blob path
    blob_id = os.path.basename(blob_path)
    # search the db cursor for the label of the blob
    select_statement = """
    SELECT t1.item 
    FROM data_items AS t1
    WHERE t1.type = "text"
    AND t1.example_id = (
        SELECT t2.example_id
        FROM data_items AS t2
        WHERE t2.type = "image"
        AND t2.hash = ?
    )
    """
    cursor.execute(select_statement, [blob_id])
    label = cursor.fetchone()
    # if we had a label, make the destination directory the subdirectory with label name
    if label:
        label = label[0]
        destination_dir = os.path.join(destination_dir, label)
    os.makedirs(destination_dir, exist_ok=True)
    # make our .jpg filename from the blob file
    destination_file = os.path.join(destination_dir, f'{blob_id}.jpg')
    copyfile(src=blob_path, dst=destination_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export an image dataset from Lobe.')
    parser.add_argument('project', help='Your project name.', type=str)
    parser.add_argument('dest', help='Your destination export directory.', type=str, default='.')
    args = parser.parse_args()
    project_name, project_id = None, None
    for name_, id_ in get_projects():
        if name_ == args.project:
            project_name = name_
            project_id = id_
            break
    if project_name:
        export_dataset(project_id=project_id, destination_dir=os.path.join(os.path.abspath(args.dest), project_name))
    else:
        print(f"Couldn't find project with name {args.project}.\nAvailable projects: {[name_ for name_, _ in get_projects()]}")
