#!/bin/bash

sync_subject=''
sync_command=()

if [[ -z "$@" ]] ; then
  # echo "no args"
  echo "########"
  echo "Welcome to the WooGenerator interactive script"
  echo "Type the number for the function you wish to perform. press ctrl-c to exit at any point"
  echo " 1. Products (interactive)"
  echo " 2. Products (safe defaults)"
  echo " 3. Products (download, report, quit)"
  echo " 4. Customers (interactive)"
  echo " 5. Customer (safe defaults)"
  echo "########"
  read -p "What would you like to sync? (default: 1) " sync
else
  # echo "args $@"
  sync="$1"
fi

case "$sync" in
  1 | '')
    sync_subject='products'
    safe_defaults=false
    ;;
  2)
    sync_subject='products'
    safe_defaults=true
    ;;
  3)
    sync_subject='products'
    safe_defaults=true
    download_report_quit=true
    ;;
  4)
    sync_subject='customers'
    safe_defaults=false
    ;;
  5)
    sync_subject='customers'
    safe_defaults=true
    ;;
  *)
    echo "invalid selection, try again"
    exit
    ;;
esac

case "$sync_subject" in
  'products' )
    echo "You have selected to sync products"
    sync_command+=("python" "source/generator.py")

    if ! $safe_defaults ; then
      read -p "has the google drive product spreadsheet been updated recently? (Y/n) " download_master
    fi

    case "$download_master" in
      "n" | "N" )
        sync_command+=('--skip-download-master')
        ;;
      *)
        sync_command+=('--download-master')
    esac

    if ! $safe_defaults ; then
      read -p "would you like to generate a sync report? (slow) (Y/n) " sync_report
    fi
    case "$sync_report" in
      "n" | "N" )
        sync_command+=('--skip-download-slave' '--skip-sync')
        sync_command+=('--skip-report')
        ;;
      *)
        sync_command+=('--download-slave' '--do-sync')
        sync_command+=('--show-report')
        ;;
    esac

    if ! $safe_defaults ; then
      read -p "do you want to process specials? (y/N) " specials
    fi

    case "$specials" in
      "y" | "Y" )
        sync_command+=('--do-specials')
        read -p "what is the current special? (e.g. SP2016-11-20-) " current_special
        if [ -z $current_special ]
        then
          sync_command+=('--add-special-categories')
          sync_command+=('--current-special' "$current_special")
        fi
        ;;
      *)
        sync_command+=('--skip-specials')
    esac

    if ! $safe_defaults ; then
      read -p "do you want to process categories? (y/N) " categories
    fi

    case "$categories" in
      "y" | "Y" )
        sync_command+=('--do-categories')
        ;;
      *)
        sync_command+=('--skip-categories')
    esac

    # auto update not finished yet
    sync_command+=('--skip-update-slave')
    # read -p "do you want to automatically update WooCommerce? (unsafe) (y/N) " update
    #
    # case "$update" in
    #   "y" | "Y" )
    #     sync_command+=('--update-slave')
    #     ;;
    #   *)
    #     sync_command+=('--skip-update-slave')
    # esac
    #
    # read -p "do you want to perform the updates in the report flagged as problematic? (y/N) " update_problematic
    #
    # case "$update_problematic" in
    #   "y" | "Y" )
    #     sync_command+=('--update-problematic')
    #     ;;
    #   *)
    #     sync_command+=('--skip-update-problematic')
    # esac
    ;;
  'customers' )
    echo "You have selected to sync customers"
    sync_command+=("python" "source/merger.py")
    ;;
esac

echo "running" ${sync_command[@]}

try_again=true
errors_present=false

while $try_again ; do
  #this is just some bash trickery so i can get the output of the program and the exit code

  exec 5>&1
  result=$(
    set -o pipefail
    exec "${sync_command[@]}" | tee >(cat - >&5)
  )
  # result=$("${sync_command[@]}" | tee >(cat - >&5))
  exit_code=$?

  # printf "\n\n\n\n"
  # echo "exit_code is $exit_code"
  # echo "result is $result"

  case "$exit_code" in
    0 )
      echo "Completed"
      try_again=false
      ;;
    * )
      errors_present=true
      echo "It looks like something went wrong."
      echo "if there was a connection error you can try again."
      echo "otherwise an report can be emailed to the developer."
      read -p "try again? (y/N) " try_again
      case "$try_again" in
        'y' | 'Y' )
          try_again=true
          ;;
        *)
          try_again=false
          ;;
      esac
      ;;
  esac
done

if ! $errors_present ; then
  checklist = ()
  case "$sync_subject" in
    'products' )
      echo "please check the report files and the generated csv files."
      checklist = (
        "syncing program did not display any errors"
        "only products you expect to be created are being created"
      )
      ;;
    'customers' )
      echo ""
      ;;
  esac

  for check in "${checklist[@]}"; do
    read -p "-> $check (Y/n) " no_anomalies
    case "$no_anomalies" in
      'n' | 'N' )
        errors_present=true
        break
        ;;
    esac
  done
fi

if ! $errors_present ; then
  case "$sync_subject" in
    'products' )
      echo "once everything looks ok you can log in to the website and upload the csv files"
      echo "see https://docs.woocommerce.com/document/product-csv-import-suite/ if you're having trouble"
      echo "WooCommerce -> csv import suite -> merge products"
      echo "WooCommerce -> csv import suite -> merge variations"
      ;;
    'customers' )
      echo ''
      ;;
  esac

  read -p "did the sync complete as expected? (Y/n) " no_anomalies
  case "$no_anomalies" in
    'n' | 'N' )
      errors_present=true
      ;;
  esac
fi

if $errors_present ; then
  read -p "would you like to email the developer a report of the errors? (Y/n) " email_dev
  case "$email_dev" in
    'n' | 'N' )
      echo "all done!"
      exit
      ;;
    *)
      echo "creating report..."
  esac
fi
