# standard modules
import os
import hashlib
import tempfile
import urllib
import subprocess
import pynotify
import time
from glib import GError
from datetime import datetime, timedelta
import logging
log = logging.getLogger("melissilogger")

# extra modules
from twisted.web import client

WORKER_RECALL = 0.1
gravatars = {}

def append_to_filename(filename, append):
    try:
        base, ext = filename.split(".", 1)
    except ValueError:
        base = filename
        ext = ''
    base = base + " " + append
    return base + ext

def get_hash(filename=None, f=None):
    if filename:
        try:
            f = open(filename, 'rb')
        except IOError, e:
            raise e

    if f:
        hash_function = hashlib.sha256()
        while True:
            chunk = f.read(4096)
            if chunk == '': break
            hash_function.update(chunk)

        if filename:
            # we opened the file ourselves
            # so we better close it
            f.close()
        else:
            # we received file descriptor
            # we don't need to close the file
            # just rewind it
            f.seek(0)
        return unicode(hash_function.hexdigest())
    else:
        # TODO return error
        return 1

# def get_signature(filename):
#     try:
#         f = open(filename, 'rb')
#     except IOError:
#         # TODO add exception if we cannot open the file
#         if __debug__:
#             dprint("Signature exception", exception=1)
#         raise

#     signature_file = librsync.SigFile(f)
#     signature = signature_file.read()
#     return signature

# def get_delta(signature, filename):
#     ''' Get a filename and generate a delta for that file
#         Returns a file object with the delta '''
#     try:
#         f = open(filename, 'rb')
#     except IOError:
#         if __debug__:
#             dprint("Exception", filename, exception=1)
#         raise Exception("delta exception")

#     delta_file = librsync.DeltaFile(signature, f)

#     return delta_file

# def patch_file(delta, filename, hash=None):
#     # TODO using stringio means that we store delta into memory!
#     try:
#         f = open(filename, 'rb')
#     except IOError:
#         if __debug__:
#             dprint("Patch error, cannot open filename '%s'" % filename, exception=1)
#         raise Exception("Patch exception")

#     new_file = librsync.PatchedFile(f, delta)
#     tmp_file = tempfile.TemporaryFile(prefix='melisi-', suffix='.patched')
#     tmp_file.write(new_file.read())
#     tmp_file.seek(0)
#     if not hash or hash == get_hash(f=tmp_file):
#         try:
#             f = open(filename, 'wb')
#             f.write(tmp_file.read())
#             f.close()
#         except IOError:
#             raise Exception("Patch exception 2")
#     else:
#         if __debug__:
#             dprint(get_hash(f=tmp_file), hash)
#         raise Exception("Hashes don't match!")


def create_path(path):
    import os, errno
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise

# def check_keys_in_data(keys, data, exact_data=True, set_default=True):
#     """Check if keys in data exist, set default values, return data.

#     keys is a list of dictionaries. Each dictionary in the list contains at
#     least 'name'. 'name' is the key to look for in 'data'. If 'default' exists
#     is the default value to be set to the 'key' if the key is missing. If
#     'default' is missing then 'key' is considered mandatory and if not found
#     a KeyError is raised.

#     Arguments:
#     - `keys`: a list of dictionaries containing the keys to look for.
#     - `data`: the data to check for the keys
#     """
#     for key in keys:
#         if data.has_key(key['name']):
#             pass
#         else:
#             if not key.has_key('default'):
#                 # the key is mandatory, raise KeyError
#                 raise KeyError("Missing key '%s'" % key['name'])
#             else:
#                 # key is optional
#                 if set_default:
#                     #set default value
#                     data[key['name']] = key['default']

#         # check key type
#         if key.has_key('type'):
#             if not isinstance(data[key['name']], key['type']):
#                 raise KeyError("Invalid data type for key '%s'"
#                                % key['name'])


#     # now if we have more keys in data than in keys then
#     # the client submitted more data. Reject it, it may be harmful
#     if exact_data and len(keys) != len(data.keys()):
#         if __debug__:
#             for key in keys:
#                 if data.has_key(key['name']):
#                     del(data[key['name']])
#             dprint("Conflicting key", data)
#         raise KeyError("More data injected")

#     return data


def urlencode(dic):
    """
    Return a unicode aware urlencoded string and prepend a '?'
    """

    for key, value in dic.items():
        if isinstance(value, unicode):
            value = value.encode("UTF-8")
            dic[key] = value

    return '?' + urllib.urlencode(dic)

def parse_datetime(dt_string):
    try:
        return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
    except:
        log.log(5, "Error parsing date string %s" % dt_string)
        return '1970-1-1 00:00:00'

def get_localtime(dt):
    """
    Return localtime from a datetime in UTC
    """
    return dt - (datetime.utcnow() - datetime.now())

def open_file(path):
    """
    Open 'path' in the user's system configured program
    """
    subprocess.Popen(["xdg-open", "%s" % path])


# from django.utils
# enhanced
### start
def ungettext(one, many, howmany):
    if howmany == 1:
        return one
    else:
        return many

def ugettext(foo):
    return foo

def timesince(d, now=None):
    """
    Takes two datetime objects and returns the time between d and now
    as a nicely formatted string, e.g. "10 minutes".  If d occurs after now,
    then "0 minutes" is returned.

    Units used are years, months, weeks, days, hours, and minutes.
    Seconds and microseconds are ignored.  Up to two adjacent units will be
    displayed.  For example, "2 weeks, 3 days" and "1 year, 3 months" are
    possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

    Adapted from http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    chunks = (
      (60 * 60 * 24 * 365, lambda n: ungettext('year', 'years', n)),
      (60 * 60 * 24 * 30, lambda n: ungettext('month', 'months', n)),
      (60 * 60 * 24 * 7, lambda n : ungettext('week', 'weeks', n)),
      (60 * 60 * 24, lambda n : ungettext('day', 'days', n)),
      (60 * 60, lambda n: ungettext('hour', 'hours', n)),
      (60, lambda n: ungettext('minute', 'minutes', n))
    )
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime):
        now = datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.now()

    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        # return u'0 ' + ugettext('minutes')
        return u'now'

    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break

    if count == 0 and name(count) == u'minutes':
        s = ugettext('now')
    else:
        s = ugettext('%(number)d %(type)s') % {'number': count, 'type': name(count)}
        if i + 1 < len(chunks):
            # Now get the second item
            seconds2, name2 = chunks[i + 1]
            count2 = (since - (seconds * count)) // seconds2
            if count2 != 0:
                s += ugettext(', %(number)d %(type)s') % {'number': count2, 'type': name2(count2)}
        s += ugettext(' ago')
    return s

### end
