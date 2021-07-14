"""
Export your dataset from a Lobe project
"""
import argparse
from sys import platform
import os
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm
from PIL import Image
from dataset.utils import _resolve_filename_conflict

if platform == 'darwin':
    PROJECTS_DIR_MAC = '~/Library/Application Support/lobe/projects'
    PROJECTS_DIR = os.path.realpath(os.path.expanduser(PROJECTS_DIR_MAC))
else:
    PROJECTS_DIR_WINDOWS = os.path.join(os.getenv('APPDATA'), 'lobe', 'projects')
    PROJECTS_DIR = os.path.realpath(PROJECTS_DIR_WINDOWS)

PROJECT_JSON_FILE = 'project.json'
PROJECT_ID_KEY = 'id'
PROJECT_META_KEY = 'meta'
PROJECT_NAME_KEY = 'name'
PROJECT_DB_FILE = 'db.sqlite'
PROJECT_BLOBS = os.path.join('data', 'blobs')


def get_projects():
    """
    Returns tuples of (project name, project id) from Lobe's appdata directory, sorted by modified date
    """
    projects = []
    for project in os.listdir(PROJECTS_DIR):
        project_dir = os.path.join(PROJECTS_DIR, project)
        if os.path.isdir(project_dir):
            try:
                project_json_file = os.path.join(project_dir, PROJECT_JSON_FILE)
                with open(project_json_file, 'r') as f:
                    project_json = json.load(f)
                    project_id = project_json.get(PROJECT_ID_KEY)
                    project_name = project_json.get(PROJECT_META_KEY, {}).get(PROJECT_NAME_KEY)
                    # return the name, the id, and the modified datetime for sorting by recency
                    projects.append(((project_name, project_id), os.path.getmtime(project_json_file)))
            except Exception:
                # didn't have the project.json file (old alpha projects)
                pass
    projects = sorted(projects, key=lambda x: x[1], reverse=True)  # sort by the modified date
    return [info for info, _ in projects]


def export_dataset(project_id, destination_dir, progress_hook=None, batch_size=1000):
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
        # go through the data item entries in the db, find the blob filenames, and save to the appropriate location
        # first get the total number of images for our progress bar
        cursor.execute("SELECT count(*) FROM example_images")
        num_images = cursor.fetchone()
        if not num_images:
            print(f"Didn't find any images for project {project_id}")
        else:
            num_images = num_images[0]
            futures = []
            lock = Lock()
            examples_query = """
            SELECT example_images.hash, example_labels.label
            FROM example_images LEFT JOIN example_labels
            ON example_images.example_id = example_labels.example_id
            LIMIT ?
            OFFSET ?
            """
            with tqdm(total=num_images) as pbar:
                with ThreadPoolExecutor() as executor:
                    for offset in range(0, num_images, batch_size):
                        cursor.execute(examples_query, [batch_size, offset])
                        res = cursor.fetchall()
                        for row in res:
                            img_hash, label = row
                            # get the image filepath from the hash
                            img_filepath = os.path.join(blob_dir, img_hash)
                            # if we had a label, make the destination directory the subdirectory with label name
                            dest_dir = os.path.join(destination_dir, label) if label is not None else destination_dir
                            futures.append(
                                executor.submit(
                                    _export_blob, blob_path=img_filepath, destination_dir=dest_dir, lock=lock
                                )
                            )

                    num_processed = 0
                    # wait for all our futures
                    for _ in as_completed(futures):
                        # update our progress bar for the finished image
                        pbar.update(1)
                        num_processed += 1
                        if progress_hook:
                            progress_hook(num_processed, num_images)
    except Exception as e:
        print(f"Error exporting project {project_id} to {destination_dir}:\n{e}")
    finally:
        if conn:
            conn.close()


def _export_blob(blob_path, destination_dir, lock=None):
    """
    Export the image to the destination, resolving names on conflict
    """
    os.makedirs(destination_dir, exist_ok=True)
    # get our image and save it with the native format in our new directory
    # get the blob id from the blob path
    blob_id = os.path.basename(blob_path)
    img = Image.open(blob_path)
    img_filename = f'{blob_id}.{img.format.lower()}'
    # look for file name conflict and resolve
    if lock:
        with lock:
            img_filename = _resolve_filename_conflict(directory=destination_dir, filename=img_filename)
            # now that we found the filename, make an empty file with it so that we don't have to wait file to download
            # for subsequent name searches with threading
            open(os.path.join(destination_dir, img_filename), 'a').close()
    else:
        img_filename = _resolve_filename_conflict(directory=destination_dir, filename=img_filename)
    # now save the file
    destination_file = os.path.join(destination_dir, img_filename)
    img.save(destination_file, quality=100)


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
