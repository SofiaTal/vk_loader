import vk_api
import os
import requests
from tqdm import tqdm
from vk_api.vk_api import VkApiMethod

USER_ID = ""
USERNAME = "Tap here username of the user whose album you want to load"  # Tap here username of the user whose album you want to load
LOGIN = "Preferably to use phone number to deal with safety"  # Preferably to use phone number to deal with safety
PASSWORD = "Your password. Don't push it :)"  # Your password. Don't push it :)
ALBUM_ID = "We need int or title here!"  # https://vk.com/album2985314_241197273 в урле такого формата то, что идет после нижнего подчеркивания - id. ВАЖНО УКАЗАТЬ НУЖНОГО ПОЛЬЗОВАТЕЛЯ, альбом ищется из альбомов пользователя
NEED_2FA_AUTH = False  # If you have 2FA - mark it as True


# Авторизация
def auth_handler():
    key = input("Enter authentication code: ")
    return key, True


def get_user_id(vk_client: VkApiMethod, username: str):
    response = vk_client.users.get(user_ids=username)
    if response:
        return response[0]["id"]

    return None


# Функция для скачивания фотографий
def download_photo(url, folder, filename) -> None:
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        try:
            with open(os.path.join(folder, filename), "wb") as out_file:
                for chunk in response.iter_content(1024):
                    out_file.write(chunk)
        except FileNotFoundError as e:
            print(f"Че-то хреново с файлом {filename}: {e}")


def download_album_photos(album, user_name, vk_client: VkApiMethod) -> None:
    album_title = album['title']
    album_folder = os.path.join(user_name, album_title)
    album_folder = album_folder.replace('"', ' ')
    os.makedirs(album_folder, exist_ok=True)

    offset = 0
    count = 100  # Максимально допустимое количество фотографий за один запрос
    while True:
        photos = vk_client.photos.get(owner_id=user_id, album_id=album['id'], extended=1, count=count, offset=offset)
        if not photos['items']:
            break

        for photo in tqdm(photos['items'], desc=f"Downloading {album_title}"):
            url = photo['sizes'][-1]['url']
            filename = f"{photo['id']}.jpg"
            download_photo(url, album_folder, filename)

        offset += count


# Скачивание фотографий из альбомов пользователя
def download_user_photos(user_id: int, vk_client: VkApiMethod, album_id_or_title: str | None = None) -> None:
    albums = vk_client.photos.getAlbums(owner_id=user_id)
    user_name = vk_client.users.get(user_ids=user_id)[0]["first_name"] + " " + vk_client.users.get(user_ids=user_id)[0]["last_name"]
    os.makedirs(user_name, exist_ok=True)

    if album_id_or_title:
        # Скачивание только указанного альбома
        for album in albums['items']:
            if album['title'] == album_id_or_title or album['id'] == int(album_id_or_title):
                download_album_photos(album, user_name=user_name, vk_client=vk_client)
                break
        else:
            print(f"Album {album_id_or_title} not found.")
    else:
        # Скачивание всех альбомов
        for album in albums['items']:
            download_album_photos(album=album, user_name=user_name, vk_client=vk_client)


# Скачивание фотографий из диалогов
def download_dialog_photos(count: int, vk_client: VkApiMethod):
    dialogs = vk_client.messages.getConversations(count=count)
    for dialog in dialogs["items"]:
        peer_id = dialog["conversation"]["peer"]["id"]
        if peer_id > 2000000000 or dialog["conversation"]["peer"]["type"] != "user":  # This is a chat
            continue

        user = vk_client.users.get(user_ids=peer_id)[0]
        dialog_folder = f"Диалог с {user['first_name']} {user['last_name']}"
        os.makedirs(dialog_folder, exist_ok=True)

        start_from = None

        while True:
            attachments = vk_client.messages.getHistoryAttachments(peer_id=peer_id, media_type='photo', count=200,
                                                            start_from=start_from)
            if not attachments['items']:
                break

            for attachment in tqdm(attachments['items'],
                                   desc=f"Downloading dialog with {user['first_name']} {user['last_name']}"):
                photo = attachment['attachment']['photo']
                url = photo['sizes'][-1]['url']
                filename = f"{photo['id']}.jpg"
                download_photo(url, dialog_folder, filename)

            start_from = attachments['next_from']


def get_albums(user_id, vk_client: VkApiMethod):
    albums = vk_client.photos.getAlbums(owner_id=user_id)
    return albums['items']


if __name__ == "__main__":
    vk_session = vk_api.VkApi(login=LOGIN, password=PASSWORD, app_id=6287487)
    if NEED_2FA_AUTH:
        vk_session.auth_handler = auth_handler

    vk_session.auth()

    vk = vk_session.get_api()

    user_id = get_user_id(vk_client=vk, username=USERNAME)
    download_user_photos(user_id=USER_ID or user_id, vk_client=vk, album_id_or_title=ALBUM_ID) # Если удалить ALBUM_ID - пройдется по всем альбомам
    download_dialog_photos(count=1, vk_client=vk)
