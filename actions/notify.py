# Contains
# Notify User
import hashlib
import gtk
import pynotify
from glib import GError

from actions import *

class NotifyUser(WorkerAction):
    def _get_gravatar_image(email):
        userhash = hashlib.md5(email).hexdigest()
        tf = tempfile.NamedTemporaryFile(suffix='.jpg', prefix='melisi-gravatar-', delete=False)
        d = client.downloadPage('http://www.gravatar.com/avatar/' + userhash, tf)

        return d

    def _show_notification(self, image, title, message):
        try:
            n = pynotify.Notification(title, message, image)
            n.set_urgency(pynotify.URGENCY_LOW)
            n.show()
        except GError:
            pass

    def _parse_avatar(self, result):
        # return filename
        return result.name

    def _execute(self):
        # pop notifications
        # notifications is a list of dictionaries
        # each dictionary contains
        # 'name', 'filepath', 'dirpath', 'owner', 'new'
        # all string except 'owner' which is a dictionary
        # containing at least email, username, first_name, last_name
        # 'new' is True when the file is new and false when the file is updated
        notifications = self._hub.queue.pop_notification_list()

        # if user does not want notifications, or there are no
        # notifications do nothing
        if self._hub.config_manager.config.get('main', 'desktop-notifications') == 'False' or \
               len(notifications) == 0:
            return



        # if one
        if len(notifications) == 1:
            # do something
            notification = notifications[0]

            message = "%(first_name)s %(last_name)s %(verb)s %(name)s" % ({
                'first_name': notification['owner']['first_name'],
                'last_name': notification['owner']['last_name'],
                'verb': notification['verb'],
                'name': notification['name']
                })

            d = self._hub.rest_client.get('http://www.gravatar.com/avatar/%s' % \
                                          (hashlib.md5(notification['owner']['email']).hexdigest())
                                          )
            d.addCallback(self._parse_avatar)
            d.addCallback(self._show_notification, notification['name'] , message)

        else:
            # do something else
            message = "Multiple updates from %(names)s%(others)s"
            self._show_notification(os.path.abspath("./images/icon-ok.svg"),
                                    "Updates",
                                    message % ({'names': ', '.join(set(' '.join((n['owner']['first_name'], n['owner']['last_name'])) for n in notifications[:2])),
                                                'others': ' and others' if len(set(' '.join((n['owner']['first_name'], n['owner']['last_name'])) for n in notifications)) > 2 else ''
                                                }),


                                    )
