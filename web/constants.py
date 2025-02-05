from web.models import Message


MESSAGE_TYPE_MAPPING = {key: value.capitalize() for key, value in Message.Type.choices}
