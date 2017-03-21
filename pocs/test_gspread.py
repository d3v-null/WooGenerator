import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials

json_key = json.load(open('My Project-db965bac73b4.json'))
print json_key
scope = ['https://spreadsheets.google.com/feeds']

credentials = SignedJwtAssertionCredentials(
    json_key['client_email'], json_key['private_key'], scope)

gc = gspread.authorize(credentials)

wks_list = gc.openall()
print wks_list


# wks = gc.open_by_key("1ps0Z7CYN4D3fQWTPlKJ0cjIkU-ODwlUnZj7ww1gN3xM")
