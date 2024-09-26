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
playlist_id = 3
include_followed_artists = False

# ask user to select a playlist
# for i, playlist in enumerate(playlists["items"]):
#     print(f"{playlist['name']} ({i})")
# playlist_id = input("Enter the playlist id: ")


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
# for artist in artists:
#     print(artist["name"])


def is_unwanted_song_or_album(name):
    # remove if name contains "Edition", "Live", "Anniversary", "Remaster", "Remastered"
    return (
        "Edition" in name
        or "Live" in name
        or "Anniversary" in name
        or "Remaster" in name
        or "Remastered" in name
        or "Instrumental" in name
        or "Acoustic" in name
        or "Instrumentals" in name
        or "Capella" in name
        or "Cappella" in name
        or "Acapella" in name
        or "Remix" in name
    )


def remove_unwanted_songs(songs):
    res = [song for song in songs if not is_unwanted_song_or_album(song["name"])]
    return res


def get_songs_from_album_without_unwanted(album):
    # first check if the album name is unwanted
    if is_unwanted_song_or_album(album["name"]):
        return []
    songs_in_album = []
    results = sp.album_tracks(album["id"])
    songs_in_album.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        songs_in_album.extend(results["items"])
    songs_in_album = remove_unwanted_songs(songs_in_album)
    return songs_in_album


def remove_duplicate_songs(songs):
    # check with title/duration
    res = []
    for song in songs:
        if song not in res and song["name"] not in [s["name"] for s in res]:
            res.append(song)
    return res


def get_artist_songs(artist, include_groups="album,single"):
    # for some reason separate album and single requests return more songs
    artist_songs = []
    albums = []
    results = sp.artist_albums(artist["id"], include_groups=include_groups)
    albums.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        albums.extend(results["items"])
    # print(f"Number of albums found for {artist['name']}: {len(albums)}")
    for album in albums:
        songs = get_songs_from_album_without_unwanted(album)
        # print(f"Number of songs found for {album['name']}: {len(songs)}")
        artist_songs.extend(songs)

    return artist_songs


# Now get all songs by the artists, and add them to a new playlist
# Get all songs by the artists
total_songs = []
for artist in artists:
    artist_songs = get_artist_songs(artist, include_groups="album")
    artist_songs.extend(get_artist_songs(artist, include_groups="single"))
    artist_songs = remove_duplicate_songs(artist_songs)
    total_songs.extend(artist_songs)

    print(f"Number of songs found for {artist['name']}: {len(artist_songs)}")

print(f"Number of songs found: {len(total_songs)}")


# Create a new playlist
playlist_name = input("Enter the name of the new playlist: ")
# playlist_name = "pouetpouetpouet2"
playlist = sp.user_playlist_create(sp.me()["id"], playlist_name, public=False)

# Convert total_songs to list of URIs
total_songs = [song["uri"] for song in total_songs]
# Add the songs to the new playlist
# requests are capped to 100 songs per request
for i in range(0, len(total_songs), 100):
    sp.playlist_add_items(playlist["id"], total_songs[i : i + 100])
print(f"Playlist {playlist_name} created with {len(total_songs)} songs")
