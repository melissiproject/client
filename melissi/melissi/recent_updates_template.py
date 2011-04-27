MAIN = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<style>
 /* using http://www.colourlovers.com/palette/1505059/The_Culinary_Edge */
 /* pallete */

body {
 font-family: 'Lucida Grande',sans-serif;
 background:#f2f2f0;
 margin:10px;
 overflow:auto;
 /* background-image:url(gradientfromtop.gif); */
 /* background-repeat:repeat-x; */
}

.day {
 display: block;
 clear: both;
 text-align: left;
 font-weight: bold;
 font-size: 0.75em;
 color: #6e8778;
 margin-bottom: 20px;
 margin-top: 20px;
 border-bottom: 2px solid #eec795;
}

ol.updates {
 list-style-image: nonel
 list-style-position: outside;
 list-style-type: none;
 margin-top: 10px;
 margin-bottom: 10px;
 padding-left: 8px;
 padding-right: 8px;
}

.thumb {
 width: 35px;
 height: 35px;
}

.content {
 font-size: 0.71em;
 word-wrap: break-word;
 display: block;
 min-height: 25px;
}


li.noentries {
 font-size: 0.71em;
}

li.update {
 border-bottom: 1px solid #e6e6e6;
 padding-bottom: 5px;
 margin-top: 10px;
 min-height: 35px;
}

li:last-child {
 border-bottom: 0;
}

.content a.file {
 text-decoration: none;
 font-weight: bold;
}

.content a.email {
 text-decoration: none;
}

.meta {
 font-size: 0.65em;
 color: grey;
}

.thumb {
 float: left;
 padding-right: 10px;
}

.actions {
 float: right;
 /* right: 0; */
 /* bottom: 12px; */
 padding-right: 10px;
 font-size: 0.65em;
}

.actions a {
 text-decoration: none;
 color: grey;
}
</style>
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
   %(verb)s %(type)s <a href="file://%(fileurl)s" class="file">%(name)s</a>
   </span>
   <span class="meta">
   about %(time)s
   </span>
   <span class="actions">
   <a href="%(view_revisions_url)s">view revisions</a>
   </span>
  </span>
  </li>

"""


NO_ENTRIES = """
 <li class="noentries">
  No entries...
 </li>
"""
