import asyncio 
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from info import ADMINS, CHANNELS
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time
import time

lock = asyncio.Lock()

# ✅ ALLOWED MIME TYPES (NEW)
ALLOWED_MIME_TYPES = [
    # 🎥 Videos
    'video/mp4',
    'video/x-matroska',

    # 🎵 Music
    'audio/mpeg',
    'audio/mp3',
    'audio/ogg',
    'audio/wav',

    # 📄 Documents
    'application/pdf',

    # 🗜 Archives
    'application/zip',
    'application/x-rar-compressed',
    'application/x-7z-compressed'
]

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    _, ident, chat, lst_msg_id, skip = query.data.split("#")
    if ident == 'yes':
        msg = query.message
        await msg.edit("<b>ɪɴᴅᴇxɪɴɢ sᴛᴀʀᴛᴇᴅ...</b>")
        try:
            chat = int(chat)
        except:
            chat = chat
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip))
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("ᴛʀʏɪɴɢ ᴛᴏ ᴄᴀɴᴄᴇʟ ɪɴᴅᴇxɪɴɢ...")

@Client.on_message(filters.command('index') & filters.private & filters.incoming & filters.user(ADMINS))
async def send_for_index(bot, message):
    if lock.locked():
        return await message.reply('ᴡᴀɪᴛ ᴜɴᴛɪʟ ᴘʀᴇᴠɪᴏᴜs ᴘʀᴏᴄᴇss ᴄᴏᴍᴘʟᴇᴛᴇ.')
    i = await message.reply("ꜰᴏʀᴡᴀʀᴅ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ᴏʀ sᴇɴᴅ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await i.delete()

    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except:
            return await message.reply('ɪɴᴠᴀʟɪᴅ ᴍᴇssᴀɢᴇ ʟɪɴᴋ!')
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.username or msg.forward_from_chat.id
    else:
        return await message.reply('ᴛʜɪs ɪs ɴᴏᴛ ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇ ᴏʀ ʟɪɴᴋ.')

    chat = await bot.get_chat(chat_id)
    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("ɪ ᴄᴀɴ ɪɴᴅᴇx ᴏɴʟʏ ᴄʜᴀɴɴᴇʟs.")

    s = await message.reply("sᴇɴᴅ sᴋɪᴘ ᴍᴇssᴀɢᴇ ɴᴜᴍʙᴇʀ.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await s.delete()

    try:
        skip = int(msg.text)
    except:
        return await message.reply("ɴᴜᴍʙᴇʀ ɪs ɪɴᴠᴀʟɪᴅ.")

    buttons = [[
        InlineKeyboardButton('ʏᴇs', callback_data=f'index#yes#{chat_id}#{last_msg_id}#{skip}')
    ],[
        InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close_data')
    ]]
    await message.reply(
        f'ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɪɴᴅᴇx {chat.title}?\nᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs: <code>{last_msg_id}</code>',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def index_files_to_db(lst_msg_id, chat, msg, bot, skip):
    start_time = time.time()
    total_files = duplicate = errors = deleted = no_media = unsupported = 0
    current = skip

    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                if temp.CANCEL:
                    temp.CANCEL = False
                    return await msg.edit("ɪɴᴅᴇxɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ.")

                current += 1

                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue

                media = getattr(message, message.media.value, None)
                if not media or not media.mime_type:
                    unsupported += 1
                    continue

                # ✅ UPDATED MIME CHECK
                if media.mime_type not in ALLOWED_MIME_TYPES:
                    unsupported += 1
                    continue

                media.caption = message.caption
                sts = await save_file(media)

                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                else:
                    errors += 1

        except FloodWait as e:
            await asyncio.sleep(e.x)
        except Exception as e:
            await msg.reply(f'ɪɴᴅᴇx ᴄᴀɴᴄᴇʟᴇᴅ - {e}')
        else:
            time_taken = get_readable_time(time.time() - start_time)
            await msg.edit(
                f'✅ sᴀᴠᴇᴅ <code>{total_files}</code> ꜰɪʟᴇs\n'
                f'⏱ ᴛɪᴍᴇ: {time_taken}\n'
                f'📄 ᴅᴜᴘʟɪᴄᴀᴛᴇs: <code>{duplicate}</code>\n'
                f'❌ ᴇʀʀᴏʀs: <code>{errors}</code>'
            )
