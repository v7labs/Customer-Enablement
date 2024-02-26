"""
# Script name: local_multi_slot_upload.py
# Last edited: 07.01.24

DESCRIPTION
When executed from the command line, this script:
- Registers local files in folders in multiple slots in a Darwin dataset.
- Files from each folder are listed, sorted naturally (i.e. "A2" < "A10"), and then placed into slots according to their sorted index.
  i.e. The first files in sorted position 1 in each folder will be placed into slots in the same item, as will the files in sorted position 2 etc.

USAGE
python local_multi_slot_upload.py [-h] api_key team_slug dataset_slug

NOTE - The SLOT_NAMES and FOLDER_PATHS variables must be populated before running the script.

REQUIRED ARGUMENTS
api_key: API key for authentication with Darwin
team_slug: Team slug for Darwin
dataset_slug: Dataset slug for Darwin

OPTIONAL ARGUMENTS
-h, --help: Print the help message for the function and exit
"""

import argparse
import requests
import json
import re
from pathlib import Path

SLOT_NAMES = ["example_slot_1", "example_slot_2", "example_slot_3"]

FOLDER_PATHS = [
    Path("example_folder_1"),
    Path("example_folder_2"),
    Path("example_folder_3"),
]


def get_args() -> argparse.Namespace:
    """
    Parse and return command line arguments.

    Returns
    -------
        args (argparse.Namespace): API key, team slug, and dataset slug
    """
    parser = argparse.ArgumentParser(
        description="Registers local files in folders in multiple slots in a Darwin dataset."
    )
    parser.add_argument("api_key", help="API key for authentication with Darwin")
    parser.add_argument("team_slug", help="Team slug for Darwin")
    parser.add_argument("dataset_slug", help="Dataset slug for Darwin")
    return parser.parse_args()


def validate_api_key(api_key: str) -> None:
    """
    Validates the given API key. Exits if validation fails.

    Parameters
    ----------
        api_key (str): The API key to be validated

    Raises
    ------
        ValueError: If the API key failed validation
    """
    example_key = "DHMhAWr.BHucps-tKMAi6rWF1xieOpUvNe5WzrHP"
    api_key_regex = re.compile(r"^.{7}\..{32}$")
    assert api_key_regex.match(
        api_key
    ), f"Expected API key to match the pattern: {example_key}"


def get_files_and_perform_upload(
    api_key: str, team_slug: str, dataset_slug: str
) -> None:
    """
    Registers local files in folders in multiple slots in a Darwin dataset.

    Parameters
    ----------
        api_key (str): API key for authentication with Darwin
        team_slug (str): Team slug for Darwin
        dataset_slug (str): Dataset slug for Darwin
    """
    # Get the folder with the most files
    path_lengths = [
        len(list(i.glob("*"))) for i in FOLDER_PATHS if not i.name.startswith(".")
    ]
    most_files_idx = path_lengths.index(max(path_lengths))

    # Generate alphanumerically sorted lists of filenames & filepaths
    filenames, filepaths = [], []
    for idx, path in enumerate(FOLDER_PATHS):
        folder_filenames = [
            i.name for i in path.glob("*") if not i.name.startswith(".")
        ]
        human_sort(folder_filenames)
        filenames.append(folder_filenames)
        for item in folder_filenames:
            filepaths.append(path / item)

    # Build the registration payload and request
    items = []
    for item_idx, item in enumerate(filenames[most_files_idx]):
        slots = []
        for path_idx, path in enumerate(FOLDER_PATHS):
            try:
                slots.append(
                    {
                        "as_frames": False,
                        "file_name": filenames[path_idx][item_idx],
                        "slot_name": SLOT_NAMES[path_idx],
                    }
                )
            except IndexError:
                pass
        items.append({"path": "/", "slots": slots, "name": item})

    url = f"https://darwin.v7labs.com/api/v2/teams/{team_slug}/items/register_upload"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {api_key}",
    }
    payload = {"items": items, "dataset_slug": dataset_slug}

    # Register the files
    response = requests.post(url, json=payload, headers=headers)
    request_response = json.loads(response.text)

    # Define dictionaries mapping filenames to filepaths and upload_ids
    filepath_dict = {}
    for path in filepaths:
        name = path.name
        filepath_dict[name] = path

    upload_id_dict = {}
    for item in request_response["items"]:
        for slot in item["slots"]:
            upload_id_dict[slot["upload_id"]] = filepath_dict[slot["file_name"]]

    # Signing uploads, uploading, and confirming uploads
    for upload_id in upload_id_dict:
        url = f"https://darwin.v7labs.com/api/v2/teams/{team_slug}/items/uploads/{upload_id}/sign"
        response = requests.get(url, headers=headers)

        res = json.loads(response.text)
        upload_url = res["upload_url"]
        with open(upload_id_dict[upload_id], "rb") as f:
            data = f.read()
        response = requests.put(url=upload_url, data=data)
        print(response.status_code)

        url = f"https://darwin.v7labs.com/api/v2/teams/{team_slug}/items/uploads/{upload_id}/confirm"
        payload = {"name": "example_slots"}
        response = requests.post(url, json=payload, headers=headers)
        print(response.status_code)


def tryint(s):
    """
    Return an int if possible, or `s` unchanged.
    """
    try:
        return int(s)
    except ValueError:
        return s


def alphanum_key(s):
    """
    Turn a string into a list of string and number chunks.

    >>> alphanum_key("z23a")
    ["z", 23, "a"]

    """
    return [tryint(c) for c in re.split("([0-9]+)", s)]


def human_sort(list_to_sort):
    """
    Sort a list in the way that humans expect.
    """
    list_to_sort.sort(key=alphanum_key)


def main() -> None:
    """
    Top level function to execute sub-functions.
    """
    # Parse and validate command line arguments
    args = get_args()
    validate_api_key(args.api_key)
    get_files_and_perform_upload(args.api_key, args.team_slug, args.dataset_slug)

    # Call the rest of your functions here


if __name__ == "__main__":
    main()
