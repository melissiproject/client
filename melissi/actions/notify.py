# Contains
# Notify User

# standard modules
import hashlib

# extra modules
import gtk
import pynotify
from glib import GError

# melissi modules
from melissi.actions import *

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
        return result.content.name

    def _execute(self):
        # init pynotify
        pynotify.init("melissi")

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
        names = set(' '.join((n['owner']['first_name'], n['owner']['last_name'])) for n in notifications[:2])

        if len(names) == 1:
            # one user made all the changes
            notification = notifications[0]
            if len(notifications) == 1:
                # do something
                title = notification['name']
                message = "%(first_name)s %(last_name)s %(verb)s %(name)s" % ({
                    'first_name': notification['owner']['first_name'],
                    'last_name': notification['owner']['last_name'],
                    'verb': notification['verb'],
                    'name': notification['name']
                    })
            else:
                message = "Updates on multiple files from %(first_name)s %(last_name)s" %\
                          notification['owner']
                title = "Updates"

            d = self._hub.rest_client.get('http://www.gravatar.com/avatar/%s' % \
                (hashlib.md5(notification['owner']['email']).hexdigest())
            )
            d.addCallback(self._parse_avatar)
            d.addCallback(self._show_notification, title, message)

        else:
            # do something else
            message = "Updates on multiple files from %(name)s%(others)s"
            others = ' and others' if len(names) > 2 else ''
            names = ', '.join(names)

            self._show_notification(os.path.abspath("./images/icon-ok.svg"),
                                    "Updates",
                                    message % ({'names': names,
                                                'others': others,
                                                }),
                                    )
