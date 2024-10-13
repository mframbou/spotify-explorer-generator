import spotipy
import os
import json
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import time
import signal
import sys
import datetime
import threading


def is_json_serializable(obj):
    try:
        json.dumps(obj)
        return True
    except:
        return False


class PlaylistGenerator:
    SPOTIFY_API_SCOPE_NEEDED = (
        "playlist-read-private user-follow-read playlist-modify-private"
    )

    class State:
        def __init__(self):
            self.last_artist_saved: any = None
            self.last_song_saved: any = None
            self.input_playlist: any = None
            self.output_playlist: any = None
            self.songs_per_artist: int = -1
            self.artists: list = None
            self.started_at: datetime.datetime = datetime.datetime.now()
            self.last_updated_at: datetime.datetime = datetime.datetime.now()

            self.filename = (
                f'{self.started_at.strftime("%Y-%m-%d_%H-%M-%S")}_state.json'
            )

            # List of values from this class to exclude in the save file
            self.values_to_exclude: list = ["values_to_exclude", "filename"]

        def save_to_file(self, filename: str):
            self.last_updated_at = datetime.datetime.now()
            try:
                with open(filename, "w") as file:
                    values_to_save = {
                        key: value if is_json_serializable(value) else str(value)
                        for key, value in self.__dict__.items()
                        if key not in self.values_to_exclude
                    }
                    json.dump(values_to_save, file, indent=4)
            except IOError as e:
                print(f"Couldn't save state to file: {e}")

        def load_from_file(self, filename: str):
            try:
                with open(filename, "r") as file:
                    values = json.load(file)
                    for key, value in values.items():
                        setattr(self, key, value)
                    self.filename = filename
            except IOError as e:
                print(f"Couldn't load state from file: {e}")

        def delete_save_file(self):
            if not os.path.exists(self.filename):
                return
            try:
                os.remove(self.filename)
            except IOError as e:
                print(f"Couldn't delete save file: {e}")

    def __init__(
        self,
        spotify_client_id: str,
        spotify_client_secret: str,
        spotify_redirect_uri: str,
    ):
        self.spotify_client_id = spotify_client_id
        self.spotify_client_secret = spotify_client_secret
        self.spotify_redirect_uri = spotify_redirect_uri
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope=PlaylistGenerator.SPOTIFY_API_SCOPE_NEEDED,
                client_id=self.spotify_client_id,
                client_secret=self.spotify_client_secret,
                redirect_uri=self.spotify_redirect_uri,
            )
        )
        self.state = self.State()


def find_state_files():
    return [
        f for f in os.listdir(".") if os.path.isfile(f) and f.endswith("_state.json")
    ]


def main():
    load_dotenv()
    pg = PlaylistGenerator(
        os.getenv("SPOTIPY_CLIENT_ID"),
        os.getenv("SPOTIPY_CLIENT_SECRET"),
        os.getenv("SPOTIPY_REDIRECT_URI"),
    )
    state_files = find_state_files()
    if len(state_files) == 1:
        print(f"Found state file: {state_files[0]}")
        while True:
            try:
                choice = input("Do you want to load this state file? (y/n) ").lower()
                if choice == "y":
                    pg.state.load_from_file(state_files[0])
                    break
                elif choice == "n":
                    break
                else:
                    raise ValueError
            except ValueError:
                print("Invalid choice. Please try again.")

    elif len(state_files) > 1:
        print(f"Found multiple state files:")
        for i, f in enumerate(state_files):
            print(f"[{i}]  {f}")
        while True:
            try:
                choice = input(
                    "If you want to load a state file, type the number of the file you want to load. Otherwise, press enter. "
                )
                if choice == "":
                    break
                choice = int(choice)
                if choice < 0 or choice >= len(state_files):
                    raise ValueError
                pg.state.load_from_file(state_files[choice])
                break
            except ValueError:
                print("Invalid choice. Please try again.")

    print(pg.state.__dict__)


if __name__ == "__main__":
    main()
