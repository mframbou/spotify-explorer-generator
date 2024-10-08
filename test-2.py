import spotipy
import os
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


def get_playlist_tracks(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    return tracks


# Scope for playlist read, followed artists read, creating playlist, and adding tracks to playlist
scope = "playlist-read-private user-follow-read playlist-modify-private"


sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=scope,
    ),
)

# List all playlists owned by the current user
playlists = sp.current_user_playlists()
playlist_id = 3
include_followed_artists = False

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

# Remove duplicate artists and sort by name
artists = sorted(
    list({artist["name"]: artist for artist in artists}.values()),
    key=lambda x: x["name"],
)

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


def get_artist_songs(artist, include_groups="album,single", progress_callback=None):
    # for some reason separate album and single requests return more songs
    artist_songs = []
    albums = []
    results = sp.artist_albums(artist["id"], include_groups=include_groups)

    albums.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        if len(results["items"]) == 0:
            break
        albums.extend(results["items"])

    total_albums = len(albums)
    for i, album in enumerate(albums):
        if progress_callback:
            progress_callback(i, total_albums)
        songs = get_songs_from_album_without_unwanted(album)
        # print(f"Number of songs found for {album['name']}: {len(songs)}")
        artist_songs.extend(songs)

    return artist_songs


current_progression_percentage = 0
total_artists = len(artists)
current_artist = 0


def show_progression():
    global current_progression_percentage
    print(f"Progression: {round(current_progression_percentage, 2)}%")


def progress_callback_single(i, total):
    global current_progression_percentage

    percentage = (i + 1) / total
    percentage /= 2
    percentage += 0.5
    # 50-100%

    # curent progression is current_artist/total_artists + the current percentage in the current artist
    progression_per_artist = 1 / total_artists
    progression_in_current_artist = percentage
    current_progression = (
        current_artist - 1
    ) / total_artists + progression_per_artist * progression_in_current_artist
    current_progression_percentage = current_progression * 100
    show_progression()


def progress_callback_album(i, total):
    global current_progression_percentage

    percentage = (i + 1) / total
    percentage /= 2
    # 0-50%
    progression_per_artist = 1 / total_artists
    progression_in_current_artist = percentage
    current_progression = (
        current_artist - 1
    ) / total_artists + progression_per_artist * progression_in_current_artist
    current_progression_percentage = current_progression * 100
    show_progression()


def sort_songs_by_popularity(songs):
    songs_ids = [song["id"] for song in songs]
    # tracks is limited to 50 per request, so we need to split the list
    songs_popularity = []
    for i in range(0, len(songs_ids), 50):
        songs_popularity.extend(sp.tracks(songs_ids[i : i + 50])["tracks"])

    # sort songs by popularity
    sorted_songs = sorted(songs_popularity, key=lambda x: x["popularity"], reverse=True)

    return sorted_songs


def get_artist_top_10_songs(artist):
    top_tracks = sp.artist_top_tracks(artist["id"])["tracks"]
    return top_tracks


# Create a new playlist
# playlist_name = input("Enter the name of the new playlist: ")
# playlist_name = "pouetpouetpouet2"
# playlist = sp.user_playlist_create(sp.me()["id"], playlist_name, public=False)

# Now get all songs by the artists, and add them to a new playlist
# Get all songs by the artists
wanted_songs_per_artist = 25
total_songs = []
for artist in artists:
    current_artist += 1
    artist_songs = get_artist_songs(
        artist, include_groups="album", progress_callback=progress_callback_album
    )
    artist_songs.extend(
        get_artist_songs(
            artist, include_groups="single", progress_callback=progress_callback_single
        )
    )
    artist_songs = remove_duplicate_songs(artist_songs)
    # print("artist songs before sort:")
    # for song in artist_songs:
    # print(song["name"])
    top_10_songs = get_artist_top_10_songs(artist)
    artist_songs = sort_songs_by_popularity(artist_songs)
    final_songs = []
    for song in top_10_songs:
        final_songs.append(song)
    for song in artist_songs:
        final_songs.append(song)
    final_songs = remove_duplicate_songs(final_songs)
    final_songs = final_songs[:wanted_songs_per_artist]
    print(f"Final songs for {artist['name']}:")
    for song in final_songs:
        print(f"{song['name']} - {song['popularity']}")

    # print("--------------------")
    # print("artist songs after sort:")
    # for song in artist_songs:
    #     print(song["name"])

#     artist_songs_uris = [song["uri"] for song in artist_songs]
#     for i in range(0, len(artist_songs_uris), 100):
#         sp.playlist_add_items(playlist["id"], artist_songs_uris[i : i + 100])

#     total_songs.extend(artist_songs)

#     show_progression()
#     # print(f"Total number of songs found for {artist['name']}: {len(artist_songs)}")

# # print(f"Final number of songs found: {len(total_songs)}")
# print(f"Playlist {playlist_name} created with {len(total_songs)} songs")
