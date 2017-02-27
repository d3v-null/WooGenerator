# -*- coding: utf-8 -*-

import logging
# from pprint import pprint
import contextlib

import npyscreen
# from npyscreen import NPSAppManaged
# from npyscreen import Form, AProductsFormctionForm
# from npyscreen import TitleText, TitleSelectOne, MultiLine, MultiLineEdit

class SyncForm(npyscreen.ActionForm):
    welcomeLines = [

    ]

    def addSingleLine(self, line):
        self.add(
            npyscreen.Textfield,
            editable=False,
            value = line
        )

    def addParagraph(self, lines):
        if lines:
            if lines[-1]:
                # pass
                lines.append('')
            for line in lines:
                self.addSingleLine(line)

    def addSimpleQuestion(self, name=None, help_str=None, default=None,
                          answers=None, indent=1):

        if answers is None:
            answers=["No", "Yes"]

        if not name:
            name=""

        if help_str:
            self.addParagraph([
                help_str
            ])

        if default is None:
            default=1

        return self.add(
            npyscreen.SelectOne,
            scroll_exit=True,
            name=name,
            values=answers,
            value=default,
            max_height=3
        )

    def create(self):
        self.addParagraph(self.welcomeLines)

class ProductsForm(SyncForm):
    # welcomeLines = [
    #     "PRODUCTS",
    #     ""
    # ]

    @contextlib.contextmanager
    def increaseIndent(self):
        self.current_indent += 1
        yield
        self.current_indent -= 1

    def create(self):
        self.current_indent = 0

        super(ProductsForm, self).create()

        self.download_master = self.addSimpleQuestion(
            name="Download Master",
            help_str="Has the Google Drive Spreadsheet Been updated recently?",
            default=1
        )

        self.generate_report = self.addSimpleQuestion(
            name="Generate Report",
            help_str="How would you like to generate a sync report? (slow)",
            default=1
        )

        self.process_specials = self.addSimpleQuestion(
            name="Process Specials",
            help_str="How would you like to process specials?",
            answers=["No Specials", "Auto Special", "All Future Specials",
                     "Override"],
            default=0
        )

        logging.info("indent pre context: %s", self.current_indent)

        with self.increaseIndent():
            logging.info("indent in context: %s", self.current_indent)
            # indent process_specials questions

        logging.info("indent post context: %s", self.current_indent)


class CustomersForm(SyncForm):
    welcomeLines = [
        "CUSTOMERS"
    ]

    def create(self):
        super(CustomersForm, self).create()

class WelcomeForm(SyncForm):
    welcomeLines = [
        # " _______ _______ __   _ _______ __   __ __   _ _______" ,
        # "    |    |_____| | \  | |______   \_/   | \  | |      " ,
        # "    |    |     | |  \_| ______|    |    |  \_| |_____ " ,

" ██████████████                                  ██████████████",
" ██          ██ ██████████████ ███████   ██████ ██          ██ ██████  ██████ ███████   ██████ ██████████████ ",
" ██████  ██████ ██          ██ ██    █  ██  ██ ██  ██████████ █  ██  █ ██    █  ██  ██ ██          ██ ",
"     ██  ██     ██  ██████  ██ ██    █ ██  ██ ██  ██          █  ██  █  ██    █ ██  ██ ██  ██████████ ",
"     ██  ██     ██  ██  ██  ██ ██  █  ███  ██ ██  ██████████   █    █   ██  █  ███  ██ ██  ██         ",
"     ██  ██     ██  ██████  ██ ██  ██  ███  ██ ██          ██    █    █    ██  ██  ███  ██ ██  ██         ",
"     ██  ██     ██          ██ ██  ███  ██  ██ ██████████  ██     █  █     ██  ███  ██  ██ ██  ██         ",
"     ██  ██     ██  ██████  ██ ██  ███  █  ██         ██  ██      ██  ██      ██  ███  █  ██ ██  ██         ",
"     ██  ██     ██  ██  ██  ██ ██  ██ █    ██         ██  ██      ██  ██      ██  ██ █    ██ ██  ██         ",
"     ██  ██     ██  ██  ██  ██ ██  ██  █    ██ ██████████  ██      ██  ██      ██  ██  █    ██ ██  ██████████ ",
"     ██  ██     ██  ██  ██  ██ ██  ██   █   ██ ██          ██      ██  ██      ██  ██   █   ██ ██          ██ ",
"     ██████     ██████  ██████ ██████    ██████ ██████████████      ██████      ██████    ██████ ██████████████ ",


        "" ,
        "Welcome to the TanSync Utility." ,
        "" ,
        "What would you like to sync?",
        ""
    ]

    helpLines = [
        "Make a selection using the arrow and enter keys, then "
    ]

    formOptions = {
        'products':'PRODUCTS',
        'customers':'CUSTOMERS'
    }

    def create(self):
        super(WelcomeForm, self).create()

        self.sync_subject = self.add(
            npyscreen.MultiLine,
            scroll_exit=True,
            name="Sync Type",
            values=self.formOptions.keys()
        )

    def afterEditing(self):
        sync_subject = (self.sync_subject.values[ self.sync_subject.value ])
        logging.info("Sync Subject Value: %s", sync_subject)
        next_form = self.formOptions.get(sync_subject)
        logging.info("setting next form to %s" , next_form)
        self.parentApp.setNextForm(next_form)

class WooGenerator(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm(
            'MAIN',
            WelcomeForm,
            name="Welcome",
        )

        self.addForm(
            'PRODUCTS',
            ProductsForm,
            name="Products"
        )

        self.addForm(
            'CUSTOMERS',
            CustomersForm,
            name='Customers'
        )

if __name__ == "__main__":
    logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)
    wgApp = WooGenerator()
    try:
        wgApp.run()
    except npyscreen.NotEnoughSpaceForWidget as e:
        print "not enough space for widget, try resizing terminal.", e

