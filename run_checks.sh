#!/bin/bash

source_files="interface.py jsonparse.py mail.py result.py scraper.py user.py weeklysend.py"

mypy $source_files && pylint $source_files
