from dataclasses import dataclass, field
@dataclass
class Event:
    chat_id:int; user_id:int; message_id:int; chat_type:str; text:str
    user_name:str=""; username:str=""; chat_title:str=""; is_reply_to_bot:bool=False
    is_mention:bool=False
    media_type:str|None=None
    file_id:str|None=None
    file_unique_id:str|None=None
    mime_type:str|None=None
    caption:str=""
    media_meta:dict = field(default_factory=dict)
