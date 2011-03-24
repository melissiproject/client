MAIN = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<link href="recent-updates.css" type="text/css" rel="stylesheet" />
</head>

<div class="day">
  Today
</div>

<ol class="updates">
%(todaysentries)s
</ol>

<div class="day">
  Yesterday
</div>

<ol class="updates">
%(yesterdaysentries)s
</ol>

<div class="day">
  Older
</div>

<ol class="updates">
%(olderentries)s
</ol>

</body> </html>
"""

ENTRY = """
  <li class="update">
  <span class="thumb"><img src="http://www.gravatar.com/avatar/%(emailhash)s?s=35&d=mm" /></span>
  <span class="action-body">
   <span class="content">
   <a href="#" class="email">%(first_name)s %(last_name)s</a>
   %(verb)s %(action_type)s <a href="file://%(fileurl)s" class="file">%(name)s</a>
   </span>
   <span class="meta">
   about %(time)s
   </span>
   <span class="actions">
   view revisions
   </span>
  </span>
  </li>

"""
