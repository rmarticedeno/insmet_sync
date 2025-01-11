#!/usr/local/bin/python

import datetime, os
from pathlib import Path
from src import JointReport, write_bulletin, get_safe_path

now = datetime.datetime.now(datetime.timezone.utc)

day_of_month = now.strftime("%d")
hour = now.strftime("%H") + '00'

bulletin = JointReport(month_day=day_of_month, hour=hour)

folder = os.getenv('BULLETIN_DATA') or '.'

name = f'WX.{hour[:2]}'

path = get_safe_path(folder) / name

if path.exists():
    path.unlink()

write_bulletin(path.absolute(), bulletin)
    