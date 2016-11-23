#!/bin/bash
echo "########"
echo "Welcome to the WooGenerator interactive script"
echo " 1. Products (interactive)"
echo " 2. Products (safe defaults)"
echo " 3. Customers (interactive)"
echo " 4. Customer (safe defaults)"
echo "Type the number for the function you wish to perform. press ctrl-c to exit at any point"
echo "########"
read -p "What would you like to sync? (default: 1)" sync

arguments=('')
sync_command=''

case $sync in
  4)
    sync_command="python source/merger.py"
    ;;
  *)
    read -p "has the google drive product spreadsheet been updated recently? (Y/n)" download_master
    case $download_master in
      n)
      N)
        arguments+=('--skip-download_master')
        ;;
      *)
        arguments+=('--download-master')
    esac
    read -p "would you like to generate a sync report? (slow) (Y/n)" sync_report
    case $sync_report in
      n)
      N)
        arguments+=('--skip-download-slave', '--skip-sync')
        ;;
      *)
        arguments+=('--download-slave' '--do-sync')
    esac

    echo "You have selected to sync products"
    read -p "what is the current special? (e.g. SP2016-11-20-) " special
    sync_command="python source/generator.py"
esac

echo sync_command ${arguments[@]}
