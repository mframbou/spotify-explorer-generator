import spotipy
import os
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


def get_playlist_tracks(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results["items"]
    # while results["next"]:
    #     results = sp.next(results)
    #     tracks.extend(results["items"])
    return tracks


# Scope for playlist read, followed artists read, creating playlist, and adding tracks to playlist
scope = "playlist-read-private user-follow-read playlist-modify-private"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=scope,
    )
)

# List all playlists owned by the current user
playlists = sp.current_user_playlists()
playlist_id = 0

# ask user to select a playlist
for i, playlist in enumerate(playlists["items"]):
    print(f"{playlist['name']} ({i})")
playlist_id = input("Enter the playlist id: ")


print(f"Selected playlist: {playlists['items'][int(playlist_id)]['name']}")

# Get all tracks in the selected playlist
tracks = get_playlist_tracks(playlists["items"][int(playlist_id)]["id"])

# print number of tracks in the playlist
print(f"Number of tracks in the playlist: {len(tracks)}")

# Get all artists in the selected playlist
artists = []
for track in tracks:
    for artist in track["track"]["artists"]:
        artists.append(artist)

print(f"Number of artists in the playlist: {len(artists)}")
for artist in artists:
    print(artist["name"])
