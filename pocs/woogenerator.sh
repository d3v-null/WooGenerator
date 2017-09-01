#!/bin/bash

# bugs:
# - doesn't ask for current-special
# - doesn't print instructions when complete
# - file info should be more verbose
# - doesn't do images
# - doesn't email report

RED='\033[0;31m'
YELLOW='\033[0;33m'
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function style_prompt() {
  printf "${PURPLE}"
  printf -- "$@"
  printf "${NC}"
}

function style_info() {
  printf "${YELLOW}"
  printf "$@"
  printf "${NC}"
  printf "\n"
}

function style_warning() {
  printf "${RED}"
  printf "$@"
  printf "${NC}"
  printf "\n"
}

function style_success() {
  printf "${GREEN}"
  printf "$@"
  printf "${NC}"
  printf "\n"
}

ANSWER_TRUE=1
ANSWER_FALSE=0

function yes_like() {
  case "$1" in
    'y' | 'Y' )
      # echo "answer is answer_true"
      return $ANSWER_TRUE
      ;;
    'n' | 'N' )
      # echo "answer is answer_false"
      return $ANSWER_FALSE
      ;;
    *)
      if [[ "$2" == "$ANSWER_FALSE" ]] ; then
        # echo "default is answer_false"
        return $ANSWER_FALSE
      elif [[ "$2" == "$ANSWER_TRUE" ]] ; then
        # echo "default is answer_true"
        return $ANSWER_TRUE
      fi
  esac
}

function binary_prompt() {
  read -d '' -t 1 -n 100 discard
  question_suffix=' '
  default_answer=$ANSWER_TRUE
  if [[ ! -z "$2" ]] ; then
    yes_like "$2" $default_answer
    default_answer=$?
  fi
  # echo "default_answer is $default_answer"
  if [[ "$default_answer" == "$ANSWER_TRUE" ]] ; then
    question_suffix='(Y/n) '
  else
    question_suffix='(y/N) '
  fi
  style_prompt "$1 $question_suffix"
  read -n 1 answer
  printf '\n'
  if [[ ! -z "$answer" ]] ; then
    yes_like "$answer" $default_answer
    response=$?
    # echo "yes_like $answer $default_answer gives $response"
  else
    response=$default_answer
    # echo "response set to default_answer: $default_answer"
  fi
  # echo "response is $response"
  return $response
  # if [[ "$response" == "$ANSWER_FALSE" ]] ; then
  #   echo "response is answer_false"
  #   return $ANSWER_FALSE
  # elif [[ "$response" == "$ANSWER_TRUE" ]] ; then
  #   echo "response is answer_true"
  #   return $ANSWER_TRUE
  # fi
}


sync_subject=''
safe_defaults=false
download_report_quit=false
sync_report=false
sync_command=()

if [[ -z "$@" ]] ; then
  # echo "no args"
  style_info "########"
  style_info "Welcome to the WooGenerator interactive script"
  style_info "Type the number for the function you wish to perform. press ctrl-c to exit at any point"
  style_info " 1. Products (interactive)"
  style_info " 2. Products (safe defaults)"
  style_info " 3. Products (download, report, quit)"
  style_info " 4. Customers (interactive)"
  style_info " 5. Customer (safe defaults)"
  style_info "########"
  style_prompt "What would you like to sync? (default: 1) "
  read -n 1 sync
  printf "\n"
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
    style_warning "invalid selection, try again"
    exit
    ;;
esac

if $safe_defaults ; then echo "safe_defaults" ; fi
if $download_report_quit ; then echo "download_report_quit" ; fi


case "$sync_subject" in
  'products' )
    style_info "You have selected to sync products"
    sync_command+=("python" "source/generator.py")

    if ! $safe_defaults ; then
      binary_prompt "has the google drive product spreadsheet been updated recently?" "y"
      download_master_answer="$?"
    fi

    if [[ "$download_master_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--download-master')
    else
      sync_command+=('--skip-download-master')
    fi

    if ! $safe_defaults ; then
      binary_prompt "would you like to generate a sync report? (slow)" "y"
      sync_report_answer="$?"
    fi
    if [[ "$sync_report_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--download-slave' '--do-sync')
      sync_command+=('--do-report')
      sync_report=true
    else
      sync_command+=('--skip-download-slave' '--skip-sync')
      sync_command+=('--skip-report')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to process specials?" "n"
      specials_answer="$?"
    elif $download_report_quit ; then
      specials_answer="$ANSWER_TRUE"
    fi

    if [[ "$specials_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--do-specials')
      if ! $download_report_quit ; then
        style_prompt "what is the current special? (e.g. SP2016-11-20-) "
        read current_special
        style_info "current special is ${current_special}"
        if [[ ! -z $current_special ]]
        then
          # sync_command+=('--add-special-categories')
          sync_command+=('--current-special' "$current_special")
        fi
      fi
    else
        sync_command+=('--skip-specials')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to process categories?" "n"
      categories_answer="$?"
    elif $download_report_quit ; then
      categories_answer=$ANSWER_TRUE
    fi

    if [[ "$categories_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--do-categories')
    else
      sync_command+=('--skip-categories')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to process variations?" "n"
      variations_answer="$?"
    elif $download_report_quit ; then
      variations_answer=$ANSWER_TRUE
    fi

    if [[ "$variations_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--do-variations')
    else
      sync_command+=('--skip-variations')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to automatically update WooCommerce? (unsafe)" "n"
      update_answer="$?"
    fi
    if [[ "$update_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--update-slave')
    else
      sync_command+=('--skip-update-slave')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to perform the updates in the report flagged as problematic?" "n"
      update_problematic_answer="$?"
    fi
    if [[ "$update_problematic_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--do-problematic')
    else
      sync_command+=('--skip-problematic')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to show verbose debugging information?" "n"
      show_debug="$?"
    fi
    if [[ "$show_debug" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('-vv')
    fi

    ;;
  'customers' )
    style_info "You have selected to sync customers"
    sync_command+=("python" "source/merger.py")

    if ! $safe_defaults ; then
      binary_prompt "has the ACT database been updated recently?" "y"
      download_master_answer="$?"
    fi

    if [[ "$download_master_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--download-master')
    else
      sync_command+=('--skip-download-master')
    fi

    if ! $safe_defaults ; then
      binary_prompt "has the Wordpress database been updated recently?" "y"
      download_slave_answer="$?"
    fi

    if [[ "$download_slave_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--download-master')
    else
      sync_command+=('--skip-download-master')
    fi

    if ! $safe_defaults ; then
      binary_prompt "Do you want to do a full analysis of the data?" "n"
      do_post_answer="$?"
    fi

    if [[ "$do_post_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--do-post')
    else
      sync_command+=('--skip-post')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to automatically update Wordpress? (unsafe)" "n"
      update_answer="$?"
    fi
    if [[ "$update_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--update-slave')
    else
      sync_command+=('--skip-update-slave')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to perform the updates in the report flagged as problematic?" "n"
      update_problematic_answer="$?"
    fi
    if [[ "$update_problematic_answer" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('--do-problematic')
    else
      sync_command+=('--skip-problematic')
    fi

    if ! $safe_defaults ; then
      binary_prompt "do you want to show verbose debugging information?" "n"
      show_debug="$?"
    fi
    if [[ "$show_debug" == "$ANSWER_TRUE" ]] ; then
      sync_command+=('-vv')
    fi


    ;;
esac

style_info "running ${sync_command[*]}"

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
  exit_code="$?"

  # printf "\n\n\n\n"
  style_info "exit_code is $exit_code"
  # echo "result is $result"

  case "$exit_code" in
    "0" )
      style_success "Completed"
      break
      ;;
    "74" )
      style_warning "It looks there were problems accessing files at some point"
      style_warning "please check the missing files exist and are readable and not currently open"
      binary_prompt "were you able to fix the problems?" "y"
      try_again_answer="$?"
      if [[ "$try_again_answer" == "$ANSWER_TRUE" ]] ; then
        continue
      fi
      ;;
    "65" )
      style_warning "It looks like there are some problems in the data"
      style_warning "please fix these problems and try again"
      binary_prompt "were you able to fix the problems?" "y"
      try_again_answer="$?"
      if [[ "$try_again_answer" == "$ANSWER_TRUE" ]] ; then
        continue
      fi
      ;;
    "69" ) # connection error
      style_warning "It looks like the connection timed out."
      style_warning "please check your internet connection"
      binary_prompt "try again with larger timeout?" "y"
      try_again_answer="$?"
      if [[ "$try_again_answer" == "$ANSWER_TRUE" ]] ; then
        continue
      fi
      ;;
    *)
      style_warning "It looks like something went wrong."
      ;;
  esac
  try_again=false
  errors_present=true
done

if ! $errors_present ; then
  checklist=()
  case "$sync_subject" in
    'products' )
      style_warning "please complete the following checklist."
      checklist=(
        "syncing program did not display any errors"
      )
      if [[ "$sync_report_answer" == "$ANSWER_TRUE" ]] ; then
        checklist+=("are only products you expect to be created being created?")
      fi
      if [[ "$specials_answer" == "$ANSWER_TRUE" ]] ; then
        checklist+=("does the specials spreadsheet information look ok?")
      fi
      if [[ "$categories_answer" == "$ANSWER_TRUE" ]] ; then
        checklist+=("does the categories spreadsheet information look ok?")
      fi
      if [[ "$variations_answer" == "$ANSWER_TRUE" ]] ; then
        checklist+=("does the variations spreadsheet information look ok?")
      fi
      ;;
    'customers' )
      echo ""
      ;;
  esac

  for check in "${checklist[@]}"; do
    binary_prompt "-> $check" "y"
    no_anomalies_answer="$?"
    if [[ "$no_anomalies_answer" == "$ANSWER_FALSE" ]] ; then
      errors_present=true
      break
    fi
  done
fi

if ! $errors_present ; then
  case "$sync_subject" in
    'products' )
      style_info "once everything looks ok you can log in to the website and upload the csv files"
      style_info "see https://docs.woocommerce.com/document/product-csv-import-suite/ if you're having trouble"
      if [[ "$specials_answer" == "$ANSWER_TRUE" ]] ; then
        style_info "WooCommerce -> csv import suite -> merge products -> upload product specials spreadsheet"
        if [[ "$variations_answer" == "$ANSWER_TRUE" ]] ; then
          style_info "WooCommerce -> csv import suite -> merge variations -> upload variation specials spreadsheet"
        fi
      else
        style_info "WooCommerce -> csv import suite -> merge products -> upload product spreadsheet"
        if [[ "$variations_answer" == "$ANSWER_TRUE" ]] ; then
          style_info "WooCommerce -> csv import suite -> merge variations -> upload variations spreadsheet"
        fi
      fi
      ;;
    'customers' )
      style_info ''
      ;;
  esac

  binary_prompt "did the sync complete as expected?" "y"
  no_anomalies_answer="$?"

  if [[ "$no_anomalies_answer" == "$ANSWER_FALSE" ]] ; then
    errors_present=true
  fi
fi

if $errors_present ; then
  binary_prompt "would you like to email the developer a report of the errors?" "y"
  email_dev_answer="$?"

  if [[ "$email_dev_answer" == "$ANSWER_FALSE" ]] ; then
    style_success "all done!"
    exit
  else
    style_prompt "any additional information to report? "
    read additional_info
    style_info "creating report..."
  fi
else
  style_success "looks like everything worked"
fi
