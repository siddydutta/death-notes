from web.models import Message

# mapping of message types to human-readable representations
MESSAGE_TYPE_MAPPING = {key: value.capitalize() for key, value in Message.Type.choices}
