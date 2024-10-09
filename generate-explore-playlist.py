import spotipy
import os
import json
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import time

# Scope for playlist read, followed artists read, creating playlist, and adding tracks to playlist
SPOTIFY_API_SCOPE = "playlist-read-private user-follow-read playlist-modify-private"


def get_playlist_tracks(playlist_id, spotify_client):
    results = spotify_client.playlist_tracks(playlist_id)
    tracks = results["items"]
    while results["next"]:
        results = spotify_client.next(results)
        tracks.extend(results["items"])
    return tracks


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


def get_songs_from_album_without_unwanted(album, spotify_client):
    # first check if the album name is unwanted
    if is_unwanted_song_or_album(album["name"]):
        return []
    songs_in_album = []
    results = spotify_client.album_tracks(album["id"])
    songs_in_album.extend(results["items"])
    while results["next"]:
        results = spotify_client.next(results)
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


def get_artist_songs(
    artist, spotify_client, include_groups="album,single", progress_callback=None
):
    # for some reason separate album and single requests return more songs
    artist_songs = []
    albums = []
    results = spotify_client.artist_albums(artist["id"], include_groups=include_groups)

    albums.extend(results["items"])
    while results["next"]:
        results = spotify_client.next(results)
        if len(results["items"]) == 0:
            break
        albums.extend(results["items"])

    total_albums = len(albums)
    for i, album in enumerate(albums):
        if progress_callback:
            progress_callback(i, total_albums)
        songs = get_songs_from_album_without_unwanted(album, spotify_client)
        # print(f"Number of songs found for {album['name']}: {len(songs)}")
        artist_songs.extend(songs)

    return artist_songs


current_progression_percentage = 0
total_artists = 0
current_artist = 0


def show_progression():
    global current_progression_percentage
    print(f"Progression: {round(current_progression_percentage, 2)}%")


def progress_callback_single(i, total):
    global current_progression_percentage
    global total_artists
    global current_artist

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
    global total_artists
    global current_artist

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


def progress_callback_generic():
    global current_progression_percentage
    global total_artists
    global current_artist

    progression_per_artist = 1 / total_artists
    progression_in_current_artist = 1
    current_progression = (
        current_artist - 1
    ) / total_artists + progression_per_artist * progression_in_current_artist
    current_progression_percentage = current_progression * 100


def sort_songs_by_popularity(songs, spotify_client):
    songs_ids = [song["id"] for song in songs]
    # tracks is limited to 50 per request, so we need to split the list
    songs_popularity = []
    for i in range(0, len(songs_ids), 50):
        songs_popularity.extend(spotify_client.tracks(songs_ids[i : i + 50])["tracks"])

    # sort songs by popularity
    sorted_songs = sorted(songs_popularity, key=lambda x: x["popularity"], reverse=True)

    return sorted_songs


def get_artist_top_10_songs(artist, spotify_client):
    top_tracks = spotify_client.artist_top_tracks(artist["id"])["tracks"]
    return top_tracks


def create_playlist(playlist_name, spotify_client, public=False):
    playlist = spotify_client.user_playlist_create(
        spotify_client.me()["id"], playlist_name, public=public
    )
    return playlist


def get_user_playlists(spotify_client):
    playlists = spotify_client.current_user_playlists()
    return playlists


def get_user_followed_artists(spotify_client):
    followed_artists = []
    results = spotify_client.current_user_followed_artists()
    followed_artists.extend(results["artists"]["items"])
    while results["artists"]["next"]:
        results = spotify_client.next(results["artists"])
        followed_artists.extend(results["artists"]["items"])

    return followed_artists


def main():
    try:
        global total_artists
        global current_artist

        load_dotenv()

        sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
                scope=SPOTIFY_API_SCOPE,
            ),
        )

        # List all playlists owned by the current user
        playlists = get_user_playlists(sp)
        source_playlist_id = 0
        include_followed_artists = False
        wanted_songs_per_artist = 10

        if len(playlists["items"]) == 0:
            print("No playlists found, please create a playlist first")
            return

        for i, playlist in enumerate(playlists["items"]):
            print(f"{i} - {playlist['name']}")

        while True:
            try:
                source_playlist_id = int(
                    input("Enter the desired source playlist id: ")
                )
                if source_playlist_id < 0 or source_playlist_id >= len(
                    playlists["items"]
                ):
                    print(
                        f"Invalid playlist id, please enter a number between 0 and {len(playlists['items']) - 1}"
                    )
                else:
                    break
            except ValueError:
                print(
                    f"Invalid playlist id, please enter a number between 0 and {len(playlists['items']) - 1}"
                )

        print(f"Selected playlist: {playlists['items'][source_playlist_id]['name']}")

        while True:
            include_followed_artists = input(
                "Do you want to include followed artists? (y/n): "
            ).lower()
            if include_followed_artists == "y":
                include_followed_artists = True
                break
            elif include_followed_artists == "n":
                include_followed_artists = False
                break
            else:
                print("Invalid input, please enter 'y' or 'n'")

        while True:
            try:
                wanted_songs_per_artist = int(
                    input(
                        "Enter the maximum number of songs you want to keep per artist (sorted by popularity): "
                    )
                )
                if wanted_songs_per_artist < 1:
                    print("Please enter a number greater than 0")
                else:
                    break
            except ValueError:
                print("Please enter a number greater than 0")

        # Create a new playlist
        output_playlist_name = input("Enter the name of the new playlist: ")

        # Get all tracks in the selected playlist
        print(
            f"Getting tracks from playlist {playlists['items'][source_playlist_id]['name']}..."
        )
        source_playlist_tracks = get_playlist_tracks(
            playlists["items"][int(source_playlist_id)]["id"], sp
        )

        # print number of tracks in the playlist
        # print(f"Number of tracks in the playlist: {len(source_playlist_tracks)}")

        # Get all artists in the selected playlist
        artists = []
        for track in source_playlist_tracks:
            for artist in track["track"]["artists"]:
                artists.append(artist)

        if include_followed_artists:
            artists.extend(get_user_followed_artists(sp))

        # Remove duplicate artists and sort by name
        artists = sorted(
            list({artist["name"]: artist for artist in artists}.values()),
            key=lambda x: x["name"],
        )

        total_artists = len(artists)  # For progression tracking

        print(
            f"There are {total_artists} artists to process for a maximum of {wanted_songs_per_artist*total_artists} songs"
        )

        print(f"Creating playlist {output_playlist_name}...")
        output_playlist = create_playlist(
            output_playlist_name, spotify_client=sp, public=False
        )
    except spotipy.client.SpotifyException as e:
        if e.http_status == 429:
            try:
                retry_after = int(e.headers["Retry-After"])
            except (KeyError, ValueError):
                print("No Retry-After header found, waiting 120 seconds")
                retry_after = 120

            print(
                f"Rate limit reached while fetching artists, waiting {retry_after + 30} seconds"
            )
            time.sleep(retry_after + 30)
        else:
            print(f"A Spotify error occurred: {e}")

    # Now get all songs by the artists, and add them to a new playlist
    # Get all songs by the artists
    total_songs = []
    uris_to_add = []
    for artist in artists:
        current_artist += 1
        try:

            top_10_songs = get_artist_top_10_songs(artist, sp)
            final_artist_songs = []
            for song in top_10_songs:
                final_artist_songs.append(song)

            if wanted_songs_per_artist > 10:
                artist_songs = get_artist_songs(
                    artist,
                    sp,
                    include_groups="album",
                    progress_callback=progress_callback_album,
                )
                artist_songs.extend(
                    get_artist_songs(
                        artist,
                        sp,
                        include_groups="single",
                        progress_callback=progress_callback_single,
                    )
                )
                artist_songs = sort_songs_by_popularity(artist_songs, sp)
                final_artist_songs.extend(artist_songs)

        except spotipy.client.SpotifyException as e:
            if e.http_status == 429:
                try:
                    retry_after = int(e.headers["Retry-After"])
                except (KeyError, ValueError):
                    print("No Retry-After header found, waiting 120 seconds")
                    retry_after = 120

                print(
                    f"Rate limit reached while fetching songs for {artist['name']}, waiting {retry_after + 30} seconds"
                )
                time.sleep(retry_after + 30)
            else:
                print(f"A Spotify error occurred: {e}")

        final_artist_songs = remove_duplicate_songs(final_artist_songs)
        # keep only the wanted number of songs
        final_artist_songs = final_artist_songs[:wanted_songs_per_artist]
        artist_songs_uris = [song["uri"] for song in final_artist_songs]
        uris_to_add.extend(artist_songs_uris)
        if len(uris_to_add) > 100:
            try:
                sp.playlist_add_items(output_playlist["id"], uris_to_add[:100])
            except spotipy.client.SpotifyException as e:
                if e.http_status == 429:
                    try:
                        retry_after = int(e.headers["Retry-After"])
                    except (KeyError, ValueError):
                        print("No Retry-After header found, waiting 120 seconds")
                        retry_after = 120

                    print(
                        f"Rate limit reached while adding songs to the playlist, waiting {retry_after + 30} seconds"
                    )
                    time.sleep(retry_after + 30)
                else:
                    print(f"A Spotify error occurred: {e}")

            # remove first 100 elements
            uris_to_add = uris_to_add[100:]

        total_songs.extend(final_artist_songs)
        # print(f"Current artist: {current_artist}/{total_artists}")
        progress_callback_generic()
        show_progression()

    # add the remaining songs
    if len(uris_to_add) > 0:
        try:
            sp.playlist_add_items(output_playlist["id"], uris_to_add)
        except spotipy.client.SpotifyException as e:
            if e.http_status == 429:
                try:
                    retry_after = int(e.headers["Retry-After"])
                except (KeyError, ValueError):
                    print("No Retry-After header found, waiting 120 seconds")
                    retry_after = 120

                print(
                    f"Rate limit reached while adding songs to the playlist, waiting {retry_after + 30} seconds"
                )
                time.sleep(retry_after + 30)
            else:
                print(f"A Spotify error occurred: {e}")

    print(f"Playlist {output_playlist_name} filled with {len(total_songs)} songs")


if __name__ == "__main__":
    main()
