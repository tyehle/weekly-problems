""" A script to test the functions in mail """

import json

from mail import * # pylint: disable=W0401,W0614

def main() -> None:
    """ Creates a Gmail API service object and outputs a list of label names
        of the user's Gmail account.
    """
    service = init_service()

    out = make_message(body="Test message to send",
                       subject="Test Message",
                       recipient="tobinyehle@gmail.com")
    print("result of send:")
    print(send(service, "me", out))

    messages = list_messages(service, user_id='me')
    for msg in messages.get("messages", []):
        message = get_message(service, "me", msg["id"])
        content = get_text_content(message)

        if message["subject"] is not None and "Delete" in message["subject"]:
            print("Found a message to delete!")
            print(message["subject"])
            print("deleting message with id: " + msg["id"])
            deleted = trash(service, "me", msg["id"])
            print(deleted)

        if message["subject"] is not None and "Modify" in message["subject"]:
            print("found a modify message!")
            reply = make_reply(message, "This service is not yet implemented")
            print(reply)
            reply.fmap(lambda r: send(service, "me", r, msg["threadId"]))

        print(content)
        print(msg)
        headers = {k: message[k] for k in message.keys()}
        print("Message details:\n{}".format(json.dumps(headers, indent=2)))


if __name__ == '__main__':
    main()
